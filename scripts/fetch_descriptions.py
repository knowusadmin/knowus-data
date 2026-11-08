#!/usr/bin/env python3
"""Official descriptions for KnowUS bill pages that have no official summary.

usage: fetch_descriptions.py [--federal] [--states] [--only=OH,PA] [--site=<unzipped site dir>] [--dump=URL]
       (no flag = both)

Writes one compact patch per jurisdiction to /home/user/tab/files/knowus-backend/descriptions-out/<XX>.json:
  {"jurisdiction","generatedAt","source", "bills": {bill_id: {"description","source","sourceUrl"[, "dataUrl"]
                                                              [, "summary","summarySource"]}}}
Only bills whose detail record has NO summary are considered. Nothing is invented: every description is an official
title / abstract copied from the official record; a candidate that only repeats the title already shown is dropped.

Federal (US): GovInfo bulk BILLSTATUS XML (no key)
  https://www.govinfo.gov/bulkdata/BILLSTATUS/<congress>/<type>/BILLSTATUS-<congress><type><num>.xml
  description = "Official Title as Introduced" (the long "To amend ..." title); if a later official title differs
  (as reported / amended / passed / enacted) it is used instead and the source says which.
  If a CRS summary has appeared since the snapshot it is returned as "summary"/"summarySource" too.
States: Open States public monthly PostgreSQL dump (same reader as fetch_state_bulk_details.py, HTTP ranges only):
  bill.title, billtitle (other titles), billabstract, bill.extras text fields — used only when longer than and not a
  restatement of the title shown.
"""
import sys, os, re, json, glob, time, datetime, zipfile, tempfile, html
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = "/home/user/tab/files/knowus-backend/descriptions-out"
STATE_DETAILS = "/home/user/tab/files/knowus-backend/state-details-out"
SNAP = "/home/user/tab/files/knowus-backend/openstates-snapshot"
SITE_ZIP = "/home/user/tab/files/knowus-site-live.zip"
UA = {"User-Agent": "KnowUS-data/1.0 (+https://knowus.sites.tab.bot)"}

def now(): return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
def clean(s, n=None):
    if s is None: return None
    s = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
    if n and len(s) > n: s = s[:n].rsplit(" ", 1)[0] + "…"
    return s or None
def norm(s): return re.sub(r"[^A-Z0-9]", "", (s or "").upper())

def adds_info(cand, title):
    """True when cand says more than the title already shown."""
    c, t = norm(cand), norm(title)
    if not c or len(c) < 25: return False
    if c == t or c in t: return False
    if t and t in c and len(c) < len(t) + 15: return False
    return len(c) > len(t) * 1.15 or (t not in c and len(c) >= 40)

def write(J, bills, source):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "%s.json" % J)
    json.dump({"jurisdiction": J, "generatedAt": now(), "source": source, "bills": bills}, open(p + ".tmp", "w"),
              ensure_ascii=False, separators=(",", ":"))
    os.replace(p + ".tmp", p)

def load_chunks(paths):
    recs = {}
    for f in paths:
        try: recs.update(json.load(open(f))["bills"])
        except Exception as e: print("skip", f, e)
    return recs

def site_dir(arg):
    if arg: return arg
    d = tempfile.mkdtemp(prefix="knowus-site-")
    with zipfile.ZipFile(SITE_ZIP) as z:
        for n in z.namelist():
            if n.startswith("data/bills/detail/") or n.startswith("data/bills/"): z.extract(n, d)
    return d

# ------------------------------------------------------------------ federal
TYPES = {"HR": "hr", "S": "s", "HJRES": "hjres", "SJRES": "sjres", "HCONRES": "hconres", "SCONRES": "sconres",
         "HRES": "hres", "SRES": "sres"}
LATER = ["Official Title as Enacted", "Official Title as Passed", "Official Title as Amended", "Official Titles as Reported",
         "Official Title as Reported"]
S = requests.Session(); S.headers.update(UA)

def get(url, tries=5):
    for i in range(tries):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 200: return r
            if r.status_code == 404: return None
        except requests.RequestException: pass
        time.sleep(1.5 * (i + 1))
    raise RuntimeError("failed " + url)

