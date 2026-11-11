#!/usr/bin/env python3
"""Build KnowUS historical executive-order data (EOs before the Federal Register API era).
Usage: python3 scripts/build_eo_history.py <out_dir=data/eo/hist> [--cache DIR] [--ucsb-list FILE] [--text-cache DIR]

Numbered orders 1937-1993 (EO 7532-12889) come from the National Archives' Executive Orders Disposition
Tables (archives.gov/federal-register/executive-orders/<year>.html), compiled by the Office of the Federal
Register: number, signing date, Federal Register citation, title and every amendment / revocation.
Nine of those year pages now answer 404 on archives.gov; for those the script reads the Internet Archive's
saved copy of the same archives.gov page (the URL is kept on each order as "via").
Status comes ONLY from those tables, plus the Federal Register's own disposition notes on later orders
(data/eo/<pres>.json "acts"), read in both directions. Nothing comes from news or from AI.
Official PDF: GovInfo's Federal Register edition, by volume and page (govinfo.gov/link/fr/<vol>/<page>).
Text: the order's text as transcribed by the American Presidency Project (UCSB), matched by EO number;
the app shows the opening of it word for word with that source named.
"""
import json, os, re, sys, time, html, collections, datetime, argparse
import requests
UA = {"User-Agent": "KnowUS-data/1.0 (+https://github.com/knowusadmin/knowus-data)"}
ARCH = "https://www.archives.gov/federal-register/executive-orders/"
WAYBACK = "https://web.archive.org/web/2023id_/" + ARCH
INDEX_URL = ARCH + "disposition"
# President, term label, EO range: the Disposition Tables index page (archives.gov/federal-register/executive-orders/disposition)
PRES = [  # id, label, first EO, last EO (as printed on that index page)
  ("clinton", "Bill Clinton (1993–2001)", 12834, 13197),
  ("bush41", "George Bush (1989–1993)", 12668, 12833),
  ("reagan", "Ronald Reagan (1981–1989)", 12287, 12667),
  ("carter", "Jimmy Carter (1977–1981)", 11967, 12286),
  ("ford", "Gerald R. Ford (1974–1977)", 11798, 11966),
  ("nixon", "Richard Nixon (1969–1974)", 11452, 11797),
  ("lbj", "Lyndon B. Johnson (1963–1969)", 11128, 11451),
  ("jfk", "John F. Kennedy (1961–1963)", 10914, 11127),
  ("eisenhower", "Dwight D. Eisenhower (1953–1961)", 10432, 10913),
  ("truman", "Harry S. Truman (1945–1953)", 9538, 10431),
  ("fdr", "Franklin D. Roosevelt (1933–1945)", 6071, 9537),
  ("hoover", "Herbert Hoover (1929–1933)", 5075, 6070),
]
SPLIT = {1945:['roosevelt','truman'],1953:['truman','eisenhower'],1961:['eisenhower','kennedy'],1963:['kennedy','johnson'],
         1969:['johnson','nixon'],1974:['nixon','ford'],1977:['ford','carter'],1981:['carter','reagan'],1989:['reagan','bush'],1993:['bush','clinton']}
RELMAP = {'revoked by':'revoked_by','revoked in part by':'revoked_part_by','partially revoked by':'revoked_part_by','revoked part by':'revoked_part_by',
 'superseded by':'superseded_by','superseded in part by':'superseded_part_by','partially superseded by':'superseded_part_by',
 'superseded or revoked by':'superseded_by','superseded or revoked in part by':'superseded_part_by','rescinded by':'revoked_by',
 'nullified by':'revoked_by','voided by':'revoked_by','revoked by in part by':'revoked_part_by','revoked in pary by':'revoked_part_by',
 'revoked by in part and supplemented by':'revoked_part_by','superseded to extent inconsistent by':'superseded_part_by','authority repealed by':'revoked_by','repealed by':'revoked_by',
 'amended by':'amended_by','amended by (continued)':'amended_by','modified by':'amended_by','suspended by':'suspended_by','reinstated by':'reinstated_by',
 'revokes':'revokes','revokes in part':'revokes_part','partially revokes':'revokes_part','rescinds':'revokes',
 'supersedes':'supersedes','supersedes in part':'supersedes_part','partially supersedes':'supersedes_part','supersedes or revokes':'supersedes',
 'provisionally supersedes':'supersedes_part','supersedes (export control provisions)':'supersedes_part',
 'amends':'amends','modifies':'amends','suspends':'suspends','reinstates':'reinstates'}
BY = ['revoked_by','revoked_part_by','superseded_by','superseded_part_by','amended_by','suspended_by','reinstated_by']
INV = {'revokes':'revoked_by','revokes_part':'revoked_part_by','supersedes':'superseded_by','supersedes_part':'superseded_part_by',
       'amends':'amended_by','suspends':'suspended_by','reinstates':'reinstated_by'}

def get(url, timeout=30, tries=3):
    last = None
    for t in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            return r
        except Exception as e:
            last = e; time.sleep(3 + 3 * t)
    raise last

def page_names():
    out = []
    for y in range(1937, 1994):
        out += [f"{y}-{n}.html" for n in SPLIT[y]] if y in SPLIT else [f"{y}.html"]
    return out

