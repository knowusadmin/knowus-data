#!/usr/bin/env python3
"""Captured VIP 5 feed (+ captured printed sample ballots) -> the app's ballot files, with the v49 verification rules.

  run.py --state NC --election 2026-11-03 --feed-source statewide-vip-5-feed --pdf-source statewide-sample-ballot-pdfs
         [--results canvass.zip] [--assets DIR] [--out DIR]

Reads data/capture/manifests/<election>/<state>/<source>.json, fetches the release assets it names (gh release download)
unless --assets holds them, then: pdftext -> build1 -> match2 -> build3 -> coverage. A ballot style is "ok" (complete) only
when it matches exactly one printed official sample ballot; everything else is written with ok:0 and its reason, so the
app shows it labelled "may not be complete" with the official button. Nothing is invented: contests come from the feed.
"""
import argparse, json, os, subprocess, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
def sh(cmd, env, t):
    print('+', ' '.join(cmd[-2:]), flush=True)
    r = subprocess.run(['timeout', '-k', '5', str(t)] + cmd, env=env, text=True, capture_output=True)
    sys.stdout.write(r.stdout[-4000:]); sys.stderr.write(r.stderr[-4000:])
    if r.returncode: raise SystemExit(f'{cmd[-1]} failed ({r.returncode})')
def assets_for(man, adir, tag):
    need = sorted({f['asset'] for f in man['files'].values()})
    for a in need:
        if not os.path.exists(os.path.join(adir, a)):
            subprocess.run(['timeout', '-k', '5', '900', 'gh', 'release', 'download', tag, '-p', a, '-D', adir], check=True)
    return [os.path.join(adir, a) for a in need]
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', required=True); ap.add_argument('--election', required=True)
    ap.add_argument('--feed-source', required=True); ap.add_argument('--pdf-source')
    ap.add_argument('--results'); ap.add_argument('--refs', default='')
    ap.add_argument('--assets'); ap.add_argument('--work'); ap.add_argument('--out')
    ap.add_argument('--source-name', default=''); ap.add_argument('--source-url', default=''); ap.add_argument('--lookup', default='')
    a = ap.parse_args()
    st, el = a.state.upper(), a.election
    capdir = os.environ.get('CAPTURE_DIR') or os.path.join(ROOT, 'data', 'capture')
    mdir = os.path.join(capdir, 'manifests', el, st); tag = f'capture-{el}-{st}'
    work = a.work or os.path.join(os.environ.get('RUNNER_TEMP', '/tmp'), f'vip5-{st}-{el}'); os.makedirs(work, exist_ok=True)
    adir = a.assets or os.path.join(work, 'assets'); os.makedirs(adir, exist_ok=True)
    out = a.out or os.path.join(capdir, 'staged', el, st)
    fman = json.load(open(os.path.join(mdir, a.feed_source + '.json')))
    feeds = [(u, f) for u, f in fman['files'].items() if f['name'].lower().endswith('.zip')]
    if not feeds: raise SystemExit('no feed zip in the manifest')
    u, f = sorted(feeds, key=lambda x: x[1]['last'])[-1]
    import zipfile
    z = zipfile.ZipFile(assets_for({'files': {u: f}}, adir, tag)[0]); feed = os.path.join(work, 'feed.zip')
    open(feed, 'wb').write(z.read(f['name']))
    pdfurls = {}
    if a.pdf_source:
        pman = json.load(open(os.path.join(mdir, a.pdf_source + '.json')))
        zs = assets_for(pman, adir, tag)
        import re
        for uu, ff in pman['files'].items(): pdfurls[re.sub(r'^\d{5}-', '', ff['name'])] = uu
        json.dump(pdfurls, open(os.path.join(work, 'pdfurls.json'), 'w'))
        sh([sys.executable, os.path.join(HERE, 'pdftext.py'), work] + zs, os.environ.copy(), 3600)
    else:
        os.makedirs(os.path.join(work, 'sbtxt'), exist_ok=True)
    env = dict(os.environ, VIP_WORK=work, VIP_FEED=feed, VIP_OUT=out, VIP_STATE=st, VIP_ELECTION=el, VIP_REFS=a.refs,
               VIP_SOURCE=a.source_name or fman.get('source', ''), VIP_SOURCE_URL=a.source_url or fman.get('page', ''),
               VIP_LOOKUP=a.lookup)
    if pdfurls: env['VIP_PDF_URLS'] = os.path.join(work, 'pdfurls.json')
    if a.results: env['VIP_RESULTS'] = a.results
    os.makedirs(out, exist_ok=True)
    for step in ['build1.py', 'match2.py', 'build3.py', 'coverage.py']:
        sh([sys.executable, os.path.join(HERE, step)], env, 3600)
    print('staged ->', out, flush=True)
if __name__ == '__main__':
    main()
