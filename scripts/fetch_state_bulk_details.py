#!/usr/bin/env python3
"""Per-bill DETAIL JSON for the KnowUS Bills tab, for every state whose list snapshot came from Open States.

usage: fetch_state_bulk_details.py [out_dir] [snapshot_dir] [--only=OH,PA] [--dump=URL]

Source: Open States' free public monthly PostgreSQL dump
  https://data.openstates.org/postgres/monthly/YYYY-MM-public.pgdump   (no key; ~10.8 GB)
It is NOT downloaded. The dump is pg_dump "custom" format: its table of contents (first ~15 KB) records the byte offset
of every table's data, so this script reads the TOC with one HTTP Range request and then streams ONLY the tables it
needs (bill, action, sponsorship, abstract, version(+link), document(+link), vote event, vote count, action related
entity, person, session, jurisdiction, organization; ~2 GB of compressed ranges) straight through zlib, keeping only
rows for bills in the list snapshots. Nothing big touches the disk. Takes ~2-3 minutes on a fast link.

Bills newer than the dump (it is cut on the 1st of each month) fall back to the list snapshot row (title, sponsor,
latest action). Where the snapshot's latest action is newer than the dump's last action it is added on top.
Never invents values: null / [] where the source has nothing.

Output layout matches scripts/fetch_bill_details.py (the format the site reads at data/bills/detail/):
  <out_dir>/<XX>-<k>.json  {"jurisdiction","generatedAt","bills":{id: record}}  k = bucket(id, chunks)
  <out_dir>/meta.json      {"generatedAt", "jurisdictions": {XX: {chunks,count,withSummary,withActions,withCosponsors,source,generatedAt,...}}}
Record fields: id number title summary summarySource introduced sponsor cosponsors cosponsorCount committees actions
law policyArea url textUrl  + (new, optional) versions votes documents dataAsOf.
"""
import sys, os, re, json, glob, zlib, datetime, time, math
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_openstates as FO          # same bill-id rules the list snapshots used
from fetch_bill_details import bucket, clean, tidy_actions, base_record, now

UA = {"User-Agent": "KnowUS-data/1.0 (+https://knowus.sites.tab.bot)"}
BILLS_PER_CHUNK = 12

# ------------------------------------------------------------------ pg_dump custom-format reader (HTTP ranges)
class _R:
    def __init__(s, b, p=0): s.b = b; s.p = p
    def byte(s): v = s.b[s.p]; s.p += 1; return v
    def int(s):
        sign = s.byte(); v = int.from_bytes(s.b[s.p:s.p + s.isz], "little"); s.p += s.isz; return -v if sign else v
    def str(s):
        n = s.int()
        if n < 0: return None
        v = s.b[s.p:s.p + n].decode("utf-8", "replace"); s.p += n; return v
    def off(s):
        f = s.byte(); v = int.from_bytes(s.b[s.p:s.p + s.osz], "little"); s.p += s.osz; return f, v

