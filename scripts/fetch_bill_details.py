#!/usr/bin/env python3
"""Build per-bill detail JSON for KnowUS from keyless official sources.

usage: fetch_bill_details.py <out_dir> <list_snapshot_dir> [--only US,WA,...]

Reads <list_snapshot_dir>/{J}.json (the Bills tab list snapshots) and writes
<out_dir>/{J}-{k}.json chunk files (k = bucket(id, N); US N=64, states N=16)
plus <out_dir>/meta.json. Sources:
  US  GovInfo bulk BILLSTATUS XML (govinfo.gov/bulkdata/BILLSTATUS/119/...)
  WA  wslwebservices.leg.wa.gov LegislationService (GetLegislation, GetLegislativeStatusChanges, GetSponsors)
  VA  LIS bulk CSVs lis.blob.core.windows.net/lisfiles/<session>/ (HISTORY, SUMMARIES, Sponsors)
  MA  malegislature.gov/api (Documents/{n}, DocumentHistoryActions)
  SD  sdlegislature.gov/api (Bills/{id}, Bills/ActionLog/{id})
  IL  ilga.gov/ftp/legislation/104/BillStatus/XML/ (synopsis, actions, sponsors)
Never invents values: null / [] where a source has nothing. python3 + requests only.
"""
import sys, os, re, json, csv, io, html, time, datetime, traceback, threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import requests, urllib3
urllib3.disable_warnings()

UA = {"User-Agent": "KnowUS-data/1.0 (+https://knowus.sites.tab.bot)"}
CHUNKS = {"US": 64}
DEFAULT_CHUNKS = 16
_tls = threading.local()

def sess():
    s = getattr(_tls, "s", None)
    if s is None:
        s = requests.Session(); s.headers.update(UA)
        a = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=16)
        s.mount("https://", a); s.mount("http://", a); _tls.s = s
    return s

def get(url, tries=5, ok404=False, **kw):
    kw.setdefault("timeout", 30)
    last = None
    for i in range(tries):
        try:
            r = sess().get(url, **kw)
            if r.status_code == 404 and ok404:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                ra = r.headers.get("Retry-After")
                last = "HTTP %d" % r.status_code
                time.sleep(min(float(ra), 30) if ra and ra.isdigit() else 1.5 * 2 ** i)
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = repr(e)[:160]
            time.sleep(1.5 * 2 ** i)
    raise RuntimeError("GET failed %s: %s" % (url, last))

def bucket(i, n):
    h = 0
    for c in i:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h % n

def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def text_of(s):
    """HTML -> plain text. Paragraph/list breaks become newlines (list items get '• '); whitespace collapsed."""
    if not s:
        return None
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<li[^>]*>", "\n• ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|h\d|li|tr|ul|ol)>|<(p|div|h\d|ul|ol)[^>]*>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    lines = [re.sub(r"[ \t\r\f\v]+", " ", l).strip() for l in s.split("\n")]
    out, blank = [], False
    for l in lines:
        if not l:
            blank = True; continue
        if out and blank and not l.startswith("• "):
            out.append("")
        out.append(l); blank = False
    t = "\n".join(out).strip()
    return t or None

def clean(s, n=None):
    if s is None:
        return None
    s = re.sub(r"<[^>]+>", " ", str(s))
    s = re.sub(r"\s+", " ", html.unescape(s).replace("\xa0", " ")).strip()
    if n and len(s) > n:
        s = s[:n - 1].rstrip() + "…"
    return s or None

