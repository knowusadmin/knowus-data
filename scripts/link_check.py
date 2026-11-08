#!/usr/bin/env python3
"""KnowUS website up/down checker (GitHub Actions, free).

  python3 scripts/link_check.py check   [--all] [--budget-min 28]
  node    scripts/link_verify.mjs        (real-browser second opinion, Playwright)
  python3 scripts/link_check.py finalize

State:  data/link-status.json  one line per tracked URL:
          {"status":"up"|"down","since":iso,"lastChecked":iso|null,"fails":n,"why":"..."}
App:    data/links-down.json   only the links that are down right now (small; the app reads it)

Rules
- Each run checks every link that is down or failed last time, plus 1/8 of all links
  (rotating by the run's 3-hour slot), so every link is checked once a day.
- One check = HEAD, then GET when HEAD fails; 20 s timeout; 2 retries.
- A link is marked DOWN only after failing 2 checks in a row AND failing in a real browser
  (Playwright) too; sites that answer bots with 401/403/429/challenge pages count as up.
- A down link is marked UP after 1 good check (a parked "domain for sale" page is not "up").
"""
import asyncio, json, os, re, sys, time, zlib, ssl, random
from collections import Counter
TARGETS = 'data/links/targets.json'
STATE = 'data/link-status.json'
DOWN = 'data/links-down.json'
PENDING = 'links-pending.json'      # not committed
VERIFIED = 'links-verified.json'    # not committed
SLOTS = 8
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/131.0.0.0 Safari/537.36')
HDR = {'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Language': 'en-US,en;q=0.9'}
BLOCK = {401, 403, 405, 406, 407, 409, 418, 429, 451, 999}   # the site answered; it just doesn't like bots
PARKED = re.compile(r'(this domain (name )?(is|may be) for sale|buy this domain|domain is parked|parked free|'
                    r'parkingcrew|sedoparking|hugedomains\.com|dan\.com/buy|afternic|bodis\.com|'
                    r'domain has expired|this domain has been registered|renew (your|this) domain|'
                    r'godaddy\.com/domainsearch|future home of something quite cool)', re.I)
CHALLENGE = re.compile(r'(cf-chl|just a moment|attention required|checking your browser|captcha|'
                       r'access denied|request rejected|incapsula|akamai|ddos-guard|sucuri)', re.I)

def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def slot_of(u):
    return zlib.crc32(u.encode()) % SLOTS

def load(p, default):
    try:
        with open(p) as fh:
            return json.load(fh)
    except Exception:
        return default

def write_state(st):
    links = st['links']
    with open(STATE, 'w') as fh:
        head = {k: v for k, v in st.items() if k != 'links'}
        fh.write('{' + ','.join('%s:%s' % (json.dumps(k), json.dumps(v)) for k, v in head.items()) + ',"links":{\n')
        fh.write(',\n'.join('%s:%s' % (json.dumps(u), json.dumps(links[u], separators=(',', ':')))
                            for u in sorted(links)))
        fh.write('\n}}\n')

def host(u):
    return re.sub(r'^https?://', '', u).split('/')[0].split('@')[-1].split(':')[0].lower()

