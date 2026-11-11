#!/usr/bin/env python3
"""Fetch the text of historical executive orders from the American Presidency Project (UCSB), for KnowUS.
Usage: python3 fetch_eo_history_text.py <ucsb_list_dir> <text_cache_dir> [--max-eo 12889] [--threads 2]
Reads the archive's "Executive Orders" category listing (saved as JSON pages), picks numbered orders up to
--max-eo and every unnumbered order, and saves {key, n, url, title, date, pres, text} per document."""
import json, os, re, sys, time, threading, argparse
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
UA = {"User-Agent": "Mozilla/5.0 (KnowUS civic app research; shmuel.knowus@mail.tab.bot)"}
BASE = "https://www.presidency.ucsb.edu"
def eo_num(title):
    m = re.match(r"Executive Order (\d+(?:-?[A-Z])?)\b", title)
    if not m: return None
    n = m.group(1); n = re.sub(r"^(\d+)-?([A-Z])$", r"\1-\2", n); return n
def key_of(it):
    return it["url"].rstrip("/").split("/")[-1][:150]
def fetch(it, out):
    fp = os.path.join(out, key_of(it) + ".json")
    if os.path.exists(fp): return "have"
    for t in range(4):
        try:
            r = requests.get(BASE + it["url"], headers=UA, timeout=40)
            if r.status_code == 200: break
            if r.status_code == 404: json.dump({**it, "n": eo_num(it["title"]), "text": "", "err": "404"}, open(fp, "w")); return "404"
        except Exception as e: pass
        time.sleep(5 + 5 * t)
    else: return "fail"
    s = BeautifulSoup(r.text, "lxml")
    c = s.select_one(".field-docs-content")
    text = c.get_text("\n", strip=True) if c else ""
    fn = s.select_one(".field-docs-footnote")
    cit = s.select_one(".ucsbapp_citation")
    j = {**it, "n": eo_num(it["title"]), "text": text, "footnote": fn.get_text(" ", strip=True) if fn else "",
         "citation": cit.get_text(" ", strip=True) if cit else ""}
    json.dump(j, open(fp, "w"), ensure_ascii=False)
    time.sleep(0.4)
    return "ok"
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("lst"); ap.add_argument("out")
    ap.add_argument("--max-eo", type=int, default=12889); ap.add_argument("--threads", type=int, default=2)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    L = []
    for f in sorted(os.listdir(a.lst)):
        if f.endswith(".json"): L += json.load(open(os.path.join(a.lst, f)))
    seen = set(); jobs = []
    for it in L:
        if it["url"] in seen: continue
        seen.add(it["url"]); n = eo_num(it["title"])
        if n is None or int(re.match(r"\d+", n).group()) <= a.max_eo: jobs.append(it)
    # newest-first listing: do 1937-1993 numbered first, then older numbered, then unnumbered
    def pri(it):
        n = eo_num(it["title"])
        if n: v = int(re.match(r"\d+", n).group()); return (0, -v) if v >= 7532 else (1, -v)
        return (2, it.get("date", ""))
    jobs.sort(key=pri)
    print("jobs", len(jobs), flush=True)
    done = {"ok": 0, "have": 0, "404": 0, "fail": 0}; lock = threading.Lock()
    def run(it):
        r = fetch(it, a.out)
        with lock:
            done[r] += 1
            if sum(done.values()) % 50 == 0: print(json.dumps(done), flush=True)
    with ThreadPoolExecutor(a.threads) as ex: list(ex.map(run, jobs))
    print("DONE", json.dumps(done), flush=True)