def fetch_pages(cache):
    os.makedirs(cache, exist_ok=True); via = {}
    for p in page_names():
        fp = os.path.join(cache, p)
        if not os.path.exists(fp):
            r = get(ARCH + p)
            ok = r.status_code == 200 and 'name="' in r.text and 'Executive Order' in r.text
            if not ok:
                r = get(WAYBACK + p, timeout=60)
                ok = r.status_code == 200 and 'name="' in r.text and 'Executive Order' in r.text
                if ok: open(fp + ".via", "w").write(WAYBACK + p)
            if not ok: print("page not available:", p, file=sys.stderr); continue
            open(fp, "w").write(r.text); time.sleep(0.5)
        if os.path.exists(fp + ".via"): via[p] = open(fp + ".via").read().strip()
    return via

def clean(s):
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S); s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s).replace("\xa0", " ")).strip()

def isodate(s):
    s = re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip().rstrip(".").strip()
    s = re.sub(r"(\d)\.\s*(\d{4})", r"\1, \2", s).replace("Sept.", "September").replace("Sept ", "September ")
    for f in ("%B %d, %Y", "%B %d,%Y", "%b %d, %Y", "%B %d %Y", "%b. %d, %Y"):
        try:
            d = datetime.datetime.strptime(s, f).date()
            return d.isoformat() if 1700 < d.year < 2100 else ""
        except ValueError: pass
    return ""

DATE_RE = re.compile(r"([A-Z][a-z]+\.? \d{1,2}, ?\d{4})")
def parse_refs(s):
    out = []
    for part in re.split(r";\s*", s):
        part = part.strip().rstrip(";").strip()
        if not part: continue
        inpart = bool(re.search(r"\bin part\b", part, re.I))
        m = re.match(r"(?:EO|E\.O\.|Executive Order(?: No\.)?)\s*(\d+(?:-?[A-C])?)\b\s*,?\s*(.*)", part)
        dm = DATE_RE.search(part)
        d = isodate(dm.group(1)) if dm else ""
        if m: out.append({"eo": m.group(1).replace("A", "-A").replace("--", "-") if re.fullmatch(r"\d+A", m.group(1)) else m.group(1), "date": d, "part": inpart, "raw": part})
        elif dm or len(part) > 6: out.append({"eo": "", "date": d, "part": inpart, "raw": part})
    return out

def parse_page(path):
    h = open(path, encoding="utf-8", errors="replace").read()
    pos = [m for m in re.finditer(r'<a\s+name="(\d[^"]*)"\s*>\s*</a>', h) if re.search(r"Executive\s+Order", h[max(0, m.start()-80):m.start()+250])]
    out = []
    for k, m in enumerate(pos):
        seg = h[m.end():(pos[k+1].start() if k+1 < len(pos) else len(h))]
        f = seg.find("</section>"); seg = seg[:f] if f >= 0 else seg
        mm = re.match(r"(.*?)</strong>(.*?)</p>(.*)", seg, re.S)
        if not mm: continue
        num = re.sub(r"^Executive Order\s*", "", clean(mm.group(1))) or m.group(1)
        title = clean(mm.group(2))
        t2 = re.match(r"^-([A-C])\s+(.*)", title)
        if t2 and "-" not in num: num, title = num + "-" + t2.group(1), t2.group(2)
        num = re.sub(r"^(\d+)([A-C])$", r"\1-\2", num)
        lis = [clean(l) for l in re.findall(r"<li[^>]*>(.*?)(?=<li|</ul>)", mm.group(3), re.S)]
        out.append({"n": num, "t": title, "lis": lis, "anchor": m.group(1)})
    return out

def numkey(n):
    m = re.match(r"(\d+)(?:-([A-C]))?", n); return (int(m.group(1)), m.group(2) or "") if m else (0, "")

def pres_of(n):
    v = numkey(n)[0]
    for pid, label, lo, hi in PRES:
        if lo <= v <= hi: return pid
    return None

def _words(s):
    return set(w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2 and w not in ("the", "and", "for", "executive", "order", "orders", "certain"))
def text_mismatch(r, tx):
    """The transcription is used only when its EO number, signing date and title agree with the table."""
    m = re.match(r"Executive Order (\d+(?:-?[A-Z])?)", tx.get("title", ""))
    if not m or re.sub(r"^(\d+)-?([A-Z])$", r"\1-\2", m.group(1)) != r["n"]: return "number differs"
    if r["s"] and tx.get("date") and abs((datetime.date.fromisoformat(r["s"]) - datetime.date.fromisoformat(tx["date"])).days) > 3:
        return "date differs: table " + r["s"] + ", transcription " + tx["date"]
    t2 = tx.get("title", "").split("\u2014", 1)[-1]
    a, b = _words(r["t"]), _words(t2)
    if a and b and len(a & b) / min(len(a), len(b)) < 0.5:
        body = _words(tx.get("text", "")[:6000])
        if not (a and len(a & body) / len(a) >= 0.75): return "title differs: " + t2[:120]
    return None

