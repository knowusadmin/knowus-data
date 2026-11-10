#!/usr/bin/env python3
"""KnowUS watchdog bot: catches missed or wrong data so nobody has to babysit the app.

Runs every 3 hours in GitHub Actions (free, public repo) and opens/updates ONE issue
("KnowUS watchdog") listing every gap it finds. Writes audit-summary.json.

Checks
 1. Results  - each state's OFFICIAL results page vs the app's counts (scripts/official_audit.py):
               counts the app lacks (GAP) and numbers that differ (MISMATCH).
 2. Ballots  - one test address per state: what the app's ballot shows vs Ballotpedia
               (statewide ballot measures, state legislative chambers up in 2026) and vs the
               app's own election data (a contest listed with fewer than 2 candidates, a missing
               U.S. House race). Every Ballotpedia item carries a link to its article.
 3. Pages    - person pages with no photo (officials in data.js, 2026 candidates) and links the
               link checker has marked down (data/links-down.json).
 4. Banned   - scripts/sources_check.py (the source-policy check) in report mode.
 5. Refresh  - with --refresh-dir, every mismatch read exactly on the official page is written into the
               app's election files under that dir (committed by the workflow), not only flagged.

Usage: python scripts/watchdog.py [--site URL] [--no-browser] [--only results,ballots,pages,banned] [--refresh-dir data/elections]
                                  [--issue] [--summary audit-summary.json]
Exit 1 when any problem is found (so the run shows red), 0 otherwise.
"""
import argparse, json, os, random, re, subprocess, sys, time
import requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import official_audit as OA

UA = OA.UA
ISSUE_TITLE = "KnowUS watchdog"
STATE_NAMES = {'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming'}
# One major-city test address per state (public buildings).
TEST_ADDR = {
 "AL": "710 20th St N, Birmingham, AL 35203",
 "AK": "632 W 6th Ave, Anchorage, AK 99501",
 "AZ": "200 W Washington St, Phoenix, AZ 85003",
 "AR": "500 W Markham St, Little Rock, AR 72201",
 "CA": "200 N Spring St, Los Angeles, CA 90012",
 "CO": "1437 Bannock St, Denver, CO 80202",
 "CT": "550 Main St, Hartford, CT 06103",
 "DE": "800 N French St, Wilmington, DE 19801",
 "FL": "3500 Pan American Dr, Miami, FL 33133",
 "GA": "55 Trinity Ave SW, Atlanta, GA 30303",
 "HI": "530 S King St, Honolulu, HI 96813",
 "ID": "150 N Capitol Blvd, Boise, ID 83702",
 "IL": "2954 W Farwell Ave, Chicago, IL 60645",
 "IN": "200 E Washington St, Indianapolis, IN 46204",
 "IA": "400 Robert D Ray Dr, Des Moines, IA 50309",
 "KS": "455 N Main St, Wichita, KS 67202",
 "KY": "527 W Jefferson St, Louisville, KY 40202",
 "LA": "1300 Perdido St, New Orleans, LA 70112",
 "ME": "389 Congress St, Portland, ME 04101",
 "MD": "100 N Holliday St, Baltimore, MD 21202",
 "MA": "1 City Hall Sq, Boston, MA 02201",
 "MI": "2 Woodward Ave, Detroit, MI 48226",
 "MN": "350 S 5th St, Minneapolis, MN 55415",
 "MS": "219 S President St, Jackson, MS 39201",
 "MO": "414 E 12th St, Kansas City, MO 64106",
 "MT": "210 N 27th St, Billings, MT 59101",
 "NE": "1819 Farnam St, Omaha, NE 68183",
 "NV": "495 S Main St, Las Vegas, NV 89101",
 "NH": "1 City Hall Plz, Manchester, NH 03101",
 "NJ": "920 Broad St, Newark, NJ 07102",
 "NM": "1 Civic Plaza NW, Albuquerque, NM 87102",
 "NY": "1 Centre St, New York, NY 10007",
 "NC": "600 E 4th St, Charlotte, NC 28202",
 "ND": "225 4th St N, Fargo, ND 58102",
 "OH": "40 Severance Cir, Cleveland Heights, OH 44118",
 "OK": "200 N Walker Ave, Oklahoma City, OK 73102",
 "OR": "1221 SW 4th Ave, Portland, OR 97204",
 "PA": "1400 John F Kennedy Blvd, Philadelphia, PA 19107",
 "RI": "25 Dorrance St, Providence, RI 02903",
 "SC": "80 Broad St, Charleston, SC 29401",
 "SD": "224 W 9th St, Sioux Falls, SD 57104",
 "TN": "1 Public Square, Nashville, TN 37201",
 "TX": "901 Bagby St, Houston, TX 77002",
 "UT": "451 S State St, Salt Lake City, UT 84111",
 "VT": "149 Church St, Burlington, VT 05401",
 "VA": "2401 Courthouse Dr, Virginia Beach, VA 23456",
 "WA": "600 4th Ave, Seattle, WA 98104",
 "WV": "105 Kanawha Blvd E, Charleston, WV 25301",
 "WI": "200 E Wells St, Milwaukee, WI 53202",
 "WY": "2101 O Neil Ave, Cheyenne, WY 82001"
}


