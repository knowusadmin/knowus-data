#!/usr/bin/env python3
"""KnowUS source-policy check: every source the app cites must be allowed by data/sources-policy.json.
  python3 scripts/sources_check.py [--site https://knowus.sites.tab.bot/] [--local SITE_DIR] [--report-only] [--out FILE]
Scans this repo's data (candidates, officials, mayors) and the live app's data files (Positions pages,
local officials' positions, election data). Any banned or unlisted source = exit 1 (the audit fails)."""
import json, os, re, sys, glob, collections, argparse, urllib.request, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sources_policy import classify, dom
ap = argparse.ArgumentParser(); ap.add_argument('--site', default=os.environ.get('KNOWUS_SITE', 'https://knowus.sites.tab.bot/'))
ap.add_argument('--local', default=''); ap.add_argument('--report-only', action='store_true'); ap.add_argument('--out', default='')
ap.add_argument('--repo-only', action='store_true'); ap.add_argument('--result', default='')
a = ap.parse_args(); SITE = a.site.rstrip('/') + '/'
SKIP_KEYS = {'site', 'siteAlt', 'siteKind', 'img', 'imgSrc'}   # a person's own site is allowed by owner rule; photos are checked separately
SKIP_FILES = re.compile(r'(link-status\.json|links/targets\.json|links-down\.json|last-check\.json|sources-policy\.json|/bills/|/eo/)')
bad = collections.Counter(); bad_where = collections.defaultdict(list); total = collections.Counter()
def _host(x):
    """a URL or a bare domain (profiles' ownSites) -> its host"""
    if not isinstance(x, str) or not x: return ''
    if '://' in x: return dom(x)
    h = x.strip().lower().split('/')[0]
    return h[4:] if h.startswith('www.') else h
# each person's own sites by id (candidates' site/siteAlt, profiles' ownSites): a photo or a citation found ON the
# person's own campaign site is allowed (campaign sites are allowed sources), whatever CDN the image itself sits on
OWN = collections.defaultdict(set)
for f in glob.glob('data/candidates/c/*.json'):
    try:
        j = json.load(open(f)); i = j.get('id') or os.path.basename(f)[:-5]
        for x in [j.get('site')] + list(j.get('siteAlt') or []): (_host(x) and OWN[i].add(_host(x)))
    except Exception: pass
import unicodedata
def _norm(x): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', x or '').encode('ascii', 'ignore').decode().lower())
SUFX = {'jr', 'sr', 'ii', 'iii', 'iv'}
CAMPAIGN_MARK = re.compile(r'(for|4|vote|elect|congress|senate|house|mayor|governor|gov|20\d\d)')
def named_site(url, name):
    """True when url's domain is named after the person: it carries their last name (russo2026.com for Frank Russo,
    presidentdaughtry.com for Mattie Daughtry), or their first name next to a campaign word (tessaforca.com,
    angelica4congress.com). A site named after the person is that person's own site (campaign sites are allowed).
    Banned and news hosts are refused before this is consulted."""
    parts = [p for p in re.sub(r'["\u201c\u201d][^"\u201c\u201d]*["\u201c\u201d]', ' ', name or '').replace(',', ' ').split() if _norm(p) not in SUFX]
    parts = [_norm(p) for p in parts if _norm(p)]
    if not parts: return False
    host = dom(url); label = _norm(host.rsplit('.', 1)[0])
    if len(parts[-1]) >= 3 and parts[-1] in label: return True
    if len(parts) > 1 and any(len(p) >= 4 and p in label for p in parts[1:-1]): return True
    first = parts[0]
    return len(first) >= 3 and first in label and bool(CAMPAIGN_MARK.search(host.rsplit('.', 1)[0].replace(first, ' ', 1)))