def d10(s):
    if not s:
        return None
    s = str(s).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return "%s-%02d-%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    m = re.match(r"/Date\((\d+)", s)
    if m:
        return datetime.datetime.utcfromtimestamp(int(m.group(1)) / 1000).date().isoformat()
    return None

def tidy_actions(acts, cap=150):
    seen, out = set(), []
    for a in acts:
        if not a.get("date") or not a.get("text"):
            continue
        k = (a["date"], a["text"])
        if k in seen:
            continue
        seen.add(k); out.append(a)
    # stable sort newest first (source order kept within a day)
    out = [x for _, x in sorted(enumerate(out), key=lambda t: (t[1]["date"], -t[0]), reverse=True)]
    return out[:cap]

def base_record(b):
    """Record from the list snapshot alone (fallback when a source fails)."""
    sp = b.get("sponsor")
    return {"id": b["id"], "number": b.get("number"), "title": b.get("title"),
            "summary": None, "summarySource": None, "introduced": b.get("introduced"),
            "sponsor": {"name": sp, "party": None, "state": None, "district": None} if sp else None,
            "cosponsors": [], "cosponsorCount": None, "committees": [],
            "actions": [{"date": b["date"], "text": b["status"], "chamber": b.get("chamber")}] if b.get("date") and b.get("status") else [],
            "law": b.get("law") or None, "policyArea": None, "url": b.get("url"), "textUrl": None}

# ---------------------------------------------------------------- federal
US_TYPES = {"HR": "hr", "S": "s", "HJRES": "hjres", "SJRES": "sjres", "HCONRES": "hconres",
            "SCONRES": "sconres", "HRES": "hres", "SRES": "sres"}

def us_record(b):
    m = re.match(r"US-(\d+)-([A-Z]+)(\d+)$", b["id"])
    cong, typ, num = m.group(1), m.group(2), m.group(3)
    t = US_TYPES[typ]
    url = "https://www.govinfo.gov/bulkdata/BILLSTATUS/%s/%s/BILLSTATUS-%s%s%s.xml" % (cong, t, cong, t, num)
    r = get(url, headers={"Accept": "application/xml"})
    x = ET.fromstring(r.content).find("bill")
    rec = base_record(b)
    rec["title"] = clean(x.findtext("title")) or rec["title"]
    rec["introduced"] = d10(x.findtext("introducedDate")) or rec["introduced"]
    sp = x.find("sponsors/item")
    if sp is not None:
        rec["sponsor"] = {"name": clean(re.sub(r"\s*\[[^\]]*\]\s*$", "", sp.findtext("fullName") or "")),
                          "party": sp.findtext("party") or None, "state": sp.findtext("state") or None,
                          "district": sp.findtext("district") or None}
    cos = []
    for c in x.findall("cosponsors/item"):
        cos.append({"name": clean(re.sub(r"\s*\[[^\]]*\]\s*$", "", c.findtext("fullName") or "")),
                    "party": c.findtext("party") or None, "state": c.findtext("state") or None,
                    "date": d10(c.findtext("sponsorshipDate")),
                    "withdrawn": bool(c.findtext("sponsorshipWithdrawnDate")),
                    "original": (c.findtext("isOriginalCosponsor") or "").lower() == "true"})
    rec["cosponsorCount"] = sum(1 for c in cos if not c["withdrawn"])
    rec["cosponsors"] = cos[:400]
    comms = []
    for c in x.findall("committees/item"):
        n = clean(c.findtext("name"))
        if not n:
            continue
        n = re.sub(r"\s+Committee$", "", n)
        ch = c.findtext("chamber")
        n = "%s %s" % (ch, n) if ch and not n.startswith(ch) else n
        if n not in comms:
            comms.append(n)
    rec["committees"] = comms
    acts = []
    for a in x.findall("actions/item"):
        src = (a.findtext("sourceSystem/name") or "")
        ch = "House" if "House" in src else "Senate" if "Senate" in src else None
        acts.append({"date": d10(a.findtext("actionDate")), "text": clean(a.findtext("text")), "chamber": ch})
    acts = tidy_actions(acts)
    if acts:
        rec["actions"] = acts
    laws = ["%s %s" % (l.findtext("type") or "Public Law", l.findtext("number")) for l in x.findall("laws/item") if l.findtext("number")]
    rec["law"] = laws[0] if laws else (b.get("law") or None)
    rec["policyArea"] = clean(x.findtext("policyArea/name"))
    sums = [s for s in x.findall("summaries/summary") if (s.findtext("text") or "").strip()]
    if sums:
        s = max(sums, key=lambda s: (s.findtext("actionDate") or "", s.findtext("updateDate") or ""))
        rec["summary"] = text_of(s.findtext("text"))
        rec["summarySource"] = "Congressional Research Service summary (%s, %s)" % (
            clean(s.findtext("actionDesc")) or "summary", d10(s.findtext("actionDate")) or "")
    tv = x.findall("textVersions/item")
    if tv:
        fm = {f.findtext("type"): f.findtext("url") for f in tv[0].findall("formats/item")}
        rec["textUrl"] = fm.get("Formatted Text") or fm.get("PDF") or next(iter(fm.values()), None)
    return rec

# ---------------------------------------------------------------- Washington
WA_NS = "{http://WSLWebServices.leg.wa.gov/}"
WA_BASE = "https://wslwebservices.leg.wa.gov/LegislationService.asmx/"

def wa_records(bills):
    g = lambda e, t: (e.findtext(WA_NS + t) or "").strip()
    # all status changes of the biennium in one call
    today = datetime.date.today().isoformat()
    st = ET.fromstring(get(WA_BASE + "GetLegislativeStatusChangesByDateRange?biennium=2025-26&beginDate=2025-01-01&endDate=" + today, timeout=120).content)
    hist = {}
    for S in st:
        num = g(S, "BillId").split()[-1] if g(S, "BillId") else ""
        hist.setdefault(num, []).append({"date": d10(g(S, "ActionDate")), "text": clean(g(S, "HistoryLine")), "chamber": None})
    def one(b):
        num = re.search(r"(\d+)$", b["number"]).group(1)
        rec = base_record(b)
        try:
            x = ET.fromstring(get(WA_BASE + "GetLegislation?biennium=2025-26&billNumber=" + num).content)
            L = list(x)
            if L:
                # prefer the original version entry for description; digest on any version
                L0 = sorted(L, key=lambda e: (g(e, "SubstituteVersion"), g(e, "EngrossedVersion")))[0]
                rec["title"] = clean(g(L0, "LongDescription")) or rec["title"]
                sp = clean(g(L0, "Sponsor").strip("()"))
                if sp:
                    rec["sponsor"] = {"name": sp, "party": None, "state": "WA", "district": None}
                rec["introduced"] = d10(g(L0, "IntroducedDate")) or rec["introduced"]
                law = None
                for e in L:
                    cs = e.find(WA_NS + "CurrentStatus")
                    if cs is not None:
                        hl = g(cs, "HistoryLine")
                        m = re.search(r"Chapter (\d+), (\d{4}) Laws", hl)
                        if m:
                            law = "Chapter %s, %s Laws" % (m.group(1), m.group(2))
                if law:
                    rec["law"] = law
        except Exception as e:
            rec["_err"] = repr(e)[:120]
        try:
            sx = ET.fromstring(get(WA_BASE + "GetSponsors?biennium=2025-26&billId=" + b["number"].replace(" ", "%20")).content)
            cos = []
            for s in sx:
                if g(s, "Type").lower() == "primary":
                    nm = g(s, "LongName") or g(s, "Name")
                    if rec["sponsor"]:
                        rec["sponsor"]["name"] = nm or rec["sponsor"]["name"]
                    continue
                nm = g(s, "LongName") or g(s, "Name")
                if nm:
                    cos.append({"name": nm, "party": None, "state": "WA", "date": None, "withdrawn": False})
            rec["cosponsors"] = cos[:400]; rec["cosponsorCount"] = len(cos)
        except Exception:
            pass
        acts = tidy_actions(hist.get(num, []))
        if acts:
            rec["actions"] = acts
        comms = []
        for a in reversed(acts):
            mm = re.match(r"Referred to (.+?)\.?$", a["text"] or "")
            if mm and not mm.group(1).startswith("Rules") and mm.group(1) not in comms:
                comms.append(mm.group(1))
            mm = re.match(r"Chapter (\d+), (\d{4}) Laws", a["text"] or "")
            if mm:
                rec["law"] = "Chapter %s, %s Laws" % (mm.group(1), mm.group(2))
        rec["committees"] = comms
        return rec
    with ThreadPoolExecutor(6) as ex:
        recs = list(ex.map(one, bills))
    wa_add_summaries(recs)
    return recs, "Washington State Legislature web services (GetLegislation, GetSponsors, GetLegislativeStatusChangesByDateRange) + bill reports from lawfilesext.leg.wa.gov"


WA_FILES = "https://lawfilesext.leg.wa.gov"

def wa_report_index():
    """Bill-report files per bill number from the lawfilesext directory listings (with modified time)."""
    idx = {}
    for ch in ("House", "Senate"):
        t = get(WA_FILES + "/biennium/2025-26/Htm/Bill%20Reports/" + ch + "/", timeout=60).text
        for dt, href in re.findall(r'(\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2} [AP]M)\s+\d+ <A HREF="([^"]+)"', t, re.I):
            name = requests.utils.unquote(href.rsplit("/", 1)[-1])
            m = re.match(r"(\d{4})(?:-[^ ]+)? ([HS]B[AR]) (.+?) (\d{2})\.htm$", name)
            if not m:
                continue
            idx.setdefault(m.group(1), []).append((datetime.datetime.strptime(dt, "%m/%d/%Y %I:%M %p"), name, href, m.group(3)))
    return idx

def wa_report_summary(href):
    t = get(WA_FILES + href).text
    t = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", " ", t)
    title = clean(re.sub(r"<[^>]+>", " ", (re.search(r"(?is)<body[^>]*>(.*?)(Brief Description|Background)", t) or [None, ""])[1]))
    m = re.search(r'(?is)class="briefSummary"[^>]*>(.*?)</div>', t)
    if m and clean(re.sub(r"<[^>]+>", " ", m.group(1))):
        s = text_of(m.group(1))
        s = re.sub(r"^Brief (?:Summary|Synopsis)[^\n]*\n+", "", s or "").strip()
        return s or None, "brief summary"
    plain = text_of(t) or ""
    m = re.search(r"(?s)\n(?:Summary(?: of (?:Engrossed |Second |First )*(?:Substitute )*Bill)?):\s*(.+?)(?:\n(?:Votes on Final Passage|Appropriation|Fiscal Note|Effective Date|Staff|Public Hearing|Rules Authority):|\Z)", "\n" + plain)
    if m:
        s = m.group(1).strip()
        if len(s) > 3000:
            s = s[:3000].rsplit(" ", 1)[0] + "…"
        return s, "summary"
    return None, None

def wa_add_summaries(recs):
    try:
        idx = wa_report_index()
    except Exception as e:
        print("WA report index failed", e)
        return
    def one(rec):
        num = re.search(r"(\d+)$", rec["number"]).group(1)
        files = idx.get(num) or []
        if not files:
            return
        fbr = [f for f in files if "FBR" in f[3].split()]
        pick = max(fbr or files, key=lambda f: f[0])
        try:
            s, kind = wa_report_summary(pick[2])
        except Exception:
            return
        if s:
            label = "final bill report" if fbr else ("House bill report" if " HB" in " " + pick[1].split(" ")[1][:2] or pick[1].split(" ")[1].startswith("HB") else "Senate bill report")
            rec["summary"] = s
            rec["summarySource"] = "Washington Legislature %s (%s, %s)" % (label, pick[1].rsplit(".", 1)[0], pick[0].date().isoformat())
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(one, recs))

