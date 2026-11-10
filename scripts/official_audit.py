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
 # IL: the State Board's statewide totals page shows the newest election it has CANVASSED (on Nov 10 2026 that was still the
 # 2026 GENERAL PRIMARY; the general is posted after the December canvass). Reading the primary's counts produced 18 false
 # mismatches/gaps on Nov 10, so the page is used only once it names the 2026 general election as the one shown.
 "IL": [dict(race="senate", url="https://www.elections.il.gov/electionoperations/ElectionVoteTotals.aspx", browser=True,
             expect=r"Election Results\s+2026 GENERAL ELECTION\s+Elections:",
             expect_why="the Illinois State Board of Elections has not posted the Nov 3 2026 general election yet (its statewide page still shows the 2026 General Primary; it posts the general after the December canvass)")],
 "IN": [dict(race="house:*", url="https://enr.indianavoters.in.gov/site/data/OffCatC_1005_B.json", fmt="in")],
 "IA": [dict(race="senate", url="https://electionresults.iowa.gov/IA/127077/", browser=True)],
 "KS": [dict(race="senate", url="https://ent.sos.ks.gov/kssos_ent.html", browser=True)],
 "KY": [dict(race="senate", url="https://vrsws.sos.ky.gov/liveresults?id=2", browser=True)],
 "LA": [dict(race="senate", url="https://voterportal.sos.la.gov/Graphical", browser=True, mode="before")],
 "ME": [dict(race="senate", url="https://www.maine.gov/sos/elections-voting/election-results-data", browser=True)],
 "MD": [dict(race="gov", url="https://elections.maryland.gov/elections/2026/general_results/gen_results_2026_1.html")],
 # MA: electionstats.state.ma.us is the Public Document 43 archive; it adds an election only after certification. Its home page
 # carries other numbers ("30,079 elections"), which were read as Markey's count on Nov 10, so the page must show the 2026 race.
 "MA": [dict(race="senate", url="https://electionstats.state.ma.us/", browser=True,
             expect=r"(?is)2026.{0,200}U\.S\. Senate.{0,200}Markey|Markey.{0,200}2026.{0,200}U\.S\. Senate",
             expect_why="the Massachusetts election archive has not added the Nov 3 2026 U.S. Senate race yet (it adds an election after certification)")],
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
 # NY: fusion voting; each candidate row lists party lines, then the candidate's total (the biggest number in the row)
 "NY": [dict(race="gov", url="https://nyenr.elections.ny.gov/", browser=True, rows="max")],
 "NC": [dict(race="senate", url="https://er.ncsbe.gov/enr/20261103/data/results_0.txt", fmt="nc")],
 "ND": [dict(race="house:AL", url="https://resultsnd.sos.nd.gov/", browser=True)],
 # OH: the Secretary of State's results file is NIST VSSC XML; read as page text its IDs were taken as counts (Nov 10 19:12Z
 # CI run: Landsman "4,078,798,702"). The wild-reading guard lists it as unreadable until an XML parser is written.
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
 # WY: a county-by-county table per race; the statewide count is the race's "Total" row (fmt "wytable"). Reading the
 # biggest number next to the name picked a county's count (Nov 10: Byrd "9,095" = Campbell County's Hageman cell).
 "WY": [dict(race="senate", url="https://sos.wyo.gov/Elections/Docs/2026/Results/General/2026_General_Statewide_Candidates_Summary.pdf", pdf=True, fmt="wytable")],
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
            self.b = self.pw.chromium.launch(headless=True, executable_path=os.environ.get("PW_CHROME") or None)
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
    t = _page_text(chk, browser, until)
    save = os.environ.get("OA_TEXT_SAVE")
    if save and st:
        os.makedirs(save, exist_ok=True)
        open(os.path.join(save, f"{st}.txt"), "w", encoding="utf-8").write(t)
    return t


def _page_text(chk, browser, until=None):
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
    if fmt == "wytable":  # per race: header "Lastname (P)" columns, then county rows, then "Total  n  n  n ..."
        cols = {}
        for block in re.split(r"\n\s*Total\b", text)[:-1]:
            tail = block[block.rfind("Official Summary"):] if "Official Summary" in block else block
            hdr = re.findall(r"([A-Z][A-Za-z'\-.]+(?: [A-Z][A-Za-z'\-.]+)?) \((?:[A-Z]{1,3})\)", tail)
            rest = text[text.index(block) + len(block):]
            tot = [int(x.replace(",", "")) for x in re.findall(r"\d{1,3}(?:,\d{3})+|\d+", rest.lstrip("\r\n").split("\n", 1)[0])]
            for i, h in enumerate(hdr):
                if i < len(tot): cols.setdefault(h.split()[-1].lower(), []).append(tot[i])
        return {n: ({"vals": cols[last_name(n).lower()], "seen": set()} if last_name(n).lower() in cols else None) for n in names}
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
                # a row usually reads "Name  Party  480,868  54.8%": stop at this row's percentage, so the last
                # candidate of a race does not pick up the next race's or the total's number (Nov 10: AR Wadlin,
                # CT-3 Rice, MD White, UT-2 Cottam, UT-3 Hooslyn read a total and voided the race's refresh)
                pc = re.search(r"(?<![\d.,])\d{1,3}(?:\.\d+)?\s*%", w[:cut])
                if pc and chk.get("rows") != "max":
                    if NUM.findall(w[:pc.start()]):          # "480,868 54.8%": the count came first
                        cut = min(cut, pc.end())
                    else:                                    # "54.8% 480,868" / "Percentage 1.80% Votes 4,561"
                        nx = NUM.search(w, pc.end())
                        if nx and nx.end() <= cut: cut = nx.end()
                nums = [int(x.replace(",", "")) for x in NUM.findall(w[:cut])]
                if nums:
                    vals.append(max(nums))
                    seen.update(nums)
        # every reading of this name on the page; the comparer accepts the app's
        # number if ANY reading shows it (a name can appear in several contests)
        # first value = best reading; the rest = every count seen next to the name
        out[n] = ({"vals": [sum(vals)] if chk.get("sum") else vals, "seen": seen} if vals else None)
    return out