# ---------------------------------------------------------------- one check
async def probe(session, u, need_body=False):
    import aiohttp
    t = aiohttp.ClientTimeout(total=20, sock_connect=15)
    async def once(method, verify=True):
        kw = dict(headers=HDR, timeout=t, allow_redirects=True, max_redirects=10)
        if not verify:
            kw['ssl'] = False
        async with session.request(method, u, **kw) as r:
            body = ''
            if method == 'GET' and r.status < 400:
                try:
                    body = (await r.content.read(65536)).decode('utf-8', 'ignore')
                except Exception:
                    body = ''
            elif method == 'GET':
                try:
                    body = (await r.content.read(16384)).decode('utf-8', 'ignore')
                except Exception:
                    body = ''
            return r.status, body, r.headers
    def classify(status, body, headers):
        server = (headers.get('server') or '').lower() if headers else ''
        if status < 400:
            if PARKED.search(body or ''):
                return ('fail', 'parked')
            return ('up', status)
        if status in BLOCK:
            return ('blocked', status)
        if status in (500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526, 530) and (
                'cloudflare' in server or (headers and headers.get('cf-mitigated')) or CHALLENGE.search(body or '')):
            if status == 503 or CHALLENGE.search(body or ''):
                return ('blocked', status)
        if status in (404, 410):
            return ('fail', 'http%d' % status)
        return ('fail', 'http%d' % status)
    last = ('fail', 'unknown')
    for attempt in range(3):              # 1 try + 2 retries
        try:
            if attempt == 0:                  # HEAD first; retries go straight to GET
                try:
                    s, b, h = await once('HEAD')
                    res = classify(s, b, h)
                    if res[0] == 'up' and not need_body:
                        return res     # HEAD can't see a parked page, so links that were failing always get a GET
                except Exception as e:
                    m = str(e).lower()
                    if 'name or service' in m or 'nodename' in m or 'no address' in m or 'name resolution' in m:
                        raise          # no DNS record: a GET can't do better
            try:
                s, b, h = await once('GET')
            except Exception as e:
                name = type(e).__name__
                msg = str(e)
                if 'SSL' in name or 'ssl' in msg.lower() or 'certificate' in msg.lower():
                    s, b, h = await once('GET', verify=False)    # expired cert: browsers still show the site
                else:
                    raise
            last = classify(s, b, h)
            if last[0] != 'fail' or last[1] == 'parked':
                return last
        except asyncio.TimeoutError:
            last = ('fail', 'timeout')
        except Exception as e:
            n = type(e).__name__
            m = str(e).lower()
            if 'name or service' in m or 'nodename' in m or 'no address' in m or 'name resolution' in m or 'getaddrinfo' in m:
                last = ('fail', 'dns')
            elif 'refused' in m:
                last = ('fail', 'refused')
            elif 'timeout' in n.lower() or 'timeout' in m:
                last = ('fail', 'timeout')
            elif 'ssl' in m or 'certificate' in m:
                last = ('fail', 'ssl')
            elif 'reset' in m or 'disconnected' in m or 'serverdisconnected' in n.lower():
                last = ('fail', 'reset')
            else:
                last = ('fail', n[:40])
        if attempt < 2:
            await asyncio.sleep(3 + 5 * attempt)
    return last

async def run_checks(urls, budget_s, need):
    import aiohttp
    conn = aiohttp.TCPConnector(limit=160, limit_per_host=3, ttl_dns_cache=600, ssl=ssl.create_default_context())
    out = {}
    deadline = time.time() + budget_s
    q = asyncio.Queue()
    for u in urls:
        q.put_nowait(u)
    async with aiohttp.ClientSession(connector=conn, cookie_jar=aiohttp.DummyCookieJar()) as s:
        async def worker():
            while time.time() < deadline:
                try:
                    u = q.get_nowait()
                except asyncio.QueueEmpty:
                    return
                try:
                    out[u] = await asyncio.wait_for(probe(s, u, u in need), timeout=120)
                except Exception:
                    out[u] = ('fail', 'timeout')
                if len(out) % 1000 == 0:
                    print(len(out), 'checked', time.strftime('%H:%M:%S'), flush=True)
        await asyncio.gather(*[worker() for _ in range(160)])
    return out