# ---------------------------------------------------------------- Virginia
def va_records(bills):
    files = {}
    def load(code, name):
        k = (code, name)
        if k not in files:
            r = get("https://lis.blob.core.windows.net/lisfiles/%s/%s" % (code, name), ok404=True, timeout=90)
            files[k] = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig", "replace")))) if r is not None else []
        return files[k]
    norm = lambda s: re.sub(r"^([A-Z]+)0*(\d+)$", r"\1\2", (s or "").strip().upper())
    idx = {}
    for code in sorted({re.search(r"/bill-details/(\d+)/", b["url"]).group(1) for b in bills if "/bill-details/" in (b.get("url") or "")}):
        hist, sums, sps = {}, {}, {}
        for h in load(code, "HISTORY.CSV"):
            d = h["History_description"] or ""
            ch = {"H": "House", "S": "Senate"}.get(d[:2].strip(), None) if re.match(r"^[HSG] ", d) else None
            hist.setdefault(norm(h["Bill_id"]), []).append({"date": d10(h["History_date"]), "text": clean(re.sub(r"^[HSG]\s+", "", d)), "chamber": ch})
        for s in load(code, "Summaries.csv"):
            sums.setdefault(norm(s["SUM_BILNO"]), []).append(s)
        for s in load(code, "Sponsors.csv"):
            sps.setdefault(norm(s["BILL_NUMBER"]), []).append(s)
        bl = {norm(r["Bill_id"]): r for r in load(code, "BILLS.CSV")}
        idx[code] = (hist, sums, sps, bl)
    today = datetime.date.today().isoformat()
    out = []
    for b in bills:
        rec = base_record(b)
        m = re.search(r"/bill-details/(\d+)/([A-Z0-9]+)", b.get("url") or "")
        if not m or m.group(1) not in idx:
            rec["_err"] = "no session code in url"; out.append(rec); continue
        hist, sums, sps, bl = idx[m.group(1)]
        k = norm(m.group(2))
        acts = tidy_actions([a for a in hist.get(k, []) if a["date"] and a["date"] <= today])
        if acts:
            rec["actions"] = acts
        if sums.get(k):
            s = sums[k][-1]
            rec["summary"] = text_of(re.sub(r"\?(\??) (?=\d+(?:\.\d+)*[-:])", lambda m: "§§ " if m.group(1) else "§ ", s["SUMMARY_TEXT"] or ""))
            rec["summarySource"] = "Virginia Division of Legislative Services summary (%s)" % (clean(s["SUMMARY_TYPE"]) or "summary").lower()
        chief, cos = None, []
        for s in sps.get(k, []):
            nm = clean(s["MEMBER_NAME"]); t = (s.get("PATRON_TYPE") or "").strip()
            if t.startswith("1") and not chief:
                chief = nm
            elif nm:
                cos.append({"name": nm, "party": None, "state": "VA", "date": None, "withdrawn": False})
        if chief:
            rec["sponsor"] = {"name": chief, "party": None, "state": "VA", "district": None}
        rec["cosponsors"] = cos[:400]; rec["cosponsorCount"] = len(cos) if sps.get(k) else None
        row = bl.get(k)
        if row and (row.get("Chapter_id") or "").strip():
            rec["law"] = "Acts of Assembly Chapter %s" % int(re.sub(r"\D", "", row["Chapter_id"]) or 0)
        comms = []
        for a in reversed(acts):
            mm = re.match(r"Referred to Committee (?:on|for) (.+?)\.?$", a["text"])
            if mm:
                n = "%s %s" % (a["chamber"], mm.group(1)) if a["chamber"] else mm.group(1)
                if n not in comms:
                    comms.append(n)
        rec["committees"] = comms
        out.append(rec)
    return out, "Virginia LIS public bulk files (HISTORY.CSV, Summaries.csv, Sponsors.csv, BILLS.CSV)"

