#!/usr/bin/env python3
"""Current mayor of each city in the app's data/mayors.json (the Mayor tab's cities). No AI, no keys.

Primary source: the city's English Wikipedia article infobox (leader_title "Mayor" -> leader_name).
Cross-check: Wikidata "head of government" (P6) on the city's item, current statement (no end time), with
start date (P580), party (P102) and photo (P18). Wikipedia wins when they disagree (it is edited fastest);
the disagreement is recorded so it is visible.
Writes data/mayors-current.json:
  {"checkedAt", "source", "cities": {"<city id>": {"city","st","n","p","s","w","img","src","wd"?: {...}, "agree": bool}}}
Field names follow the app's people records: n name, p party, s start date ("January 2, 2023"), w Wikipedia URL, img photo URL.
Guard: if fewer cities resolve than last time (more than a 10% drop) or none, the previous file is kept and the step fails.
"""
import json, os, re, sys, datetime as dt
import requests

UA = {"User-Agent": "KnowUS-data-refresh/1.0 (https://github.com/knowusadmin/knowus-data; knowusadmin@gmail.com)"}
SITE = os.environ.get("KNOWUS_SITE", "https://knowus.sites.tab.bot/")
OUT = "data/mayors-current.json"
MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]
TITLE_FIX = {"washington-dc": "Washington, D.C."}

def cities():
    try:
        r = requests.get(SITE + "data/mayors.json", params={"x": dt.datetime.now().timestamp()}, headers=UA, timeout=30); r.raise_for_status()
        d = r.json(); assert d.get("cities")
        txt = json.dumps(d, ensure_ascii=False, indent=1)
        os.makedirs("base", exist_ok=True)
        if not os.path.exists("base/mayors.json") or open("base/mayors.json").read() != txt: open("base/mayors.json", "w").write(txt)
    except Exception as e:
        print("site mayors.json unavailable (%s); using base/mayors.json" % e)
        d = json.load(open("base/mayors.json"))
    return d["cities"]

def wiki(params):
    p = {"format": "json", "formatversion": 2, **params}
    r = requests.get("https://en.wikipedia.org/w/api.php", params=p, headers=UA, timeout=40); r.raise_for_status(); return r.json()

def wd_entities(ids, props):
    out = {}
    ids = list(ids)
    for i in range(0, len(ids), 50):
        r = requests.get("https://www.wikidata.org/w/api.php", params={"action": "wbgetentities", "ids": "|".join(ids[i:i+50]), "props": props,
                         "languages": "en", "sitefilter": "enwiki", "format": "json"}, headers=UA, timeout=40)
        r.raise_for_status(); out.update(r.json().get("entities", {}))
    return out

def iso2txt(s):
    m = re.match(r"[+]?(\d{4})-(\d\d)-(\d\d)", s or "")
    if not m: return ""
    if m.group(2) == "00": return m.group(1)
    if m.group(3) == "00": return "%s %s" % (MONTHS[int(m.group(2)) - 1], m.group(1))
    return "%s %d, %s" % (MONTHS[int(m.group(2)) - 1], int(m.group(3)), m.group(1))

def party_name(p):
    p = re.sub(r"\s+Party$", "", p or "").strip()
    return "Independent" if p.lower() in ("independent politician", "independent") else p

def strip_wiki(v):
    v = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>|<!--.*?-->", "", v, flags=re.S)
    v = re.sub(r"<ref.*$|\{\{\s*(?:cite|efn|refn|sfn)[^}]*\}\}", "", v, flags=re.S | re.I)
    m = re.search(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", v)
    if m: return (m.group(2) or m.group(1)).strip(), m.group(1).strip()
    v = re.sub(r"\{\{[^}]*\}\}", "", v).strip(" '\n")
    return (v or None), None

def infobox_mayor(text):
    titles = dict(re.findall(r"\|\s*leader_title(\d*)\s*=\s*([^\n]*)", text))
    names = dict(re.findall(r"\|\s*leader_name(\d*)\s*=\s*([^\n]*)", text))
    for k, t in titles.items():
        t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t)  # [[List of mayors of X|Mayor]] -> Mayor
        if re.search(r"\bmayor\b", t, re.I) and not re.search(r"vice|deputy|pro tem", t, re.I) and k in names:
            n, link = strip_wiki(names[k])
            pm = re.search(r"\|\s*([DRI])\s*\]\]\s*\)|\(\s*([DRI])\s*\)", names[k])
            party = {"D": "Democratic", "R": "Republican", "I": "Independent"}.get(pm and (pm.group(1) or pm.group(2)), "")
            if n and len(n) > 3: return n, link, party
    return None, None, ""

def first_claim(ent, pid):
    best = None
    for c in ent.get("claims", {}).get(pid, []):
        if c.get("rank") == "deprecated": continue
        q = c.get("qualifiers", {})
        if "P582" in q: continue  # ended
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if v is None: continue
        start = (q.get("P580") or [{}])[0].get("datavalue", {}).get("value", {}).get("time")
        cand = (c.get("rank") == "preferred", start or "", v)
        if best is None or cand[:2] > best[:2]: best = cand
    return (best[2], best[1]) if best else (None, None)

def norm(n):
    n = re.sub(r"\b(jr|sr|ii|iii)\b\.?", "", (n or "").lower()); return re.sub(r"[^a-z ]", " ", n).split()