def site_json(site, path):
    r = requests.get(f"{site}/{path}?x={random.random()}", headers=UA, timeout=40)
    r.raise_for_status()
    return r.json() if not path.endswith(".js") else r.text


# ---------------------------------------------------------------- 2. ballots
def census_cd(addr):
    r = requests.get("https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress",
                     params={"address": addr, "benchmark": "Public_AR_Current", "vintage": "Current_Current", "format": "json", "layers": "all"},
                     headers=UA, timeout=40)
    m = r.json()["result"]["addressMatches"]
    if not m:
        return None, None
    g = m[0]["geographies"]
    cdk = [k for k in g if "Congressional" in k]
    cd = (g[cdk[0]][0] if cdk else {})
    name = str(cd.get("BASENAME") or cd.get("NAME") or "")
    num = "AL" if "Large" in name else (str(int(re.search(r"\d+", name).group())) if re.search(r"\d+", name) else None)
    county = (g.get("Counties") or [{}])[0].get("NAME")
    return num, county


def app_ballot(eo, st, cd):
    """What the app's ballot (ballot.js gen26, 'stored' kind) lists for this state/district."""
    out = []
    for e in eo.get("senate", {}).get(st) or []:
        out.append(dict(contest="U.S. Senate" + (f" ({e.get('label')})" if e.get("label") else ""), cands=len(e.get("cands") or [])))
    ds = ((eo.get("house", {}).get("states", {}) or {}).get(st) or {}).get("districts") or []
    hd = next((d for d in ds if str(d.get("d")) == str(cd) or (cd == "AL" and len(ds) == 1)), None)
    out.append(dict(contest=f"U.S. House {st}-{cd}", cands=len(hd["cands"])) if hd else dict(contest="U.S. House", cands=0, missing=True))
    for e in eo.get("gov", {}).get(st) or []:
        out.append(dict(contest="Governor", cands=len(e.get("cands") or [])))
    return out


def bp_text(browser, url, until):
    if browser.enabled:
        return browser.text(url, until=until, wait=25)
    r = requests.get(url, headers=UA, timeout=40)
    if r.status_code != 200 or not r.text:
        raise RuntimeError(f"Ballotpedia answered {r.status_code} without a browser")
    return r.text


def bp_measures(text):
    """Statewide measure titles listed on Ballotpedia's '<State> 2026 ballot measures' page."""
    t = re.sub(r"\s+", " ", text)
    names = re.findall(r"([A-Z][A-Za-z0-9.'\- ]{2,80}?(?:Amendment|Measure|Initiative|Proposition|Question|Referendum|Issue|Proposal|Bond|Act)(?: \d+| [A-Z0-9]{1,4})?)", t)
    seen, out = set(), []
    for n in names:
        n = n.strip()
        if n.lower() in seen or len(n) < 8:
            continue
        seen.add(n.lower()); out.append(n)
    return out


