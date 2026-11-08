#!/usr/bin/env python3
"""Official-summary refresh for KnowUS bill pages (unattended; meant for the hourly GitHub job).

usage: refresh_summaries.py <detail_dir> [--federal] [--states] [--force] [--dump=URL] [--state-file=PATH]
       (no flag = both)   <detail_dir> = the folder with meta.json + <XX>-<k>.json chunks
                          (the site's data/bills/detail, or bills/detail in the GitHub data repo)

Re-checks every bill whose detail record has NO official summary and, the moment one is published, writes it into
the record ("summary" + "summarySource") and removes the official-title stand-in ("description*", "titleIsDescription").
Official text only: nothing is written or rephrased here.

  Federal: GovInfo bulk BILLSTATUS XML (no key). Each run reads the 8 GovInfo folder listings (one request per bill
           type) and downloads only the BILLSTATUS files whose size/date changed since the last check, so an hourly run
           is a handful of requests. A CRS summary in the file becomes the bill's summary.
  States:  Open States' free public monthly export (HTTP range reads; no key). It changes once a month, so the state
           pass runs only when a newer export is out (or with --force). A legislature abstract that is not just the
           title becomes the bill's summary; one the page already shows (as "From the legislature's official abstract")
           is left as it is.

Incremental state is kept in <detail_dir>/../.summary-refresh-state.json (or --state-file). Chunk names and buckets
never change; meta.json gets updated withSummary / withDescription counts, "summariesCheckedAt", and "generatedAt"
when anything changed (the app prefers the hourly copy when its generatedAt is newer).
Exit code 0 always unless the detail dir is unreadable; source errors are reported and retried next run.
"""
import sys, os, re, json, glob, datetime
from concurrent.futures import ThreadPoolExecutor
import requests

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
UA = {"User-Agent": "KnowUS-data/1.0 (+https://knowus.sites.tab.bot)"}
S = requests.Session(); S.headers.update(UA)
TYPES = {"HR": "hr", "S": "s", "HJRES": "hjres", "SJRES": "sjres", "HCONRES": "hconres", "SCONRES": "sconres", "HRES": "hres", "SRES": "sres"}
DROP = ("description", "descriptionLabel", "descriptionSource", "descriptionUrl", "titleIsDescription")

def now(): return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
def norm(s): return re.sub(r"[^A-Z0-9]", "", (s or "").upper())

class Detail:
    """All chunks of a detail dir, loaded lazily per jurisdiction; writes back only changed chunks."""
    def __init__(self, d):
        self.d = d; self.meta = json.load(open(os.path.join(d, "meta.json"))); self.chunks = {}; self.dirty = set()
    def records(self, pred=lambda j: True):
        for f in sorted(glob.glob(os.path.join(self.d, "[A-Z][A-Z]-*.json"))):
            j = os.path.basename(f)[:2]
            if not pred(j): continue
            if f not in self.chunks: self.chunks[f] = json.load(open(f))
            for bid, r in self.chunks[f]["bills"].items(): yield f, bid, r
    def set_summary(self, f, r, summary, source):
        r["summary"] = summary; r["summarySource"] = source
        for k in DROP: r.pop(k, None)
        self.dirty.add(f)
    def save(self):
        for f in self.dirty:
            json.dump(self.chunks[f], open(f + ".tmp", "w"), ensure_ascii=False, separators=(",", ":")); os.replace(f + ".tmp", f)
        for f in self.dirty:   # recount the touched jurisdictions
            j = os.path.basename(f)[:2]; jm = self.meta.get("jurisdictions", {}).get(j)
            if not jm: continue
            ws = wd = 0
            for g in glob.glob(os.path.join(self.d, "%s-*.json" % j)):
                for r in (self.chunks.get(g) or json.load(open(g)))["bills"].values():
                    ws += bool(r.get("summary")); wd += bool(r.get("description") or r.get("titleIsDescription"))
            jm["withSummary"] = ws; jm["withDescription"] = wd; jm["generatedAt"] = now()
        self.meta["summariesCheckedAt"] = now()
        if self.dirty: self.meta["generatedAt"] = now()
        json.dump(self.meta, open(os.path.join(self.d, "meta.json") + ".tmp", "w"), ensure_ascii=False, indent=1)
        os.replace(os.path.join(self.d, "meta.json") + ".tmp", os.path.join(self.d, "meta.json"))

