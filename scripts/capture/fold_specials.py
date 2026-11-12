#!/usr/bin/env python3
"""Fold staged Miami-Dade municipal run-off / special ballots (capture system, data/capture/staged/<date>/FL/)
into site files data/ballots/sp-fl-miami-dade-<date>.json (KUS-SPECIALS, v88).
Rules (Shmuel): a run-off ballot applies only inside the official municipal boundary (Miami-Dade County GIS
'Municipal Boundary' layer, fetched at full resolution here, not the staged simplified rings); each is its own
ballot with its own date, never mixed into the Nov 3 ballot; contests exactly as parsed from the official PDF
(re-checked here against the PDF's text and sha256); a ballot not verified complete is shipped labelled (ok 0).
usage: fold_specials.py REPO OUTDIR [date ...]"""
import json, sys, os, hashlib, subprocess, urllib.request, urllib.parse, datetime
REPO, OUT = sys.argv[1], sys.argv[2]
DATES = sys.argv[3:] or ['2026-11-17', '2026-11-24', '2026-12-01', '2026-12-08']
GS = 'https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/Municipalitypoly_gdb/FeatureServer/0'
SC = 1e6
def get(u, t=60):
    req = urllib.request.Request(u, headers={'User-Agent': 'KnowUS civic app (knowus.sites.tab.bot)'})
    with urllib.request.urlopen(req, timeout=t) as r: return r.read()
def rings_for(name):
    q = urllib.parse.urlencode(dict(where="NAME='%s'" % name.upper().replace("'", "''"), outFields='NAME,MUNICID', returnGeometry='true', outSR=4326, f='json', geometryPrecision=7))
    j = json.loads(get(GS + '/query?' + q))
    rs = [r for f in j.get('features', []) for r in f['geometry']['rings']]
    if not rs: raise SystemExit('no official boundary for ' + name)
    return rs
def enc(rings):
    out = []; xs = []; ys = []
    for r in rings:
        pts = [(round(x * SC), round(y * SC)) for x, y in r]; px = py = 0; f = []
        for X, Y in pts: f += [X - px, Y - py]; px, py = X, Y; xs.append(X); ys.append(Y)
        out.append(f)
    return [min(xs), min(ys), max(xs), max(ys)], out
def norm(s): return ' '.join(s.replace('\u2019', "'").split())
def pdf_check(b, tmp):
    raw = get(b['pdf'], 90); h = hashlib.sha256(raw).hexdigest()
    p = os.path.join(tmp, 'b.pdf'); open(p, 'wb').write(raw)
    txt = subprocess.run(['timeout', '-k', '5', '60', 'pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout
    lines = [norm(l) for l in txt.splitlines() if l.strip()]
    errs = []
    if h != b['sha256']: errs.append('pdf changed since capture (sha256 %s)' % h[:12])
    for c in b['c']:
        if not any(l == norm(c['t']) for l in lines): errs.append('contest title not on pdf: ' + c['t'])
        n_ovals = 0
        for nm, _ in c['c']:
            if not any(l.startswith(norm(nm) + ' ') or l == norm(nm) for l in lines): errs.append('candidate not on pdf: ' + nm)
    # every "(Vote for N ..." block on the pdf must be a parsed contest
    if sum(1 for l in lines if l.startswith('(Vote for')) != len(b['c']): errs.append('contest count differs from the pdf')
    return errs, h, txt
os.makedirs(OUT, exist_ok=True); tmp = os.path.join(OUT, '.tmp'); os.makedirs(tmp, exist_ok=True); rep = {}
for d in DATES:
    sp = os.path.join(REPO, 'data/capture/staged', d, 'FL', 'fl-miami-dade-%s.json' % d)
    if not os.path.exists(sp): continue
    S = json.load(open(sp))
    if not S.get('ballots'): rep[d] = 'no ballots staged (county has not posted them)'; continue
    o = {'v': 1, 'st': 'FL', 'county': 'Miami-Dade County, Florida', 'day': d, 'read': S['read'], 'built': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
         'office': 'Miami-Dade County Elections Department', 'source': S['source'], 'sourceUrl': S['sourceUrl'], 'lookup': S['lookup'],
         'geoSource': 'Miami-Dade County GIS \u2014 Municipal Boundary (' + GS + ')', 'rule': 'one official sample ballot per municipality; only addresses inside the official municipal boundary get it',
         'geo': {'scale': SC, 'p': []}, 'b': {}}
    for b in S['ballots']:
        key = b['muni'].upper(); errs, h, txt = pdf_check(b, tmp)
        kind = (b.get('kind') or 'Run-Off Election') if 'Run-Off Election' in txt else None
        if not kind: errs.append('pdf does not say Run-Off Election')
        ok = 1 if (b.get('ok') and not errs) else 0
        bbox, rr = enc(rings_for(b['muni'])); o['geo']['p'].append([key, bbox, rr])
        o['b'][key] = {'muni': b['muni'], 'name': b['muni'] + ' run-off election', 'ok': ok, 'why': (b.get('why') or []) + errs,
                       'c': [{'t': c['t'], 'vf': str(c.get('vf') or 1), 'c': [[x[0], x[1] or ''] for x in c['c']], 'n': c.get('n') or []} for c in b['c']],
                       'pdf': b['pdf'], 'sha256': h, 'fetched': b.get('fetched')}
        rep[d + ' ' + b['muni']] = ('ok' if ok else 'LABELLED: ' + '; '.join(o['b'][key]['why'])) + ' · %d contests · boundary %d rings/%d pts' % (len(b['c']), len(rr), sum(len(x) // 2 for x in rr))
    json.dump(o, open(os.path.join(OUT, 'sp-fl-miami-dade-%s.json' % d), 'w'), separators=(',', ':'), ensure_ascii=False)
for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
os.rmdir(tmp)
print(json.dumps(rep, indent=1))