def bp_chambers(text):
    t = text.replace("\r", "")
    i = t.find("Choose a state below")
    block = t[i:i + 4000] if i >= 0 else t
    ch = {}
    for line in block.split("\n"):
        line = line.strip()
        for ab, nm in STATE_NAMES.items():
            if line.startswith(nm + " ") and re.search(r"(House|Senate|Assembly)$", line) and not line.startswith(nm + " " + "Dakota"):
                rest = line[len(nm) + 1:]
                if rest in ("House", "Senate", "Assembly"):
                    ch.setdefault(ab, []).append(line)
    return ch


# addresses whose ballot the app builds from a full official sample-ballot file (verified complete; v46+)
FULL_BALLOTS = {("CT", None): "ct-2026-11-03.json", ("IL", "Cook"): "il-chicago-2026-11-03.json",
                ("OH", "Cuyahoga"): "oh-cuyahoga-2026-11-03.json", ("NY", "Rockland"): "ny-rockland-2026-11-03.json"}


def check_ballots(site, eo, browser):
    rows = []
    leg_url = "https://ballotpedia.org/State_legislative_elections,_2026"
    try:
        chambers = bp_chambers(bp_text(browser, leg_url, "Wyoming"))
    except Exception as e:
        chambers, leg_err = {}, str(e)[:120]
    else:
        leg_err = None
    for st, addr in TEST_ADDR.items():
        row = dict(st=st, address=addr, problems=[], ballotpedia=[])
        try:
            cd, county = census_cd(addr)
        except Exception as e:
            cd, county = None, None
            row["problems"].append(f"address lookup failed: {str(e)[:80]}")
        row["county"], row["cd"] = county, cd
        full = next((f for (s2, cty), f in FULL_BALLOTS.items() if s2 == st and (cty is None or (county or "").startswith(cty))), None)
        if full:
            try:
                ok = requests.head(f"{site}/data/ballots/{full}", headers=UA, timeout=30).status_code == 200
            except Exception:
                ok = False
            if ok:
                row["appShows"] = [f"the full official sample ballot (data/ballots/{full})"]
                row["complete"] = True
                rows.append(row)
                continue
        shows = app_ballot(eo, st, cd)
        row["appShows"] = [f"{c['contest']} ({c['cands']} candidates)" for c in shows]
        for c in shows:
            if c.get("missing"):
                row["problems"].append("U.S. House race not shown (no district data or district not matched)")
            elif c["cands"] < 2:
                row["problems"].append(f"{c['contest']} lists {c['cands']} candidate(s); the real ballot had more")
        mu = f"https://ballotpedia.org/{STATE_NAMES[st].replace(' ', '_')}_2026_ballot_measures"
        try:
            ms = bp_measures(bp_text(browser, mu, "measure"))
        except Exception as e:
            ms = None
            row["problems"].append(f"Ballotpedia measures page not read: {str(e)[:80]}")
        app_measures = 1 if st == "OH" else 0   # the app adds Ohio Issue 3 only
        if ms:
            row["ballotpedia"].append(dict(item=f"{len(ms)} statewide ballot measure(s)", names=ms[:20], src=mu))
            if len(ms) > app_measures:
                row["problems"].append(f"missing {len(ms) - app_measures} statewide ballot measure(s) (Ballotpedia lists {len(ms)})")
        for chname in chambers.get(st, []):
            row["ballotpedia"].append(dict(item=chname + " (2026 election)", src=leg_url))
        if chambers.get(st):
            row["problems"].append(f"missing state legislative race(s): {', '.join(chambers[st])}")
        row["problems"].append("county, city, judicial and local contests are not in the app (only the county's official sample ballot lists them)")
        if cd is None and not any(p.startswith("address lookup failed") for p in row["problems"]):
            # the Census geocoder did not match this test address: the House line above is the checker's miss, not the app's
            row["problems"] = [p for p in row["problems"] if not p.startswith("U.S. House race not shown")]
            row["problems"].insert(0, "test address not matched by the Census geocoder (House district not checked)")
        rows.append(row)
    return rows, leg_err