# ---------- before 1937: the numbered series 1–7531 and the unnumbered orders ----------
# The disposition tables start in 1937. Older numbered orders come from the WPA Historical Records Survey's
# "Presidential Executive Orders, Numbered 1-8030, 1862-1938" (Clifford L. Lord, ed., 1944; public-domain scan
# at the Internet Archive, catalogued at HathiTrust), whose entries give each order's number, date and a
# one-line description. Orders the American Presidency Project (UCSB) also carries get its title, date check and text.
# Unnumbered orders (Washington to the 1930s) come only from UCSB's "Executive Orders" category.
LORD_URL = "https://archive.org/download/PresidentialExecutiveOrdersV1/PresidentialExecutiveOrdersV1_djvu.txt"
LORD_PAGE = "https://archive.org/details/PresidentialExecutiveOrdersV1"
LORD_LABEL = "Archived copy (WPA Historical Records Survey, 1944)"
TERMS = [  # id, label, first day in office (orders are matched to a president by signing date)
  ("washington", "George Washington (1789–1797)", "1789-04-30"), ("jadams", "John Adams (1797–1801)", "1797-03-04"),
  ("jefferson", "Thomas Jefferson (1801–1809)", "1801-03-04"), ("madison", "James Madison (1809–1817)", "1809-03-04"),
  ("monroe", "James Monroe (1817–1825)", "1817-03-04"), ("jqadams", "John Quincy Adams (1825–1829)", "1825-03-04"),
  ("jackson", "Andrew Jackson (1829–1837)", "1829-03-04"), ("vanburen", "Martin Van Buren (1837–1841)", "1837-03-04"),
  ("wharrison", "William Henry Harrison (1841)", "1841-03-04"), ("tyler", "John Tyler (1841–1845)", "1841-04-04"),
  ("polk", "James K. Polk (1845–1849)", "1845-03-04"), ("taylor", "Zachary Taylor (1849–1850)", "1849-03-05"),
  ("fillmore", "Millard Fillmore (1850–1853)", "1850-07-09"), ("pierce", "Franklin Pierce (1853–1857)", "1853-03-04"),
  ("buchanan", "James Buchanan (1857–1861)", "1857-03-04"), ("lincoln", "Abraham Lincoln (1861–1865)", "1861-03-04"),
  ("ajohnson", "Andrew Johnson (1865–1869)", "1865-04-15"), ("grant", "Ulysses S. Grant (1869–1877)", "1869-03-04"),
  ("hayes", "Rutherford B. Hayes (1877–1881)", "1877-03-04"), ("garfield", "James A. Garfield (1881)", "1881-03-04"),
  ("arthur", "Chester A. Arthur (1881–1885)", "1881-09-20"), ("cleveland1", "Grover Cleveland (1885–1889)", "1885-03-04"),
  ("bharrison", "Benjamin Harrison (1889–1893)", "1889-03-04"), ("cleveland2", "Grover Cleveland (1893–1897)", "1893-03-04"),
  ("mckinley", "William McKinley (1897–1901)", "1897-03-04"), ("tr", "Theodore Roosevelt (1901–1909)", "1901-09-14"),
  ("taft", "William Howard Taft (1909–1913)", "1909-03-04"), ("wilson", "Woodrow Wilson (1913–1921)", "1913-03-04"),
  ("harding", "Warren G. Harding (1921–1923)", "1921-03-04"), ("coolidge", "Calvin Coolidge (1923–1929)", "1923-08-03"),
  ("hoover", "Herbert Hoover (1929–1933)", "1929-03-04"), ("fdr", "Franklin D. Roosevelt (1933–1945)", "1933-03-04"),
]
UCSB_PRES = {"George Washington": "washington", "John Adams": "jadams", "Thomas Jefferson": "jefferson", "James Madison": "madison",
  "James Monroe": "monroe", "John Quincy Adams": "jqadams", "Andrew Jackson": "jackson", "Martin van Buren": "vanburen",
  "Martin Van Buren": "vanburen", "William Henry Harrison": "wharrison", "John Tyler": "tyler", "James K. Polk": "polk",
  "Zachary Taylor": "taylor", "Millard Fillmore": "fillmore", "Franklin Pierce": "pierce", "James Buchanan": "buchanan",
  "Abraham Lincoln": "lincoln", "Andrew Johnson": "ajohnson", "Ulysses S. Grant": "grant", "Rutherford B. Hayes": "hayes",
  "James A. Garfield": "garfield", "Chester A. Arthur": "arthur", "Benjamin Harrison": "bharrison", "William McKinley": "mckinley",
  "Theodore Roosevelt": "tr", "William Howard Taft": "taft", "Woodrow Wilson": "wilson", "Warren G. Harding": "harding",
  "Calvin Coolidge": "coolidge", "Herbert Hoover": "hoover", "Franklin D. Roosevelt": "fdr"}
def term_of(date):
    pid = None
    for p, label, start in TERMS:
        if date and date >= start: pid = p
    return pid