# ------------------------------------------------------------------ federal
def listing(cong, t):
    r = S.get("https://www.govinfo.gov/bulkdata/json/BILLSTATUS/%s/%s" % (cong, t), headers={"Accept": "application/json"}, timeout=90)
    r.raise_for_status()
    return {f["name"]: "%s|%s" % (f.get("formattedLastModifiedTime"), f.get("size")) for f in r.json().get("files", [])}

def federal(D, st, force=False):
    import fetch_descriptions as FD          # same BILLSTATUS reader as the official-title step
    seen = st.setdefault("federal", {}); todo = []
    for f, bid, r in D.records(lambda j: j == "US"):
        if not r.get("summary"): todo.append((f, bid, r))
    rep = {"lacking": len(todo), "checked": 0, "newSummaries": [], "errors": []}
    if not todo: return rep
    groups = {}
    for f, bid, r in todo:
        m = re.fullmatch(r"US-(\d+)-([A-Z]+)(\d+)", bid)
        if m and m.group(2) in TYPES: groups.setdefault((m.group(1), TYPES[m.group(2)]), []).append((f, bid, r, m))
    fetch = []
    for (cong, t), items in groups.items():
        try: L = listing(cong, t)
        except Exception as e:
            rep["errors"].append("listing %s/%s: %s" % (cong, t, e)); L = None
        for f, bid, r, m in items:
            name = "BILLSTATUS-%s%s%s.xml" % (cong, t, m.group(3))
            sig = L.get(name) if L is not None else None
            if L is not None and sig is None: continue                 # not on GovInfo yet; nothing to read
            if not force and sig is not None and seen.get(bid) == sig: continue   # unchanged since last check
            fetch.append((f, bid, r, sig))
    def one(x):
        f, bid, r, sig = x
        try: return x, FD.us_one(r)[1], None
        except Exception as e: return x, None, str(e)
    with ThreadPoolExecutor(12) as ex:
        for (f, bid, r, sig), out, err in ex.map(one, fetch):
            if err: rep["errors"].append("%s: %s" % (bid, err)); continue
            rep["checked"] += 1
            if out and out.get("summary"):
                D.set_summary(f, r, out["summary"], out.get("summarySource") or "Congressional Research Service summary")
                rep["newSummaries"].append(bid)
            if sig: seen[bid] = sig
    return rep