class Dump:
    def __init__(self, url):
        self.url = url
        h = requests.head(url, headers=UA, timeout=60); h.raise_for_status()
        self.total = int(h.headers["content-length"]); self.last_modified = h.headers.get("last-modified")
        head = requests.get(url, headers=dict(UA, Range="bytes=0-2000000"), timeout=120).content
        assert head[:5] == b"PGDMP", "not a pg_dump custom archive"
        r = _R(head, 5); vmaj, vmin, vrev, isz, osz, fmt = [r.byte() for _ in range(6)]
        r.isz, r.osz = isz, osz
        assert (vmaj, vmin) == (1, 14) and fmt == 1, "archive version %d.%d fmt %d not handled" % (vmaj, vmin, fmt)
        r.int(); [r.int() for _ in range(7)]; r.str(); r.str(); r.str()
        toc = []
        for _ in range(r.int()):
            e = {"id": r.int()}; r.int(); r.str(); r.str(); e["tag"] = r.str(); e["desc"] = r.str(); r.int()
            r.str(); r.str(); e["copy"] = r.str(); r.str(); r.str(); r.str(); r.str(); r.str()
            while r.str() is not None: pass
            e["flag"], e["off"] = r.off(); toc.append(e)
        data = sorted([e for e in toc if e["desc"] == "TABLE DATA" and e["flag"] == 2], key=lambda e: e["off"])
        for i, e in enumerate(data):
            e["size"] = (data[i + 1]["off"] if i + 1 < len(data) else self.total) - e["off"]
        self.t = {e["tag"]: e for e in data}

    def cols(self, tag):
        c = self.t[tag]["copy"]; return [x.strip().strip('"') for x in c[c.index("(") + 1:c.index(")")].split(",")]

    def lines(self, tag):
        e = self.t[tag]
        with requests.get(self.url, headers=dict(UA, Range="bytes=%d-%d" % (e["off"], e["off"] + e["size"] - 1)),
                          stream=True, timeout=180) as resp:
            resp.raise_for_status()
            it = resp.iter_content(1 << 20); buf = bytearray(); p = 0
            def fill(n):
                nonlocal buf, p
                while len(buf) - p < n:
                    c = next(it, None)
                    if c is None: return False
                    buf = buf[p:] + c; p = 0
                return True
            fill(6); assert buf[0] == 1; p += 6          # block type BLK_DATA + dump id
            d = zlib.decompressobj(); tail = b""
            while fill(5):
                L = int.from_bytes(buf[p + 1:p + 5], "little"); p += 5
                if L == 0: break
                fill(L); out = d.decompress(bytes(buf[p:p + L])); p += L
                while d.unused_data:
                    u = d.unused_data; d = zlib.decompressobj(); out += d.decompress(u)
                parts = (tail + out).split(b"\n"); tail = parts.pop()
                yield from parts
            yield from [l for l in (tail + d.flush()).split(b"\n") if l]

    _esc = re.compile(r"\\(.)")
    @classmethod
    def unesc(cls, v):
        if v == "\\N": return None
        if "\\" not in v: return v
        return cls._esc.sub(lambda m: {"t": "\t", "n": "\n", "r": "\r", "\\": "\\", "b": "\b", "f": "\f", "v": "\v"}.get(m.group(1), m.group(1)), v)

    def rows(self, tag, key=None, keys=None, sel=None):
        cs = self.cols(tag); idx = {c: i for i, c in enumerate(cs)}; sel = sel or cs; n = len(cs); ki = idx[key] if key else None
        out = []
        for ln in self.lines(tag):
            if not ln or ln == b"\\.": continue
            f = ln.decode("utf-8", "replace").split("\t")
            if len(f) != n: continue
            if ki is not None and f[ki] not in keys: continue
            out.append({c: self.unesc(f[idx[c]]) for c in sel})
        return out

# ------------------------------------------------------------------ helpers
def latest_dump_url():
    d = datetime.date.today().replace(day=1)
    for _ in range(4):
        u = "https://data.openstates.org/postgres/monthly/%s-public.pgdump" % d.strftime("%Y-%m")
        try:
            if requests.head(u, headers=UA, timeout=30).status_code == 200: return u
        except requests.RequestException: pass
        d = (d - datetime.timedelta(days=1)).replace(day=1)
    raise RuntimeError("no monthly Open States dump found")

PARTY = {"Republican": "R", "Democratic": "D", "Democrat": "D", "Independent": "I", "Libertarian": "L", "Green": "G"}
def party(p): return (PARTY.get(p, p) if p else None) or None

def norm(s): return re.sub(r"[^A-Z0-9]", "", (s or "").upper())

def pgarray(s):
    """postgres text[] literal -> list"""
    if not s or s in ("{}",): return []
    s = s[1:-1]; out = []; cur = ""; q = False; i = 0
    while i < len(s):
        c = s[i]
        if c == '"': q = not q
        elif c == "\\" and q: i += 1; cur += s[i]
        elif c == "," and not q: out.append(cur); cur = ""
        else: cur += c
        i += 1
    out.append(cur)
    return [x for x in out if x and x != "NULL"]

def jload(s, d):
    try: return json.loads(s) if s else d
    except ValueError: return d

def chamber_of(org, orgs, ab):
    o = orgs.get(org) if org else None
    if not o: return None
    c = o["classification"]
    if c == "upper": return "Senate"
    if c == "lower": return "House" if ab not in ("CA", "NV", "NJ", "NY", "WI") else {"CA": "Assembly", "NV": "Assembly", "NJ": "Assembly", "NY": "Assembly", "WI": "Assembly"}[ab]
    if c == "legislature": return {"DC": "Council", "NE": "Legislature"}.get(ab)   # joint/whole-legislature actions in bicameral states: no chamber
    if c == "executive": return "Governor" if ab != "DC" else "Mayor"
    return clean(o["name"], 60)

