#!/usr/bin/env python3
"""KnowUS pre-election ballot capture ("our own VIP data").

Reads data/capture/calendar.json (official election dates) and data/capture/sources.json (where each state/county
posts its official sample ballots), and at fixed checkpoints before each election (45, 30, 14, 5 and 2 days out)
downloads every registered official source, records a manifest (URL, sha256, bytes, fetch time) in the repo and
stores the raw files as GitHub release assets (one zip per source per checkpoint, only new or changed files).

Rules: official sources only (the registry is the allow-list); an honest User-Agent; robots.txt respected;
a source that walls automated fetches is queued in data/capture/needs-browser.json instead of being retried;
every request has a timeout; at most 3 downloads at once; a polite delay per host. No paid services.

Usage:
  capture.py plan  [--today YYYY-MM-DD]                      what is due today
  capture.py run   [--today D] [--only ST] [--election D --state ST --checkpoint T14]
                   [--max-files N] [--no-upload] [--out DIR]
"""
import argparse, concurrent.futures as cf, datetime as dt, hashlib, json, os, re, sys, threading, time, zipfile
import urllib.parse as up, urllib.robotparser as rp
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAP = os.environ.get('CAPTURE_DIR') or os.path.join(ROOT, 'data', 'capture')
CHECKPOINTS = [45, 30, 14, 5, 2]          # days before election day
UA = 'KnowUS-ballot-capture/1.0 (free civic app; +https://github.com/knowusadmin/knowus-data)'
TIMEOUT = (15, 60)
MAX_FILE = 150 * 1024 * 1024
MAX_RUN_BYTES = int(os.environ.get('CAPTURE_MAX_RUN_BYTES', 6 * 1024 ** 3))
HOST_DELAY = 0.6
WALL_MARKERS = re.compile(r'(?i)(captcha|cf-chl|challenge-platform|access denied|request unsuccessful|incapsula|are you a robot|perimeterx|ddos protection|awswaf|x-amzn-waf)')
HREF_RX = re.compile(r"""(?i)\bhref\s*=\s*["']([^"'#]+)""")

def load(p, default):
    try:
        with open(p) as f: return json.load(f)
    except FileNotFoundError: return default

def save(p, obj, compact=False):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w') as f:
        if compact: json.dump(obj, f, separators=(',', ':'), ensure_ascii=False, sort_keys=True)
        else: json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write('\n')
    os.replace(tmp, p)

def slug(s): return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')[:60] or 'x'