# ---------------------------------------------------------------- commands
def cmd_check(argv):
    full = '--all' in argv
    budget = 28
    if '--budget-min' in argv:
        budget = float(argv[argv.index('--budget-min') + 1])
    targets = load(TARGETS, {}).get('urls', {})
    if not targets:
        raise SystemExit('no targets')
    st = load(STATE, {'version': 1, 'links': {}})
    links = st.setdefault('links', {})
    t = now()
    for u in list(links):                      # links the app no longer shows
        if u not in targets:
            del links[u]
    for u in targets:
        links.setdefault(u, {'status': 'up', 'since': t, 'lastChecked': None, 'fails': 0})
    slot = (time.gmtime().tm_hour // 3) % SLOTS
    due = [u for u, v in links.items() if v['status'] == 'down' or v.get('fails', 0) > 0]
    dset = set(due)
    rest = [u for u in links if u not in dset and (full or slot_of(u) == slot)]
    random.shuffle(rest)
    order = due + rest
    print('slot', slot, 'checking', len(due), 'down/suspect +', len(rest), 'others', flush=True)
    res = asyncio.run(run_checks(order, budget * 60, dset))
    # A big host that suddenly fails for most of its links is throttling this runner (it happened with
    # federalregister.gov: 820 timeouts here, all fine from a normal connection). Those failures say
    # nothing about the site, so they are not counted.
    CONN = ('timeout', 'reset', 'refused', 'ssl', 'TooManyRedirects')
    per = Counter(host(u) for u in res)
    bad = Counter(host(u) for u, (k, i) in res.items() if k == 'fail' and i in CONN)
    throttled = {h for h, n in per.items() if n >= 10 and bad[h] >= 0.5 * n}
    if throttled:
        print('hosts throttling this runner (not counted):', sorted(throttled)[:20], flush=True)
    pending = []
    c = Counter()
    for u, (kind, info) in res.items():
        v = links[u]
        v['lastChecked'] = t
        if kind == 'fail' and info in CONN and host(u) in throttled:
            c['throttled'] += 1
            if v['status'] == 'up':
                v['fails'] = 0
                v['why'] = 'throttled'
            continue
        if kind in ('up', 'blocked'):
            c['ok'] += 1
            if v['status'] == 'down':
                v['status'] = 'up'; v['since'] = t; c['back_up'] += 1
            v['fails'] = 0
            v.pop('why', None)
            if kind == 'blocked':
                v['bot'] = info
            else:
                v.pop('bot', None)
        else:
            c['fail'] += 1
            v['fails'] = min(v.get('fails', 0) + 1, 99)
            v['why'] = info
            if v['status'] == 'up' and v['fails'] >= 2:
                pending.append(u)
    st['lastRun'] = t
    st['slot'] = slot
    write_state(st)
    json.dump({'urls': pending, 'at': t}, open(PENDING, 'w'))
    print('checked', len(res), 'of', len(order), dict(c), 'to verify in a browser:', len(pending), flush=True)

def cmd_finalize(argv):
    st = load(STATE, None)
    links = st['links']
    ver = load(VERIFIED, {}).get('results', {})
    t = load(PENDING, {}).get('at') or now()
    c = Counter()
    for u, r in ver.items():
        v = links.get(u)
        if not v or v['status'] != 'up':
            continue
        if r.get('ok'):
            v['fails'] = 0; v['bot'] = r.get('status') or 'browser-only'; v.pop('why', None); c['browser_ok'] += 1
        else:
            v['status'] = 'down'; v['since'] = t; c['now_down'] += 1
            if r.get('why'):
                v['why'] = v.get('why') or r['why']
    # DNS failures and parked domains need no browser opinion
    for u, v in links.items():
        if v['status'] == 'up' and v.get('fails', 0) >= 2 and v.get('why') in ('dns', 'parked') and u not in ver:
            v['status'] = 'down'; v['since'] = t; c['now_down'] += 1
    write_state(st)
    down = {u: {'since': v['since'], 'why': ('page' if v.get('why') in ('http404', 'http410') else 'site')}
            for u, v in links.items() if v['status'] == 'down'}
    old = load(DOWN, {})
    if old.get('down') != down:
        doc = {'updated': now(), 'tracked': len(links), 'down': dict(sorted(down.items()))}
        with open(DOWN, 'w') as fh:
            json.dump(doc, fh, separators=(',', ':'))
            fh.write('\n')
        c['down_file_changed'] = 1
    print('finalize', dict(c), 'down now:', len(down), 'tracked:', len(links), flush=True)

if __name__ == '__main__':
    a = sys.argv[1:]
    {'check': cmd_check, 'finalize': cmd_finalize}[a[0]](a[1:])
