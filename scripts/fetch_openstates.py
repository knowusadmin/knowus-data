#!/usr/bin/env python3
"""KnowUS state bill snapshots from the Open States v3 API (Plural Policy).

Writes one file per state, <out>/<XX>.json, in the shape the KnowUS app reads:
  {"jurisdiction","name","session","generatedAt","source","sourceUrl","bills":[
     {"id","number","title","status","date","introduced","sponsor","url","chamber",
      "classification","passed"}]}
plus <out>/_report.json. Bills are the most recently acted-on (sort=latest_action_desc).

Budget-aware and rerunnable:
  * every HTTP attempt is counted in <out>/_usage.json per UTC day; the run stops at
    --daily-limit minus --reserve (free keys: Plural publishes a per-day and per-second
    limit; the 429 body names the limit, which this script reads and obeys).
  * depth comes in tiers (--tiers 2,5,10 = pages of 20 per state): every state gets the
    first tier before any state gets the second, so a short budget still covers all states.
  * progress per state is kept in <out>/_progress.json for --fresh-hours, so a rerun the same
    day continues deeper instead of refetching; older progress restarts from page 1.
  * new results are merged into an existing file (refetched bills replace old copies), capped
    at --keep bills per state.

env:  OPENSTATES_API_KEY (required)
usage: python3 fetch_openstates.py --rebuild [--out DIR]   (no network: rewrite files from _cache)
       python3 fetch_openstates.py [--out DIR] [--tiers 2,5,10] [--skip WA,VA,MA,SD,IL]
         [--states XX,YY] [--daily-limit 250] [--reserve 20] [--interval 1.2]
         [--max-minutes 40] [--keep 300]
Free tier measured 2026-11-05: 10 requests/minute (429 "exceeded limit of 10/min") and 250 requests/day
(429 "exceeded limit of 250/day"), so --interval 6.5 and --daily-limit 250. Error responses count too.
Note: latest_action_desc pages are not stable when many bills share a date, so pages overlap; ids are de-duplicated.
Hourly job example (small refresh): --tiers 1 --max-requests 9
"""
import argparse, collections, datetime as dt, json, os, re, sys, time
import requests

STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"}
BASE = "https://v3.openstates.org"
PASSED_CLASSES = {"became-law", "executive-signature"}
PASSED_TEXT = re.compile(r"\bchaptered\b|\bsigned by (the )?governor\b|\bgovernor signed\b|\bapproved by (the )?governor\b|"
                         r"\bbec(ame|omes) law\b|\bbecame (an )?act\b|\bpublic act\b|\bsession law\b", re.I)
NOT_PASSED_TEXT = re.compile(r"\bveto(ed)?\b|\bnot signed\b|\bto governor\b|\bfor (the )?governor'?s? (signature|action)\b", re.I)

def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def today():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

def clean(s, n=300):
    s = re.sub(r"<[^>]+>", " ", s or ""); s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"

def load(path, default):
    try:
        with open(path) as f: return json.load(f)
    except Exception: return default

def save(path, obj, compact=False):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":") if compact else None, indent=None if compact else 1)
    os.replace(tmp, path)

def session_key(sess):
    """'2025' / '2025-2026' -> '2025'; special sessions keep their suffix so ids never collide: '2025S1' -> '2025S1'."""
    sess = sess or ""
    if re.fullmatch(r"(19|20)\d\d(\s*-\s*(19|20)?\d\d)?", sess.strip()):
        return sess.strip()[:4]
    m = re.search(r"(19|20)\d\d", sess)
    rest = re.sub(r"[^A-Za-z0-9]", "", re.sub(r"(19|20)\d\d", "", sess)) if m else re.sub(r"[^A-Za-z0-9]", "", sess)
    return (m.group(0) if m else "") + rest.upper()