def same(a, b):
    a, b = norm(a), norm(b)
    return bool(a and b and a[-1] == b[-1])

def main():
    cs = cities()
    titles = {c["id"]: TITLE_FIX.get(c["id"], "%s, %s" % (c["city"], c["state"])) for c in cs}
    j = wiki({"action": "query", "prop": "revisions|pageprops", "rvprop": "content", "rvslots": "main", "ppprop": "wikibase_item",
              "titles": "|".join(titles.values()), "redirects": 1})["query"]
    alias = {x["from"]: x["to"] for x in j.get("normalized", []) + j.get("redirects", [])}
    pages = {p["title"]: p for p in j["pages"] if not p.get("missing")}
    res, city_q = {}, {}
    for cid, t in titles.items():
        while t in alias: t = alias[t]
        p = pages.get(t)
        if not p: print("no article for", cid); continue
        text = p["revisions"][0]["slots"]["main"]["content"]
        n, link, wparty = infobox_mayor(text)
        res[cid] = {"n": n, "link": link, "p": wparty, "article": "https://en.wikipedia.org/wiki/" + t.replace(" ", "_")}
        q = p.get("pageprops", {}).get("wikibase_item")
        if q: city_q[cid] = q
    # Wikidata cross-check
    ents = wd_entities(city_q.values(), "claims")
    heads = {}
    for cid, q in city_q.items():
        v, start = first_claim(ents.get(q, {}), "P6")
        if v: heads[cid] = (v["id"], start)
    people = wd_entities({h[0] for h in heads.values()}, "labels|sitelinks|claims")
    party_ids = set()
    for e in people.values():
        pv, _ = first_claim(e, "P102")
        if pv: party_ids.add(pv["id"])
    parties = wd_entities(party_ids, "labels") if party_ids else {}
    out = {}
    for c in cs:
        cid = c["id"]; r = res.get(cid) or {}
        wd = None
        if cid in heads:
            pq, start = heads[cid]; e = people.get(pq, {})
            pv, _ = first_claim(e, "P102"); img, _ = first_claim(e, "P18")
            wd = {"n": e.get("labels", {}).get("en", {}).get("value"), "qid": pq, "s": iso2txt(start),
                  "p": party_name(parties.get(pv["id"], {}).get("labels", {}).get("en", {}).get("value") if pv else ""),
                  "w": ("https://en.wikipedia.org/wiki/" + e["sitelinks"]["enwiki"]["title"].replace(" ", "_")) if e.get("sitelinks", {}).get("enwiki") else "",
                  "img": ("https://commons.wikimedia.org/wiki/Special:FilePath/" + img.replace(" ", "_") + "?width=250") if img else None}
        n = r.get("n") or (wd and wd["n"])
        if not n: print("no mayor found for", cid); continue
        agree = bool(wd and same(wd["n"], n))
        x = {"city": c["city"], "st": c["st"], "n": n, "p": r.get("p") or "", "s": "", "w": "", "img": None,
             "src": {"name": "Wikipedia", "url": r.get("article")} if r.get("n") else {"name": "Wikidata", "url": "https://www.wikidata.org/wiki/" + city_q[cid]},
             "agree": agree}
        if r.get("link"): x["w"] = "https://en.wikipedia.org/wiki/" + r["link"].replace(" ", "_")
        if agree:  # same person: take party/start/photo from Wikidata
            for k in ("p", "s", "img"): x[k] = wd[k] or x[k]
            x["w"] = x["w"] or wd["w"]
        if wd and not agree: x["wd"] = {k: wd[k] for k in ("n", "s", "p")}
        out[cid] = x
    # photos for Wikipedia-only names: the article's lead image
    need = {cid: x["w"].rsplit("/", 1)[1].replace("_", " ") for cid, x in out.items() if not x["img"] and x["w"]}
    if need:
        jj = wiki({"action": "query", "prop": "pageimages", "piprop": "thumbnail", "pithumbsize": 250, "titles": "|".join(need.values()), "redirects": 1})["query"]
        al = {x["from"]: x["to"] for x in jj.get("normalized", []) + jj.get("redirects", [])}
        th = {p["title"]: p.get("thumbnail", {}).get("source") for p in jj["pages"]}
        for cid, t in need.items():
            while t in al: t = al[t]
            if th.get(t): out[cid]["img"] = th[t]
    # guard
    prev = None
    if os.path.exists(OUT):
        try: prev = json.load(open(OUT))
        except Exception: prev = None
    if not out or (prev and len(out) < 0.9 * len(prev.get("cities", {}))):
        print("::error::mayors sanity guard: %d cities resolved (previously %d); previous file kept" % (len(out), len(prev.get("cities", {})) if prev else 0))
        sys.exit(1)
    doc = {"checkedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
           "source": "Wikipedia city article infobox (leader_name for Mayor); cross-checked with Wikidata head of government (P6)",
           "cities": out}
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    dis = [cid for cid, x in out.items() if not x["agree"]]
    print("mayors: %d of %d cities; Wikipedia/Wikidata disagree or Wikidata missing: %s" % (len(out), len(cs), ", ".join(dis) or "none"))
    for cid, x in out.items(): print(" ", cid, "|", x["n"], "|", x["p"], "|", x["s"], "|", "img" if x["img"] else "no img", "| wd:", (x.get("wd") or {}).get("n", "same" if x["agree"] else "-"))

if __name__ == "__main__":
    main()