def ballot_label_ok(site):
    """Owner's ballot rule (Shmuel, Nov 10 2026): an address's ballot is either verified complete, or it carries the heading
    "Races we've confirmed for your address (may not be complete)" and the blue "See your complete official sample ballot"
    button. The gaps listed above are what the nationwide fill still has to do; each of those ballots is shown with that
    label. What fails the watchdog is the label or the button missing from the live app's ballot code."""
    try:
        js = requests.get(f"{site}/ballot.js?x={random.random()}", headers=UA, timeout=40).text
    except Exception as e:
        return dict(ok=None, why=f"ballot.js not read: {str(e)[:80]}")
    need = ["may not be complete", "See your complete official sample ballot"]
    miss = [n for n in need if n not in js]
    return dict(ok=not miss, missing=miss)


# ---------------------------------------------------------------- 3. pages
def check_pages(site):
    dj = site_json(site, "data.js")
    gd = json.loads(dj[dj.index("=") + 1:].rstrip().rstrip(";"))
    people = gd.get("people", {})
    no_img = sorted([f"{p.get('n')} ({p.get('r', '')})" for p in people.values() if not p.get("img")])
    idx = site_json(site, "data/candidates/index.json")
    photos = site_json(site, "data/candidates/photos.json").get("photos", {})
    cand_no = []
    for race, cs in (idx.get("races") or {}).items():
        for c in cs:
            if not c.get("f"):          # only candidates who have their own page
                continue
            if c.get("id") in photos:
                continue
            m = c.get("m")
            if m and people.get(m, {}).get("img"):
                continue
            cand_no.append(f"{c.get('n')} ({race})")
    try:
        down = site_json(site, "data/links-down.json")
        down_list = (down.get("down") or down.get("links")) if isinstance(down, dict) else down
    except Exception:
        down_list = None
    return dict(officialsNoPhoto=len(no_img), officialsNoPhotoList=no_img[:300], candidatesNoPhoto=len(cand_no), candidatesNoPhotoList=cand_no[:300],
                brokenLinks=(len(down_list) if isinstance(down_list, (list, dict)) else None),
                brokenLinksList=(list(down_list)[:100] if isinstance(down_list, (list, dict)) else None))


# ---------------------------------------------------------------- 4. banned sources
def check_banned(site):
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "sources_check.py")
    if not os.path.exists(p):
        return dict(ran=False, why="scripts/sources_check.py not found")
    out = "banned-report.json"
    r = subprocess.run([sys.executable, p, "--site", site + "/", "--report-only", "--out", out], capture_output=True, text=True, timeout=1500)
    rep = None
    if os.path.exists(out):
        try: rep = json.load(open(out))
        except Exception: rep = None
    tail = (r.stdout or "")[-1500:]
    m = re.search(r"banned\D{0,20}(\d+)", tail, re.I)
    return dict(ran=True, exit=r.returncode, banned=(int(m.group(1)) if m else None), report=rep if isinstance(rep, (dict, list)) and len(json.dumps(rep)) < 20000 else None, tail=tail)