MON = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'hay':5,'june':6,'jun':6,'july':7,'jul':7,'aug':8,'sept':9,'sep':9,'oct':10,'nov':11,'dec':12}
ROMAN = {"I": 1, "1": 1, "l": 1}
def lord_text(cache):
    fp = os.path.join(cache, "lord-1944-numbered.txt")
    if not os.path.exists(fp):
        r = get(LORD_URL, timeout=120); open(fp, "w").write(r.text)
    t = open(fp).read()
    i = t.find("EXECUTIVE  ORDER  TITLE  LIST")
    return t[i:] if i >= 0 else t
def lord_clean(s):
    s = re.sub(r"\s+", " ", s).strip().lstrip("*# ").strip()
    s = re.sub(r"(\w)- (\w)", r"\1\2", s)
    s = re.sub(r"\bE\. ?[0O]\. ?", "E. O. ", s).replace("’", "'").replace("Sec'y", "Secretary")
    refs = []
    while True:  # trailing references to where the text is printed ("VI R 122", "1907 CSR 131", "I Fed. Reg. 1312", "IR 19; III K 669")
        m = re.search(r"(?:^|[.;]\s*)((?:[IVXl1]{1,4}|Ill|Til|\d{4}|[A-Z][a-z]{2,4}\.? \d{4})?\s*(?:D\.\s*)?(?:R|K|Fed\.\s*Reg\.|CSR|CSA|GLO|MR|IR|CFR|Stat\.\s*L\.|Richardson)\s*[\d][\d,\- ]*(?:[A-Za-z]{0,6}\s*\d{4}\s*CSA\s*[\d\-, ]+)?)[.;]?\s*$", s)
        if not m or m.start(1) < 25: break
        refs.insert(0, m.group(1).strip()); s = s[:m.start(1)].rstrip(" ;.") + "."
    return s.strip(), refs
def parse_lord(txt):
    year = None; cur = None; out = []; page = None
    ent = re.compile(r"^\[?(\d{1,4}(?:\s*-\s*[A-Z0-9]{1,2})*(?:\s*,\s*\d{1,4}(?:-[A-Z0-9]{1,2})?)*)\]?\s*\*?\s*:\s*(.*)$")
    dre = re.compile(r"^([A-Z][a-z]{2,4})\.?\s+(\S{1,3}?)\*?(?:\s+|$)(.*)$")
    LS = [x.strip() for x in txt.split("\n")]; LS = [x for x in LS if x]
    for i, l in enumerate(LS):
        if re.fullmatch(r"(18[6-9]\d|19[0-3]\d)", l):
            # a year heading starts a year or tops a page; a bare year inside a wrapped description is neither
            prev = LS[i - 1] if i else ""; nxt = LS[i + 1] if i + 1 < len(LS) else ""
            heading = bool(ent.match(nxt) and dre.match(ent.match(nxt).group(2))) or prev.startswith("Digitized") or prev == "Google" or prev.startswith("EXECUTIVE")
            if heading: year = int(l); continue
            if not heading:
                if cur: cur["text"] += " " + l
                continue
            continue
        pm = re.fullmatch(r"[\[f]\s*(\d{1,3})\s*[\]'’]?", l)
        if pm: page = int(pm.group(1)); continue
        if l.startswith("Digitized") or l == "Google": continue
        m = ent.match(l)
        if m and year:
            dm = dre.match(m.group(2)); mon = MON.get(dm.group(1).lower()) if dm else None
            if mon:
                dd = dm.group(2).rstrip("*"); day = int(dd) if dd.isdigit() and 1 <= int(dd) <= 31 else None
                ns = [re.sub(r"^(\d+)-?([A-Z])$", r"\1-\2", re.sub(r"\s+", "", x)) for x in m.group(1).split(",")]
                cur = {"ns": ns, "y": year, "m": mon, "d": day, "text": dm.group(3), "page": page, "notes": []}
                out.append(cur); continue
            if m.group(2).startswith("[") or re.match(r"See\b", m.group(2)): cur = {"ns": [], "text": "", "notes": []}; continue  # "3016-B: See Jan. 11, 1919." points to the real entry
        if l[0] in "*#•" and cur: cur["notes"].append(l.lstrip("*#• ").strip()); continue
        if cur: cur["text"] += " " + l
    return out
