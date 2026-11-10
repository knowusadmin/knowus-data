#!/usr/bin/env python3
"""KnowUS official results audit (standing check).

Re-reads each state's OFFICIAL results page (Secretary of State / Board of
Elections / the vendor it hosts results on) and compares it with what the app
shows (the live site's data/election-official.json and data/districts/XX.json).

It FAILS (exit 1) and opens/updates the "Official results audit" issue when:
  * GAP      - the official page shows vote counts for a race the app shows
               as "no count yet", or
  * MISMATCH - a candidate's count on the official page differs from the app.
Pages it could not read are listed as UNREACHABLE (reported, not a failure,
unless --strict).

Sources are official only (see CHECKS). No percentages are used; counts are
read as printed. Usage:
  python scripts/official_audit.py [--site https://knowus.sites.tab.bot]
         [--states OH,TX] [--no-browser] [--strict] [--issue] [--json out.json]
Env: GITHUB_TOKEN + GITHUB_REPOSITORY for --issue.
"""
import argparse, json, os, random, re, sys, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (KnowUS official-results audit; +https://knowus.sites.tab.bot)"}
ISSUE_TITLE = "Official results audit"

# How each state's official page is read. race: senate | gov | house:<d> | house:*
# mode: after (count follows the name) | before (count precedes the name, LA)
# sum: candidate appears on several party lines and is summed (CT)
# browser: page is JS / bot-walled and needs a real browser (Playwright)
CHECKS = {
 "AL": [dict(race="senate", url="https://www2.alabamavotes.gov/electionNight/statewideResultsByContest.aspx?ecode=1001305")],
 "AK": [dict(race="senate", url="https://www.elections.alaska.gov/enr/26GENR/results/ElectionSummaryReportRPT.pdf", pdf=True)],
 "AZ": [dict(race="gov", url="https://app.enhancedvoting.com/results/public/Arizona/elections/110326GeneralElection", browser=True)],
 "AR": [dict(race="senate", url="https://arkansas.tally-enr.com/#bucket=results&filter=Federal", browser=True)],
 "CA": [dict(race="gov", url="https://electionresults.sos.ca.gov/returns/governor", browser=True)],
 "CO": [dict(race="senate", url="https://results.enr.clarityelections.com/CO/127407/", browser=True)],
 "CT": [dict(race="gov", url="https://ctemspublic.tgstg.net/", browser=True, sum=True)],
 "DE": [dict(race="senate", url="https://elections.delaware.gov/results/enr/GE2026.html?group=federal", browser=True)],
 "FL": [dict(race="senate", url="https://results.elections.myflorida.com/", browser=True)],
 "GA": [dict(race="senate", url="https://results.sos.ga.gov/results/public/Georgia/11032026GeneralAndSpecialElection", browser=True)],
 "HI": [dict(race="gov", url="https://elections.hawaii.gov/wp-content/results/2026 General/histatewide.pdf", pdf=True)],
 "ID": [dict(race="senate", url="https://app.enhancedvoting.com/results/public/id/elections/nov2026", browser=True)],
 "IL": [dict(race="senate", url="https://www.elections.il.gov/electionoperations/ElectionVoteTotals.aspx", browser=True)],
 "IN": [dict(race="house:*", url="https://enr.indianavoters.in.gov/site/data/OffCatC_1005_B.json", fmt="in")],
 "IA": [dict(race="senate", url="https://electionresults.iowa.gov/IA/127077/", browser=True)],
 "KS": [dict(race="senate", url="https://ent.sos.ks.gov/kssos_ent.html", browser=True)],
 "KY": [dict(race="senate", url="https://vrsws.sos.ky.gov/liveresults?id=2", browser=True)],
 "LA": [dict(race="senate", url="https://voterportal.sos.la.gov/Graphical", browser=True, mode="before")],
 "ME": [dict(race="senate", url="https://www.maine.gov/sos/elections-voting/election-results-data", browser=True)],
 "MD": [dict(race="gov", url="https://elections.maryland.gov/elections/2026/general_results/gen_results_2026_1.html")],
 "MA": [dict(race="senate", url="https://electionstats.state.ma.us/", browser=True)],
 "MI": [dict(race="senate", url="https://mielections.us/", browser=True)],
 "MN": [dict(race="senate", url="https://electionresultsfiles.sos.mn.gov/20261103/ussenate.txt", fmt="mn")],
 "MS": [dict(race="senate", url="https://www.sos.ms.gov/elections-voting/election-results")],
 "MO": [dict(race="house:1", url="https://enr.sos.mo.gov/PickaRace.aspx", browser=True)],
 "MT": [dict(race="senate", url="https://electionresults.mt.gov/resultsSW.aspx?type=FED&map=CTY", browser=True)],
 "NE": [dict(race="senate", url="https://electionresults.nebraska.gov/resultsSW.aspx?type=SW&map=CTY")],
 "NV": [dict(race="house:*", url="https://silverstateelection.nv.gov/", browser=True)],
 "NH": [dict(race="senate", url="https://www.sos.nh.gov/elections/elections/election-results", browser=True)],
 "NJ": [dict(race="senate", url="https://www.nj.gov/state/elections/election-information-results.shtml", browser=True)],
 "NM": [dict(race="senate", url="https://electionresults.sos.nm.gov/resultsSW.aspx?type=FED&map=CTY")],
 "NY": [dict(race="gov", url="https://nyenr.elections.ny.gov/", browser=True)],
 "NC": [dict(race="senate", url="https://er.ncsbe.gov/enr/20261103/data/results_0.txt", fmt="nc")],
 "ND": [dict(race="house:AL", url="https://resultsnd.sos.nd.gov/", browser=True)],
 "OH": [dict(race="senate", url="https://liveresults.ohiosos.gov/Api/v1/download?filename=VSSC1622XmlFileBlob", browser=True, fetch=True)],
 "OK": [dict(race="senate", url="https://results.okelections.gov/OKER/?elecDate=20261103", browser=True)],
 "OR": [dict(race="senate", url="https://results.oregonvotes.gov/resultsSW.aspx?type=FED&map=CTY")],
 "PA": [dict(race="gov", url="https://www.electionreturns.pa.gov/", browser=True)],
 "RI": [dict(race="senate", url="https://electionresults.ri.gov/results/public/RhodeIsland/elections/2026StatewideGeneralElection", browser=True)],
 "SC": [dict(race="senate", url="https://www.enr-scvotes.org/SC/127300/", browser=True)],
 "SD": [dict(race="senate", url="https://electionresults.sd.gov/resultsSW.aspx?type=SWR&map=CTY")],
 "TN": [dict(race="senate", url="https://www.elections.tn.gov/categories/congressional/offices", browser=True)],
 "TX": [dict(race="senate", url="https://electionresults.sos.state.tx.us/results.html")],
 "UT": [dict(race="house:*", url="https://electionresults.utah.gov/results/public/Utah/elections/General11032026", browser=True)],
 "VT": [dict(race="gov", url="https://static.electionresults.vermont.gov/elections/rss/68d61e96-1d28-4210-8c1d-8e90512ae105/election-summary.xml", fmt="xmlvotes")],
 "VA": [dict(race="senate", url="https://enr.elections.virginia.gov/results/public/virginia/elections/2026-November-General", browser=True)],
 "WA": [dict(race="house:*", url="https://results.votewa.gov/results/public/washington/20261103", browser=True)],
 "WV": [dict(race="senate", url="https://results.enr.clarityelections.com/WV/127496/", browser=True)],
 "WI": [dict(race="gov", url="https://elections.wi.gov/elections/election-results", browser=True)],
 "WY": [dict(race="senate", url="https://sos.wyo.gov/Elections/Docs/2026/Results/General/2026_General_Statewide_Candidates_Summary.pdf", pdf=True)],
}

NUM = re.compile(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d+)(?!\d|,\d|\.\d|\s*%)")
STOP = re.compile(r"\b(total votes|total|vote cast|votes cast|blank votes|over votes|under votes|registered voters)\b", re.I)
SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def last_name(n):
    n = re.sub(r"[\"\u201c\u201d][^\"\u201c\u201d]*[\"\u201c\u201d]", " ", n).replace(",", " ")
    parts = [p for p in n.split() if p.lower().rstrip(".") not in SUFFIX]
    return parts[-1] if parts else n


def get(url, timeout=40):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r


class Browser:
    """Lazy Playwright page; None when Playwright is not installed or --no-browser."""
    def __init__(self, enabled):
        self.enabled, self.pw, self.b, self.page = enabled, None, None, None

    def text(self, url, until=None, wait=25):
        if not self.enabled:
            raise RuntimeError("browser disabled")
        if self.page is None:
            from playwright.sync_api import sync_playwright
            self.pw = sync_playwright().start()
            self.b = self.pw.chromium.launch(headless=True)
            self.page = self.b.new_page(user_agent=UA["User-Agent"].replace("KnowUS", "Chrome KnowUS"))
        self.page.goto(url, wait_until="load", timeout=60000)
        t0, txt = time.time(), ""
        while time.time() - t0 < wait:
            time.sleep(1.5)
            txt = self.page.evaluate("() => document.body ? document.body.innerText : ''")
            if until and re.search(until, txt, re.I):
                time.sleep(1.5)
                txt = self.page.evaluate("() => document.body.innerText")
                break
        return txt

    def close(self):
        try:
            if self.b: self.b.close()
            if self.pw: self.pw.stop()
        except Exception:
            pass


def pdf_text(url):
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(get(url, 60).content); f.flush()
        return subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True, timeout=60).stdout