# ---------------------------------------------------------------- report
def summary_md(S):
    L = [f"Watchdog run {S['runAt']} against {S['site']}.", f"**{S['problems']} problem(s)**.", ""]
    res = S.get("results") or {}
    if res:
        L.append(f"### 1. Results vs official sources\nGaps: {len(res['gaps'])} · Mismatches: {len(res['mismatches'])} · Could not check: {len(res['unchecked'])} · OK: {res['ok']}")
        fx = {id(x) for x in res.get("fixedByRefresh") or []}
        if res.get("appReadsRepoCounts") is False:
            L.append("_The live app does not read data/elections/ yet (needs the v48 app build), so refreshed counts below reach phones only with the next site publish._")
        for f in res["gaps"] + res["mismatches"]:
            tag = "FIXED (official count written to data/elections/)" if id(f) in fx else f["kind"]
            L.append(f"- **{tag}** {f['st']} {f['race']}: {f['detail']} ([official page]({f['url']}))")
        for f in res["unchecked"]:
            L.append(f"- not checked: {f['st']} {f['race']} — {f['kind']}: {f['detail']}")
    if S.get("refreshed") is not None:
        L.append(f"\n### Refreshed counts written to data/elections/ ({len(S['refreshed'])} changed)")
        L += [f"- {x}" for x in S["refreshed"][:200]]
    if S.get("refreshError"):
        L.append(f"\nRefresh failed: {S['refreshError']}")
    if S.get("ballots") is not None:
        bl = S.get("ballotLabel") or {}
        L.append("\n### 2. Sample ballots (one address per state)")
        L.append("Label check (incomplete ballot = \"may not be complete\" heading + blue official sample ballot button): " +
                 ("OK in the live app" if bl.get("ok") else ("**MISSING: " + ", ".join(bl.get("missing") or []) + "**" if bl.get("ok") is False else bl.get("why", "not run"))) +
                 ". The gaps below are what the nationwide ballot fill still has to add; each is shown with that label, so they are listed, not failures.")
        for b in S["ballots"]:
            if b["problems"]:
                L.append(f"- **{b['st']}** {b['address']}: app shows {', '.join(b['appShows'])}. " + "; ".join(b["problems"][:-1] or b["problems"]))
    if S.get("pages"):
        p = S["pages"]
        L.append(f"\n### 3. Pages\nOfficials without a photo: {p['officialsNoPhoto']} ({len(p.get('officialsNoPhotoUnexplained') or [])} not yet searched) · Candidates without a photo: {p['candidatesNoPhoto']} ({len(p.get('candidatesNoPhotoUnexplained') or [])} not yet searched) · Links marked down: {p['brokenLinks']} (listed; the app shows \"Website currently down\" next to each)")
        for x in (p.get("officialsNoPhotoUnexplained") or [])[:40] + (p.get("candidatesNoPhotoUnexplained") or [])[:40]:
            L.append(f"- no photo yet: {x}")
    if S.get("banned"):
        b = S["banned"]
        L.append(f"\n### 4. Banned sources\n" + (f"exit {b.get('exit')}, banned: {b.get('banned')}" if b.get("ran") else b.get("why", "")))
    return "\n".join(L)



# ---------- refresh: write the official counts into this repo (data/elections/) ----------
PARTY_K = lambda p: "D" if p and p.startswith("Democ") else ("R" if p and p.startswith("Repub") else "O")


def _leader(cands, key):
    c = [x for x in cands if isinstance(x.get(key), int)]
    if not c:
        return None, None
    top = max(c, key=lambda x: x[key])
    return PARTY_K(top.get("p")), top["n"]


