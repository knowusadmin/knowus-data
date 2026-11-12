#!/usr/bin/env python3
"""KnowUS: bill sponsor -> person page map (Shmuel, Nov 12 2026: every bill's sponsor taps through to a full profile).

Reads the federal bill list + saved details (data/bills/US.json, data/bills/detail/US-*.json), fetches each bill's
GovInfo BILLSTATUS XML (public domain, keyless) and records the bioguideId that BILLSTATUS gives beside each
sponsor/cosponsor. Matching is by that ID only, never by name.

Writes data/bills/sponsor-ids.json:
  ids:    "F:<BILLSTATUS fullName>" (bill-list sponsor string), "S:<name>|<party>|<state>|<district>" (detail sponsor),
          "C:<name>|<party>|<state>" (detail cosponsor)  ->  bioguideId
  people: bioguideId -> {n: display name, a: app person id when the member now holds another office in the app
          (e.g. cabinet), x: 1 when a built profile exists in data/people-extra.json}
usage: build_sponsor_ids.py <repo_dir> [--cache DIR] [--aliases data/people-former/aliases.json]
"""
import json, os, re, sys, time, datetime as dt, concurrent.futures as cf
import xml.etree.ElementTree as ET
import requests
UA = {"User-Agent": "KnowUS sponsor links (https://knowus.sites.tab.bot)", "Accept": "application/xml"}
T = {"HR": "hr", "S": "s", "HJRES": "hjres", "SJRES": "sjres", "HCONRES": "hconres", "SCONRES": "sconres", "HRES": "hres", "SRES": "sres"}

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()

def strip_tag(n):
    return clean(re.sub(r"\s*\[[^\]]*\]\s*$", "", n or ""))

def fetch(bid, cache):
    p = os.path.join(cache, bid + ".xml")
    if os.path.exists(p) and os.path.getsize(p) > 500:
        return open(p, "rb").read()
    m = re.match(r"US-(\d+)-([A-Z]+)(\d+)$", bid)
    c, t, n = m.group(1), T[m.group(2)], m.group(3)
    u = "https://www.govinfo.gov/bulkdata/BILLSTATUS/%s/%s/BILLSTATUS-%s%s%s.xml" % (c, t, c, t, n)
    for k in range(4):
        try:
            r = requests.get(u, headers=UA, timeout=30)
            if r.status_code == 200:
                open(p, "wb").write(r.content); return r.content
            if r.status_code == 404:
                return None
        except Exception:
            pass
        time.sleep(2 + 3 * k)
    return None

def main():
    repo = sys.argv[1]
    a = sys.argv[2:]
    cache = a[a.index("--cache") + 1] if "--cache" in a else "/tmp/billstatus-cache"
    os.makedirs(cache, exist_ok=True)
    bills = json.load(open(os.path.join(repo, "data/bills/US.json")))["bills"]
    det = {}
    dd = os.path.join(repo, "data/bills/detail")
    for f in os.listdir(dd):
        if f.startswith("US-") and f.endswith(".json"):
            det.update(json.load(open(os.path.join(dd, f)))["bills"])
    ids = sorted(set([b["id"] for b in bills] + list(det)))
    with cf.ThreadPoolExecutor(3) as ex:
        xml = dict(zip(ids, ex.map(lambda i: fetch(i, cache), ids)))
    out, people, conflicts, miss = {}, {}, [], 0
    def put(k, bg):
        if not bg: return
        if k in out and out[k] != bg: conflicts.append([k, out[k], bg]); return
        out[k] = bg
    for bid in ids:
        if not xml.get(bid): miss += 1; continue
        x = ET.fromstring(xml[bid]).find("bill")
        items = [("sp", it) for it in x.findall("sponsors/item")] + [("co", it) for it in x.findall("cosponsors/item")]
        for kind, it in items:
            bg = it.findtext("bioguideId"); fn = it.findtext("fullName")
            if not bg: continue
            put("F:" + (fn or ""), bg)
            nm = " ".join(w for w in [it.findtext("firstName"), it.findtext("middleName"), it.findtext("lastName")] if w)
            people.setdefault(bg, {"n": clean(nm)})
        d = det.get(bid)
        if not d: continue
        sp = x.find("sponsors/item")
        if sp is not None and d.get("sponsor") and strip_tag(sp.findtext("fullName")) == d["sponsor"].get("name"):
            s = d["sponsor"]; put("S:%s|%s|%s|%s" % (s.get("name") or "", s.get("party") or "", s.get("state") or "", s.get("district") or ""), sp.findtext("bioguideId"))
        for c, xi in zip(d.get("cosponsors") or [], x.findall("cosponsors/item")):
            if strip_tag(xi.findtext("fullName")) == c.get("name"):
                put("C:%s|%s|%s" % (c.get("name") or "", c.get("party") or "", c.get("state") or ""), xi.findtext("bioguideId"))
    # display names + app ids: current members from the app's officials data, aliases + built profiles from data/people-former
    off = {}
    try: off = json.load(open(os.path.join(repo, "data/officials.json"))).get("people", {})
    except Exception: pass
    for k, v in off.items():
        if v.get("bg") in people: people[v["bg"]]["n"] = v.get("n") or people[v["bg"]]["n"]
    pf = os.path.join(repo, "data/people-former")
    al = {}
    try: al = json.load(open(os.path.join(pf, "aliases.json"))).get("aliases", {})
    except Exception: pass
    for bg, v in al.items():
        if bg in people:
            people[bg]["a"] = v["id"]
            if v.get("n"): people[bg]["n"] = v["n"]
    ex = {}
    try: ex = json.load(open(os.path.join(repo, "data/people-extra.json"))).get("people", {})
    except Exception: pass
    for bg, v in ex.items():
        if bg in people:
            people[bg]["x"] = 1; people[bg]["n"] = v.get("n") or people[bg]["n"]
    doc = {"generatedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
           "source": "GovInfo bulk BILLSTATUS XML (sponsors/cosponsors bioguideId)", "bills": len(ids), "missingXml": miss,
           "ids": out, "people": people}
    if conflicts: doc["conflicts"] = conflicts
    json.dump(doc, open(os.path.join(repo, "data/bills/sponsor-ids.json"), "w"), separators=(",", ":"), ensure_ascii=False)
    inapp = sum(1 for bg in people if any(v.get("bg") == bg for v in off.values()))
    print("sponsor-ids: %d keys, %d people (%d in officials, %d alias, %d built), %d bills, %d missing xml, %d conflicts" % (
        len(out), len(people), inapp, sum(1 for p in people.values() if p.get("a")), sum(1 for p in people.values() if p.get("x")), len(ids), miss, len(conflicts)))

if __name__ == "__main__":
    main()