class Api:
    def __init__(self, key, out, daily_limit, reserve, interval, max_requests, deadline):
        self.s = requests.Session()
        self.s.headers.update({"X-API-KEY": key, "User-Agent": "KnowUS bill snapshot job"})
        self.out, self.daily_limit, self.reserve = out, daily_limit, reserve
        self.interval, self.max_requests, self.deadline = interval, max_requests, deadline
        self.usage_path = os.path.join(out, "_usage.json")
        self.usage = load(self.usage_path, {})
        self.run_used, self.last = 0, 0.0
        self.stopped = None
        self.limits_seen = {}

    def used_today(self):
        return int(self.usage.get(today(), 0))

    def can_spend(self):
        if self.stopped: return False
        if time.time() > self.deadline: self.stopped = "time limit reached"; return False
        if self.max_requests and self.run_used >= self.max_requests: self.stopped = "per-run request cap reached"; return False
        if self.used_today() >= self.daily_limit - self.reserve: self.stopped = "daily budget reached (%d used, limit %d, reserve %d)" % (self.used_today(), self.daily_limit, self.reserve); return False
        return True

    def _count(self):
        self.run_used += 1
        self.usage[today()] = self.used_today() + 1
        self.usage = {k: v for k, v in self.usage.items() if k >= (dt.date.today() - dt.timedelta(days=7)).isoformat()}
        save(self.usage_path, self.usage)

    def get(self, path, params):
        backoff = 15
        for attempt in range(6):
            if not self.can_spend(): return None
            wait = self.interval - (time.time() - self.last)
            if wait > 0: time.sleep(wait)
            self.last = time.time()
            self._count()
            try:
                r = self.s.get(BASE + path, params=params, timeout=(15, 90))
            except requests.RequestException as e:
                print("  network error:", type(e).__name__, flush=True); time.sleep(backoff); backoff *= 2; continue
            for h, v in r.headers.items():
                if "ratelimit" in h.lower() or h.lower() == "retry-after": self.limits_seen[h.lower()] = v
            if r.status_code == 429:
                body = r.text[:300]
                print("  429:", body, flush=True)
                m = re.search(r"(\d+)\s*(?:per|/)\s*(sec|min|hour|day)", body, re.I)
                if m:
                    n, unit = int(m.group(1)), {"sec": "second", "min": "minute"}.get(m.group(2).lower(), m.group(2).lower())
                    self.limits_seen["429_limit"] = "%d/%s" % (n, unit)
                    if unit == "day":
                        self.daily_limit = min(self.daily_limit, n); self.stopped = "daily limit hit (%s)" % body; return None
                    if unit == "hour":
                        self.stopped = "hourly limit hit (%s)" % body; return None
                    per = {"second": 1, "minute": 60}[unit]
                    self.interval = max(self.interval, per / max(n, 1) * 1.15 + 0.2)
                    print("  interval now %.1fs" % self.interval, flush=True)
                ra = r.headers.get("retry-after")
                time.sleep(float(ra) if ra and ra.replace(".", "").isdigit() else backoff); backoff = min(backoff * 2, 240)
                continue
            if r.status_code >= 500:
                print("  HTTP", r.status_code, flush=True); time.sleep(backoff); backoff = min(backoff * 2, 240); continue
            if r.status_code in (401, 403):
                self.stopped = "key refused: HTTP %d %s" % (r.status_code, r.text[:200]); return None
            if r.status_code >= 400:
                print("  HTTP", r.status_code, r.text[:200], flush=True); return {"_error": r.status_code, "_body": r.text[:300]}
            return r.json()
        return None

def id_session(ab, sess, sess_names=None):
    """Session part of a bill id: the session's first year ('20252026' -> 2025, '2026rs' -> 2026; Alaska's '34' -> its
    start year). Special sessions keep their identifier ('2026S1', '2025 1st Special' -> '20251ST...') so ids never collide."""
    sess = sess or ""
    meta = (sess_names or {}).get("%s|%s" % (STATES.get(ab), sess)) or {}
    m = re.search(r"(19|20)\d\d", sess)
    year = m.group(0) if m else (meta.get("start") or "")
    rem = re.sub(r"[^A-Za-z0-9]", "", re.sub(r"(19|20)\d\d", "", sess)).upper() if m else ""
    if re.fullmatch(r"\d\d", rem): rem = ""  # '2025_26' is a regular biennium (Georgia)
    special = meta.get("cls") == "special" or rem not in ("", "RS", "R", "REGULAR", "REGULARSESSION")
    if not special: return year or re.sub(r"[^A-Za-z0-9]", "", sess).upper()
    rest = re.sub(r"[^A-Za-z0-9]", "", re.sub(r"(19|20)\d\d", "", sess)).upper() or "S"
    return year + rest

