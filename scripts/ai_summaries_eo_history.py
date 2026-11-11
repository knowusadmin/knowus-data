#!/usr/bin/env python3
"""AI summaries for KnowUS's historical executive orders (data/eo/hist), stored in data/ai-summaries/EO-hist.json.
Same rules, prompt and checks as scripts/ai_summaries.py (imported from it): 2-4 plain sentences written only
from the order's own text; numbers checked against that text; no labels or opinions. No text, no summary.
Text: the text cache written by fetch_eo_history_text.py (the order's text as transcribed by the American
Presidency Project, UCSB, linked on each order as "tu"); when a cached copy is missing the page at "tu" is read.
Status never comes from here.
Usage: python3 scripts/ai_summaries_eo_history.py [--data data] [--text-cache DIR] [--max N] [--concurrency 2] [--minutes M]
"""
import argparse, datetime, json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_summaries as A
import requests
from bs4 import BeautifulSoup
MIN_TEXT = 120
def today(): return datetime.date.today().isoformat()
def key_of(url): return url.rstrip("/").split("/")[-1][:150]
def text_for(row, cache):
    u = row.get("tu")
    if not u: return None
    if cache:
        fp = os.path.join(cache, key_of(u) + ".json")
        if os.path.exists(fp):
            try:
                t = json.load(open(fp)).get("text") or ""
                if t: return t
            except Exception: pass
    try:
        r = requests.get(u, headers=A.UA, timeout=30)
        if r.status_code != 200: return None
        c = BeautifulSoup(r.text, "lxml").select_one(".field-docs-content")
        return c.get_text("\n", strip=True) if c else None
    except Exception: return None
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data"); ap.add_argument("--text-cache", default="")
    ap.add_argument("--max", type=int, default=0); ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--backend", default=os.environ.get("KNOWUS_AI_BACKEND", "tab"))
    ap.add_argument("--model", default=os.environ.get("KNOWUS_AI_MODEL", "gpt-5.4-mini"))
    ap.add_argument("--minutes", type=float, default=0); ap.add_argument("--only", default="")
    ap.add_argument("--save-every", type=int, default=40)
    a = ap.parse_args()
    hd = os.path.join(a.data, "eo", "hist"); out = os.path.join(a.data, "ai-summaries", "EO-hist.json")
    store = {"jur": "EO-hist", "items": {}, "noText": {}}
    if os.path.exists(out):
        try: store = json.load(open(out)); store.setdefault("noText", {})
        except Exception: pass
    idx = json.load(open(os.path.join(hd, "index.json")))
    only = set(x for x in a.only.split(",") if x)
    rows = []; have_tu = {}
    for p in idx["presidents"]:
        for r in json.load(open(os.path.join(hd, p["id"] + ".json")))["items"]: have_tu[r["n"]] = r.get("tu")
    for n in list(store["items"]):  # a summary stays only while its order still has a matching transcription
        if not have_tu.get(n): store["items"].pop(n); store["noText"][n] = "transcription no longer matched"
        else: store["items"][n]["src"] = have_tu[n]
    for p in idx["presidents"]:
        if only and p["id"] not in only: continue
        for r in json.load(open(os.path.join(hd, p["id"] + ".json")))["items"]:
            if r["n"] not in store["items"]: rows.append(r)
    if a.max: rows = rows[:a.max]
    M = A.Model(a.backend, a.model, 0); lock = threading.Lock(); t0 = time.time(); done = [0]
    stats = {"done": 0, "noText": 0, "failed": 0}
    def save():
        store["asOf"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        store["counts"] = {"summaries": len(store["items"]), "noText": len(store["noText"])}
        tmp = out + ".tmp"; json.dump(store, open(tmp, "w"), ensure_ascii=False, separators=(",", ":")); os.replace(tmp, out)
    def job(r):
        if a.minutes and time.time() - t0 > a.minutes * 60: return
        n = r["n"]; text = text_for(r, a.text_cache)
        if not text or len(text) < MIN_TEXT:
            with lock: store["noText"][n] = "no text copy" if not text else "text too short"; stats["noText"] += 1
            return
        text = text[:A.TEXT_CAP]
        name = ("Executive Order " + n) if not n.startswith("u-") else "Executive order (unnumbered)"
        user = f"{name}: {r.get('t')}\nSigned: {r.get('s') or 'date not given'}\n\nThe order's text:\n{text}"
        s, err = A.summarize(M, user, user)
        with lock:
            if s:
                store["items"][n] = {"s": s, "basis": "order text (American Presidency Project transcription)", "src": r.get("tu"), "page": r.get("pdf") or r.get("u"), "model": a.model, "date": today()}
                store["noText"].pop(n, None); stats["done"] += 1
            else:
                stats["failed"] += 1; print("fail", n, err, flush=True)
            done[0] += 1
            if done[0] % a.save_every == 0: save(); print(json.dumps(stats), flush=True)
    with ThreadPoolExecutor(a.concurrency) as ex: list(ex.map(job, rows))
    save(); print("DONE", json.dumps(stats), json.dumps(M.usage), flush=True)
if __name__ == "__main__": main()