def text_of(s):
    if not s: return None
    s = re.sub(r"</p>\s*<p>", "\n\n", s); s = re.sub(r"<br\s*/?>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    return "\n\n".join(p for p in (re.sub(r"[ \t]+", " ", x).strip() for x in s.split("\n\n")) if p) or None

def us_one(rec):
    m = re.fullmatch(r"US-(\d+)-([A-Z]+)(\d+)", rec["id"]); cong, t, num = m.group(1), TYPES[m.group(2)], m.group(3)
    url = "https://www.govinfo.gov/bulkdata/BILLSTATUS/%s/%s/BILLSTATUS-%s%s%s.xml" % (cong, t, cong, t, num)
    r = get(url)
    if r is None: return rec["id"], None, "BILLSTATUS file not found"
    x = ET.fromstring(r.content).find("bill")
    titles = [(clean(i.findtext("titleType")) or "", clean(i.findtext("title")), i.findtext("updateDate") or "")
              for i in x.findall("titles/item")]
    intro = next((tt for ty, tt, _ in titles if ty == "Official Title as Introduced" and tt), None)
    later = None
    for ty, tt, ud in sorted(titles, key=lambda z: z[2], reverse=True):
        if tt and ty.startswith("Official Title") and ty != "Official Title as Introduced" and norm(tt) != norm(intro):
            later = (ty, tt); break
    page = rec.get("url") or ""
    out = {}
    if later:
        out = {"description": later[1], "source": "%s (Congress.gov / GovInfo)" % later[0], "label": "From the bill's official title"}
    elif intro:
        out = {"description": intro, "source": "Official title as introduced (Congress.gov / GovInfo)", "label": "From the bill's official title"}
    if out and not adds_info(out["description"], rec.get("title")):
        # the headline already IS the official long title ("To amend ..."): nothing new to add, but the page can say so
        out = {"titleIsDescription": True, "source": out["source"]}
    if out:
        out["sourceUrl"] = (page.rstrip("/") + "/titles") if page.startswith("https://www.congress.gov/bill/") else url
        out["dataUrl"] = url
    sums = [s for s in x.findall("summaries/summary") if (s.findtext("text") or "").strip()]
    if sums:
        s = sorted(sums, key=lambda s: s.findtext("updateDate") or s.findtext("actionDate") or "")[-1]
        out["summary"] = text_of(s.findtext("text"))
        out["summarySource"] = "Congressional Research Service summary (%s, %s)" % (
            clean(s.findtext("actionDesc")) or "summary", (s.findtext("actionDate") or "")[:10])
        out.setdefault("dataUrl", url)
    return rec["id"], (out or None), (None if out else ("official title only repeats the display title" if intro else "no official title in BILLSTATUS"))

def federal(sd):
    recs = load_chunks(glob.glob(os.path.join(sd, "data/bills/detail/US-*.json")))
    todo = [r for r in recs.values() if not r.get("summary")]
    print("US bills", len(recs), "without summary", len(todo), flush=True)
    res, why = {}, {}
    with ThreadPoolExecutor(12) as ex:
        for i, (bid, out, w) in enumerate(ex.map(lambda r: _safe(us_one, r), todo)):
            if out: res[bid] = out
            else: why[bid] = w
            if i % 100 == 99: print(i + 1, "done", flush=True); write("US", res, SRC_US)
    write("US", res, SRC_US)
    return {"lacking": len(todo), "described": sum(1 for v in res.values() if v.get("description")),
            "titleIsDescription": sum(1 for v in res.values() if v.get("titleIsDescription")),
            "newCrsSummary": sum(1 for v in res.values() if v.get("summary")), "empty": why}

SRC_US = "GovInfo bulk BILLSTATUS XML (Library of Congress / Congress.gov): official bill titles; CRS summaries"

def _safe(fn, r):
    try: return fn(r)
    except Exception as e: return r["id"], None, "error: %s" % e

# ------------------------------------------------------------------ states (Open States monthly dump)
EXTRA_KEYS = re.compile(r"summary|description|digest|synopsis|abstract|purpose|caption|long_title|relating|impact", re.I)

def states(sd, only=None, dump=None):
    import fetch_state_bulk_details as FS
    import fetch_openstates as FO
    # detail records lacking a summary: Open States states + DC, plus WA/VA/MA/SD/IL from the site chunks
    recs = {}
    for f in glob.glob(os.path.join(STATE_DETAILS, "[A-Z][A-Z]-*.json")):
        recs.update(json.load(open(f))["bills"])
    for ab in ("WA", "VA", "MA", "SD", "IL"):
        recs.update(load_chunks(glob.glob(os.path.join(sd, "data/bills/detail/%s-*.json" % ab))))
    # list-only bills (no detail record) count too: take them from the snapshots
    snap = {}
    for f in glob.glob(os.path.join(SNAP, "[A-Z][A-Z].json")):
        for b in json.load(open(f))["bills"]: snap[b["id"]] = b
    for f in glob.glob(os.path.join(sd, "data/bills/[A-Z][A-Z].json")):
        try:
            for b in json.load(open(f)).get("bills", []): snap.setdefault(b["id"], b)
        except Exception: pass
    lacking = {}; urls = {}
    for bid, r in recs.items():
        if not r.get("summary"): lacking[bid] = r.get("title"); urls[bid] = r.get("url")
    for bid, b in snap.items():
        if bid not in recs and not b.get("summary"): lacking[bid] = b.get("title"); urls[bid] = b.get("url")
    lacking = {k: v for k, v in lacking.items() if not k.startswith("US-")}
    if only: lacking = {k: v for k, v in lacking.items() if k[:2] in only}
    print("state bills without summary", len(lacking), flush=True)

    D = FS.Dump(dump or FS.latest_dump_url()); print("dump", D.url, D.last_modified, flush=True)
    juris = D.rows("opencivicdata_jurisdiction", sel=["id", "name"]); jid = {}
    for j in juris:
        m = re.fullmatch(r"ocd-jurisdiction/country:us/(state|district):([a-z]{2})/government", j["id"])
        if m: jid[m.group(2).upper()] = j["id"]
    ab_of = {v: k for k, v in jid.items()}
    sessions = {s["id"]: s for s in D.rows("opencivicdata_legislativesession")}
    names = {}
    for s in sessions.values():
        ab = ab_of.get(s["jurisdiction_id"])
        if ab: names["%s|%s" % (FO.STATES.get(ab), s["identifier"])] = {"name": s["name"], "start": (s["start_date"] or "")[:4] or None, "cls": s["classification"]}
    want = {jid[ab] for ab in {k[:2] for k in lacking} if ab in jid}
    sess_ok = {sid for sid, s in sessions.items() if s["jurisdiction_id"] in want}
    # loose key (state + identifier digits/letters + session) as a fallback for the 5 official-API states
    def loose(ab, yr, ident): return "%s|%s|%s" % (ab, yr, norm(ident))
    lack_loose = {}
    for k in lacking:
        m = re.match(r"([A-Z]{2})-(\d{4})-([A-Z]+\d+)$", k)
        if m: lack_loose.setdefault(loose(m.group(1), m.group(2), m.group(3)), []).append(k)
    def years(s):
        y = {(s.get("start_date") or "")[:4], (s.get("end_date") or "")[:4]}
        y |= set(re.findall(r"(?:19|20)\d\d", (s.get("identifier") or "") + " " + (s.get("name") or "")))
        return {v for v in y if v}
    bills = {}
    for r in D.rows("opencivicdata_bill", key="legislative_session_id", keys=sess_ok,
                    sel=["id", "identifier", "title", "extras", "legislative_session_id", "first_action_date"]):
        s = sessions[r["legislative_session_id"]]; ab = ab_of[s["jurisdiction_id"]]
        try: oid = FO.bill_id(ab, s["identifier"], r["identifier"], names)
        except Exception: oid = None
        if oid in lacking:
            r["_oid"] = oid; bills[r["id"]] = r
        elif ab in ("WA", "VA", "MA", "SD", "IL"):
            c = next((lack_loose[kk] for kk in (loose(ab, y, r["identifier"]) for y in years(s)) if kk in lack_loose), None)
            if c and len(c) == 1:
                r["_oid"] = c[0]; r["_loose"] = True
                prev = next((b for b in bills.values() if b["_oid"] == c[0]), None)
                if prev is None or (r["first_action_date"] or "") > (prev["first_action_date"] or ""):
                    if prev: bills.pop(prev["id"], None)
                    bills[r["id"]] = r
    B = set(bills); print("matched", len(B), flush=True)
    others = {}
    for t in D.rows("opencivicdata_billtitle", key="bill_id", keys=B): others.setdefault(t["bill_id"], []).append(t)
    abss = {}
    for a in D.rows("opencivicdata_billabstract", key="bill_id", keys=B): abss.setdefault(a["bill_id"], []).append(a)

    res = {}; stats = {}
    for b in bills.values():
        oid = b["_oid"]; ab = oid[:2]; shown = lacking[oid] or ""
        cands = []
        for a in abss.get(b["id"], []):
            cands.append((clean(a["abstract"], 3000), "Official abstract%s (state legislature, via Open States)" % (" — " + clean(a["note"]) if clean(a["note"]) else "")))
        for t in others.get(b["id"], []):
            cands.append((clean(t["title"], 3000), "Official %s (state legislature, via Open States)" % ((clean(t["note"]) or "alternate title").lower())))
        cands.append((clean(b["title"], 3000), "Official bill title (state legislature, via Open States)"))
        try: ex = json.loads(b["extras"] or "{}")
        except Exception: ex = {}
        for k, v in (ex.items() if isinstance(ex, dict) else []):
            if isinstance(v, str) and EXTRA_KEYS.search(k):
                cands.append((clean(v, 3000), "Official %s (state legislature, via Open States)" % k.replace("_", " ")))
        core = norm(re.sub(r"(?i)^an act\s+", "", shown))
        def keep(c):
            if not c[0] or not adds_info(c[0], shown): return False
            if norm(c[0]).startswith(norm(shown)): return False          # shown title + an appendix (e.g. WA "REVISED FOR ENGROSSED")
            if c[0].startswith("By ") and len(core) > 20 and core in norm(c[0]): return False   # MA docket line restating the title + petitioners
            return True
        good = [c for c in cands if keep(c)]
        if good:
            d, src = max(good, key=lambda c: len(c[0]))
            res.setdefault(ab, {})[oid] = {"description": d, "source": src,
                                          "label": "From the legislature's official abstract" if "abstract" in src.lower() else "From the bill's official title",
                                          "sourceUrl": urls.get(oid),
                                          **({"matched": "identifier+state (session by latest)"} if b.get("_loose") else {})}
    for ab in sorted({k[:2] for k in lacking}):
        write(ab, res.get(ab, {}), "Open States public monthly export (%s): official titles/abstracts as published by the legislature" % (D.last_modified or ""))
        n = sum(1 for k in lacking if k[:2] == ab)
        stats[ab] = {"lacking": n, "matchedInDump": sum(1 for b in bills.values() if b["_oid"][:2] == ab), "described": len(res.get(ab, {}))}
    return stats

def main():
    a = sys.argv[1:]; fl = {x for x in a if x in ("--federal", "--states")} or {"--federal", "--states"}
    only = next((set(x.split("=", 1)[1].upper().split(",")) for x in a if x.startswith("--only=")), None)
    dump = next((x.split("=", 1)[1] for x in a if x.startswith("--dump=")), None)
    sd = site_dir(next((x.split("=", 1)[1] for x in a if x.startswith("--site=")), None))
    rep = {}
    if "--federal" in fl: rep["US"] = federal(sd)
    if "--states" in fl: rep["states"] = states(sd, only, dump)
    os.makedirs(OUT, exist_ok=True)
    tag = "_report-%s.json" % ("-".join(sorted(x.strip("-") for x in fl)))
    json.dump(rep, open(os.path.join(OUT, tag), "w"), indent=1)
    print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk != "empty"} if k == "US" else v) for k, v in rep.items()}, indent=1))

if __name__ == "__main__":
    main()