def early_records(a, texts, log):
    """Numbered orders before EO 7532 and unnumbered orders, as records shaped like the disposition-table ones."""
    recs = {}
    try: L = parse_lord(lord_text(a.cache))
    except Exception as e: L = []; log["earlyError"] = str(e)[:200]
    skipped = []
    # OCR misreads a digit now and then (5000 printed as "6000"). From 1900 the list runs in number order, so a
    # number far from its neighbours is kept only when one OCR-confusable digit change puts it back in place AND the
    # American Presidency Project has that number on the same date; otherwise the entry is left out.
    CONF = {"0": "689", "1": "7", "3": "8", "5": "6", "6": "58", "7": "1", "8": "036", "9": "0"}
    def lead(e):
        m = re.match(r"\d+", e["ns"][0]) if e["ns"] else None; return int(m.group(0)) if m else None
    def eday(e): return datetime.date(e["y"], e["m"], e["d"] or 15)
    idxs = [i for i, e in enumerate(L) if lead(e) is not None]; N = [lead(L[i]) for i in idxs]
    allnums = collections.Counter(N); ocr_fixed = []; ocr_dropped = []
    def ucsb_same_day(c, e):
        tx = texts.get(str(c))
        return bool(tx and tx.get("date") and abs((datetime.date.fromisoformat(tx["date"]) - eday(e)).days) <= (3 if e["d"] else 31))
    # the list runs in number order: entries on the longest non-decreasing run of numbers are in place; any other
    # entry is a misread (or out of place) and is fixed only as below, else left out
    import bisect
    tails, tail_k, parent = [], [], [-1] * len(N)
    for k, v in enumerate(N):
        j = bisect.bisect_right(tails, v)
        if j == len(tails): tails.append(v); tail_k.append(k)
        else: tails[j] = v; tail_k[j] = k
        parent[k] = tail_k[j - 1] if j else -1
    inrun = set(); k = tail_k[-1] if tail_k else -1
    while k >= 0: inrun.add(k); k = parent[k]
    runk = sorted(inrun)
    for k, i in enumerate(idxs):
        e = L[i]; v = N[k]; sv = str(v)
        tx = texts.get(sv)
        wrong_day = bool(tx and tx.get("date") and abs((datetime.date.fromisoformat(tx["date"]) - eday(e)).days) > 366)
        if k in inrun and not wrong_day: continue
        if not wrong_day and re.fullmatch(r"\d+-[A-Z0-9]{1,2}", e["ns"][0]) and v in set(N[q] for q in runk):
            continue  # a lettered order (3016-R) listed beside its base number
        p = bisect.bisect_left(runk, k)
        lo = N[runk[p - 1]] if p > 0 else 0
        hi = N[runk[p]] if p < len(runk) and runk[p] != k else (N[runk[p + 1]] if p + 1 < len(runk) else 99999)
        cands = sorted(set(int(sv[:j] + alt + sv[j + 1:]) for j, ch in enumerate(sv) for alt in CONF.get(ch, "") if not (alt == "0" and j == 0)))
        cands = [c for c in cands if lo <= c <= hi]
        ok = [(c, "ucsb") for c in cands if ucsb_same_day(c, e)]
        free = [c for c in cands if not allnums.get(c) and not texts.get(str(c))]
        if not ok and len(free) == 1: ok = [(free[0], "gap")]
        if len(ok) == 1:
            c, why = ok[0]; allnums[c] += 1
            e["notes"].append("The scan of the WPA list reads this number as " + sv + "; " + ("the American Presidency Project lists EO " + str(c) + " on the same date." if why == "ucsb" else "EO " + str(c) + " is the only reading that fits the list's number order and is not already in the list."))
            e["ns"] = [str(c) + e["ns"][0][len(sv):]] + e["ns"][1:]; ocr_fixed.append([sv, str(c), why])
        else:
            ocr_dropped.append(sv); e["ns"] = []
    log["earlyOcrNumberFixed"] = ocr_fixed; log["earlyOcrNumberDropped"] = ocr_dropped
    for e in L:
        if re.search(r"not a numbered order", e["text"], re.I): e["notes"].append("Not a Numbered Order.")
        notes = [re.sub(r"\s+", " ", x) for x in e["notes"]]
        if any(re.search(r"not a numbered order|does not appear in the official numbered series", x, re.I) for x in notes):
            skipped.append(e["ns"][0] if e["ns"] else ""); continue
        desc, refs = lord_clean(e["text"])
        s = "%04d-%02d-%02d" % (e["y"], e["m"], e["d"]) if e["d"] else ""
        try: datetime.date.fromisoformat(s)
        except Exception: s = ""
        fr = ""
        for x in refs:
            m = re.match(r"(?:I|1|l)\s*(?:D\.\s*)?Fed\.\s*Reg\.\s*(\d+)", x)
            if m: fr = m.group(1)
        main_ns = [n for n in e["ns"] if re.fullmatch(r"\d{1,4}(?:-[A-Z0-9]{1,2})?", n)]
        for k, n in enumerate(main_ns):
            if numkey(n)[0] >= 7532 or n in recs: continue
            nt = ["Description from the WPA Historical Records Survey list (1944)" + (", page " + str(e["page"]) if e.get("page") else "") + "."]
            nt += [x.rstrip(".") + "." for x in notes if x]
            if len(main_ns) > 1: nt.append("Issued as one order numbered " + " and ".join(main_ns) + ".")
            if refs: nt.append("Printed in: " + "; ".join(refs) + " (as cited by the WPA list).")
            recs[n] = {"n": n, "t": desc, "s": s, "d": "", "c": ("1 FR " + fr) if fr else "", "rel": collections.defaultdict(list),
                       "notes": nt, "u": LORD_PAGE, "ul": LORD_LABEL,
                       "pdf": ("https://www.govinfo.gov/link/fr/1/" + fr) if fr else "", "early": True, "srcname": "WPA list",
                       "srcid": "wpa"}
    log["earlySkippedNotNumbered"] = skipped
    # UCSB numbered orders the WPA list parse did not yield (OCR gaps) — kept when UCSB carries the number
    for n, tx in texts.items():
        if numkey(n)[0] >= 7532 or n in recs or not tx.get("date"): continue
        t = tx.get("title", "").split("\u2014", 1)
        recs[n] = {"n": n, "t": t[1].strip() if len(t) > 1 else "", "s": tx["date"], "d": "", "c": "", "rel": collections.defaultdict(list),
                   "notes": ["Listed from the American Presidency Project; not matched in the WPA list."], "u": "", "pdf": "",
                   "early": True, "srcname": "American Presidency Project", "srcid": "ucsb"}
    for r in recs.values():
        tx = texts.get(r["n"])
        if tx and r["srcid"] == "wpa":
            t = tx.get("title", "").split("\u2014", 1)
            if len(t) > 1 and t[1].strip():
                r["notes"].insert(0, "WPA list description: " + r["t"]); r["t"] = t[1].strip()
    return recs