def page_text(chk, browser, until=None, st=None):
    cache = os.environ.get("OA_TEXT_CACHE")
    if cache and st and os.path.exists(os.path.join(cache, f"{st}.txt")):
        return open(os.path.join(cache, f"{st}.txt"), encoding="utf-8").read()
    if chk.get("pdf"):
        return pdf_text(chk["url"])
    if chk.get("browser"):
        return browser.text(chk["url"], until=until)
    r = get(chk["url"])
    if "json" in r.headers.get("content-type", "") or chk.get("fmt"):
        return r.text
    from bs4 import BeautifulSoup
    s = BeautifulSoup(r.content, "lxml")
    for x in s(["script", "style"]): x.decompose()
    return s.get_text(" ")


def official_counts(text, names, chk):
    """Map each app candidate name -> count read on the official page (or None)."""
    fmt = chk.get("fmt")
    if fmt == "mn":  # MN SOS results file: ...;name;;;party;...;votes;pct;total
        rows = {}
        for line in text.splitlines():
            f = line.split(";")
            if len(f) > 14: rows[f[7].lower()] = int(f[13])
        return {n: ({"vals": [v for k, v in rows.items() if last_name(n).lower() in k], "seen": set()} if any(last_name(n).lower() in k for k in rows) else None) for n in names}
    if fmt == "nc":  # NC SBE results_0.txt JSON list
        rows = [x for x in json.loads(text) if x.get("cnm", "").upper().startswith(chk.get("contest", "US SENATE"))]
        return {n: ({"vals": [int(x["vct"]) for x in rows if last_name(n).lower() in x["bnm"].lower()], "seen": set()} if any(last_name(n).lower() in x["bnm"].lower() for x in rows) else None) for n in names}
    if fmt == "in":  # Indiana ENR JSON: Root.StatewideSummary.Race[].Candidates.Candidate[]
        races = json.loads(text)["Root"]["StatewideSummary"]["Race"]
        d = chk.get("district")
        pool = [c for r in races if d is None or re.search(r"\(%s\) District" % d, r.get("SubSortOrder", ""))
                for c in (r["Candidates"]["Candidate"] if isinstance(r["Candidates"]["Candidate"], list) else [r["Candidates"]["Candidate"]])]
        return {n: ({"vals": [int(c["TOTAL"]) for c in pool if last_name(n).lower() in c["NAME_ON_BALLOT"].lower()], "seen": set()} if any(last_name(n).lower() in c["NAME_ON_BALLOT"].lower() for c in pool) else None) for n in names}
    if fmt == "xmlvotes":  # <Candidate><Name>..</Name>..<Votes>n</Votes> (Vermont election-summary.xml)
        rows = re.findall(r"<Name>([^<]+)</Name>.*?<Votes>(\d+)</Votes>.*?<CandidateType>([^<]*)</CandidateType>", text, re.S)
        return {n: ({"vals": [int(v) for nm, v, ty in rows if last_name(n).lower() in nm.lower() and ty != "Write-in"], "seen": set()} if any(last_name(n).lower() in nm.lower() and ty != "Write-in" for nm, v, ty in rows) else None) for n in names}
    t = re.sub(r"\s+", " ", text)
    keys = [last_name(n) for n in names]
    out = {}
    for n, ln in zip(names, keys):
        vals, seen = [], set()
        first = re.sub(r"[\"\u201c\u201d][^\"\u201c\u201d]*[\"\u201c\u201d]", " ", n).split()[0].strip(".,") if n.split() else ""
        full = list(re.finditer(r"\b" + re.escape(first) + r"\b[^0-9]{0,40}?\b" + re.escape(ln) + r"\b", t, re.I)) if first and first.lower() != ln.lower() and len(first) > 1 else []
        # prefer places where the first and last name appear together (e.g. "Riley Moore" vs "Shelley Moore Capito")
        hits = [re.match(r"", "")] and ([x for x in (re.search(r"\b" + re.escape(ln) + r"\b", t[f.start():f.end() + 1], re.I) for f in full)] and
                [type("M", (), {"start": (lambda self, a=f: a.end() - len(ln)), "end": (lambda self, a=f: a.end())})() for f in full]) \
            or list(re.finditer(r"\b" + re.escape(ln) + r"\b", t, re.I))
        for m in hits:
            if chk.get("mode") == "before":
                w = t[max(0, m.start() - 160):m.start()]
                for ok in keys:
                    if ok.lower() != ln.lower():
                        for mm in re.finditer(r"\b" + re.escape(ok) + r"\b", w, re.I): w = w[mm.end():]
                nums = [int(x.replace(",", "")) for x in NUM.findall(w)]
                if nums:
                    vals.append(nums[-1])
                    seen.add(nums[-1])
            else:
                w = t[m.end():m.end() + 260]
                cut = len(w)
                for ok in keys:
                    if ok.lower() != ln.lower():
                        mm = re.search(r"\b" + re.escape(ok) + r"\b", w, re.I)
                        if mm: cut = min(cut, mm.start())
                st = STOP.search(w)
                if st: cut = min(cut, st.start())
                nums = [int(x.replace(",", "")) for x in NUM.findall(w[:cut])]
                if nums:
                    vals.append(max(nums))
                    seen.update(nums)
        # every reading of this name on the page; the comparer accepts the app's
        # number if ANY reading shows it (a name can appear in several contests)
        # first value = best reading; the rest = every count seen next to the name
        out[n] = ({"vals": [sum(vals)] if chk.get("sum") else vals, "seen": seen} if vals else None)
    return out


