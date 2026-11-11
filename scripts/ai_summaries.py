#!/usr/bin/env python3
"""KnowUS AI summaries for every bill and executive order.

Writes data/ai-summaries/<JUR>.json (bills; JUR = US or a state code) and data/ai-summaries/EO.json
(executive orders). The app shows each one in its own "AI summary" box under the official summary.

Rules (Shmuel's): written ONLY from the official text (Congress.gov/GovInfo bill text or the Congressional
Research Service summary; the state legislature's own bill text or official summary; the Federal Register's
text for executive orders). 2-4 plain factual sentences, no opinions, no critics' labels, light conservative
vocabulary where accurate wordings tie. Nothing invented: every number in a summary must appear in the
source text, or it is not stored. When the official text can't be fetched, no summary is stored and the item
is listed under "noText" (retried later). The official summary is never touched. EO status never comes
from here.

Usage:
  python3 scripts/ai_summaries.py [--data data] [--only US,EO,OH] [--max N] [--concurrency 2]
        [--backend tab|openai|github] [--model M] [--rpm 0] [--retry-days 3] [--minutes 0]
Backends: tab = Tab's model proxy (on Tab's box); openai = OPENAI_API_KEY; github = GitHub Models with the
Actions GITHUB_TOKEN (free; needs `permissions: models: read`).
"""
import argparse, datetime, glob, html, json, os, re, subprocess, sys, tempfile, threading, time, random
from concurrent.futures import ThreadPoolExecutor
import requests

UA = {"User-Agent": "KnowUS-data/1.0 (+https://github.com/knowusadmin/knowus-data)"}
TEXT_CAP = 16000
MIN_TEXT = 250
BAD_SCRIPT = re.compile(r"[\u0370-\u03FF\u0400-\u052F\u0590-\u06FF\u0900-\u0DFF\u3040-\u30FF\u3400-\u9FFF\uAC00-\uD7AF]")
STATE = {"US":"the U.S. Congress","AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","DC":"the District of Columbia","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"}

SYSTEM = """You write the "AI summary" box for KnowUS, a free civic phone app. It sits under the official summary of a bill or executive order.

Write 2 to 4 short sentences in plain English (6th-8th grade reading level) saying what the measure does or would do and who it affects.

Hard rules:
- Use ONLY facts stated in the official text you are given. Never add numbers, dates, names, places, costs or effects that are not in it. No outside knowledge, no guessing about motives, history or likely results.
- Plain and factual. No opinions, no praise or criticism, no predictions, no "critics say" or "supporters say", no labels or accusations about any person or group. Do not mention parties or sponsors.
- A bill "would" do things (it may not pass); say it passed or became law only if the input says so. An executive order "directs", "requires" or "revokes".
- Vocabulary: when two wordings are equally accurate, use the plain conservative-leaning term rather than activist phrasing: e.g. "illegal immigrants" or "illegal immigration" (not "undocumented"), "abortion" (not "reproductive care"), "firearms" / "Second Amendment rights" (not "gun violence prevention" as a label), "tax relief" or "tax cuts" (not "giveaways"), "biological sex" where the text means sex at birth. If the official text itself uses a term, you may quote it in quotation marks. Never change a fact to fit wording.
- Don't begin with the bill number or repeat the title as the whole summary. Never mention "the text", "the input", or that something was cut off.
- If the text is only a formal title or a resolution recognizing or honoring something, still write 2 plain sentences from what it says.
Return JSON only: {"summary": "..."}"""

NUM_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?")
WORDNUM = {"one","two","three","four","five","six","seven","eight","nine","ten"}
BANNED = re.compile(r"\b(critics?|supporters?|controversial|so-called|far-right|far-left|extremist|racist|radical|slammed|landmark|historic|sweeping|draconian|common-sense|commonsense)\b", re.I)