def bill_id(ab, sess, ident, sess_names=None):
    return "%s-%s-%s" % (ab, id_session(ab, sess, sess_names), re.sub(r"[^A-Za-z0-9]", "", ident or "").upper())

def fix_url(ab, url, ident):
    """DC's Open States source is a bulk-data API URL; its council page per bill is lims.dccouncil.gov/Legislation/<B26-0856>
    (pattern checked 2026-11-05, HTTP 200)."""
    if ab == "DC" and url and "/api/v2/PublicData/BulkData" in url and ident:
        return "https://lims.dccouncil.gov/Legislation/" + ident.replace(" ", "")
    return url

def latest_action(b):
    acts = b.get("actions") or []
    if not acts: return None
    return max(acts, key=lambda a: ((a.get("date") or "")[:10], a.get("order") or 0))

def to_bill(ab, b, sess_names=None):
    ident = b.get("identifier") or ""
    sps = b.get("sponsorships") or []
    sp = [s for s in sps if s.get("primary")] or sps
    srcs = [s.get("url") for s in (b.get("sources") or []) if (s.get("url") or "").startswith("http")]
    srcs = [u for u in srcs if u.startswith("https://")] + [u for u in srcs if not u.startswith("https://")]
    org = ((b.get("from_organization") or {}).get("classification") or "")
    la = latest_action(b)
    acts = b.get("actions") or []
    passed = any(PASSED_CLASSES & set(a.get("classification") or []) for a in acts) or any(
        "chaptered" in " ".join(a.get("classification") or []) for a in acts) or any(
        PASSED_TEXT.search(a.get("description") or "") and not NOT_PASSED_TEXT.search(a.get("description") or "") for a in acts)
    return {"id": bill_id(ab, b.get("session"), ident, sess_names),
            "number": ident or None,
            "title": clean(b.get("title")) or None,
            "status": clean(b.get("latest_action_description"), 400) or None,
            "date": (b.get("latest_action_date") or "")[:10] or None,
            "introduced": (b.get("first_action_date") or "")[:10] or None,
            "sponsor": clean(sp[0].get("name"), 120) if sp and sp[0].get("name") else None,
            "url": fix_url(ab, srcs[0], ident) if srcs else b.get("openstates_url"),
            "chamber": {"upper": "Senate", "lower": "House"}.get(org),
            "classification": list(la.get("classification") or []) if la else [],
            "passed": bool(passed),
            "_session": b.get("session")}

def rebuild(out, keep=300):
    """No network: rewrite every <XX>.json from this build's cache (_cache/XX.json) with current id/passed rules."""
    prog = load(os.path.join(out, "_progress.json"), {})
    names = (prog.get("_sessions") or {}).get("names") or {}
    report_path = os.path.join(out, "_report.json"); report = load(report_path, {"states": {}})
    for fn in sorted(os.listdir(os.path.join(out, "_cache"))):
        ab = fn[:2]
        cache = load(os.path.join(out, "_cache", fn), [])
        byid = {}
        for b in cache:
            b = dict(b); b["id"] = bill_id(ab, b.get("_session"), b.get("number"), names)
            b["url"] = fix_url(ab, b.get("url"), b.get("number"))
            byid.setdefault(b["id"], b)
        bills = sorted(byid.values(), key=lambda b: (b.get("date") or "", b.get("id")), reverse=True)[:keep]
        sc = collections.Counter(b.get("_session") for b in bills if b.get("_session"))
        top = sc.most_common(1)[0][0] if sc else None
        sname = (names.get("%s|%s" % (STATES[ab], top)) or {}).get("name") or top
        for b in bills: b.pop("_session", None)
        path = os.path.join(out, ab + ".json"); old = load(path, {})
        doc = {"jurisdiction": ab, "name": STATES[ab], "session": sname, "generatedAt": old.get("generatedAt") or now(),
               "source": "Open States (Plural)", "sourceUrl": "https://open.pluralpolicy.com/%s/bills/" % ab.lower(), "bills": bills}
        save(path, doc)
        r = report["states"].setdefault(ab, {})
        r.update({"count": len(bills), "newest": bills[0]["date"] if bills else None, "oldest": bills[-1]["date"] if bills else None,
                  "passed": sum(1 for b in bills if b.get("passed")), "session": sname,
                  "sessions_in_file": {names.get("%s|%s" % (STATES[ab], k), {}).get("name") or k: v for k, v in sc.items()}})
    save(report_path, report)
    print("rebuilt", len(report["states"]), "states")