# ---------------------------------------------------------------- Massachusetts
def ma_records(bills):
    api = "https://malegislature.gov/api/GeneralCourts/194/Documents/"
    today = datetime.date.today().isoformat()
    def one(b):
        rec = base_record(b)
        num = b["url"].rstrip("/").split("/")[-1]
        try:
            d = get(api + num).json()
            rec["title"] = clean(d.get("Title")) or rec["title"]
            ps = d.get("PrimarySponsor") or {}
            if ps.get("Name"):
                rec["sponsor"] = {"name": ps["Name"], "party": None, "state": "MA", "district": None}
            cos = []
            for c in d.get("Cosponsors") or []:
                if c.get("Name") and c.get("Name") != ps.get("Name"):
                    cos.append({"name": c["Name"], "party": None, "state": "MA", "date": d10(c.get("ResponseDate")), "withdrawn": False})
            if not rec["sponsor"] and cos and not d.get("PrimarySponsor"):
                pass  # MA lists filers as cosponsors when no primary sponsor; keep them as cosponsors (no guessing)
            rec["cosponsors"] = cos[:400]; rec["cosponsorCount"] = len(cos)
        except Exception as e:
            rec["_err"] = repr(e)[:120]
        try:
            acts = get(api + num + "/DocumentHistoryActions").json()
            acts = [{"date": d10(a.get("Date")), "text": clean(a.get("Action")), "chamber": a.get("Branch") if a.get("Branch") in ("House", "Senate") else None}
                    for a in acts if not a.get("IsStricken")]
            acts = tidy_actions([a for a in acts if a["date"] and a["date"] <= today])
            if acts:
                rec["actions"] = acts
                rec["introduced"] = min(a["date"] for a in acts)
            comms = []
            for a in reversed(acts):
                for mm in re.finditer(r"referred to the (?:joint )?committee on (.+?)(?:\s+-\s+|\s*;|\.?$)", a["text"], re.I):
                    n = clean(mm.group(1))
                    if n and n not in comms:
                        comms.append(n)
            rec["committees"] = comms
            for a in acts:
                mm = re.search(r"Signed by the Governor, Chapter (\d+) of the Acts of (\d{4})", a["text"])
                if mm:
                    rec["law"] = "Chapter %s of the Acts of %s" % (mm.group(1), mm.group(2)); break
        except Exception as e:
            rec["_err"] = repr(e)[:120]
        return rec
    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(one, bills)), "Massachusetts Legislature open API (malegislature.gov/api Documents + DocumentHistoryActions)"

