#!/usr/bin/env python3
"""Federal bills snapshot for KnowUS.

Keyless default: GovInfo bulk BILLSTATUS (public domain, no API key), the most
recently updated bills of the current Congress.
With CONGRESS_API_KEY set (free api.data.gov key), it instead asks the Congress.gov
API for the most recently updated bills (fresher: Congress.gov updates within hours).
Output: <out>/US.json in the KnowUS bills schema.
"""
import json, os, sys, re, time, datetime as dt
import concurrent.futures as cf
import xml.etree.ElementTree as ET
import requests

CONGRESS = int(os.environ.get("CONGRESS", "119"))
LIMIT = int(os.environ.get("FED_LIMIT", "800"))
TYPES = ["hr", "s", "hjres", "sjres", "hconres", "sconres"]
TYPE_LABEL = {"hr": "H.R.", "s": "S.", "hjres": "H.J.Res.", "sjres": "S.J.Res.", "hconres": "H.Con.Res.", "sconres": "S.Con.Res.", "hres": "H.Res.", "sres": "S.Res."}
TYPE_SLUG = {"hr": "house-bill", "s": "senate-bill", "hjres": "house-joint-resolution", "sjres": "senate-joint-resolution", "hconres": "house-concurrent-resolution", "sconres": "senate-concurrent-resolution", "hres": "house-resolution", "sres": "senate-resolution"}
UA = {"User-Agent": "KnowUS bills snapshot (https://knowus.sites.tab.bot)"}

def ordinal(n):
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])

def official_url(t, num):
    return "https://www.congress.gov/bill/%s-congress/%s/%s" % (ordinal(CONGRESS), TYPE_SLUG[t], num)

def clean(s, n=300):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]

def bill(t, num, title, status, date, introduced, sponsor, law=None):
    return {"law": law, "id": "US-%d-%s%s" % (CONGRESS, t.upper(), num), "number": "%s %s" % (TYPE_LABEL[t], num),
            "title": clean(title), "status": clean(status, 400), "date": date, "introduced": introduced,
            "sponsor": sponsor, "url": official_url(t, num), "chamber": "Senate" if t.startswith("s") else "House"}

# ---------- keyless: GovInfo bulk BILLSTATUS ----------
def govinfo():
    files = []
    for t in TYPES:
        r = requests.get("https://www.govinfo.gov/bulkdata/json/BILLSTATUS/%d/%s" % (CONGRESS, t), headers={**UA, "Accept": "application/json"}, timeout=60)
        r.raise_for_status()
        for f in r.json().get("files", []):
            if not f.get("name", "").endswith(".xml"): continue
            m = dt.datetime.strptime(f["formattedLastModifiedTime"], "%d-%b-%Y %H:%M")
            files.append((m, t, f["link"]))
    files.sort(reverse=True)
    files = files[: LIMIT * 2]  # fetch extra, then keep the most recent by action date

    with cf.ThreadPoolExecutor(8) as ex:
        bills = [b for b in ex.map(billstatus, files) if b and b.get("date")]
    return bills, "GovInfo (U.S. Government Publishing Office)", "https://www.govinfo.gov/bulkdata/BILLSTATUS"

def billstatus(item):
        m, t, link = item
        for attempt in range(3):
            try:
                r = requests.get(link, headers=UA, timeout=30); r.raise_for_status()
                x = ET.fromstring(r.content).find("bill")
                num = (x.findtext("number") or x.findtext("billNumber") or "").strip()
                la = x.find("latestAction")
                sp = x.find("sponsors/item")
                sponsor = sp.findtext("fullName") if sp is not None else None
                title = x.findtext("title") or ""
                law = None
                for it in x.findall("laws/item"):
                    if (it.findtext("type") or "").startswith("Public"): law = (it.findtext("number") or "").strip() or None
                return bill(t, num, title, la.findtext("text") if la is not None else "",
                            la.findtext("actionDate") if la is not None else None,
                            x.findtext("introducedDate"), sponsor, law)
            except Exception as e:
                err = e; time.sleep(1 + attempt)
        print("skip", link, err, file=sys.stderr)
        return None