def main():
    if "--rebuild" in sys.argv:
        i = sys.argv.index("--out") if "--out" in sys.argv else -1
        return rebuild(sys.argv[i + 1] if i >= 0 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "openstates-snapshot"))
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--out", default=os.path.join(here, "..", "openstates-snapshot"))
    ap.add_argument("--tiers", default="2,5,10")
    ap.add_argument("--skip", default="WA,VA,MA,SD,IL")
    ap.add_argument("--states", default="")
    ap.add_argument("--daily-limit", type=int, default=int(os.environ.get("OPENSTATES_DAILY_LIMIT", "250")))
    ap.add_argument("--reserve", type=int, default=20)
    ap.add_argument("--interval", type=float, default=6.5)  # free tier: 10 requests/minute (429 body: "exceeded limit of 10/min")
    ap.add_argument("--max-requests", type=int, default=0)
    ap.add_argument("--max-minutes", type=float, default=40)
    ap.add_argument("--keep", type=int, default=300)
    ap.add_argument("--per-page", type=int, default=20)
    ap.add_argument("--fresh-hours", type=float, default=20)
    a = ap.parse_args()
    key = os.environ.get("OPENSTATES_API_KEY")
    if not key: sys.exit("OPENSTATES_API_KEY not set")
    out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    api = Api(key, out, a.daily_limit, a.reserve, a.interval, a.max_requests, time.time() + a.max_minutes * 60)
    tiers = [int(x) for x in a.tiers.split(",") if x.strip()]
    skip = {x.strip().upper() for x in a.skip.split(",") if x.strip()}
    states = [x.strip().upper() for x in a.states.split(",") if x.strip()] or [s for s in STATES if s not in skip]
    print("start", now(), "states", len(states), "tiers", tiers, "used today", api.used_today(), flush=True)

    prog_path = os.path.join(out, "_progress.json")
    prog = load(prog_path, {})
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=a.fresh_hours)).isoformat()
    for ab in list(prog):
        if prog[ab].get("started", "") < cutoff: del prog[ab]
    report_path = os.path.join(out, "_report.json")
    report = load(report_path, {"states": {}})

    # session names (1 request, cached in progress for the day)
    sess_names = prog.get("_sessions", {}).get("names")
    if not sess_names:
        sess_names = {}
        j = api.get("/jurisdictions", {"classification": "state", "include": "legislative_sessions", "per_page": 52})
        for jur in (j or {}).get("results") or []:
            for s in jur.get("legislative_sessions") or []:
                sess_names["%s|%s" % (jur.get("name"), s.get("identifier"))] = {"name": s.get("name"),
                    "start": (s.get("start_date") or "")[:4] or None, "cls": s.get("classification")}
        if sess_names: prog["_sessions"] = {"started": now(), "names": sess_names}
        save(prog_path, prog)

    # raw cache of this build's converted bills per state
    cache_dir = os.path.join(out, "_cache"); os.makedirs(cache_dir, exist_ok=True)

    def write_state(ab, fresh):
        path = os.path.join(out, ab + ".json")
        old = load(path, {"bills": []})
        byid = {b["id"]: b for b in old.get("bills", [])}
        seen = set()
        for b in fresh:
            if b["id"] in seen: continue  # pages overlap when many bills share a date; first copy wins
            seen.add(b["id"]); byid[b["id"]] = b
        bills = sorted(byid.values(), key=lambda b: (b.get("date") or "", b.get("id")), reverse=True)[: a.keep]
        sc = collections.Counter(b.get("_session") for b in fresh if b.get("_session"))
        top = sc.most_common(1)[0][0] if sc else None
        sname = (sess_names.get("%s|%s" % (STATES[ab], top)) or {}).get("name") or top or old.get("session")
        for b in bills: b.pop("_session", None)
        doc = {"jurisdiction": ab, "name": STATES[ab], "session": sname, "generatedAt": now(),
               "source": "Open States (Plural)", "sourceUrl": "https://open.pluralpolicy.com/%s/bills/" % ab.lower(), "bills": bills}
        save(path, doc)
        p = prog.get(ab, {})
        report["states"][ab] = {"count": len(bills), "newest": bills[0]["date"] if bills else None,
            "oldest": bills[-1]["date"] if bills else None, "passed": sum(1 for b in bills if b.get("passed")),
            "session": sname, "sessions_in_file": dict(sc), "pages_fetched": p.get("pages", 0), "max_page": p.get("max_page"),
            "requests_used": p.get("requests", 0), "generatedAt": doc["generatedAt"]}

    per_page = [a.per_page]
    for tier in tiers:
        for ab in states:
            p = prog.setdefault(ab, {"started": now(), "pages": 0, "max_page": None, "requests": 0})
            if p["pages"] >= tier or (p["max_page"] is not None and p["pages"] >= p["max_page"]): continue
            cpath = os.path.join(cache_dir, ab + ".json")
            fresh = load(cpath, []) if p["pages"] else []
            got_any = False
            while p["pages"] < tier and (p["max_page"] is None or p["pages"] < p["max_page"]):
                if not api.can_spend(): break
                page = p["pages"] + 1
                j = api.get("/bills", {"jurisdiction": STATES[ab], "sort": "latest_action_desc", "per_page": per_page[0], "page": page,
                                       "include": ["sponsorships", "sources", "actions"]})
                if j and j.get("_error") == 400 and per_page[0] != 20 and p["pages"] == 0:
                    print("  per_page %d refused; using 20" % per_page[0], flush=True); per_page[0] = 20; continue
                if j is not None: p["requests"] += 1
                if j is None or "_error" in j:
                    if j and j.get("_error") in (400, 404): p["max_page"] = p["pages"]
                    break
                p["max_page"] = (j.get("pagination") or {}).get("max_page") or page
                fresh += [to_bill(ab, b, sess_names) for b in (j.get("results") or [])]
                p["pages"] = page; got_any = True
            if got_any:
                save(cpath, fresh, compact=True)
                write_state(ab, [dict(b) for b in fresh])
                report["generatedAt"] = now(); report["requests"] = {"used_today": api.used_today(), "this_run": api.run_used,
                    "daily_limit_assumed": api.daily_limit, "limits_seen": api.limits_seen, "interval_s": api.interval}
                save(report_path, report); save(prog_path, prog)
                r = report["states"][ab]
                print("%s tier %d: %d bills (pages %d/%s), newest %s, passed %d, used today %d" % (ab, tier, r["count"], p["pages"], p["max_page"], r["newest"], r["passed"], api.used_today()), flush=True)
            if api.stopped: break
        if api.stopped: break
    report["generatedAt"] = now(); report["stopped"] = api.stopped or "all tiers done"
    report["requests"] = {"used_today": api.used_today(), "this_run": api.run_used, "daily_limit_assumed": api.daily_limit,
                          "limits_seen": api.limits_seen, "interval_s": api.interval}
    save(report_path, report); save(prog_path, prog)
    print("done", now(), report["stopped"], "requests this run", api.run_used, "today", api.used_today(), flush=True)

if __name__ == "__main__":
    main()