# ---------------------------------------------------------------- South Dakota
def sd_records(bills):
    api = "https://sdlegislature.gov/api/"
    today = datetime.date.today().isoformat()
    def one(b):
        rec = base_record(b)
        bid = b["url"].rstrip("/").split("/")[-1]
        try:
            det = get(api + "Bills/%s" % bid, tries=7).json()
            sps = [s for s in (det.get("BillSponsor") or []) if s.get("Member")]
            nm = lambda s: clean("%s %s" % (s["Member"].get("FirstName", ""), s["Member"].get("LastName", "")))
            prim = [s for s in sps if s.get("SponsorType") == "P"]
            prim.sort(key=lambda s: s.get("MemberType") != b["number"][:1])
            if prim:
                rec["sponsor"] = {"name": nm(prim[0]), "party": None, "state": "SD", "district": None}
            elif det.get("BillCommitteeSponsor"):
                rec["sponsor"] = {"name": clean(det["BillCommitteeSponsor"]), "party": None, "state": "SD", "district": None}
            cos = [{"name": nm(s), "party": None, "state": "SD", "date": None, "withdrawn": False} for s in sps if not (prim and s is prim[0])]
            rec["cosponsors"] = cos[:400]; rec["cosponsorCount"] = len(cos)
        except Exception as e:
            rec["_err"] = repr(e)[:120]
        try:
            log = get(api + "Bills/ActionLog/%s" % bid, tries=7).json()
            acts, comms = [], []
            for a in sorted(log, key=lambda a: (a.get("ActionDate") or "", a.get("StatusSort") or 0)):
                t = a.get("StatusText") or a.get("Description") or ""
                ac = a.get("AssignedCommittee") or {}
                if a.get("ShowAssignedCommittee") and ac.get("FullName"):
                    t += " " + ac["FullName"]
                    if ac["FullName"] not in comms:
                        comms.append(ac["FullName"])
                if a.get("ShowPassed") or a.get("ShowFailed"):
                    r = {"P": "Passed", "F": "Failed"}.get(a.get("Result"))
                    if r:
                        t += ", " + r
                v = a.get("Vote") or {}
                if isinstance(v, dict) and v.get("Yeas") is not None:
                    t += " (Y %s, N %s)" % (v.get("Yeas"), v.get("Nays"))
                body = (a.get("ActionCommittee") or {}).get("Body")
                acts.append({"date": d10(a.get("ActionDate")), "text": clean(t.strip(" ,")),
                             "chamber": {"H": "House", "S": "Senate"}.get(body)})
            acts = tidy_actions([a for a in acts if a["date"] and a["date"] <= today])
            if acts:
                rec["actions"] = acts
            rec["committees"] = comms
        except Exception as e:
            rec["_err"] = repr(e)[:120]
        return rec
    with ThreadPoolExecutor(4) as ex:
        return list(ex.map(one, bills)), "South Dakota Legislature (LRC) public API (api/Bills/{id}, api/Bills/ActionLog/{id})"