def unnumbered(texts_all, log):
    rows = []; seq = collections.Counter()
    for tx in sorted(texts_all, key=lambda j: (j.get("date", ""), j.get("url", ""))):
        if tx.get("n") or not tx.get("date") or tx["date"] >= "1937-01-01": continue
        # every item of UCSB's Executive Orders category counts (a few are titled "Commission" or "Order ...")
        pid = UCSB_PRES.get(tx.get("pres", "")) or term_of(tx["date"])
        if pid == "cleveland" or tx.get("pres") == "Grover Cleveland": pid = "cleveland1" if tx["date"] < "1893-03-04" else "cleveland2"
        if not pid: continue
        key = pid + "-" + tx["date"].replace("-", ""); seq[key] += 1
        n = "u-" + key + ("" if seq[key] == 1 else "-" + str(seq[key]))
        t = tx["title"].split("\u2014", 1); note = "Unnumbered order, listed in the American Presidency Project's Executive Orders collection."
        title = (t[1].strip() if t[0].strip() == "Executive Order" else tx["title"].strip()) if len(t) > 1 and t[1].strip() else ("" if re.fullmatch(r"Executive Order\s*", tx["title"]) else tx["title"].strip())
        if not title:  # untitled in the source: show the order's own opening words
            body = re.sub(r"\s+", " ", re.sub(r"^(?:[A-Z][A-Za-z .,]*\d{4}\.?\s*)", "", tx["text"].strip())).strip()
            w = body[:110].rsplit(" ", 1)[0] if len(body) > 110 else body
            title = "\u201c" + w.rstrip(" ,;:") + ("\u2026" if len(body) > 110 else "") + "\u201d"
            note += " It has no title there; the title shown is the order's opening words."
        rows.append((pid, tx, {"n": n, "t": title, "s": tx["date"], "d": "", "c": "", "pdf": "",
                     "u": "", "st": "N", "by": [], "acts": [], "notes": note,
                     "abs": "", "src": "ucsb"}))
    return rows

def neighbour_date(order, n, recs):
    i = order.index(n)
    for d in range(1, 30):
        for j in (i - d, i + d):
            if 0 <= j < len(order) and recs[order[j]]["s"]: return recs[order[j]]["s"]
    return ""