APP_SOURCE = {"overlay": False}
GH_ELECTIONS = "https://raw.githubusercontent.com/knowusadmin/knowus-data/main/data/elections/"


def app_reads_overlay(site):
    """True when the live app reads the refreshed counts in this repo (data/elections/) before its own copy (election.js v48+)."""
    try:
        return "KUS_ELEC_GET" in requests.get(f"{site}/election.js?x={random.random()}", headers=UA, timeout=40).text
    except Exception:
        return False


def app_races(site):
    """The counts the app shows: the repo's refreshed copy when the live app reads it (and it is for the live build), else the
    live site's own files."""
    ov = app_reads_overlay(site)
    site_eo = requests.get(f"{site}/data/election-official.json?x={random.random()}", headers=UA, timeout=40).json()
    if ov:
        try:
            r_eo = requests.get(GH_ELECTIONS + f"election-official.json?x={random.random()}", headers=UA, timeout=40).json()
            ov = bool(r_eo.get("builtAt") and site_eo.get("builtAt") and r_eo["builtAt"] >= site_eo["builtAt"])
        except Exception:
            ov = False

    def j(p):
        if ov and p.startswith("data/") and (p == "data/election-official.json" or p.startswith("data/districts/") or p == "data/statewide.json"):
            try:
                return requests.get(GH_ELECTIONS + p[5:] + f"?x={random.random()}", headers=UA, timeout=40).json()
            except Exception:
                pass
        return requests.get(f"{site}/{p}?x={random.random()}", headers=UA, timeout=40).json()
    eo = j("data/election-official.json")
    APP_SOURCE["overlay"] = ov
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
                if re.search(r"Access Denied|403 Forbidden|Request blocked|security check|bot\"?\)? activity|scraping|Attention Required|captcha", text[:3000], re.I) and len(text) < 4000:
                    findings.append(dict(st=st, race=chk["race"], kind="UNREACHABLE", url=chk["url"], detail="the state's results site blocked the automated check (bot protection); compare by hand or find its public results file"))
                    continue
                if not chk.get("fmt") and re.search(r"xsi:type|ObjectId|GpUnit|This XML file does not appear", text[:300000]):
                    findings.append(dict(st=st, race=chk["race"], kind="UNREADABLE", url=chk["url"], detail="the state's results file is XML (NIST election results format); the checker has no parser for it yet, so it was not compared"))
                    continue
                if len(text.strip()) < 50:
                    findings.append(dict(st=st, race=chk["race"], kind="UNREACHABLE", url=chk["url"], detail="the results page came back empty (it did not render for the checker)"))
                    continue
                if chk.get("expect") and not re.search(chk["expect"], text):
                    findings.append(dict(st=st, race=chk["race"], kind="NOT_POSTED", url=chk["url"], detail=chk.get("expect_why") or "the official page does not show the Nov 3 2026 general election yet"))
                    continue
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
                WI = re.compile(r"^(write-?ins?|scattering|blank|void|over ?votes|under ?votes)$", re.I)
                big = [(n, v) for n, v in cmp if v >= 100 and not WI.match(n.strip())]
                def one(n, v):
                    """the count read for this candidate: the only reading, or the only one within canvass range of the app's
                    (a name can appear in two contests on a page, e.g. LA's two Davises)"""
                    o = off.get(n)
                    if not o: return None
                    vs = sorted(set(o["vals"]))
                    if len(vs) == 1: return vs[0]
                    near = [x for x in vs if 0.97 * v <= x <= 1.6 * v]
                    return near[0] if len(near) == 1 else None
                lns = [last_name(n).lower() for n, _ in r["cands"]]
                clash = len(set(lns)) != len(lns)          # two candidates share a last name: never auto-refresh
                if diffs and big and not clash and all(one(n, v) is not None for n, v in big):
                    upd = {}
                    for n, v in r["cands"]:
                        if v is None:
                            continue
                        nv = one(n, v)
                        nv = v if nv is None else nv
                        lo, hi = (0.97 * v, 1.6 * v) if v >= 100 else (0.5 * v, 3 * v + 5)
                        if not (lo <= nv <= hi):
                            nv = None if v >= 100 else v   # a big candidate out of range voids the race
                        upd[n] = nv
                    newvals = [x for x in upd.values() if x is not None and x >= 100]
                    if any(x is None for x in upd.values()) or len(set(newvals)) != len(newvals):
                        upd = None
                # a reading far from the app's count for BOTH leading candidates is not a canvass update: the checker read
                # the wrong thing (another election, a county cell, an ID in an XML file); list it as unreadable, with numbers
                wild = [n for n, (a_, b_) in diffs.items() if a_ >= 1000 and not (a_ / 3 <= b_ <= a_ * 3)]
                if diffs and len(wild) == len(diffs) and len(diffs) >= min(2, len(major)):
                    findings.append(dict(st=st, race=k, kind="UNREADABLE", url=chk["url"],
                                         detail="the count read on the page is nowhere near the app's (" + "; ".join(f"{n}: app {a_:,} vs read {b_:,}" for n, (a_, b_) in diffs.items()) + "): the checker read the wrong figure; check the page by hand"))
                    continue
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
    unk = [f for f in findings if f["kind"] in ("UNREACHABLE", "UNREADABLE", "UNKNOWN", "NOT_POSTED")]
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