PHOTO_FILE_KEYS = {'file', 'fileUrl', 'imgUrl'}   # the image's own URL; the photo is judged by the page it came from ('src')
def walk(o, where, own=(), who=(), path=(), name=None):
    if isinstance(o, dict):
        own2 = list(own) + ([o['site']] if isinstance(o.get('site'), str) else []) + [x for x in (o.get('siteAlt') or []) if isinstance(x, str)]
        own2 += ['http://' + _host(x) for x in (o.get('ownSites') or []) if _host(x)]
        if isinstance(o.get('id'), str) and o['id'] in OWN: own2 += ['http://' + h for h in OWN[o['id']]]
        who2 = list(who) + [x for x in (o.get('id') if isinstance(o.get('id'), str) else None, o.get('m') if isinstance(o.get('m'), str) else None) if x] + (['cand:' + o['id']] if isinstance(o.get('id'), str) and isinstance(o.get('race'), dict) else []) + ([o['bg']] if isinstance(o.get('bg'), str) else [])
        photo = isinstance(o.get('src'), str) and isinstance(o.get('img'), str)
        nm = o.get('n') if isinstance(o.get('n'), str) and (o.get('id') or photo or o.get('office') or o.get('race')) else name
        for k, v in o.items():
            if isinstance(v, str) and v.startswith('http') and k not in SKIP_KEYS:
                if photo and k in PHOTO_FILE_KEYS: continue
                # owner's narrow exception (sources-policy.json narrow_exceptions): AP only as the source of a
                # US House race call on the Elections tab (house.states.*.districts[].callSrc)
                ctx = 'house_call' if k == 'url' and path[-1:] == ('callSrc',) and 'house' in path else None
                oh = [dom(x) for x in own2]
                if nm and named_site(v, nm): oh.append(dom(v))
                st, g = classify(v, oh, who2, ctx)
                total[st] += 1
                if st == 'banned':
                    d = dom(v); bad[d] += 1
                    if len(bad_where[d]) < 5: bad_where[d].append(where)
            else:
                kid_own = own2 + (['http://' + h for h in OWN[k]] if isinstance(o, dict) and k in OWN else [])
                walk(v, where, kid_own, who2 + ([k] if k in OWN else []), path + (k,), nm)
    elif isinstance(o, list):
        for v in o: walk(v, where, own, who, path, name)
def get(u):
    if a.local:
        p = os.path.join(a.local, u)
        return json.load(open(p)) if os.path.exists(p) else None
    try:
        with urllib.request.urlopen(urllib.request.Request(SITE + u + '?x=srccheck', headers={'User-Agent': 'KnowUS-sources-check'}), timeout=40) as r: return json.load(r)
    except Exception: return None
# 1) this repo's data
for f in glob.glob('data/**/*.json', recursive=True):
    if SKIP_FILES.search(f): continue
    try: walk(json.load(open(f)), f)
    except Exception: pass
# 2) the app's data files
if not a.repo_only:
    idx = get('data/profiles-full/index.json') or {}
    ids = list((idx.get('people') or {}).keys())
    files = ['data/profiles-full/%s.json' % i for i in ids] + ['data/local-ai/%s.json' % s for s in 'AK AR AZ CA CO DC FL GA IL IN KS KY LA MA MD MI MN MO MT NC NE NJ NV NY OH OK OR PA TN TX VA WA WI'.split()]
    files += ['data/profiles.json', 'data/statewide.json', 'data/mayors.json', 'data/elections.json']
    files += ['data/districts/%s.json' % s for s in 'AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()]
    files += ['data/local/%s.json' % s for s in 'AL AK AZ AR CA CO CT DC DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()]
    with cf.ThreadPoolExecutor(12) as ex:
        for f, j in zip(files, ex.map(get, files)):
            if j is None: continue
            if '/local-ai/' in f and isinstance(j.get('people'), dict):
                for k, pp in j['people'].items(): walk(pp, f, (), ['local:' + k])
            else: walk(j, f, (), [os.path.basename(f)[:-5]] if '/profiles-full/' in f else ())
rep = {'checked': dict(total), 'banned_total': sum(bad.values()), 'banned_by_domain': dict(bad.most_common()), 'examples': {d: bad_where[d] for d, _ in bad.most_common(30)}}
print(json.dumps({k: rep[k] for k in ('checked', 'banned_total')}), '\ntop banned:', bad.most_common(15))
if a.out:
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True); json.dump(rep, open(a.out, 'w'), indent=1)
if a.result:   # shard file for audit/report.mjs: one high-severity issue per banned domain
    os.makedirs(a.result, exist_ok=True)
    iss = [{'severity': 'high', 'type': 'Banned source cited', 'route': ', '.join(bad_where[d][:2]), 'viewport': None, 'element': d, 'error': '%d citation(s) of %s, which data/sources-policy.json does not allow' % (n, d), 'screenshot': None, 'shard': 'sources'} for d, n in bad.most_common(60)]
    json.dump({'shard': 'sources', 'issues': iss, 'coverage': {'cited sources checked': sum(total.values()), 'banned citations': rep['banned_total']}, 'pages': 0, 'seconds': 0}, open(os.path.join(a.result, 'result.json'), 'w'))
if rep['banned_total'] and not a.report_only:
    print('::error::%d cited sources are not allowed by data/sources-policy.json' % rep['banned_total']); sys.exit(1)
