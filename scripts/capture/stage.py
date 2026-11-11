#!/usr/bin/env python3
"""After a capture run: every captured source whose registry entry names a parser is converted into the app's ballot
format under data/capture/staged/<election>/<state>/ (never into data/ballots: a person reviews and publishes).
Parsers: vip5 (scripts/capture/parsers/vip5: a VIP 5 CSV feed, checked against the printed sample ballots captured
for the same state and election); miamidade-pdf (Miami-Dade County's one-PDF-per-municipality sample ballots). Sources without a parser stay raw until one is written (see data/capture/README.md)."""
import glob, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAP = os.environ.get('CAPTURE_DIR') or os.path.join(ROOT, 'data', 'capture')
M = os.path.join(CAP, 'manifests')
done = []
for p in sorted(glob.glob(os.path.join(M, '*', '*', '*.json'))):
    man = json.load(open(p)); el, st, sid = p.split(os.sep)[-3], p.split(os.sep)[-2], os.path.basename(p)[:-5]
    if man.get('parser') not in ('vip5', 'miamidade-pdf') or not man.get('runs'): continue
    last = man['runs'][-1]
    out = os.path.join(CAP, 'staged', el, st)
    stamp = os.path.join(out, 'staged-from.json')
    if os.path.exists(stamp) and json.load(open(stamp)).get('at', '') >= last['at']: continue
    if man['parser'] == 'miamidade-pdf':
        adir = os.path.join(os.environ.get('RUNNER_TEMP', '/tmp'), 'assets-' + el + '-' + st); os.makedirs(adir, exist_ok=True)
        for asset in sorted({f['asset'] for f in man['files'].values()}):
            if not os.path.exists(os.path.join(adir, asset)):
                subprocess.run(['timeout', '-k', '5', '900', 'gh', 'release', 'download', f'capture-{el}-{st}', '-p', asset, '-D', adir])
        r = subprocess.run(['timeout', '-k', '5', '1800', sys.executable, os.path.join(ROOT, 'scripts', 'capture', 'parsers', 'miamidade_pdf.py'),
                            '--election', el, '--manifest', p, '--assets', adir, '--out', out])
        if r.returncode == 0: os.makedirs(out, exist_ok=True); json.dump({'at': last['at'], 'source': sid}, open(stamp, 'w'))
        done.append((el, st, sid, r.returncode)); continue
    pdf = [os.path.basename(q)[:-5] for q in glob.glob(os.path.join(M, el, st, '*.json'))
           if json.load(open(q)).get('format') in ('pdf-per-style', 'pdf-per-precinct')]
    cmd = [sys.executable, os.path.join(ROOT, 'scripts', 'capture', 'parsers', 'vip5', 'run.py'), '--state', st, '--election', el,
           '--feed-source', sid] + (['--pdf-source', pdf[0]] if pdf else [])
    r = subprocess.run(['timeout', '-k', '5', '7000'] + cmd)
    if r.returncode == 0:
        json.dump({'at': last['at'], 'feed': sid, 'pdfs': pdf[:1]}, open(stamp, 'w'))
    done.append((el, st, sid, r.returncode))
print('staged:', done or 'nothing new')