# ---------------------------------------------------------------- Illinois
def il_records(bills):
    base = "https://www.ilga.gov/ftp/legislation/104/BillStatus/XML/10400%s%04d.xml"
    today = datetime.date.today().isoformat()
    def one(b):
        rec = base_record(b)
        m = re.match(r"([A-Z]+)\s*(\d+)$", b["number"])
        try:
            x = ET.fromstring(get(base % (m.group(1), int(m.group(2))), verify=False).content)
            seq = list(x.find("actions")) if x.find("actions") is not None else []
            acts = []
            i = 0
            while i < len(seq):
                if seq[i].tag == "statusdate" and i + 2 < len(seq):
                    acts.append({"date": d10(seq[i].text), "text": clean(seq[i + 2].text),
                                 "chamber": clean(seq[i + 1].text) if clean(seq[i + 1].text) in ("House", "Senate") else None})
                    i += 3
                else:
                    i += 1
            chron = [a for a in acts if a["date"] and a["date"] <= today and a["text"]]
            cos, comms = {}, []
            for a in chron:
                t = a["text"]
                mm = re.match(r"Added (?:as )?(?:Chief |Alternate |Alternate Chief )*Co-Sponsor (?:Rep\.|Sen\.)\s*(.+)$", t)
                if mm:
                    cos[mm.group(1)] = {"name": clean(mm.group(1)), "party": None, "state": "IL", "date": a["date"], "withdrawn": False}
                mm = re.match(r"Remove[ds]? (?:as )?(?:Chief |Alternate |Alternate Chief )*Co-Sponsor (?:Rep\.|Sen\.)\s*(.+)$", t)
                if mm and mm.group(1) in cos:
                    cos[mm.group(1)]["withdrawn"] = True
                mm = re.match(r"(?:Assigned to|Referred to)\s+(.+)$", t)
                if mm:
                    n = "%s %s" % (a["chamber"], clean(mm.group(1))) if a["chamber"] else clean(mm.group(1))
                    if n not in comms:
                        comms.append(n)
                mm = re.match(r"Public Act[ .]*(\d{2,3}-\d{3,4})", t)
                if mm:
                    rec["law"] = "Public Act " + mm.group(1)
            c = list(cos.values())
            rec["cosponsors"] = c[:400]; rec["cosponsorCount"] = sum(1 for v in c if not v["withdrawn"])
            rec["committees"] = comms
            ta = tidy_actions(chron)
            if ta:
                rec["actions"] = ta
            syns = x.findall("synopsis")
            if syns:
                s = syns[-1]
                st = text_of(s.findtext("SynopsisText"))
                if st:
                    rec["summary"] = st
                    tt = clean(s.findtext("synopsistitle"))
                    rec["summarySource"] = "Illinois General Assembly synopsis" + (" (%s)" % tt if tt else " (as introduced)")
            for a in chron:
                mm = re.match(r"Filed with (?:the Clerk|Secretary) by (?:Rep\.|Sen\.)\s*(.+)$", a["text"])
                if mm:
                    rec["sponsor"] = {"name": clean(mm.group(1)), "party": None, "state": "IL", "district": None}
                    break
            rec["textUrl"] = None
        except Exception as e:
            rec["_err"] = repr(e)[:120]
        return rec
    with ThreadPoolExecutor(6) as ex:
        return list(ex.map(one, bills)), "Illinois General Assembly BillStatus XML (ilga.gov/ftp/legislation/104/BillStatus/XML)"