# ---------- enacted laws: GovInfo PLAW (public laws), keyless ----------
def enacted():
    """Every public law of this Congress that GovInfo has published, as bills with law numbers."""
    r = requests.get("https://www.govinfo.gov/bulkdata/json/PLAW/%d/public" % CONGRESS, headers={**UA, "Accept": "application/json"}, timeout=60)
    r.raise_for_status()
    links = [f["link"] for f in r.json().get("files", []) if re.match(r"PLAW-\d+publ\d+\.xml$", f.get("name", ""))]
    def one(link):
        try:
            x = requests.get(link, headers=UA, timeout=30).text
            m = re.search(r'href="/us/bill/%d/([a-z]+)/(\d+)"' % CONGRESS, x)
            lawno = "%d-%s" % (CONGRESS, re.search(r"publ(\d+)", link).group(1))
            d = re.search(r"<approvedDate[^>]*>([^<]+)</approvedDate>|<dc:date>([^<]+)</dc:date>", x)
            approved = re.search(r"<dc:date>(\d{4}-\d\d-\d\d)</dc:date>", x)
            if not m: return None
            return (m.group(1), m.group(2), lawno, approved.group(1) if approved else None)
        except Exception as e:
            print("plaw skip", link, e, file=sys.stderr); return None
    with cf.ThreadPoolExecutor(8) as ex:
        found = [f for f in ex.map(one, links) if f]
    out = []
    def detail(f):
        t, num, lawno, approved = f
        if t not in TYPE_LABEL: return None
        b = billstatus((None, t, "https://www.govinfo.gov/bulkdata/BILLSTATUS/%d/%s/BILLSTATUS-%d%s%s.xml" % (CONGRESS, t, CONGRESS, t, num)))
        if not b: b = bill(t, num, "", "", approved, None, None)
        b["law"] = lawno
        b["status"] = "Became Public Law No: %s." % lawno
        b["date"] = approved or b.get("date")
        return b
    with cf.ThreadPoolExecutor(8) as ex:
        out = [b for b in ex.map(detail, found) if b]
    return out

# ---------- keyed: Congress.gov API ----------
def congress_api(key):
    bills, offset = [], 0
    while len(bills) < LIMIT:
        r = requests.get("https://api.congress.gov/v3/bill/%d" % CONGRESS, params={"api_key": key, "format": "json", "sort": "updateDate+desc", "limit": 250, "offset": offset}, headers=UA, timeout=60)
        r.raise_for_status()
        page = r.json().get("bills", [])
        if not page: break
        for b in page:
            t = b["type"].lower()
            if t not in TYPE_LABEL: continue
            la = b.get("latestAction") or {}
            bills.append(bill(t, b["number"], b.get("title"), la.get("text"), la.get("actionDate"), None, None))
        offset += 250
    # sponsor + introduced date: one detail call per bill (5,000 calls/hour on a real key)
    def detail(b):
        t, num = b["id"].split("-")[2][:-len(b["number"].split(" ")[1])].lower(), b["number"].split(" ")[1]
        try:
            r = requests.get("https://api.congress.gov/v3/bill/%d/%s/%s" % (CONGRESS, t, num), params={"api_key": key, "format": "json"}, headers=UA, timeout=30)
            d = r.json().get("bill", {})
            sp = (d.get("sponsors") or [{}])[0]
            b["sponsor"] = sp.get("fullName"); b["introduced"] = d.get("introducedDate")
        except Exception:
            pass
        return b
    with cf.ThreadPoolExecutor(6) as ex:
        bills = list(ex.map(detail, bills[:LIMIT]))
    return bills, "Congress.gov API (Library of Congress)", "https://www.congress.gov/"

def main(out):
    key = os.environ.get("CONGRESS_API_KEY")
    bills, source, source_url = congress_api(key) if key else govinfo()
    bills.sort(key=lambda b: (b["date"] or "", b["id"]), reverse=True)
    bills = bills[:LIMIT]
    try:
        laws = enacted()
        byid = {b["id"]: b for b in bills}
        for l in laws:
            if l["id"] in byid:
                byid[l["id"]]["law"] = l["law"]
            else:
                bills.append(l)
        bills.sort(key=lambda b: (b["date"] or "", b["id"]), reverse=True)
        print("enacted laws from GovInfo PLAW:", len(laws))
    except Exception as e:
        print("PLAW failed:", e, file=sys.stderr)
    doc = {"jurisdiction": "US", "name": "Federal (U.S. Congress)", "session": "%s Congress" % ordinal(CONGRESS),
           "generatedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
           "source": source, "sourceUrl": source_url, "bills": bills}
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "US.json"), "w") as f:
        json.dump(doc, f, separators=(",", ":"), ensure_ascii=False)
    print("US.json", len(bills), "bills, newest", bills[0]["date"] if bills else None, "source", source)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "site/data/bills")