# ------------------------------------------------------------------ states (Open States monthly export)
def states(D, st, force=False, dump=None):
    import fetch_state_bulk_details as FS
    import fetch_openstates as FO
    import fetch_descriptions as FD          # same "adds information beyond the title" test as the official-title step
    lacking = {}
    for f, bid, r in D.records(lambda j: j != "US"):
        if not r.get("summary"): lacking[bid] = (f, r)
    rep = {"lacking": len(lacking), "dump": None, "matched": 0, "newSummaries": [], "skipped": None}
    if not lacking: return rep
    url = dump or FS.latest_dump_url(); rep["dump"] = url
    if not force and st.get("statesDump") == url:
        rep["skipped"] = "no newer Open States export since the last check"; return rep
    Dm = FS.Dump(url)
    jid = {}
    for j in Dm.rows("opencivicdata_jurisdiction", sel=["id", "name"]):
        m = re.fullmatch(r"ocd-jurisdiction/country:us/(state|district):([a-z]{2})/government", j["id"])
        if m: jid[m.group(2).upper()] = j["id"]
    ab_of = {v: k for k, v in jid.items()}
    sessions = {s["id"]: s for s in Dm.rows("opencivicdata_legislativesession")}
    names = {}
    for s in sessions.values():
        ab = ab_of.get(s["jurisdiction_id"])
        if ab: names["%s|%s" % (FO.STATES.get(ab), s["identifier"])] = {"name": s["name"], "start": (s["start_date"] or "")[:4] or None, "cls": s["classification"]}
    want = {jid[ab] for ab in {k[:2] for k in lacking} if ab in jid}
    sess_ok = {sid for sid, s in sessions.items() if s["jurisdiction_id"] in want}
    OFFICIAL_API = ("WA", "VA", "MA", "SD", "IL")      # ids built from the legislatures' own APIs: match loosely
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
    for r in Dm.rows("opencivicdata_bill", key="legislative_session_id", keys=sess_ok, sel=["id", "identifier", "legislative_session_id", "first_action_date"]):
        s = sessions[r["legislative_session_id"]]; ab = ab_of[s["jurisdiction_id"]]
        try: oid = FO.bill_id(ab, s["identifier"], r["identifier"], names)
        except Exception: oid = None
        if oid in lacking: bills[r["id"]] = oid
        elif ab in OFFICIAL_API:
            c = next((lack_loose[kk] for kk in (loose(ab, y, r["identifier"]) for y in years(s)) if kk in lack_loose), None)
            if c and len(c) == 1 and c[0] not in bills.values(): bills[r["id"]] = c[0]
    rep["matched"] = len(bills)
    abss = {}
    for a in Dm.rows("opencivicdata_billabstract", key="bill_id", keys=set(bills)): abss.setdefault(a["bill_id"], []).append(a)
    for obid, rows in abss.items():
        oid = bills[obid]; f, r = lacking[oid]
        rows = [x for x in rows if (x["abstract"] or "").strip()]
        if not rows: continue
        rows.sort(key=lambda x: (0 if re.search(r"summary|digest|synopsis", x["note"] or "", re.I) else 1, -len(x["abstract"] or "")))
        a = re.sub(r"\s+", " ", rows[0]["abstract"]).strip()[:4000]
        t = r.get("title") or ""; core = norm(re.sub(r"(?i)^an act\s+", "", t))
        if norm(a) == norm(t) or not FD.adds_info(a, t): continue        # only repeats the title
        if norm(a).startswith(norm(t)): continue                          # the title + an appendix (e.g. WA "REVISED FOR ENGROSSED")
        if a.startswith("By ") and len(core) > 20 and core in norm(a): continue   # MA docket line: title restated + petitioners
        if norm(a) == norm(r.get("description")): continue               # already shown as the official abstract
        note = re.sub(r"\s+", " ", rows[0]["note"] or "").strip()
        D.set_summary(f, r, a, "Official abstract%s (state legislature, via Open States)" % (" — " + note if note else ""))
        rep["newSummaries"].append(oid)
    st["statesDump"] = url; st["statesDumpModified"] = Dm.last_modified
    return rep

def main():
    a = sys.argv[1:]
    pos = [x for x in a if not x.startswith("--")]
    if not pos: print(__doc__); sys.exit(2)
    d = os.path.abspath(pos[0]); fl = {x for x in a if x in ("--federal", "--states")} or {"--federal", "--states"}
    force = "--force" in a
    dump = next((x.split("=", 1)[1] for x in a if x.startswith("--dump=")), None)
    stf = next((x.split("=", 1)[1] for x in a if x.startswith("--state-file=")), None) or os.path.join(os.path.dirname(d), ".summary-refresh-state.json")
    st = json.load(open(stf)) if os.path.exists(stf) else {}
    D = Detail(d); rep = {"startedAt": now()}
    if "--federal" in fl:
        try: rep["US"] = federal(D, st, force)
        except Exception as e: rep["US"] = {"error": str(e)}
    if "--states" in fl:
        try: rep["states"] = states(D, st, force, dump)
        except Exception as e: rep["states"] = {"error": str(e)}
    D.save(); st["lastRun"] = now()
    json.dump(st, open(stf + ".tmp", "w"), indent=0); os.replace(stf + ".tmp", stf)
    out = {k: ({kk: (vv if kk != "errors" else vv[:10]) for kk, vv in v.items()} if isinstance(v, dict) else v) for k, v in rep.items()}
    print(json.dumps(out, indent=1))
    n = sum(len(v.get("newSummaries", [])) for v in rep.values() if isinstance(v, dict))
    print("new official summaries:", n)

if __name__ == "__main__":
    main()
