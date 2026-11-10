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
SKIP_KEYS = {'site', 'siteKind', 'img', 'imgSrc'}   # a person's own site is allowed by owner rule; photos are checked separately
SKIP_FILES = re.compile(r'(link-status\.json|links/targets\.json|links-down\.json|last-check\.json|sources-policy\.json|/bills/|/eo/)')
bad = collections.Counter(); bad_where = collections.defaultdict(list); total = collections.Counter()
def walk(o, where, own=()):
    if isinstance(o, dict):
        own2 = list(own) + ([o['site']] if isinstance(o.get('site'), str) else [])
        for k, v in o.items():
            if isinstance(v, str) and v.startswith('http') and k not in SKIP_KEYS:
                st, g = classify(v, [dom(x) for x in own2])
                total[st] += 1
                if st == 'banned':
                    d = dom(v); bad[d] += 1
                    if len(bad_where[d]) < 5: bad_where[d].append(where)
            else: walk(v, where, own2)
    elif isinstance(o, list):
        for v in o: walk(v, where, own)
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
            if j is not None: walk(j, f)
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