LAW_CLASSES = {"became-law", "executive-signature"}
LAW_TEXT = re.compile(FO.PASSED_TEXT.pattern + r"|\bveto override\b.*\bchapter \d+|\blaw without (the )?governor'?s? signature\b|\bbecame effective without\b|\benacted without (the )?(mayor|governor)'?s? signature\b", re.I)
VETO_OVERRIDE_LAW = re.compile(r"\bveto override\b.*\bchapter \d+", re.I)   # e.g. MD "Gubernatorial Veto Override ... - Chapter 880"
NOT_LAW_TEXT = FO.NOT_PASSED_TEXT   # same rule the list snapshots used (became-law / executive-signature or official law text)

LINK_PREF = {"text/html": 0, "application/pdf": 1}
def best_link(links):
    links = [l for l in links if (l.get("url") or "").startswith("http")]
    if not links: return None
    links.sort(key=lambda l: (LINK_PREF.get(l.get("media_type"), 5), 0 if l["url"].startswith("https") else 1))
    return links[0]

def fmt_type(mt):
    return {"application/pdf": "PDF", "text/html": "HTML", "text/xml": "XML", "application/msword": "Word",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word"}.get(mt or "", None)

# ------------------------------------------------------------------ main
def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_dir = args[0] if args else "/home/user/tab/files/knowus-backend/state-details-out"
    snap = args[1] if len(args) > 1 else "/home/user/tab/files/knowus-backend/openstates-snapshot"
    only = None; url = None
    for a in sys.argv[1:]:
        if a.startswith("--only="): only = set(a.split("=", 1)[1].upper().split(","))
        if a.startswith("--dump="): url = a.split("=", 1)[1]
    url = url or latest_dump_url()
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    D = Dump(url); print("dump", url, D.last_modified, "%d tables" % len(D.t), flush=True)
    dump_date = datetime.datetime.strptime(D.last_modified, "%a, %d %b %Y %H:%M:%S GMT").date().isoformat() if D.last_modified else None

    # list snapshots
    snap_bills = {}; snap_meta = {}
    for f in sorted(glob.glob(os.path.join(snap, "[A-Z][A-Z].json"))):
        ab = os.path.basename(f)[:2]
        if only and ab not in only: continue
        j = json.load(open(f)); snap_meta[ab] = j
        for b in j["bills"]: snap_bills[b["id"]] = (ab, b)
    print("snapshot bills", len(snap_bills), "in", len(snap_meta), "jurisdictions", flush=True)

    juris = D.rows("opencivicdata_jurisdiction", sel=["id", "name"])
    jid = {}
    for j in juris:
        m = re.fullmatch(r"ocd-jurisdiction/country:us/(state|district):([a-z]{2})/government", j["id"])
        if m: jid[m.group(2).upper()] = j["id"]
    ab_of = {v: k for k, v in jid.items()}
    sessions = {s["id"]: s for s in D.rows("opencivicdata_legislativesession")}
    orgs = {o["id"]: o for o in D.rows("opencivicdata_organization", sel=["id", "name", "classification", "jurisdiction_id"])}
    names = {}
    for s in sessions.values():
        ab = ab_of.get(s["jurisdiction_id"])
        if ab: names["%s|%s" % (FO.STATES.get(ab), s["identifier"])] = {"name": s["name"], "start": (s["start_date"] or "")[:4] or None, "cls": s["classification"]}
    want_j = {jid[ab] for ab in snap_meta if ab in jid}
    sess_ok = {sid for sid, s in sessions.items() if s["jurisdiction_id"] in want_j}

    bills = {}
    for r in D.rows("opencivicdata_bill", key="legislative_session_id", keys=sess_ok,
                    sel=["id", "identifier", "title", "subject", "from_organization_id", "legislative_session_id", "first_action_date", "citations"]):
        s = sessions[r["legislative_session_id"]]; ab = ab_of[s["jurisdiction_id"]]
        oid = FO.bill_id(ab, s["identifier"], r["identifier"], names)
        if oid in snap_bills: r["_oid"] = oid; r["_ab"] = ab; bills[r["id"]] = r
    B = set(bills); print("matched", len(B), "bills in the dump", flush=True)

    jobs = [("opencivicdata_billaction", "bill_id", None), ("opencivicdata_billsponsorship", "bill_id", None),
            ("opencivicdata_billabstract", "bill_id", None), ("opencivicdata_billversion", "bill_id", ["id", "note", "date", "bill_id"]),
            ("opencivicdata_billdocument", "bill_id", ["id", "note", "date", "bill_id"]),
            ("opencivicdata_voteevent", "bill_id", ["id", "motion_text", "start_date", "result", "bill_id", "organization_id", "order"])]
    T = {}
    with ThreadPoolExecutor(len(jobs)) as ex:
        for tag, res in zip([j[0] for j in jobs], ex.map(lambda j: D.rows(j[0], key=j[1], keys=B, sel=j[2]), jobs)): T[tag] = res
    acts_ids = {a["id"] for a in T["opencivicdata_billaction"]}
    jobs2 = [("opencivicdata_billversionlink", "version_id", {v["id"] for v in T["opencivicdata_billversion"]}),
             ("opencivicdata_billdocumentlink", "document_id", {v["id"] for v in T["opencivicdata_billdocument"]}),
             ("opencivicdata_votecount", "vote_event_id", {v["id"] for v in T["opencivicdata_voteevent"]}),
             ("opencivicdata_billactionrelatedentity", "action_id", acts_ids),
             ("opencivicdata_person", "id", {s["person_id"] for s in T["opencivicdata_billsponsorship"] if s["person_id"]})]
    with ThreadPoolExecutor(len(jobs2)) as ex:
        for tag, res in zip([j[0] for j in jobs2], ex.map(lambda j: D.rows(j[0], key=j[1], keys=j[2],
                            sel=["id", "name", "primary_party", "current_jurisdiction_id", "current_role"] if j[0].endswith("person") else None), jobs2)): T[tag] = res
    print("streamed in %.0fs" % (time.time() - t0), {k: len(v) for k, v in T.items()}, flush=True)

    by = lambda tag, k: (lambda d: [d[r[k]].append(r) for r in T[tag]] and d or d)(defaultdict(list))
    acts, spons, abss, vers, docs, votes = (by("opencivicdata_billaction", "bill_id"), by("opencivicdata_billsponsorship", "bill_id"),
        by("opencivicdata_billabstract", "bill_id"), by("opencivicdata_billversion", "bill_id"), by("opencivicdata_billdocument", "bill_id"),
        by("opencivicdata_voteevent", "bill_id"))
    vlinks, dlinks, vcounts, rel = (by("opencivicdata_billversionlink", "version_id"), by("opencivicdata_billdocumentlink", "document_id"),
        by("opencivicdata_votecount", "vote_event_id"), by("opencivicdata_billactionrelatedentity", "action_id"))
    people = {p["id"]: p for p in T["opencivicdata_person"]}

    def person_bits(sp, ab):
        p = people.get(sp.get("person_id")) if sp.get("person_id") else None
        pty = party(p["primary_party"]) if p else None
        dist = None
        if p and p.get("current_jurisdiction_id") == jid.get(ab):
            d = jload(p.get("current_role"), {}).get("district")
            dist = str(d) if d not in (None, "") else None
        return pty, dist

    recs = {}
    for bid, r in bills.items():
        ab, sb = snap_bills[r["_oid"]][0], snap_bills[r["_oid"]][1]
        # actions
        A = []
        for a in sorted(acts.get(bid, []), key=lambda a: ((a["date"] or "")[:10], float(a["order"] or 0))):
            A.append({"date": (a["date"] or "")[:10] or None, "text": clean(a["description"], 600), "chamber": chamber_of(a["organization_id"], orgs, ab)})
        lastd = max([a["date"] for a in A if a["date"]] or [""]); dump_last = lastd
        if sb.get("date") and sb.get("status") and sb["date"] > lastd:
            A.append({"date": sb["date"], "text": clean(sb["status"], 600), "chamber": sb.get("chamber")})
        A = tidy_actions(A)
        # committees (organizations named on actions: referrals, reports)
        com = []
        for a in sorted(acts.get(bid, []), key=lambda a: ((a["date"] or "")[:10], float(a["order"] or 0))):
            ch = chamber_of(a["organization_id"], orgs, ab)
            for e in rel.get(a["id"], []):
                nm = clean(e["name"], 120)
                if not nm: continue
                if ch and ch not in ("Legislature", "Council", "Governor", "Mayor") and not nm.lower().startswith(ch.lower()) and "committee" not in nm.lower():
                    nm = "%s %s" % (ch, nm)
                if nm.lower() not in [c.lower() for c in com]: com.append(nm)
        # sponsors
        S = spons.get(bid, [])
        prim = [s for s in S if s["primary"] == "t"] or [s for s in S if s["classification"] in ("primary", "author", "sponsor")]
        sp = None
        if prim:
            pty, dist = person_bits(prim[0], ab)
            sp = {"name": clean(prim[0]["name"], 120), "party": pty, "state": ab, "district": dist}
        elif sb.get("sponsor"):
            sp = {"name": sb["sponsor"], "party": None, "state": ab, "district": None}
        cos = []
        for s in S:
            if prim and s is prim[0]: continue
            pty, dist = person_bits(s, ab)
            c = {"name": clean(s["name"], 120), "party": pty, "state": ab, "date": None, "withdrawn": False}
            role = s["classification"] if s["classification"] not in ("cosponsor",) else None
            if s["primary"] == "t" or role: c["role"] = "Primary sponsor" if s["primary"] == "t" else role.capitalize()
            if c["name"] and c["name"] not in [x["name"] for x in cos]: cos.append(c)
        # summary
        ab_rows = [x for x in abss.get(bid, []) if clean(x["abstract"])]
        ab_rows.sort(key=lambda x: (0 if re.search(r"summary|digest|synopsis", x["note"] or "", re.I) else 1, -len(x["abstract"] or "")))
        summ = clean(ab_rows[0]["abstract"], 4000) if ab_rows else None
        title = clean(r["title"]) or sb.get("title")
        if summ and title and norm(summ) == norm(title): summ = None    # an abstract that only repeats the title adds nothing
        ssrc = None
        if summ:
            note = clean(ab_rows[0]["note"], 60)
            ssrc = "%s legislature%s (via Open States)" % (FO.STATES.get(ab, ab), (", " + note) if note else "")
        # versions
        V = []
        for v in sorted(vers.get(bid, []), key=lambda v: (v["date"] or "")[:10]):   # stable: undated versions keep the source's order
            L = best_link(vlinks.get(v["id"], []))
            if not L: continue
            V.append({"label": clean(v["note"], 80) or "Bill text", "date": (v["date"] or "")[:10] or None, "url": L["url"], "type": fmt_type(L.get("media_type"))})
        Dc = []
        for d in sorted(docs.get(bid, []), key=lambda d: (d["date"] or "")[:10]):
            L = best_link(dlinks.get(d["id"], []))
            if L: Dc.append({"label": clean(d["note"], 80) or "Document", "date": (d["date"] or "")[:10] or None, "url": L["url"], "type": fmt_type(L.get("media_type"))})
        # votes
        VO = []
        for ve in votes.get(bid, []):
            cnt = {}
            for c in vcounts.get(ve["id"], []):
                try: n = int(c["value"])
                except (TypeError, ValueError): continue
                if n or c["option"] in ("yes", "no"): cnt[c["option"]] = cnt.get(c["option"], 0) + n
            VO.append({"date": (ve["start_date"] or "")[:10] or None, "motion": clean(ve["motion_text"], 200), "result": ve["result"],
                       "chamber": chamber_of(ve["organization_id"], orgs, ab), "counts": cnt})
        VO.sort(key=lambda v: v["date"] or "", reverse=True)
        # law / topics
        cits = [c for c in jload(r["citations"], []) if c.get("citation")]
        chap = [c for c in cits if c.get("citation_type") in ("chapter", "final")]
        law = ("%s%s" % (chap[0]["citation"], (" (" + chap[0]["publication"] + ")") if chap[0].get("publication") else "")) if chap else (sb.get("law") or None)
        subj = pgarray(r["subject"])
        txt = [v for v in V if not re.search(r"amend|comparison|fiscal|summary|analysis", v["label"], re.I)] or V
        tx = (txt[-1]["url"] if txt else None)   # newest bill text (not an amendment) for the existing "Full text" button
        # enacted? (steer 2026-11-05: true only if it became law / was signed — not one chamber's "passage")
        enacted = False; how = None
        for a in acts.get(bid, []):
            cl = set(pgarray(a["classification"])); t = a["description"] or ""
            if cl & LAW_CLASSES: enacted = True; how = "classified " + ",".join(sorted(cl & LAW_CLASSES)); break
            if (LAW_TEXT.search(t) and not NOT_LAW_TEXT.search(t)) or VETO_OVERRIDE_LAW.search(t): enacted = True; how = "action text: " + clean(t, 80); break
        recs[r["_oid"]] = {"id": r["_oid"], "passed": enacted, "_how": how, "_dl": dump_last, "number": sb.get("number") or r["identifier"], "title": title,
            "summary": summ, "summarySource": ssrc, "introduced": (r["first_action_date"] or "")[:10] or sb.get("introduced"),
            "sponsor": sp, "cosponsors": cos[:150], "cosponsorCount": len(cos), "committees": com[:12], "actions": A,
            "law": law, "policyArea": ", ".join(subj[:3]) if subj else None, "url": sb.get("url"), "textUrl": tx,
            "versions": V[-25:][::-1], "votes": VO[:20], "documents": Dc[-10:][::-1], "dataAsOf": dump_date}

    # write per jurisdiction
    gen = now()
    mp = os.path.join(out_dir, "meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {"jurisdictions": {}}
    meta["generatedAt"] = gen
    corr = {}; corr_n = Counter(); corr_log = []
    for ab, sm in sorted(snap_meta.items()):
        for b in sm["bills"]:
            x = recs.get(b["id"])
            if x is None: continue
            lastd = x["_dl"]
            if b.get("passed") and not x["passed"] and (b.get("date") or "") > lastd:
                x["passed"] = True; continue    # snapshot saw newer actions than the monthly export: keep its flag
            if bool(b.get("passed")) != x["passed"]:
                corr[b["id"]] = x["passed"]; corr_n[(ab, x["passed"])] += 1
                corr_log.append("%s snapshot=%s -> %s (%s; latest: %s)" % (b["id"], b.get("passed"), x["passed"], x["_how"] or "no law/signature action", clean(b.get("status"), 80)))
    for x in recs.values(): x.pop("_how", None); x.pop("_dl", None)
    with open(os.path.join(out_dir, "passed-corrections.json"), "w") as f: json.dump(corr, f, indent=0, sort_keys=True)
    with open(os.path.join(out_dir, "passed-corrections.log.txt"), "w") as f: f.write("\n".join(corr_log) + "\n")
    for ab, sm in sorted(snap_meta.items()):
        R = []; fb = 0
        for b in sm["bills"]:
            if b["id"] in recs: R.append(recs[b["id"]])
            else:
                x = base_record(b); x["sponsor"] = {"name": b["sponsor"], "party": None, "state": ab, "district": None} if b.get("sponsor") else None
                x["listOnly"] = True; x["passed"] = bool(b.get("passed")); R.append(x); fb += 1
        n = max(1, math.ceil(len(R) / BILLS_PER_CHUNK))
        for f in glob.glob(os.path.join(out_dir, "%s-*.json" % ab)): os.remove(f)
        ch = [dict() for _ in range(n)]
        for x in R: ch[bucket(x["id"], n)][x["id"]] = x
        for k in range(n):
            p = os.path.join(out_dir, "%s-%d.json" % (ab, k))
            with open(p + ".tmp", "w") as f:
                json.dump({"jurisdiction": ab, "generatedAt": gen, "bills": ch[k]}, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(p + ".tmp", p)
        full = [x for x in R if not x.get("listOnly")]
        m = {"chunks": n, "count": len(R), "withDetails": len(full),
             "withSummary": sum(1 for x in R if x.get("summary")),
             "withActions": sum(1 for x in R if len(x.get("actions") or []) > 1),
             "withCosponsors": sum(1 for x in R if x.get("cosponsors")),
             "withSponsor": sum(1 for x in R if x.get("sponsor")),
             "withVersions": sum(1 for x in R if x.get("versions")),
             "withVotes": sum(1 for x in R if x.get("votes")),
             "enacted": sum(1 for x in R if x.get("passed")),
             "passedCorrected": {"toFalse": corr_n[(ab, False)], "toTrue": corr_n[(ab, True)]},
             "source": "Open States bulk data (monthly public database export, %s), from the %s legislature's official records" % (dump_date, FO.STATES.get(ab, ab)),
             "generatedAt": gen}
        if fb: m["notes"] = "%d bill%s newer than the %s export: list info only (title, sponsor, latest action)" % (fb, "" if fb == 1 else "s", dump_date)
        meta["jurisdictions"][ab] = m
        print(ab, m["count"], "details", m["withDetails"], "summary", m["withSummary"], "actions", m["withActions"], "versions", m["withVersions"], "votes", m["withVotes"], flush=True)
    with open(mp + ".tmp", "w") as f: json.dump(meta, f, indent=1, ensure_ascii=False)
    os.replace(mp + ".tmp", mp)
    print("done in %.0fs" % (time.time() - t0))

if __name__ == "__main__":
    main()