def build(a):
    via = fetch_pages(a.cache)
    texts, texts_all = {}, []
    if a.text_cache and os.path.isdir(a.text_cache):
        for f in os.listdir(a.text_cache):
            if f.endswith(".json"):
                try: j = json.load(open(os.path.join(a.text_cache, f)))
                except Exception: continue
                if j.get("text"): texts_all.append(j)
                if j.get("n") and j.get("text"): texts[j["n"]] = j
    recs = {}; log = {"pagesViaInternetArchive": sorted(via), "duplicates": [], "noSignDate": [], "unparsedLabels": collections.Counter()}
    for p in page_names():
        fp = os.path.join(a.cache, p)
        if not os.path.exists(fp): continue
        page_url = via.get(p) or (ARCH + p)
        for e in parse_page(fp):
            n = e["n"]
            r = {"n": n, "t": e["t"], "s": "", "d": "", "c": "", "rel": collections.defaultdict(list), "notes": [],
                 "u": ARCH + p + "#" + e["anchor"], "pdf": ""}
            if p in via: r["u"] = page_url + "#" + e["anchor"]; r["ul"] = "National Archives disposition table (archived copy)"
            for li in e["lis"]:
                m = re.match(r"([A-Za-z ()]+?)\s*:\s*(.*)", li, re.S)
                if not m: r["notes"].append(li); continue
                lab, val = m.group(1).strip().lower(), m.group(2).strip()
                if lab == "signed": r["s"] = isodate(val.split(";")[0].split("(")[0])
                elif lab.startswith("federal register"):
                    mm = re.match(r"(\d+)\s*FR\s*(\d+)\s*[,;]?\s*(.*)", val)
                    if mm:
                        r["c"] = f"{mm.group(1)} FR {mm.group(2)}"; r["d"] = isodate(mm.group(3).split("(")[0])
                        r["pdf"] = f"https://www.govinfo.gov/link/fr/{mm.group(1)}/{mm.group(2)}"
                    else: r["notes"].append(li)
                elif lab in RELMAP:
                    r["rel"][RELMAP[lab]] += parse_refs(val); r["notes"].append(li)
                else:
                    log["unparsedLabels"][lab] += 1; r["notes"].append(li)
            if not r["s"]: log["noSignDate"].append(n)
            if n in recs:
                log["duplicates"].append(n)
                if recs[n]["t"] == r["t"]: continue
                n = r["n"] = n + "-dup"
            recs[n] = r
    for n, r in early_records(a, texts, log).items():
        if n not in recs: recs[n] = r
    # later orders' Federal Register notes (data/eo/<pres>.json, built by build_eo.py) that act on these orders
    later = []
    for f in os.listdir(a.modern):
        if f.endswith(".json") and f not in ("index.json", "eo-build-log.json", "text-revocations.json"):
            try: later += json.load(open(os.path.join(a.modern, f))).get("items", [])
            except Exception: pass
    # events: target -> rel -> {actor: info}
    ev = collections.defaultdict(lambda: collections.defaultdict(dict))
    acts = collections.defaultdict(lambda: collections.defaultdict(set))
    for n, r in recs.items():
        for rel, refs in r["rel"].items():
            for x in refs:
                if rel in BY:
                    real = rel
                    if x["part"] and rel == "revoked_by": real = "revoked_part_by"
                    if x["part"] and rel == "superseded_by": real = "superseded_part_by"
                    key = x["eo"] or ("doc:" + x["raw"])
                    info = {"date": x["date"]}
                    if not x["eo"]: info["label"] = re.sub(r"\s+", " ", re.sub(r",?\s*" + DATE_RE.pattern, "", re.sub(r"\s*\((?:in part)\)\s*", " ", x["raw"]))).strip(" ,") or x["raw"]
                    ev[n][real][key] = info
                else:
                    real = rel
                    if x["part"] and rel == "revokes": real = "revokes_part"
                    if x["part"] and rel == "supersedes": real = "supersedes_part"
                    if x["eo"]:
                        acts[n][real].add(x["eo"])
                        if x["eo"] in recs: ev[x["eo"]][INV[real]].setdefault(n, {"date": r["s"]})
    for it in later:
        for t, k in it.get("acts", []):
            if t in recs and k in INV:
                ev[t][INV[k]].setdefault(it["n"], {"date": it.get("s", "")})
        for b in it.get("by", []):
            pass
    def okey(a_, info): return (info.get("date", ""), numkey(a_)[0] if not a_.startswith("doc:") else 0)
    def status(n):
        e = ev.get(n, {})
        def latest(rels):
            xs = [(x, i) for rr in rels for x, i in e.get(rr, {}).items()]
            return max(xs, key=lambda v: okey(*v)) if xs else None
        full = latest(["revoked_by", "superseded_by"]); rein = latest(["reinstated_by"])
        if full and not (rein and okey(*rein) > okey(*full)):
            return "R" if full[0] in e.get("revoked_by", {}) else "S"
        if rein: return "I"
        if e.get("revoked_part_by"): return "P"
        if e.get("superseded_part_by"): return "SP"
        if e.get("suspended_by"): return "U"
        if e.get("amended_by"): return "M"
        return "N" if recs[n].get("early") else "A"
    # signing dates: EO numbers run in signing order, so a printed date far from its neighbours' is a typo in
    # the table (e.g. EO 8969 printed 1946 inside 1941's run). Then, and when the table gives no date, the
    # American Presidency Project's date for the same order is used and the note says so; else the date stays blank.
    order = sorted((n for n in recs if not recs[n].get("early")), key=numkey); fixed = []
    for n, r in recs.items():
        if not r.get("early"): continue
        u = (texts.get(n) or {}).get("date", "")
        if u and not r["s"]:
            r["s"] = u; r["notes"].append("The WPA list's date is unreadable in the scan; the date shown is the American Presidency Project's.")
        elif u and r["s"] and abs((datetime.date.fromisoformat(u) - datetime.date.fromisoformat(r["s"])).days) > 3:
            r["notes"].append("The WPA list gives the date as " + r["s"] + "; the American Presidency Project gives " + u + ", the date shown.")
            fixed.append([n, r["s"], u]); r["s"] = u
    for i, n in enumerate(order):
        r = recs[n]; nb = [recs[m]["s"] for m in order[max(0, i-4):i+5] if m != n and recs[m]["s"]]
        nb.sort(); med = nb[len(nb)//2] if nb else ""
        odd = bool(r["s"] and med and abs(int(r["s"][:4]) - int(med[:4])) >= 1 and abs((datetime.date.fromisoformat(r["s"]) - datetime.date.fromisoformat(med)).days) > 200)
        if odd or not r["s"]:
            u = (texts.get(n) or {}).get("date", "")
            if u and (not med or abs((datetime.date.fromisoformat(u) - datetime.date.fromisoformat(med)).days) <= 200):
                r["notes"].append(("The disposition table prints the signing date as " + r["s"] + "; " if r["s"] else "The disposition table gives no signing date; ") + "the date shown is the American Presidency Project's.")
                fixed.append([n, r["s"], u]); r["s"] = u
            elif odd:
                r["notes"].append("The disposition table prints the signing date as " + r["s"] + ", which is out of sequence; no second source confirms a date."); fixed.append([n, r["s"], ""]); r["s"] = ""
    log["dateFixes"] = fixed
    per = collections.defaultdict(list); ptext = collections.defaultdict(dict)
    order_e = sorted((n for n in recs if recs[n].get("early")), key=numkey)
    modern_n = set(it["n"] for it in later)
    for n, r in recs.items():
        if r.get("early"):
            tx0 = texts.get(n) or {}
            pid = UCSB_PRES.get(tx0.get("pres", "")) or term_of(r["s"]) or term_of(neighbour_date(order_e, n, recs))
            if pid in ("cleveland1", "cleveland2") or tx0.get("pres") == "Grover Cleveland": pid = "cleveland1" if (r["s"] or "1890") < "1893-03-04" else "cleveland2"
        else: pid = pres_of(n)
        if not pid or n in modern_n: continue
        e = ev.get(n, {}); by = []
        for rr in BY:
            for x, info in e.get(rr, {}).items():
                if x.startswith("doc:"): by.append(["", rr, info.get("date", ""), {"label": info.get("label", "")}])
                else: by.append([x, rr, info.get("date", "")])
        by.sort(key=lambda v: (v[2], numkey(v[0])[0] if v[0] else 0))
        ac = sorted([[x, k] for k, xs in acts.get(n, {}).items() for x in xs], key=lambda v: numkey(v[0]))
        row = {"n": n, "t": r["t"], "s": r["s"], "d": r["d"], "c": r["c"], "u": r["u"], "pdf": r["pdf"],
               "st": status(n), "by": by, "acts": ac, "notes": "\n".join(r["notes"]), "abs": "", "src": r.get("srcid", "dt")}
        if r.get("ul"): row["ul"] = r["ul"]
        tx = texts.get(n)
        if tx:
            why = text_mismatch(r, tx)
            if why: log.setdefault("textMismatch", []).append([n, why]); tx = None
        if tx:
            row["tu"] = ("https://www.presidency.ucsb.edu" + tx["url"]) if tx["url"].startswith("/") else tx["url"]
            ptext[pid][n] = opening(tx["text"])
        per[pid].append(row)
    for pid, tx, row in unnumbered(texts_all, log):
        row["tu"] = ("https://www.presidency.ucsb.edu" + tx["url"]) if tx["url"].startswith("/") else tx["url"]
        ptext[pid][row["n"]] = opening(tx["text"]); per[pid].append(row)
    os.makedirs(os.path.join(a.out, "text"), exist_ok=True)
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    idx = {"asOf": now, "source": "National Archives, Office of the Federal Register: Executive Orders Disposition Tables",
           "sourceUrl": INDEX_URL, "textSource": "The American Presidency Project (UCSB), presidency.ucsb.edu",
           "presidents": [], "log": {"pagesViaInternetArchive": log["pagesViaInternetArchive"], "duplicates": log["duplicates"],
           "noSignDate": log["noSignDate"], "dateFixes": log.get("dateFixes", []), "textMismatch": log.get("textMismatch", []), "earlySkippedNotNumbered": log.get("earlySkippedNotNumbered", []), "earlyOcrNumberFixed": log.get("earlyOcrNumberFixed", []), "earlyOcrNumberDropped": log.get("earlyOcrNumberDropped", []), "earlyError": log.get("earlyError", ""), "unparsedLabels": dict(log["unparsedLabels"])}}
    allp = list(PRES) + [(p, label, None, None) for p, label, _ in reversed(TERMS) if p not in [x[0] for x in PRES]]
    for pid, label, lo, hi in allp:
        L = sorted(per.get(pid, []), key=lambda r: (r["s"] or "", numkey(r["n"])), reverse=True)
        if not L: continue
        json.dump({"asOf": now, "pres": pid, "items": L}, open(os.path.join(a.out, pid + ".json"), "w"), separators=(",", ":"), ensure_ascii=False)
        json.dump(ptext.get(pid, {}), open(os.path.join(a.out, "text", pid + ".json"), "w"), separators=(",", ":"), ensure_ascii=False)
        nums = [numkey(r["n"])[0] for r in L if not r["n"].startswith("u-")]
        idx["presidents"].append({"id": pid, "label": label, "count": len(L), "min": min(nums) if nums else None, "max": max(nums) if nums else None,
                                  "termMin": lo if lo is not None else (min(nums) if nums else None), "termMax": hi if hi is not None else (max(nums) if nums else None),
                                  "unnumbered": sum(1 for r in L if r["n"].startswith("u-")),
                                  "withText": sum(1 for r in L if r.get("tu")), "status": dict(collections.Counter(r["st"] for r in L))})
    json.dump(idx, open(os.path.join(a.out, "index.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({p["id"]: [p["count"], p["withText"]] for p in idx["presidents"]}))

def opening(t, cap=1400):
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= cap: return t
    cut = t[:cap]; k = cut.rfind(". ")
    return (cut[:k+1] if k > cap * 0.5 else cut.rstrip() + " …")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="data/eo/hist")
    ap.add_argument("--modern", default="data/eo")
    ap.add_argument("--cache", default=".cache/eo-dispositions")
    ap.add_argument("--text-cache", default="")
    build(ap.parse_args())
