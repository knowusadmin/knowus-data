#!/usr/bin/env python3
"""KnowUS link targets: every official / city / county / legislator website and every
positions-page source link the live app shows. Rebuilt from the live site's own data files,
so a republished app is picked up automatically. Output: data/links/targets.json
  {"built": iso, "site": url, "n": N, "urls": {url: kind}}
kind: city | county | local (local official pages) | leg (state legislators) | official | campaign (candidate pages) | source
Wikipedia / Wikidata / Internet Archive links are not tracked (never "down" in a useful sense)."""
import json, re, sys, os, time, concurrent.futures as cf
import requests
SITE = os.environ.get('KNOWUS_SITE', 'https://knowus.sites.tab.bot/').rstrip('/') + '/'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'data/links/targets.json'
STATES = 'AK AL AR AZ CA CO CT DC DE FL GA HI IA ID IL IN KS KY LA MA MD ME MI MN MO MS MT NC ND NE NH NJ NM NV NY OH OK OR PA RI SC SD TN TX UT VA VT WA WI WV WY'.split()
SKIP_HOST = re.compile(r'(^|\.)(wikipedia\.org|wikidata\.org|wikimedia\.org|archive\.org|archive\.ph|archive\.today|tab\.bot)$', re.I)
IMG = re.compile(r'\.(png|jpe?g|gif|webp|svg|ico)(\?|$)', re.I)
URL = re.compile(r'^https?://[^\s/$.?#][^\s]*$', re.I)
H = {'User-Agent': 'KnowUS-link-targets/1.0 (+https://github.com/knowusadmin/knowus-data)'}

def get(path, tries=3):
    for i in range(tries):
        try:
            r = requests.get(SITE + path, headers=H, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
        except Exception:
            pass
        time.sleep(2 * (i + 1))
    raise RuntimeError('could not fetch ' + path)

def host(u):
    return re.sub(r'^https?://', '', u).split('/')[0].split('@')[-1].split(':')[0].lower()

def keep(u):
    return isinstance(u, str) and URL.match(u) and not SKIP_HOST.search(host(u)) and not IMG.search(u)

def walk(x, path, out):
    if isinstance(x, dict):
        for k, v in x.items():
            walk(v, path + (k,), out)
    elif isinstance(x, list):
        for v in x:
            walk(v, path, out)
    elif keep(x):
        out.append((path, x.strip()))

urls = {}
def add(u, kind):
    # a city/county site outranks a source link when one URL is both
    rank = {'city': 0, 'county': 1, 'local': 2, 'leg': 3, 'official': 4, 'campaign': 4, 'source': 5}
    if u not in urls or rank[kind] < rank[urls[u]]:
        urls[u] = kind

def local(st):
    d = get('data/local/%s.json' % st)
    if not d:
        return
    out = []
    walk(d, (), out)
    for p, u in out:
        if p and p[0] == 'places' and p[-1] == 'w':
            add(u, 'city')
        elif p and p[0] == 'counties' and p[-1] == 'w':
            add(u, 'county')
        elif p and p[0] == 'leg':
            add(u, 'leg')
        elif p and p[-1] in ('u', 'url', 'site', 'w'):
            add(u, 'local')

def main():
    os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
    with cf.ThreadPoolExecutor(12) as ex:
        list(ex.map(local, STATES))
    for f in ('statewide.json', 'mayors.json', 'state-roles.json', 'local-roles.json', 'profiles.json'):
        d = get('data/' + f)
        out = []
        walk(d, (), out)
        for p, u in out:
            add(u, 'official' if f != 'profiles.json' else 'source')
    idx = get('data/profiles-full/index.json') or {}
    ids = list((idx.get('people') or {}).keys())
    def prof(i):
        d = get('data/profiles-full/%s.json' % i)
        out = []
        walk(d, (), out)
        return out
    with cf.ThreadPoolExecutor(16) as ex:
        for out in ex.map(prof, ids):
            for p, u in out:
                add(u, 'source')
    # 2026 candidate pages (#/candidate/<id>): campaign / official websites and position sources.
    # Read from this repo's own copy (the app reads the same files from here), falling back to the live app.
    try:
        cidx = json.load(open('data/candidates/index.json'))
        local_c = True
    except Exception:
        cidx = get('data/candidates/index.json') or {}
        local_c = False
    cids = [e['id'] for L in (cidx.get('races') or {}).values() for e in L if e.get('f')]
    def cand(i):
        try:
            d = json.load(open('data/candidates/c/%s.json' % i)) if local_c else get('data/candidates/c/%s.json' % i)
        except Exception:
            d = None
        out = []
        walk(d or {}, (), out)
        return out
    with cf.ThreadPoolExecutor(16) as ex:
        for out in ex.map(cand, cids):
            for p, u in out:
                if p and p[-1] == 'site':
                    add(u, 'campaign')
                elif p and p[-1] in ('src', 'via'):
                    add(u, 'source')
    if len(urls) < 5000:
        raise SystemExit('only %d targets found; refusing to overwrite (site layout changed?)' % len(urls))
    doc = {'built': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'site': SITE, 'n': len(urls),
           'urls': dict(sorted(urls.items()))}
    old = None
    try:
        old = json.load(open(OUT))
    except Exception:
        pass
    if old and old.get('urls') == doc['urls']:
        print('targets unchanged:', len(urls))
        return
    with open(OUT, 'w') as fh:
        fh.write('{"built":%s,"site":%s,"n":%d,"urls":{\n' % (json.dumps(doc['built']), json.dumps(SITE), len(urls)))
        fh.write(',\n'.join('%s:%s' % (json.dumps(u), json.dumps(k)) for u, k in doc['urls'].items()))
        fh.write('\n}}\n')
    from collections import Counter
    print('targets written:', len(urls), dict(Counter(urls.values())))

if __name__ == '__main__':
    main()