def today_et():
    # election offices work in local time; US Eastern is close enough for a daily job
    return (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()

# ---------------------------------------------------------------- plan
def elections(cal, only=None):
    for st, s in sorted((cal.get('states') or {}).items()):
        if only and st not in only: continue
        for e in s.get('elections') or []:
            try: d = dt.date.fromisoformat(e['date'])
            except Exception: continue
            yield st, d, e

def scope_of(e, county_names):
    """Which registered counties an election reaches: None = all (statewide or unknown), else the set whose names the
    calendar entry itself names (e.g. "Pinecrest Runoff election (Miami-Dade County)")."""
    if (e.get('scope') or '').startswith('statewide') or (e.get('whoVotes') or '').strip().lower() == 'all': return None
    txt = ' '.join(str(e.get(k) or '') for k in ('name', 'covers', 'whoVotes', 'notes')).lower()
    hit = {c for c in county_names if c and re.search(r'\b' + re.escape(c.lower()) + r'\b', txt)}
    return hit or None

def due(cal, state, today, only=None):
    """One job per (election date, state): the closest checkpoint already reached and not yet done."""
    jobs = {}
    for st, d, e in elections(cal, only):
        left = (d - today).days
        if left < 0 or left > max(CHECKPOINTS): continue
        key = f'{d.isoformat()}|{st}'
        done = (state.get(key) or {}).get('done') or {}
        reached = [c for c in CHECKPOINTS if left <= c]
        if not reached: continue
        cp = min(reached)
        if f'T{cp}' in done: continue
        j = jobs.setdefault(key, {'state': st, 'election': d.isoformat(), 'daysLeft': left, 'checkpoint': f'T{cp}', 'names': [], 'scope': set()})
        j['names'].append(e.get('name') or ''); j.setdefault('kinds', []).append((e.get('kind') or '').lower())
        sc = scope_of(e, COUNTY_NAMES.get(st, []))
        j['scope'] = None if (sc is None or j['scope'] is None) else (j['scope'] | sc)
    for j in jobs.values(): j['scope'] = sorted(j['scope']) if j['scope'] is not None else None
    return sorted(jobs.values(), key=lambda j: (j['election'], j['state']))
COUNTY_NAMES = {}

# ---------------------------------------------------------------- fetch helpers
class Fetcher:
    def __init__(self):
        self.s = requests.Session(); self.s.headers['User-Agent'] = UA
        self.lock = threading.Lock(); self.last = {}; self.robots = {}; self.bytes = 0
    def allowed(self, url):
        h = up.urlsplit(url); base = f'{h.scheme}://{h.netloc}'
        with self.lock:
            r = self.robots.get(base)
        if r is None:
            r = rp.RobotFileParser()
            try:
                x = self.s.get(base + '/robots.txt', timeout=(10, 20))
                ok = x.status_code == 200 and 'html' not in x.headers.get('content-type', '')
                r.parse(x.text.splitlines() if ok else [])
            except Exception:
                r.parse([])
            with self.lock: self.robots[base] = r
        return r.can_fetch(UA, url)
    def wait_host(self, url):
        h = up.urlsplit(url).netloc
        while True:
            with self.lock:
                t = time.time(); last = self.last.get(h, 0)
                if t - last >= HOST_DELAY:
                    self.last[h] = t; return
            time.sleep(HOST_DELAY / 3)
    def get(self, url, stream=False, headers=None):
        self.wait_host(url)
        return self.s.get(url, timeout=TIMEOUT, stream=stream, allow_redirects=True, headers=headers)

def walled(resp, body=b''):
    head = body[:20000].decode('latin-1', 'ignore')
    if resp.status_code in (401, 403, 429) or (resp.status_code == 503 and WALL_MARKERS.search(head)):
        return f'HTTP {resp.status_code}'
    if 'html' in resp.headers.get('content-type', '') and len(body) < 60000 and WALL_MARKERS.search(head):
        return 'bot challenge page'
    return None

def fill(tmpl, election):
    d = dt.date.fromisoformat(election)
    return (tmpl.replace('{date}', d.isoformat()).replace('{yyyymmdd}', d.strftime('%Y%m%d'))
                .replace('{mmddyyyy}', d.strftime('%m%d%Y')).replace('{mmddyy}', d.strftime('%m%d%y'))
                .replace('{yymmdd}', d.strftime('%y%m%d')).replace('{year}', str(d.year))
                .replace('{mm}', d.strftime('%m')).replace('{dd}', d.strftime('%d')).replace('{yy}', d.strftime('%y'))
                .replace('{yyyy}', str(d.year)).replace('{mmdd}', d.strftime('%m%d')).replace('{m}', str(d.month)).replace('{d}', str(d.day))
                .replace('{month}', d.strftime('%B').lower()).replace('{mon}', d.strftime('%b').lower()))

def list_links(f, url, rx, file_base=None):
    r = f.get(url); body = r.content
    w = walled(r, body)
    if w: return None, w
    if r.status_code != 200: return None, f'HTTP {r.status_code}'
    txt = body.decode(r.encoding or 'utf-8', 'ignore')
    out = []
    if '<ListBucketResult' in txt[:500]:           # an S3 bucket listing (e.g. the NC State Board's files)
        base = file_base or url.split('?')[0].rstrip('/') + '/'
        while True:
            out += [base + up.quote(k) for k in re.findall(r'<Key>([^<]+)</Key>', txt) if re.search(rx, k, re.I)]
            tok = re.search(r'<NextContinuationToken>([^<]+)<', txt)
            if not tok or len(out) > 20000: break
            txt = f.get(url + ('&' if '?' in url else '?') + 'continuation-token=' + up.quote(tok.group(1))).text
    else:
        for h in HREF_RX.findall(txt):
            a = up.urljoin(r.url, h.strip())
            if re.search(rx, a, re.I): out.append(a)
    seen = set(); res = []
    for u in out:
        if u not in seen: seen.add(u); res.append(u)
    return res, None

def ev_links(f, fe, election):
    """Enhanced Voting sample-ballot API (the official sample-ballot app Georgia's and New York's counties link to):
    jurisdiction -> counties with their elections -> ballot styles -> one full ballot JSON per style."""
    api = fe.get('base') or 'https://app.enhancedvoting.com/ebd/voter/api'
    hd = dict(fe.get('headers') or {'X-CSRF': '1'})
    r = f.get(f"{api}/jurisdiction/{up.quote(fe['jurisdiction'])}", headers=hd)
    if walled(r, r.content): return None, walled(r, r.content), hd
    parent = r.json()['id']
    locs = f.get(f'{api}/jurisdiction/{parent}/localities/?includeElection=true', headers=hd).json()
    out = []
    for c in locs:
        if fe.get('counties') and c['name'][0]['text'] not in fe['counties']: continue
        for e in c.get('elections') or []:
            if (e.get('date') or '')[:10] != election: continue
            x = f.get(f"{api}/jurisdiction/{c['id']}/election/{e['id']}/ballotStyles?excludeFederalOnly=false", headers=hd)
            if x.status_code != 200: continue
            for s in x.json():
                if not s.get('precincts'): continue
                out.append(f"{api}/ballotStyle/{s['id']}?jurisdictionId={c['id']}&precinctId={s['precincts'][0]['id']}&ballotType=sample")
            out.append(f"{api}/jurisdiction/{c['id']}/election/{e['id']}/ballotStyles?excludeFederalOnly=false")
    return out, None, hd

# ---------------------------------------------------------------- run
DATE_TOKENS = [re.compile(r'(?<!\d)(20\d\d)[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?!\d)'),   # 2026-11-03, 20261103
               re.compile(r'(?<!\d)(0[1-9]|1[0-2])[-_.](0[1-9]|[12]\d|3[01])[-_.](20\d\d|\d\d)(?!\d)')]     # 11-03-2026, 11.17.26
def other_election(url, election):
    """True when the file name is dated, and none of its dates is this election's (a different election's ballot)."""
    d = dt.date.fromisoformat(election); name = up.unquote(url.split('?')[0].rsplit('/', 1)[-1])
    seen = []
    for m in DATE_TOKENS[0].finditer(name): seen.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in DATE_TOKENS[1].finditer(name):
        y = int(m.group(3)); seen.append((y + 2000 if y < 100 else y, int(m.group(1)), int(m.group(2))))
    return bool(seen) and (d.year, d.month, d.day) not in seen

def entries_of(reg):
    out = [dict(e, _scope='statewide', _county=None) for e in reg.get('statewide') or []]
    out += [dict(e, _scope='county', _county=e.get('county') or e.get('town')) for e in reg.get('counties') or []]
    return out

def seen_elsewhere(st, el):
    """URL -> sha256 of every file already captured for this state's OTHER elections (an undated file still posted from
    the last election must not be filed under the next one)."""
    out = {}
    base = os.path.join(CAP, 'manifests')
    if not os.path.isdir(base): return out
    for d in os.listdir(base):
        if d == el: continue
        p = os.path.join(base, d, st)
        if not os.path.isdir(p): continue
        for fn in os.listdir(p):
            for u, fi in (load(os.path.join(p, fn), {}).get('files') or {}).items(): out[u] = (d, fi.get('sha256'))
    return out

def run_job(job, sources, args, f, queue):
    st, el, cp = job['state'], job['election'], job['checkpoint']
    elsewhere = seen_elsewhere(st, el)
    BASE = load(os.path.join(CAP, 'baseline.json'), {}).get('urls') or {}
    reg = (sources.get('states') or {}).get(st) or {}
    rel_tag = f'capture-{el}-{st}'
    out_dir = os.path.join(args.out, rel_tag); os.makedirs(out_dir, exist_ok=True)
    now0 = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    summary = {'state': st, 'election': el, 'checkpoint': cp, 'at': now0, 'sources': 0, 'files': 0, 'new': 0,
               'bytesNew': 0, 'captured': [], 'notPosted': [], 'walled': [], 'lookupOnly': [], 'errors': []}
    def enqueue(sid, name, url, why):
        queue[f'{el}|{st}|{sid}'] = {'state': st, 'election': el, 'source': name, 'url': url, 'why': why, 'queued': now0}
        summary['walled'].append(name)
    scope = set(job.get('scope') or []) or None
    for e in entries_of(reg):
        if scope and e['_county'] and e['_county'] not in scope: continue
        fe = e.get('fetch') or {}
        what = e.get('what') or e.get('format') or 'source'
        name = (e['_county'] + ': ' if e['_county'] else '') + what
        sid = slug(('statewide' if e['_scope'] == 'statewide' else e['_county']) + '-' + what)
        typ = fe.get('type') or 'none'
        summary['sources'] += 1
        if typ == 'none' or e.get('format') == 'lookup-only':
            summary['lookupOnly'].append(name); continue
        tmpl = fe.get('urlTemplate') or (fe.get('indexTemplate') if typ == 'index' else None)
        kinds = ' '.join(job.get('kinds') or [])
        if tmpl and job.get('kinds') and any(w in tmpl.lower() and w not in kinds for w in ('general', 'primary')):
            summary.setdefault('needsPage', []).append(f'{name}: its template is for {"general" if "general" in tmpl.lower() else "primary"} elections only'); continue
        if tmpl and not fe.get('urlTemplate'): fe['urlTemplate'] = tmpl
        url = (fill(tmpl, el) if tmpl else None) or fe.get('url') or e.get('url')
        if not url: summary['errors'].append(f'{name}: no URL in the registry'); continue
        # an entry can only serve this election if it is dated by template, standing ("evergreen": the office's page that
        # always shows the next election), an API matched on the date, or recorded for exactly this election
        dated = bool(fe.get('urlTemplate') and '{' in fe['urlTemplate']) or '{' in (fe.get('mustContain') or '')
        if not (dated or e.get('evergreen') or typ == 'api' or e.get('election') == el or (url and not other_election(url, el) and el.replace('-', '') in re.sub(r'\D', '', url))):
            summary.setdefault('needsPage', []).append(f'{name}: the registered page is for another election'); continue
        if e.get('walled'): enqueue(sid, name, url, e.get('wallNote') or 'walled (registry)'); continue
        if not f.allowed(url): enqueue(sid, name, url, 'robots.txt disallows automated fetches'); continue
        try:
            if typ == 'index':
                links, why = list_links(f, url, fe.get('linkRegex') or r'\.pdf($|\?)', fe.get('fileBase'))
                if links is None and why in ('HTTP 404', 'HTTP 410'):
                    summary['notPosted'].append(f'{name}: page {why}'); continue
                if links is None: enqueue(sid, name, url, why); continue
                if fe.get('mustContain'):
                    need = fill(fe['mustContain'], el).lower()
                    links = [u for u in links if need in up.unquote(u).lower()]
                n0 = len(links); links = [u for u in links if not other_election(u, el)]
                if n0 != len(links): summary.setdefault('skippedOtherElection', []).append(f'{name}: {n0 - len(links)} files dated for another election')
            elif typ == 'api' and fe.get('api') == 'enhancedvoting':
                links, why, hdrs = ev_links(f, fe, el)
                if links is None: enqueue(sid, name, url, why); continue
            else:
                links = [url]
        except Exception as ex:
            summary['errors'].append(f'{name}: {type(ex).__name__}: {str(ex)[:160]}'); continue
        if not links:
            summary['notPosted'].append(f'{name}: no matching files on the page yet'); continue
        links = links[:args.max_files]
        mpath = os.path.join(CAP, 'manifests', el, st, sid + '.json')
        man = load(mpath, {'state': st, 'election': el, 'source': name, 'page': url, 'format': e.get('format'),
                           'parser': e.get('parser'), 'files': {}, 'runs': []})
        asset = f'{sid}-{cp}-{now0[:10].replace("-", "")}.zip'
        zpath = os.path.join(out_dir, asset)
        zlock = threading.Lock(); zf = zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED)
        stats = {'files': 0, 'new': 0, 'bytes': 0, 'wall': 0, 'err': 0, 'missing': 0}
        hdrs = fe.get('headers') or ({'X-CSRF': '1'} if fe.get('api') == 'enhancedvoting' else None)
        def one(u):
            if f.bytes > MAX_RUN_BYTES or stats['wall'] >= 3: return
            try:
                r = f.get(u, stream=True, headers=hdrs)
                body = r.raw.read(MAX_FILE + 1, decode_content=True) if r.status_code == 200 else r.content[:30000]
                r.close()
            except Exception:
                with zlock: stats['err'] += 1
                return
            if walled(r, body):
                with zlock: stats['wall'] += 1
                return
            if r.status_code in (404, 410):
                with zlock: stats['missing'] += 1
                return
            if r.status_code != 200 or len(body) > MAX_FILE:
                with zlock: stats['err'] += 1
                return
            h = hashlib.sha256(body).hexdigest()
            now = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
            lm = r.headers.get('last-modified')
            if u in BASE:
                try:
                    import email.utils as eu
                    fresh = lm and eu.parsedate_to_datetime(lm).replace(tzinfo=None) > dt.datetime.fromisoformat(BASE[u][:19])
                except Exception: fresh = False
                if not fresh:
                    with zlock: stats['other'] = stats.get('other', 0) + 1
                    return
            if u in elsewhere and elsewhere[u][1] == h:
                with zlock: stats['other'] = stats.get('other', 0) + 1
                return
            with zlock:
                f.bytes += len(body); stats['files'] += 1
                old = man['files'].get(u)
                if old and old['sha256'] == h:
                    old['last'] = now; return
                base = re.sub(r'[^A-Za-z0-9._-]+', '_', up.unquote(u.split('?')[0].rsplit('/', 1)[-1]))[-120:] or 'file'
                if fe.get('api'): base = hashlib.sha1(u.encode()).hexdigest()[:12] + '-' + base + '.json'
                arc = f'{len(man["files"]):05d}-{base}'
                zf.writestr(arc, body)
                man['files'][u] = {'sha256': h, 'bytes': len(body), 'type': r.headers.get('content-type', '').split(';')[0],
                                   'first': (old or {}).get('first', now), 'last': now, 'asset': asset, 'name': arc}
                stats['new'] += 1; stats['bytes'] += len(body)
        with cf.ThreadPoolExecutor(max_workers=3) as ex:
            list(ex.map(one, links))
        zf.close()
        if stats['new'] == 0: os.remove(zpath)
        if stats['wall'] >= 3: enqueue(sid, name, url, 'files walled mid-download')
        man['runs'].append({'cp': cp, 'at': now0, 'links': len(links), 'ok': stats['files'], 'new': stats['new'],
                            'bytesNew': stats['bytes'], 'errors': stats['err'], 'notServed': stats['missing'], 'walled': stats['wall'],
                            'asset': asset if stats['new'] else None, 'release': rel_tag if stats['new'] else None})
        save(mpath, man, compact=True)
        summary['files'] += stats['files']; summary['new'] += stats['new']; summary['bytesNew'] += stats['bytes']
        summary['captured'].append(f'{name}: {stats["files"]} files ({stats["new"]} new)' + (f', {stats["missing"]} listed but not served (404)' if stats['missing'] else ''))
        if stats['err']: summary['errors'].append(f'{name}: {stats["err"]} of {len(links)} files failed')
        if stats.get('other'): summary.setdefault('skippedOtherElection', []).append(f'{name}: {stats["other"]} files unchanged from another election')
    return summary, out_dir, rel_tag

