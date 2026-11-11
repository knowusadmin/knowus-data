#!/usr/bin/env python3
"""Miami-Dade County Elections sample ballots (one official PDF per municipal election, trilingual ES&S layout)
-> the app's ballot format, with the same rules as the county parsers in scripts/ballots/pa:
every "(Vote for" on the PDF is a parsed contest, every numbered line is a candidate or a choice of a parsed contest,
ballot position numbers only go up, the header's date and municipality match the election and the file, and nothing on
the page is left unread. A ballot that fails any check is kept with ok:0 and its reasons (the app labels it and shows the
county's PDF button). Address -> ballot: the municipality polygon from Miami-Dade County's own GIS (Municipalitypoly).

  miamidade_pdf.py --election 2026-11-17 --manifest data/capture/manifests/2026-11-17/FL/<source>.json --assets DIR --out DIR
"""
import argparse, datetime as dt, json, os, re, subprocess, tempfile, zipfile
import requests
GIS = 'https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/Municipalitypoly_gdb/FeatureServer/0'
NUM = re.compile(r'^\s{2,}(\S.*?\S)\s{3,}(\d{1,4})\s*$')
VOTEFOR = re.compile(r'^\(Vote for (\d+|one|two|three)\b', re.I)
WORDS = {'one': 1, 'two': 2, 'three': 3}
def text(pdf_bytes, layout=True):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as t:
        t.write(pdf_bytes); t.flush()
        return subprocess.run(['timeout', '-k', '5', '60', 'pdftotext'] + (['-layout'] if layout else []) + [t.name, '-'],
                              capture_output=True, text=True, timeout=70).stdout
def parse(pdf_bytes, election, muni_from_name):
    lay = text(pdf_bytes); raw = text(pdf_bytes, False)
    lines = lay.replace('\f', '\n').split('\n')
    why = []; contests = []
    d = dt.date.fromisoformat(election).strftime('%B %-d, %Y')
    head = '\n'.join(lines[:12])
    if d not in head: why.append(f'header date is not {d}')
    m = re.search(r'^\s*(.+?), Florida\s{2,}', head, re.M)
    muni = m.group(1).strip() if m else None
    if not muni or (muni_from_name and re.sub(r'[^a-z]', '', muni.lower()) != re.sub(r'[^a-z]', '', muni_from_name.lower())):
        why.append(f'header municipality {muni!r} does not match the file ({muni_from_name})')
    first = next((i for i, l in enumerate(lines) if VOTEFOR.match(l.strip())), None)
    if first is None: return {'muni': muni, 'ok': 0, 'why': ['no "(Vote for" contest found'], 'c': []}
    # contest titles: the 3 non-empty lines above each "(Vote for" (English, Spanish, Haitian Creole); English first
    i = first - 3; unread = []; last_no = 0; cur = None
    while i < len(lines):
        l = lines[i]; s = l.strip()
        if not s: i += 1; continue
        if i + 3 < len(lines) and VOTEFOR.match(lines[i + 3].strip()) and not NUM.match(l):
            vf = lines[i + 3].strip(); n = VOTEFOR.match(vf).group(1).lower()
            cur = {'t': s, 'vf': int(WORDS.get(n, n)), 'c': [], 'n': []}; contests.append(cur); i += 4; continue
        mm = NUM.match(l)
        if mm and cur is not None:
            no = int(mm.group(2))
            if no <= last_no: why.append(f'ballot position {no} after {last_no}')
            last_no = no; cur['c'].append([mm.group(1).strip(), '']); i += 1; continue
        unread.append(s); i += 1
    n_vf = len(re.findall(r'\(Vote for ', raw))
    if n_vf != len(contests): why.append(f'{n_vf} "(Vote for" on the PDF, {len(contests)} contests parsed')
    for c in contests:
        if not c['c']: why.append(f'{c["t"]}: no candidates read')
        elif len(c['c']) < c['vf']: why.append(f'{c["t"]}: fewer candidates than seats')
    if re.search(r'\b(YES|NO)\b\s+\d+\s*$', lay, re.M): why.append('the ballot has a question; questions are not parsed by this reader yet')
    if unread: why.append('unread text on the ballot: ' + ' | '.join(unread[:4]))
    return {'muni': muni, 'ok': 0 if why else 1, 'why': why, 'c': contests}
def polygon(muni):
    q = requests.get(GIS + '/query', params={'where': f"NAME='{muni.upper()}'", 'outFields': 'NAME,MUNICID', 'outSR': 4326,
                                            'geometryPrecision': 5, 'maxAllowableOffset': 0.00005, 'f': 'json'}, timeout=60).json()
    rings = [r for f in q.get('features', []) for r in f['geometry']['rings']]
    return rings
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--election', required=True); ap.add_argument('--manifest', required=True)
    ap.add_argument('--assets', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    man = json.load(open(a.manifest)); os.makedirs(a.out, exist_ok=True)
    zips = {}
    ballots = []; geo = {}
    for url, f in sorted(man['files'].items()):
        if not f['name'].lower().endswith('.pdf'): continue
        z = zips.setdefault(f['asset'], zipfile.ZipFile(os.path.join(a.assets, f['asset'])))
        body = z.read(f['name'])
        mm = re.search(r'\d{4}-\d\d-\d\d-(.+?)-(?:run-off|runoff|general|special|municipal)', url.rsplit('/', 1)[-1])
        name_muni = mm.group(1).replace('-', ' ').title() if mm else None
        b = parse(body, a.election, name_muni)
        b.update({'pdf': url, 'sha256': f['sha256'], 'fetched': f['last']})
        rings = polygon(b['muni'] or name_muni or '') if (b['muni'] or name_muni) else []
        if not rings: b['ok'] = 0; b['why'].append('municipality not found on the county GIS map')
        else: geo[(b['muni'] or name_muni).upper()] = rings
        ballots.append(b)
    out = {'v': 1, 'state': 'FL', 'county': 'Miami-Dade', 'election': a.election, 'read': dt.date.today().isoformat(),
           'source': 'Miami-Dade County Elections Department (official sample ballots)', 'sourceUrl': man.get('page'),
           'lookup': 'https://www.votemiamidade.gov/elections/voters/information.page',
           'geoSource': GIS, 'rule': 'one official sample ballot per municipality: every voter inside the municipality gets this ballot',
           'ballots': ballots}
    json.dump(out, open(os.path.join(a.out, f'fl-miami-dade-{a.election}.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump({'v': 1, 'source': GIS, 'munis': geo}, open(os.path.join(a.out, f'fl-miami-dade-{a.election}-munis.json'), 'w'), separators=(',', ':'))
    for b in ballots: print(b['muni'], 'ok' if b['ok'] else 'LABELLED', len(b['c']), 'contests', '; '.join(b['why']))
if __name__ == '__main__':
    main()