STATE_FNS_ALL = {"WA": wa_records, "VA": va_records, "MA": ma_records, "SD": sd_records, "IL": il_records}

# ---------------------------------------------------------------- runner
def run_parallel(fn, bills, workers):
    out, fails = [], []
    def safe(b):
        try:
            return fn(b), None
        except Exception as e:
            return base_record(b), "%s: %s" % (b["id"], repr(e)[:200])
    with ThreadPoolExecutor(workers) as ex:
        for rec, err in ex.map(safe, bills):
            out.append(rec)
            if err:
                fails.append(err)
    return out, fails

def write_jur(out_dir, J, records, source, notes=None):
    n = CHUNKS.get(J, DEFAULT_CHUNKS)
    gen = now()
    chunks = [dict() for _ in range(n)]
    for r in records:
        r.pop("_err", None)
        chunks[bucket(r["id"], n)][r["id"]] = r
    for k in range(n):
        p = os.path.join(out_dir, "%s-%d.json" % (J, k))
        tmp = p + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"jurisdiction": J, "generatedAt": gen, "bills": chunks[k]}, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, p)
    import fcntl
    lockf = open(os.path.join(out_dir, ".meta.lock"), "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    mp = os.path.join(out_dir, "meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {"jurisdictions": {}}
    meta["generatedAt"] = gen
    meta["jurisdictions"][J] = {"chunks": n, "count": len(records),
                                "withSummary": sum(1 for r in records if r.get("summary")),
                                "withActions": sum(1 for r in records if len(r.get("actions") or []) > 1),
                                "withCosponsors": sum(1 for r in records if r.get("cosponsors")),
                                "source": source, "generatedAt": gen}
    if notes:
        meta["jurisdictions"][J]["notes"] = notes
    with open(mp + ".tmp", "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    os.replace(mp + ".tmp", mp)
    fcntl.flock(lockf, fcntl.LOCK_UN); lockf.close()
    print("wrote", J, meta["jurisdictions"][J], flush=True)

STATE_FNS = STATE_FNS_ALL

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_dir = args[0] if args else "detail-out"
    list_dir = args[1] if len(args) > 1 else "data/bills"
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--only="):
            only = a.split("=", 1)[1].split(",")
    os.makedirs(out_dir, exist_ok=True)
    jurs = only or ["US"] + list(STATE_FNS)
    for J in jurs:
        p = os.path.join(list_dir, J + ".json")
        if not os.path.exists(p):
            print("no list snapshot for", J); continue
        bills = json.load(open(p))["bills"]
        t0 = time.time()
        try:
            if J == "US":
                recs, fails = run_parallel(us_record, bills, 8)
                src = "GovInfo bulk BILLSTATUS XML (Library of Congress / Congress.gov data; summaries by the Congressional Research Service)"
                notes = ("%d bills fell back to the list snapshot: %s" % (len(fails), "; ".join(fails[:5]))) if fails else None
            else:
                recs, src = STATE_FNS[J](bills)
                errs = [r for r in recs if r.get("_err")]
                notes = ("%d records partially filled (source errors), e.g. %s" % (len(errs), errs[0]["_err"])) if errs else None
        except Exception as e:
            traceback.print_exc()
            recs = [base_record(b) for b in bills]
            src = "list snapshot only (detail source failed)"
            notes = "detail source failed: %s" % repr(e)[:300]
        write_jur(out_dir, J, recs, src, notes)
        print(J, "took %.0fs" % (time.time() - t0), flush=True)

if __name__ == "__main__":
    main()