def upload(out_dir, rel_tag, job):
    import subprocess
    files = [os.path.join(out_dir, x) for x in sorted(os.listdir(out_dir)) if x.endswith('.zip')]
    if not files: return 'nothing new'
    if subprocess.run(['gh', 'release', 'view', rel_tag], capture_output=True, timeout=60).returncode != 0:
        subprocess.run(['gh', 'release', 'create', rel_tag, '--title', f'Ballot capture {job["election"]} {job["state"]}',
                        '--notes', 'Raw official sample ballots captured before the election (KnowUS ballot capture). '
                        f'Manifest: data/capture/manifests/{job["election"]}/{job["state"]}/', '--latest=false'],
                       check=True, timeout=120, capture_output=True)
    subprocess.run(['gh', 'release', 'upload', rel_tag, '--clobber'] + files, check=True, timeout=1800, capture_output=True)
    return f'{len(files)} asset(s) to release {rel_tag}'

def baseline(src, f, out_path):
    """Record every file an evergreen (standing) page lists right now as belonging to elections already past, so the
    next election's capture never files them as its own. URL list only (no downloads); a later capture takes such a URL
    only when its Last-Modified is after the baseline date."""
    base = load(out_path, {'v': 1, 'note': 'files already posted on standing pages before capture began; not filed under later elections unless modified', 'urls': {}})
    now = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'; n = 0
    for st, reg in sorted((src.get('states') or {}).items()):
        for e in entries_of(reg):
            fe = e.get('fetch') or {}
            if not e.get('evergreen') or e.get('walled') or fe.get('type') not in ('index', 'file'): continue
            url = fe.get('url') or e.get('url')
            if not url: continue
            try:
                links = list_links(f, url, fe.get('linkRegex') or r'\.pdf($|\?)', fe.get('fileBase'))[0] if fe['type'] == 'index' else [url]
            except Exception: links = None
            for u in links or []:
                base['urls'].setdefault(u, now); n += 1
    save(out_path, base, compact=True)
    return n