def app_races(site):
    def j(p):
        return requests.get(f"{site}/{p}?x={random.random()}", headers=UA, timeout=40).json()
    eo = j("data/election-official.json")
    races = {}
    for st in CHECKS:
        rs = {}
        for kind in ("senate", "gov"):
            for e in eo.get(kind, {}).get(st, []) or []:
                rs[kind] = dict(cands=[(c["n"], c.get("votes")) for c in e.get("cands", [])], noData=bool(e.get("noData")))
        try:
            d = j(f"data/districts/{st}.json")
        except Exception:
            d = {}
        off = (d.get("off") or {}).get("r", {}) if isinstance(d.get("off"), dict) else {}
        for k, v in off.items():
            rs[f"house:{k}"] = dict(cands=[(c["n"], c.get("v")) for c in v.get("cands", [])], noData=False)
        hs = (eo.get("house", {}).get("states", {}) or {}).get(st) or {}
        for dd in hs.get("districts", []) or []:
            key = f"house:{dd['d']}"
            if key not in rs:
                rs[key] = dict(cands=[(c["n"], None) for c in dd.get("cands", [])], noData=True)
        races[st] = rs
    return races


def audit(site, states, browser):
    races = app_races(site)
    findings = []
    for st in states:
        for chk in CHECKS.get(st, []):
            # every race of the state is looked for on the page; only the check's own race is
            # reported as UNREADABLE when its names are not on the page
            want = [k for k in races.get(st, {}) if k == chk["race"] or (chk["race"] == "house:*" and k.startswith("house:")) or chk.get("all", True)]
            if not want:
                want = [chk["race"]]
            try:
                names_all = [n for k in want for n, _ in races.get(st, {}).get(k, {}).get("cands", [])]
                until = (last_name(names_all[0]) + r"[\s\S]{0,140}\d{1,3},\d{3}") if names_all else None
                text = page_text(chk, browser, until, st)
            except Exception as e:
                findings.append(dict(st=st, race=chk["race"], kind="UNREACHABLE", url=chk["url"], detail=str(e)[:200]))
                continue
            for k in want:
                r = races.get(st, {}).get(k)
                if not r or not r["cands"]:
                    findings.append(dict(st=st, race=k, kind="UNKNOWN", url=chk["url"], detail="app has no candidate list for this race"))
                    continue
                names = [n for n, _ in r["cands"]]
                c2 = dict(chk)
                if k.startswith("house:") and chk.get("fmt") == "in":
                    c2["district"] = k.split(":")[1]
                off = official_counts(text, names, c2)
                app_has = any(v is not None for _, v in r["cands"])
                if not app_has:
                    got = {n: o["vals"][0] for n, o in off.items() if o and len(set(o["vals"])) == 1 and o["vals"][0] >= 100}
                    if got:
                        findings.append(dict(st=st, race=k, kind="GAP", url=chk["url"], detail=f"official page shows counts the app lacks: {got}", official=got))
                    continue
                cmp = sorted([(n, v) for n, v in r["cands"] if v is not None], key=lambda x: -x[1])
                major = cmp[:2]
                diffs, missing = {}, []
                for n, v in major:
                    o = off.get(n)
                    if not o:
                        missing.append(n)
                    elif v not in o["vals"] and v not in o["seen"]:
                        diffs[n] = (v, o["vals"][0])
                # refresh: every app candidate with >=100 votes read exactly once on the page
                upd = None
                big = [(n, v) for n, v in cmp if v >= 100]
                lns = [last_name(n).lower() for n, _ in r["cands"]]
                clash = len(set(lns)) != len(lns)          # two candidates share a last name: never auto-refresh
                if diffs and big and not clash and all(off.get(n) and len(set(off[n]["vals"])) == 1 for n, _ in big):
                    upd = {}
                    for n, v in r["cands"]:
                        if v is None:
                            continue
                        o = off.get(n)
                        nv = o["vals"][0] if o and len(set(o["vals"])) == 1 else v
                        lo, hi = (0.97 * v, 1.6 * v) if v >= 100 else (0.5 * v, 3 * v + 5)
                        if not (lo <= nv <= hi):
                            nv = None if v >= 100 else v   # a big candidate out of range voids the race
                        upd[n] = nv
                    newvals = [x for x in upd.values() if x is not None and x >= 100]
                    if any(x is None for x in upd.values()) or len(set(newvals)) != len(newvals):
                        upd = None
                if diffs:
                    findings.append(dict(st=st, race=k, kind="MISMATCH", url=chk["url"], refresh=upd,
                                         detail="; ".join(f"{n}: app {a:,} vs official {b:,}" for n, (a, b) in diffs.items())))
                elif missing and len(missing) == len(major):
                    if not (k == chk["race"] or (chk["race"] == "house:*" and k.startswith("house:"))):
                        continue
                    findings.append(dict(st=st, race=k, kind="UNREADABLE", url=chk["url"], detail="the leading candidates were not found with a count on the page"))
                else:
                    findings.append(dict(st=st, race=k, kind="OK", url=chk["url"], detail=("not found on page: " + ", ".join(missing)) if missing else ""))
    return findings