def refresh_counts(site, findings, out_dir):
    """Apply every MISMATCH that carries exact official counts to the app's election files and write them
    to out_dir (data/elections/ in this repo): election-official.json, statewide.json, districts/<ST>.json,
    refresh-patch.json and refresh-log.json. Base = the repo copy when it exists (so refreshes accumulate),
    else the live site's file. Only candidates named on the official page are touched; nothing is estimated."""
    P = OA.refresh_patch(findings, site)
    os.makedirs(os.path.join(out_dir, "districts"), exist_ok=True)

    # the repo copy accumulates refreshes for ONE app build; when the live app was rebuilt since (a newer builtAt on the
    # site's election-official.json), start again from the live files so the overlay never carries an older build
    try:
        site_built = (site_json(site, "data/election-official.json") or {}).get("builtAt")
    except Exception:
        site_built = None
    try:
        repo_built = json.load(open(os.path.join(out_dir, "election-official.json"))).get("builtAt")
    except Exception:
        repo_built = None
    rebase = bool(site_built and (not repo_built or site_built > repo_built))

    def base(rel):
        p = os.path.join(out_dir, rel)
        if os.path.exists(p) and not rebase:
            return json.load(open(p))
        try:
            return site_json(site, "data/" + rel)
        except Exception:
            return None

    eo, sw = base("election-official.json"), base("statewide.json")
    changed = []
    when = P["builtAt"]
    for kind in ("senate", "gov"):
        for st, item in (P.get(kind) or {}).items():
            for e in ((eo or {}).get(kind) or {}).get(st) or []:
                hit = 0
                for c in e.get("cands", []):
                    if c["n"] in item["votes"]:
                        if c.get("votes") != item["votes"][c["n"]]:
                            changed.append(f"{kind} {st} {c['n']}: {c.get('votes')} -> {item['votes'][c['n']]}")
                        c["votes"] = item["votes"][c["n"]]; hit += 1
                if hit:
                    e.setdefault("src", {})["refreshedAt"] = when
                    if "leaderName" in e:
                        e["leader"], e["leaderName"] = _leader(e["cands"], "votes")
            for e in ((sw or {}).get(kind) or {}).get(st) or []:
                for c in e.get("cands", []):
                    if c["n"] in item["votes"]:
                        c["v"] = item["votes"][c["n"]]
                e.setdefault("src", {})["refreshedAt"] = when
    if rebase:
        for st in STATE_NAMES:
            if st not in (P.get("house") or {}):
                try:
                    D0 = site_json(site, f"data/districts/{st}.json")
                    json.dump(D0, open(os.path.join(out_dir, "districts", f"{st}.json"), "w"), ensure_ascii=False, separators=(",", ":"))
                except Exception:
                    pass
    for st, ds in (P.get("house") or {}).items():
        D = base(f"districts/{st}.json")
        if not D or not (D.get("off") or {}).get("r"):
            continue
        for d, item in ds.items():
            r = D["off"]["r"].get(d)
            if not r:
                continue
            for c in r["cands"]:
                if c["n"] in item["votes"]:
                    if c.get("v") != item["votes"][c["n"]]:
                        changed.append(f"house {st}-{d} {c['n']}: {c.get('v')} -> {item['votes'][c['n']]}")
                    c["v"] = item["votes"][c["n"]]
            for dd in (((eo or {}).get("house") or {}).get("states", {}).get(st) or {}).get("districts", []):
                if str(dd.get("d")) == str(d):
                    vm = {c["n"]: c.get("v") for c in r["cands"]}
                    L, N = _leader([dict(n=c["n"], p=c.get("p"), v=vm.get(c["n"])) for c in dd.get("cands", [])], "v")
                    if L:
                        dd["leader"], dd["leaderName"] = L, N
        D["off"].setdefault("src", {})["refreshedAt"] = when
        json.dump(D, open(os.path.join(out_dir, "districts", f"{st}.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    if eo is not None:
        eo["refreshedAt"] = when
        json.dump(eo, open(os.path.join(out_dir, "election-official.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    if sw is not None:
        json.dump(sw, open(os.path.join(out_dir, "statewide.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    json.dump(P, open(os.path.join(out_dir, "refresh-patch.json"), "w"), indent=1)
    json.dump({"runAt": when, "changed": changed}, open(os.path.join(out_dir, "refresh-log.json"), "w"), indent=1)
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="https://knowus.sites.tab.bot")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--only", default="results,ballots,pages,banned")
    ap.add_argument("--issue", action="store_true")
    ap.add_argument("--summary", default="audit-summary.json")
    ap.add_argument("--refresh-dir", default="", help="write refreshed official counts into this dir (e.g. data/elections)")
    a = ap.parse_args()
    site = a.site.rstrip("/")
    only = set(a.only.split(","))
    browser = OA.Browser(not a.no_browser)
    S = dict(runAt=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), site=site, problems=0)
    try:
        if "results" in only:
            f = OA.audit(site, sorted(OA.CHECKS), browser)
            S["results"] = dict(gaps=[x for x in f if x["kind"] == "GAP"], mismatches=[x for x in f if x["kind"] == "MISMATCH"],
                                unchecked=[x for x in f if x["kind"] in ("UNREACHABLE", "UNREADABLE", "UNKNOWN", "NOT_POSTED")], ok=sum(1 for x in f if x["kind"] == "OK"))
            S["results"]["appReadsRepoCounts"] = OA.APP_SOURCE.get("overlay")
            if a.refresh_dir:
                try:
                    S["refreshed"] = refresh_counts(site, f, a.refresh_dir)
                except Exception as e:
                    S["refreshError"] = repr(e)[:500]
            # a mismatch this run fixed itself (exact official counts written to data/elections/, which the live app reads)
            # is reported but is not a failure; one it could not fix needs a person
            fixed = bool(a.refresh_dir and S.get("refreshed") is not None and OA.APP_SOURCE.get("overlay"))
            S["results"]["fixedByRefresh"] = [x for x in S["results"]["mismatches"] if fixed and x.get("refresh")]
            S["results"]["needsPerson"] = [x for x in S["results"]["mismatches"] if not (fixed and x.get("refresh"))]
            S["problems"] += len(S["results"]["gaps"]) + len(S["results"]["needsPerson"])
        if "ballots" in only:
            eo = site_json(site, "data/election-official.json")
            S["ballots"], S["ballotsLegErr"] = check_ballots(site, eo, browser)
            S["ballotLabel"] = ballot_label_ok(site)
            # incomplete ballots are listed (the nationwide fill's to-do list) but are not failures while the app labels
            # them "may not be complete" with the official button; a missing label/button is a failure
            S["problems"] += (1 if S["ballotLabel"].get("ok") is False else 0)
        if "pages" in only:
            S["pages"] = check_pages(site)
            # a person with no photo fails the run unless the photo search checked every allowed source and found none
            # (data/photos-none.json: {"people": {"<name> (<role>)": "where we looked"}}). Links marked down are listed:
            # the app itself shows "Website currently down" next to them and drops the note when the site answers again.
            pg = S["pages"]
            none = set()
            root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
            try:   # photos/MISSING.csv: everyone the photo search found no allowed photo for, with where it looked
                import csv
                for row in csv.DictReader(open(os.path.join(root, "photos", "MISSING.csv"), encoding="utf-8")):
                    if (row.get("name") or "").strip(): none.add(row["name"].strip().lower())
            except Exception:
                pass
            try:
                none |= {k.split(" (")[0].strip().lower() for k in (json.load(open(os.path.join(root, "data", "photos-none.json"))).get("people") or {})}
            except Exception:
                pass
            nm = lambda x: x.split(" (")[0].strip().lower()
            none.add("vacant")   # an empty seat has no one to photograph
            pg["noPhotoSearchedNone"] = len(none)
            pg["officialsNoPhotoUnexplained"] = [x for x in pg.get("officialsNoPhotoList") or [] if nm(x) not in none]
            pg["candidatesNoPhotoUnexplained"] = [x for x in pg.get("candidatesNoPhotoList") or [] if nm(x) not in none]
            S["problems"] += 1 if (pg["officialsNoPhotoUnexplained"] or pg["candidatesNoPhotoUnexplained"]) else 0
        if "banned" in only:
            S["banned"] = check_banned(site)
            if S["banned"].get("ran") and (S["banned"].get("exit") or S["banned"].get("banned")):
                S["problems"] += 1
    finally:
        browser.close()
    json.dump(S, open(a.summary, "w"), indent=1)
    md = summary_md(S)
    print(md)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(md + "\n")
    if a.issue:
        OA.ISSUE_TITLE = ISSUE_TITLE
        OA.update_issue(md[:60000], S["problems"] > 0)
    sys.exit(1 if S["problems"] else 0)


if __name__ == "__main__":
    main()