def today(): return datetime.date.today().isoformat()
def nowz(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def strip_html(s):
    s = re.sub(r"(?is)<(script|style|head|nav|footer)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>|</h\d>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()

def fetch_text(url, timeout=25):
    """Official text as plain text (PDFs parsed in a temp file that is deleted at once). None if unusable."""
    if not url: return None, "no url"
    try:
        r = requests.get(url, headers=UA, timeout=timeout, stream=True, allow_redirects=True)
        if r.status_code != 200: return None, f"HTTP {r.status_code}"
        data = b""
        for chunk in r.iter_content(65536):
            data += chunk
            if len(data) > 12_000_000: break
        r.close()
        ct = (r.headers.get("content-type") or "").lower()
        if data[:5] == b"%PDF-" or "pdf" in ct:
            fd, p = tempfile.mkstemp(suffix=".pdf")
            try:
                os.write(fd, data); os.close(fd); del data
                out = subprocess.run(["timeout", "-k", "3", "40", "pdftotext", "-l", "12", "-layout", p, "-"],
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=50)
                txt = out.stdout.decode("utf-8", "ignore")
            finally:
                try: os.unlink(p)
                except OSError: pass
            txt = re.sub(r"[ \t]+", " ", txt)
            txt = re.sub(r"\n\s*\n+", "\n", txt)
            txt = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", txt)  # line numbers
        elif "html" in ct or "xml" in ct or data[:300].lstrip()[:1] == b"<":
            txt = strip_html(data.decode(r.encoding or "utf-8", "ignore"))
        elif "json" in ct:
            return None, "json, not text"
        elif "word" in ct or "officedocument" in ct or data[:2] == b"PK":
            return None, "word document"
        else:
            txt = data.decode("utf-8", "ignore")
        txt = txt.strip()
        if len(txt) < MIN_TEXT: return None, f"text too short ({len(txt)} chars)"
        return txt[:TEXT_CAP], None
    except Exception as e:
        return None, f"{type(e).__name__}"

# ---------- model ----------
class Model:
    def __init__(self, backend, model, rpm):
        self.backend, self.model, self.rpm = backend, model, rpm
        if backend == "github":
            # GitHub Models; the second endpoint is the older Azure-hosted one (model names without the "openai/" prefix)
            self.endpoints = [("https://models.github.ai/inference/chat/completions", model),
                              ("https://models.inference.ai.azure.com/chat/completions", model.split("/")[-1])]
            self.url, self.model = self.endpoints.pop(0)
            self.headers = {"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"], "Content-Type": "application/json",
                            "Accept": "application/json", "X-GitHub-Api-Version": "2022-11-28"}
        elif backend == "openai":
            self.url = "https://api.openai.com/v1/chat/completions"
            self.headers = {"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]}
        else:
            mc = json.load(open("/home/user/tab/.model-capability.json"))
            self.url = mc["base_url"].rstrip("/") + "/openai/v1/chat/completions"
            self.headers = {"Authorization": "Bearer " + mc["token"], "x-tab-task": os.environ.get("TAB_TASK_ID", "")}
        self.lock = threading.Lock(); self.last = 0.0
        self.usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "errors": 0}
        self.dead = None

    def call(self, user):
        if self.dead: return None, self.dead
        body = {"model": self.model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                "response_format": {"type": "json_object"}}
        if re.search(r"gpt-5", self.model): body["reasoning_effort"] = "low"
        else: body["temperature"] = 0.2
        last = None
        for attempt in range(5):
            if self.rpm:
                with self.lock:
                    wait = self.last + 60.0 / self.rpm - time.time()
                    if wait > 0: time.sleep(wait)
                    self.last = time.time()
            try:
                r = requests.post(self.url, headers=self.headers, json=body, timeout=120)
                if r.status_code == 200:
                    try:
                        j = r.json()
                    except ValueError:
                        last = f"200 but not JSON from {self.url} ({r.headers.get('content-type')}): {r.text[:120]!r}"
                        print("  model endpoint: " + last, flush=True)
                        if getattr(self, "endpoints", None):
                            self.url, self.model = self.endpoints.pop(0); body["model"] = self.model
                            print("  switching to " + self.url, flush=True)
                            continue
                        self.dead = last; return None, last
                    u = j.get("usage") or {}
                    with self.lock:
                        self.usage["calls"] += 1
                        self.usage["prompt_tokens"] += u.get("prompt_tokens", 0)
                        self.usage["completion_tokens"] += u.get("completion_tokens", 0)
                    txt = j["choices"][0]["message"]["content"]
                    txt = re.sub(r"^```(?:json)?|```$", "", txt.strip()).strip()
                    return (json.loads(txt).get("summary") or "").strip(), None
                last = f"HTTP {r.status_code}: {r.text[:160]}"
                if r.status_code == 429 and self.backend == "github" and "day" in r.text.lower():
                    self.dead = "daily model limit reached"; return None, self.dead
                if r.status_code in (400, 401, 403, 404, 413): return None, last
            except Exception as e:
                last = f"{type(e).__name__}: {e}"
            with self.lock:
                self.usage["errors"] += 1
                self.usage["last_error"] = (last or "")[:200]
            time.sleep(min(60, 3 * 2 ** attempt + random.random() * 2))
        return None, last

def check(summary, source):
    """Never invent: every number in the summary must appear in the source. 1-4 sentences, English, no labels."""
    if not summary: return "empty"
    if BAD_SCRIPT.search(summary): return "non-English characters"
    if BANNED.search(summary): return "label/opinion word: " + BANNED.search(summary).group(0)
    n = len(re.findall(r"[.!?](?:\s|$)", summary.strip()))
    if n < 1 or n > 4 or len(summary) > 900: return f"{n} sentences / {len(summary)} chars"
    src = source.replace(",", "")
    for m in re.finditer(r"\$?(\d[\d,]*(?:\.\d+)?)(\s*(?:million|billion|thousand))?", summary):
        v = m.group(1).replace(",", "").rstrip(".")
        if not v or v.isdigit() and len(v) == 1: continue  # single digits ("2 programs") are often spelled out
        if v in src: continue
        mult = {"thousand": 1e3, "million": 1e6, "billion": 1e9}.get((m.group(2) or "").strip().lower())
        if mult:
            full = str(int(round(float(v) * mult)))
            if full in src: continue
        return f"number not in official text: {m.group(0)}"
    return None

def summarize(model, user, source):
    s, err = model.call(user)
    if s is None: return None, err
    bad = check(s, source)
    if bad:
        s2, err2 = model.call(user + f"\n\n(Your last draft was rejected: {bad}. Follow the rules exactly; 2-4 sentences; only facts and numbers from the official text.)")
        if s2 is None: return None, err2
        bad2 = check(s2, source)
        if bad2: return None, "rejected: " + bad2
        s = s2
    return s, None

# ---------- sources ----------
US_RE = re.compile(r"^US-(\d+)-([A-Z]+)(\d+)$")
def us_text_url(bid):
    m = US_RE.match(bid)
    if not m: return None
    return f"https://www.govinfo.gov/link/bills/{m.group(1)}/{m.group(2).lower()}/{m.group(3)}?link-type=html"

def load_bills(data):
    lists, det = {}, {}
    for f in sorted(glob.glob(os.path.join(data, "bills", "*.json"))):
        j = os.path.basename(f)[:-5]
        if len(j) != 2: continue
        try: d = json.load(open(f))
        except Exception: continue
        lists[j] = d.get("bills") or []
    for f in glob.glob(os.path.join(data, "bills", "detail", "*-*.json")):
        j = os.path.basename(f).rsplit("-", 1)[0]
        try: c = json.load(open(f))
        except Exception: continue
        det.setdefault(j, {}).update(c.get("bills") or {})
    return lists, det

OS_KEY = os.environ.get("OPENSTATES_API_KEY")
_os_lock = threading.Lock(); _os_last = [0.0]; _os_used = [0]
def openstates_versions(jur, number, max_calls):
    if not OS_KEY or _os_used[0] >= max_calls: return []
    with _os_lock:
        w = _os_last[0] + 6.5 - time.time()
        if w > 0: time.sleep(w)
        _os_last[0] = time.time(); _os_used[0] += 1
    try:
        r = requests.get("https://v3.openstates.org/bills", params={"jurisdiction": STATE.get(jur, jur).replace("the ", ""), "identifier": number,
                         "include": "versions", "sort": "updated_desc", "per_page": 3}, headers={"X-API-KEY": OS_KEY, **UA}, timeout=30)
        if r.status_code != 200: return []
        res = r.json().get("results") or []
        if not res: return []
        out = []
        for v in res[0].get("versions") or []:
            links = v.get("links") or []
            links.sort(key=lambda l: 0 if "html" in (l.get("media_type") or "") else 1 if "pdf" in (l.get("media_type") or "") else 2)
            for l in links[:1]: out.append(l.get("url"))
        return out[::-1]  # newest last in Open States -> newest first
    except Exception:
        return []

def state_urls(rec):
    urls = []
    if rec.get("textUrl"): urls.append(rec["textUrl"])
    vs = [v for v in (rec.get("versions") or []) if v.get("url")]
    vs_sorted = sorted(vs, key=lambda v: v.get("date") or "", reverse=True) if any(v.get("date") for v in vs) else vs[::-1]
    for v in vs_sorted:
        if v["url"] not in urls: urls.append(v["url"])
    return urls[:3]

def bill_job(bid, jur, item, rec, a):
    """Returns (entry or None, why-not)."""
    title = (rec or {}).get("title") or (item or {}).get("title") or ""
    number = (rec or {}).get("number") or (item or {}).get("number") or bid
    text, src, why = None, None, None
    urls = [us_text_url(bid)] if jur == "US" else state_urls(rec or {})
    if jur != "US" and not urls:
        urls = openstates_versions(jur, number, a.os_calls)[:2]
    for u in urls:
        if not u: continue
        text, why = fetch_text(u)
        if text: src = u; break
    off = (rec or {}).get("summary")
    if off and off != "None" and len(off) > 60 and (not text):
        # the official summary (CRS for Congress; the legislature's own digest for states) is official text too
        text, src, basis = off[:TEXT_CAP], (rec or {}).get("summarySource") or "official summary", "official summary"
    else:
        basis = "bill text"
    if not text:
        return None, why or "no official text link"
    parts = [f"Legislature: {STATE.get(jur, jur)}", f"Bill: {number}", f"Official title: {title}"]
    st = (item or {}).get("status")
    if st: parts.append(f"Latest official action: {st}")
    if off and off != "None" and basis == "bill text": parts.append("Official summary:\n" + off[:4000])
    parts.append(("Official bill text" if basis == "bill text" else "Official summary") + ":\n" + text)
    user = "\n\n".join(parts)
    s, err = summarize(a.M, user, user)
    if not s: return None, "model: " + str(err)
    return {"s": s, "basis": basis, "src": src, "model": a.model, "date": today()}, None

def eo_govinfo_url(row):
    """The order as printed in the Federal Register, from GovInfo's official FR edition (HTML). Avoids
    federalregister.gov's API, which rate-limits bulk use."""
    pdf = row.get("pdf") or ""
    if "/pdf/" in pdf and pdf.endswith(".pdf"):
        return pdf.replace("/pdf/", "/html/")[:-4] + ".htm"
    d, doc = row.get("d") or "", row.get("doc") or ""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", d) and doc:
        return f"https://www.govinfo.gov/content/pkg/FR-{d}/html/{doc}.htm"
    return None

def eo_job(n, row, a):
    url = eo_govinfo_url(row)
    text, why = fetch_text(url) if url else (None, "no Federal Register text link")
    if not text: return None, why
    text = re.sub(r"(?s)^.*?(?=Executive Order\s+\d{5})", "", text, count=1) or text
    user = f"Executive Order {n}: {row.get('t')}\nSigned: {row.get('s')}\n\nOfficial text (Federal Register):\n{text}"
    s, err = summarize(a.M, user, user)
    if not s: return None, "model: " + str(err)
    return {"s": s, "basis": "order text", "src": row.get("u") or url, "model": a.model, "date": today()}, None

# ---------- store ----------
def load_store(p, jur):
    try: return json.load(open(p))
    except Exception: return {"jurisdiction": jur, "items": {}, "noText": {}}

def save_store(p, st):
    st["updatedAt"] = nowz(); st["count"] = len(st["items"]); st["noTextCount"] = len(st["noText"])
    st["note"] = "AI summaries written only from each item's official text (see src). Not official summaries."
    tmp = p + ".tmp"
    with open(tmp, "w") as f: json.dump(st, f, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, p)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--only", default="")
    ap.add_argument("--ids", default="")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--backend", default=os.environ.get("KNOWUS_AI_BACKEND", "tab"))
    ap.add_argument("--model", default=os.environ.get("KNOWUS_AI_MODEL", "gpt-5.4-mini"))
    ap.add_argument("--rpm", type=float, default=0)
    ap.add_argument("--retry-days", type=int, default=3)
    ap.add_argument("--minutes", type=float, default=0)
    ap.add_argument("--os-calls", type=int, default=200)
    ap.add_argument("--order", default="")
    ap.add_argument("--text-cap", type=int, default=0)
    ap.add_argument("--report", action="store_true", help="only count what is missing (no model, no fetches)")
    a = ap.parse_args()
    global TEXT_CAP
    if a.text_cap: TEXT_CAP = a.text_cap
    elif a.backend == "github": TEXT_CAP = 12000  # GitHub Models free tier: 8,000 input tokens per call
    if a.report:
        lists, det = load_bills(a.data); outdir = os.path.join(a.data, "ai-summaries"); miss = {}
        for j in ["US"] + sorted(x for x in lists if x != "US"):
            st = load_store(os.path.join(outdir, j + ".json"), j)
            ids = {b["id"] for b in lists.get(j, [])}
            m = [k for k in ids if k not in st["items"]]
            miss[j] = {"inApp": len(ids), "withSummary": len(ids) - len(m), "noOfficialTextYet": sum(1 for k in m if k in st["noText"]), "notTriedYet": sum(1 for k in m if k not in st["noText"])}
        print(json.dumps(miss, indent=0)); return
    a.M = Model(a.backend, a.model, a.rpm)
    outdir = os.path.join(a.data, "ai-summaries"); os.makedirs(outdir, exist_ok=True)
    only = [x for x in a.only.split(",") if x]
    ids = set(x for x in a.ids.split(",") if x)
    lists, det = load_bills(a.data)
    jurs = only or (["US", "EO"] + sorted(j for j in lists if j != "US"))
    t0 = time.time(); total = [0, 0]; stop = [False]
    cutoff = (datetime.date.today() - datetime.timedelta(days=a.retry_days)).isoformat()
    for jur in jurs:
        if stop[0]: break
        p = os.path.join(outdir, jur + ".json"); st = load_store(p, jur)
        if jur == "EO":
            rows = []
            for f in sorted(glob.glob(os.path.join(a.data, "eo", "*.json"))):
                b = os.path.basename(f)[:-5]
                if b in ("index", "eo-build-log", "text-revocations"): continue
                try: rows += json.load(open(f)).get("items") or []
                except Exception: pass
            todo = [(r["n"], r) for r in sorted(rows, key=lambda r: -int(re.sub(r"\D", "", r["n"]) or 0))]
        else:
            L = lists.get(jur, []); D = det.get(jur, {})
            seen = set(); todo = []
            for b in L:
                if b["id"] not in seen: seen.add(b["id"]); todo.append((b["id"], b))
            for k in D:
                if k not in seen: seen.add(k); todo.append((k, None))
        todo = [(k, v) for k, v in todo if (not ids or k in ids) and k not in st["items"]
                and not (k in st["noText"] and st["noText"][k].get("tried", "") > cutoff)]
        if a.max: todo = todo[:max(0, a.max - total[0])]
        if not todo: print(f"{jur}: nothing to do ({len(st['items'])} have summaries, {len(st['noText'])} no text)", flush=True); continue
        print(f"{jur}: {len(todo)} to do", flush=True)
        lock = threading.Lock(); dirty = [0]; last = [time.time()]
        def run(kv):
            k, v = kv
            if stop[0]: return
            try:
                if jur == "EO": e, why = eo_job(k, v, a)
                else: e, why = bill_job(k, jur, v, det.get(jur, {}).get(k), a)
            except Exception as ex:
                e, why = None, f"error {type(ex).__name__}"
            with lock:
                if e:
                    st["items"][k] = e; st["noText"].pop(k, None); total[0] += 1
                elif why and why.startswith("model:"):
                    total[1] += 1  # model trouble: not a no-text case; retried next run
                    if total[1] <= 5: print(f"  {k}: {why[:300]}", flush=True)
                    if a.M.dead: stop[0] = True
                else:
                    st["noText"][k] = {"why": why, "tried": today()}; total[1] += 1
                dirty[0] += 1
                if dirty[0] >= 15 or time.time() - last[0] > 60:
                    save_store(p, st); dirty[0] = 0; last[0] = time.time()
                    print(f"  {jur}: {len(st['items'])} done, {len(st['noText'])} no text, run total {total}, {int(time.time()-t0)}s, {a.M.usage}", flush=True)
                if a.minutes and time.time() - t0 > a.minutes * 60: stop[0] = True
        with ThreadPoolExecutor(max_workers=max(1, a.concurrency)) as ex:
            list(ex.map(run, todo))
        save_store(p, st)
        print(f"{jur}: finished, {len(st['items'])} with summaries, {len(st['noText'])} without fetchable official text", flush=True)
    # index for the app / checks
    idx = {"updatedAt": nowz(), "jurisdictions": {}}
    for f in sorted(glob.glob(os.path.join(outdir, "*.json"))):
        j = os.path.basename(f)[:-5]
        if j == "index": continue
        try: s = json.load(open(f))
        except Exception: continue
        idx["jurisdictions"][j] = {"count": len(s.get("items", {})), "noText": len(s.get("noText", {})), "updatedAt": s.get("updatedAt")}
    with open(os.path.join(outdir, "index.json"), "w") as f: json.dump(idx, f, indent=1, sort_keys=True)
    print("done", total, a.M.usage, f"{int(time.time()-t0)}s", flush=True)

if __name__ == "__main__":
    main()