def refresh_patch(findings, site):
    """Updated counts in the app's own shapes, for the publisher to drop in (scripts/apply_refresh.py)."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    P = {"builtAt": now, "site": site, "senate": {}, "gov": {}, "house": {}, "note": "only races where every candidate with 100+ votes was read exactly once on the official page"}
    for f in findings:
        if f.get("kind") != "MISMATCH" or not f.get("refresh"):
            continue
        st, race = f["st"], f["race"]
        item = {"votes": f["refresh"], "src": {"url": f["url"], "fetchedAt": now}}
        if race in ("senate", "gov"):
            P[race][st] = item
        elif race.startswith("house:"):
            P["house"].setdefault(st, {})[race.split(":")[1]] = item
    return P


def report_md(findings, site):
    bad = [f for f in findings if f["kind"] in ("GAP", "MISMATCH")]
    unk = [f for f in findings if f["kind"] in ("UNREACHABLE", "UNREADABLE", "UNKNOWN")]
    ok = [f for f in findings if f["kind"] == "OK"]
    lines = [f"Run {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} against {site}.",
             f"**{len(bad)} problem(s)** (gaps/mismatches), {len(unk)} not checked, {len(ok)} OK.", ""]
    if bad:
        lines += ["| State | Race | Problem | Detail | Official page |", "|---|---|---|---|---|"]
        lines += [f"| {f['st']} | {f['race']} | {f['kind']} | {f['detail']} | {f['url']} |" for f in bad]
    if unk:
        lines += ["", "Could not check:", ""] + [f"- {f['st']} {f['race']}: {f['kind']} - {f['detail']} ({f['url']})" for f in unk]
    return "\n".join(lines)


def update_issue(body, failing):
    tok, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not tok or not repo:
        print("no GITHUB_TOKEN/GITHUB_REPOSITORY; skipping issue update"); return
    h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{repo}/issues"
    r = requests.get(f"{api}/1", headers=h, timeout=30)
    num = 1 if r.status_code == 200 and "pull_request" not in r.json() else None
    if num is None:
        q = requests.get(api, headers=h, params={"state": "all", "per_page": 100}, timeout=30).json()
        num = next((i["number"] for i in q if i.get("title") == ISSUE_TITLE and "pull_request" not in i), None)
    if num is None:
        if not failing: return
        r = requests.post(api, headers=h, json={"title": ISSUE_TITLE, "body": body, "labels": ["data-audit"]}, timeout=30)
        print("opened issue", r.status_code, r.json().get("number")); return
    requests.patch(f"{api}/{num}", headers=h, json={"title": ISSUE_TITLE, "body": body, "state": "open" if failing else "closed"}, timeout=30)
    if failing:
        requests.post(f"{api}/{num}/comments", headers=h, json={"body": body}, timeout=30)
    print("updated issue", num, "open" if failing else "closed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="https://knowus.sites.tab.bot")
    ap.add_argument("--states", default="")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--issue", action="store_true")
    ap.add_argument("--json", default="")
    ap.add_argument("--refresh-out", default="", help="write updated counts (refresh-patch.json) for the publisher")
    a = ap.parse_args()
    states = [s.strip().upper() for s in a.states.split(",") if s.strip()] or sorted(CHECKS)
    browser = Browser(not a.no_browser)
    try:
        findings = audit(a.site.rstrip("/"), states, browser)
    finally:
        browser.close()
    md = report_md(findings, a.site)
    print(md)
    if a.json:
        json.dump(findings, open(a.json, "w"), indent=1, default=list)
    if a.refresh_out:
        json.dump(refresh_patch(findings, a.site), open(a.refresh_out, "w"), indent=1)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(md + "\n")
    failing = any(f["kind"] in ("GAP", "MISMATCH") for f in findings) or (a.strict and any(f["kind"] in ("UNREACHABLE", "UNREADABLE") for f in findings))
    if a.issue:
        update_issue(md, failing)
    sys.exit(1 if failing else 0)


if __name__ == "__main__":
    main()