def ingest(a, queue):
    """Files saved by browser_fetch.mjs -> the same manifest + release asset as a plain capture."""
    out = []
    for d in sorted(os.listdir(a.browser_dir)):
        lp = os.path.join(a.browser_dir, d, 'list.json')
        if not os.path.exists(lp): continue
        L = json.load(open(lp)); q = L['queued']; st, el = q['state'], q['election']
        sid = slug(L['key'].split('|', 2)[2]); rel_tag = f'capture-{el}-{st}'
        out_dir = os.path.join(a.out, rel_tag); os.makedirs(out_dir, exist_ok=True)
        now = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        mpath = os.path.join(CAP, 'manifests', el, st, sid + '.json')
        man = load(mpath, {'state': st, 'election': el, 'source': q['source'], 'page': q['url'], 'files': {}, 'runs': []})
        reg = (load(os.path.join(CAP, 'sources.json'), {}).get('states') or {}).get(st) or {}
        ent = next((e for e in entries_of(reg) if ((e['_county'] + ': ') if e['_county'] else '') + (e.get('what') or e.get('format') or 'source') == q['source']), {})
        man['format'] = ent.get('format'); man['parser'] = ent.get('parser')
        asset = f'{sid}-browser-{now[:10].replace("-", "")}.zip'; zpath = os.path.join(out_dir, asset)
        n_new = n_ok = 0
        with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for it in L['files']:
                if not it.get('file'): continue
                body = open(os.path.join(a.browser_dir, d, 'files', it['file']), 'rb').read(); h = hashlib.sha256(body).hexdigest(); n_ok += 1
                old = man['files'].get(it['url'])
                if old and old['sha256'] == h: old['last'] = now; continue
                arc = f'{len(man["files"]):05d}-' + it['file'][6:]
                zf.writestr(arc, body); n_new += 1
                man['files'][it['url']] = {'sha256': h, 'bytes': len(body), 'type': (it.get('type') or '').split(';')[0],
                                           'first': (old or {}).get('first', now), 'last': now, 'asset': asset, 'name': arc, 'via': 'browser'}
        if not n_new: os.remove(zpath)
        man['runs'].append({'cp': 'browser', 'at': now, 'links': L['links'], 'ok': n_ok, 'new': n_new, 'asset': asset if n_new else None,
                            'release': rel_tag if n_new else None, 'via': 'browser'})
        save(mpath, man, compact=True)
        if n_ok: queue[L['key']]['browserDone'] = now
        out.append({'state': st, 'election': el, 'source': q['source'], 'files': n_ok, 'new': n_new, 'dir': out_dir, 'tag': rel_tag})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['plan', 'run', 'ingest', 'baseline']); ap.add_argument('--browser-dir')
    ap.add_argument('--today'); ap.add_argument('--only'); ap.add_argument('--election'); ap.add_argument('--state')
    ap.add_argument('--checkpoint')
    ap.add_argument('--max-files', type=int, default=5000); ap.add_argument('--no-upload', action='store_true')
    ap.add_argument('--out', default=os.path.join(os.environ.get('RUNNER_TEMP', '/tmp'), 'knowus-capture'))
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.today) if a.today else today_et()
    cal = load(os.path.join(CAP, 'calendar.json'), {}); src = load(os.path.join(CAP, 'sources.json'), {})
    stp = os.path.join(CAP, 'state.json'); state = load(stp, {})
    for st_, r_ in (src.get('states') or {}).items(): COUNTY_NAMES[st_] = [x.get('county') or x.get('town') for x in r_.get('counties') or []]
    only = set(a.only.upper().split(',')) if a.only else None
    if a.election and a.state:
        d = dt.date.fromisoformat(a.election)
        jobs = [{'state': a.state.upper(), 'election': a.election, 'daysLeft': (d - today).days,
                 'checkpoint': a.checkpoint or 'manual', 'names': ['manual run']}]
    else:
        jobs = due(cal, state, today, only)
    if a.cmd == 'plan':
        print(json.dumps({'today': today.isoformat(), 'jobs': jobs}, indent=1)); return
    if a.cmd == 'baseline':
        print('baseline urls:', baseline(src, Fetcher(), os.path.join(CAP, 'baseline.json'))); return
    qp = os.path.join(CAP, 'needs-browser.json'); queue = load(qp, {})
    if a.cmd == 'ingest':
        res = ingest(a, queue)
        for r in res:
            if r['new'] and not a.no_upload:
                try: r['upload'] = upload(r['dir'], r['tag'], {'election': r['election'], 'state': r['state']})
                except Exception as ex: r['upload'] = f'FAILED: {str(ex)[:200]}'
        print(json.dumps(res, indent=1)); save(qp, queue); return
    f = Fetcher(); log = load(os.path.join(CAP, 'status.json'), {'runs': []})
    for job in jobs:
        print(f'== {job["election"]} {job["state"]} {job["checkpoint"]} ({job["daysLeft"]} days left)', flush=True)
        summ, out_dir, tag = run_job(job, src, a, f, queue)
        try: summ['upload'] = 'skipped (--no-upload)' if a.no_upload else upload(out_dir, tag, job)
        except Exception as ex: summ['upload'] = f'FAILED: {str(ex)[:200]}'
        print(json.dumps(summ, indent=1), flush=True)
        if job['checkpoint'] != 'manual' and not summ['upload'].startswith('FAILED'):
            state.setdefault(f'{job["election"]}|{job["state"]}', {}).setdefault('done', {})[job['checkpoint']] = summ['at']
        log['runs'] = (log.get('runs') or [])[-199:] + [summ]
        save(stp, state); save(qp, queue)
        if f.bytes > MAX_RUN_BYTES: print('run byte budget reached; the rest waits for the next run', flush=True); break
    log['last'] = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'; log['today'] = today.isoformat()
    log['upcoming'] = [{'state': st, 'date': d.isoformat(), 'name': e.get('name'), 'daysLeft': (d - today).days}
                       for st, d, e in elections(cal) if 0 <= (d - today).days <= 60]
    save(os.path.join(CAP, 'status.json'), log)

if __name__ == '__main__':
    main()
