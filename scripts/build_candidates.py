#!/usr/bin/env python3
"""KnowUS candidate profiles: picks up any NEW candidate in the election results and builds a basic profile.
Free: runs on GitHub-hosted runners; no AI calls.

Reads the same public sources the app's Election tab shows:
  - Wikipedia's 2026 Senate / governor / House results pages (public parse API), and
  - the live app's data/mayors.json and data/statewide.json (city/county and Secretary of State counts).
For every candidate who is not yet in data/candidates/index.json:
  - if they are already an official in the app (data/officials.json: same name + same state + same party, or the
    seat's own incumbent with the same last name, party and a matching first name) the index points at that page;
  - otherwise it writes data/candidates/c/<id>.json with the race, plus (when the results page links a Wikipedia
    article that is verifiably about them) a short Wikipedia intro, a free Wikimedia photo, past offices and the
    website from Wikidata. Any sentence with a loaded label is dropped; a neutral line replaces a dropped first sentence.
  - and adds them to data/candidates/pending-positions.json. Sourced "Key positions" need the AI step, which does not
    run on GitHub (it is filled in by a periodic run outside this repo, then committed here).
Nothing is ever removed, and existing profiles are left as they are. Writes only when something is new."""
import json, os, re, sys, time, hashlib, unicodedata
import requests
from lxml import html as LH
SITE = os.environ.get('KNOWUS_SITE', 'https://knowus.sites.tab.bot/').rstrip('/') + '/'
D = 'data/candidates'
API = 'https://en.wikipedia.org/w/api.php'; WD = 'https://www.wikidata.org/w/api.php'
YEAR = os.environ.get('KNOWUS_ELECTION_YEAR', '2026')
PAGES = {'senate': YEAR + ' United States Senate elections', 'gov': YEAR + ' United States gubernatorial elections', 'house': YEAR + ' United States House of Representatives elections'}
S = requests.Session(); S.headers.update({'User-Agent': 'KnowUS-candidates/1.0 (+https://github.com/knowusadmin/knowus-data)'})
NAMES = {'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','DC':'District of Columbia','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming'}
NB = sorted(NAMES.items(), key=lambda z: -len(z[1]))
BAN = re.compile(r"\b(racis[mt]|extremis[mt]|far[- ]right|far[- ]left|radical|authoritarian|controversial|divisive|conspirac(y|ies)|baseless|debunked|false(ly)? claim(s|ed)?|insurrection|misinformation|disinformation|demagogue|white nationalis[mt]|populis[mt]|socialist|maga|terroris[mt]|bigot|hate group|fringe)\b", re.I)
SUF = {'jr', 'sr', 'ii', 'iii', 'iv'}
NICK = {"jim": ["james"], "bill": ["william"], "bob": ["robert"], "rob": ["robert"], "rick": ["richard", "eric", "frederick"], "mike": ["michael"], "chris": ["christopher"], "ed": ["edward"], "hal": ["harold"], "pat": ["patrick", "patricia"], "greg": ["gregory"], "jeff": ["jefferson", "jeffrey"], "lou": ["luis", "louis"], "gil": ["gilbert"], "eli": ["elijah"], "nick": ["nicholas"], "zach": ["zachary"], "brad": ["bradley"], "rich": ["richard"], "don": ["donald"], "herb": ["herbert"], "tom": ["thomas"], "dan": ["daniel"], "dave": ["david"], "steve": ["stephen", "steven"], "ted": ["edward", "theodore"], "joe": ["joseph"], "tony": ["anthony"], "ben": ["benjamin"], "sam": ["samuel"], "andy": ["andrew"], "matt": ["matthew"], "tim": ["timothy"], "ken": ["kenneth"], "chuck": ["charles"], "charlie": ["charles"], "larry": ["lawrence"], "jerry": ["gerald", "jerome"], "ron": ["ronald"], "dick": ["richard"], "fred": ["frederick"], "al": ["albert", "alan", "alfred"], "alex": ["alexander", "alexandria"], "vince": ["vincent"], "nate": ["nathaniel"], "josh": ["joshua"], "jon": ["jonathan"], "liz": ["elizabeth"], "beth": ["elizabeth"], "kate": ["katherine", "kathryn"], "sue": ["susan"], "cathy": ["catherine"], "debbie": ["deborah"], "abe": ["abraham"], "buddy": [], "drew": ["andrew"], "jake": ["jacob"], "will": ["william"], "gus": ["gustavo", "augustus"], "ro": ["rohit"], "jay": ["james", "john"], "mark": ["marcus"], "max": ["maxwell", "maximilian"], "jared": ["jared"], "deb": ["deborah"], "jen": ["jennifer"], "jenn": ["jennifer"], "jenny": ["jennifer"], "kim": ["kimberly"], "becca": ["rebecca"], "becky": ["rebecca"], "nancy": ["ann"], "marcy": ["marcia"], "val": ["valerie"], "randy": ["randall", "randolph"], "russ": ["russell"], "doug": ["douglas"], "wes": ["wesley"], "frank": ["francis", "franklin"], "tommy": ["thomas"], "bobby": ["robert"], "johnny": ["john"], "jimmy": ["james"], "danny": ["daniel"], "mo": ["morris", "maurice"]}

def call(url, params, post=True):
    for k in range(6):
        try:
            r = S.post(url, data=params, timeout=40) if post else S.get(url, params=params, timeout=40)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(5 * (k + 1))
    return None
def strip(s):
    s = unicodedata.normalize('NFD', str(s or '')); return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
def nkey(n):
    s = strip(n); s = re.sub(r'["“”][^"“”]*["“”]', ' ', s); s = re.sub(r'\([^)]*\)', ' ', s)
    s = re.sub(r"[^a-z\s]", ' ', s.replace("'", '').replace('’', '')); t = [w for w in s.split() if w not in SUF and len(w) > 1]
    return '' if not t else (t[0] + ' ' + t[-1] if len(t) > 1 else t[0])
def toks(n): return [w for w in re.sub(r"[^a-z\s]", ' ', strip(n).replace("'", '')).split() if len(w) > 1]
def firstok(cn, on):
    f = (toks(cn) or [''])[0]; T = toks(on)
    return f in T or any(t.startswith(f) and len(f) >= 3 for t in T) or any(x in T for x in NICK.get(f, [])) or any(f in NICK.get(t, []) for t in T)
def pk(p):
    p = p or ''
    if re.match(r'^(Democratic|DFL|Democrat)', p, re.I): return 'D'
    if re.match(r'^Republican', p, re.I): return 'R'
    return 'X' if p else ''
def stof(t):
    t = t.replace('\xa0', ' ').strip()
    for ab, nm in NB:
        if t.startswith(nm): return ab
    return None
def cands_from_li(li):
    t = re.sub(r'\s+', ' ', li.text_content().replace('\xa0', ' ')).strip()
    t = re.sub(r'^▌\s*', '', t); t = re.sub(r'^Y\s+', '', t); t = re.sub(r'\[\d+\]', '', t)
    t = re.sub(r'\s*[\d.]+\s*%\s*$', '', t)
    m = re.match(r'^(.*?)\s*\(([^()]*)\)?\s*$', t)
    if not m or not m.group(1).strip(): return None
    wt = None
    for a in li.iter('a'):
        h = a.get('href', '')
        if h.startswith('/wiki/') and ':' not in h[6:] and 'redlink' not in (a.get('class') or ''):
            from urllib.parse import unquote
            wt = unquote(h[6:]).replace('_', ' '); break
    return {'n': m.group(1).strip(), 'p': (m.group(2) or '').strip(), 'wt': wt}
def results():
    out = []  # (mode, st, d, city, name, party, wt)
    for mode, title in PAGES.items():
        j = call(API, dict(action='parse', prop='text', formatversion=2, format='json', redirects=1, page=title), post=False)
        if not j or 'parse' not in j: print('no page', title); continue
        doc = LH.fromstring('<div>' + j['parse']['text'] + '</div>')
        h2 = h3 = ''
        for tr in doc.iter('h2', 'h3', 'tr'):
            if tr.tag == 'h2': h2 = tr.text_content().replace('[edit]', '').strip(); h3 = ''; continue
            if tr.tag == 'h3': h3 = tr.text_content().replace('[edit]', '').strip(); continue
            # the same tables the app reads: governor "States" summary; Senate regular + special summaries; House per-state sections
            if mode == 'gov' and h3 != 'States': continue
            if mode == 'senate' and h3 not in ('Special elections during the preceding Congress', 'Elections leading to the next Congress'): continue
            if mode == 'house' and h2 not in NAMES.values(): continue
            cells = [c for c in tr if c.tag in ('td', 'th')]
            if len(cells) < 2: continue
            first = cells[0].text_content().strip(); st = stof(first)
            if not st: continue
            d = ''
            if mode == 'house':
                rest = first[len(NAMES[st]):].strip()
                d = 'AL' if re.search(r'at.?large', rest, re.I) else (re.findall(r'\d+', rest) or [''])[0]
                if not d: continue
            last = None
            for c in reversed(cells):
                if c.tag == 'td' and c.find('.//li') is not None: last = c; break
            if last is None: continue
            if st == 'DC': continue
            for li in last.iter('li'):
                if li.find('.//li') is not None: continue
                c = cands_from_li(li)
                if c and '▌' in c['n']: continue
                if c and nkey(c['n']) and not re.match(r'^write-?in', c['n'], re.I): out.append((mode, st, d, '', c['n'], c['p'], c['wt']))
    for f, mode in (('statewide.json', None),):
        try:
            sw = S.get(SITE + 'data/statewide.json', timeout=30).json()
            for m in ('gov', 'senate'):
                for st, L in (sw.get(m) or {}).items():
                    for o in L:
                        for c in o.get('cands', []): out.append((m, st, '', '', c['n'], c.get('p', ''), None))
        except Exception as e: print('statewide', e)
    try:
        my = S.get(SITE + 'data/mayors.json', timeout=30).json()
        for c in my.get('cities', []):
            for x in c.get('cands', []): out.append(('mayor', c['st'], '', c['id'], x['n'], x.get('p', ''), None))
    except Exception as e: print('mayors', e)
    return out
def rkey(mode, st, d, city):
    if mode == 'mayor': return 'mayor_' + city
    if mode == 'house': return 'house_%s_%s' % (st.lower(), str(d).lower())
    return '%s_%s' % (mode, st.lower())
def find(L, n, p):
    k = nkey(n)
    for e in L:
        if nkey(e['n']) == k or any(nkey(a) == k for a in e.get('a', [])): return e
    l = k.split(' ')[-1]; f = k.split(' ')[0]
    hit = [e for e in L if nkey(e['n']).split(' ')[-1] == l and (not p or not e.get('p') or pk(e['p']) == pk(p)) and (' ' not in k or ' ' not in nkey(e['n']) or nkey(e['n'])[0] == f[0])]
    return hit[0] if len(hit) == 1 else None
def match_official(G, mode, st, d, n, p):
    P = G['people']; S_ = G['states'].get(st, {})
    ids = set(S_.get('sen', []) + S_.get('rep', []) + S_.get('exec', []))
    for ch in (S_.get('leg') or {}).get('chambers', []): ids |= set(ch.get('leaders', []))
    k = nkey(n)
    hit = [i for i in ids if i in P and nkey(P[i]['n']) == k and pk(P[i].get('p')) == pk(p)]
    if len(hit) == 1: return hit[0]
    if hit: return None
    pool = []
    if mode == 'house': pool = [i for i in S_.get('rep', []) if i in P and str(P[i].get('dist') or '') == str(d).lstrip('0') or (d == 'AL' and i in P and 'at-large' in P[i].get('r', ''))]
    elif mode == 'senate': pool = S_.get('sen', [])
    elif mode == 'gov': pool = S_.get('exec', [])[:1]
    hit = [i for i in pool if i in P and nkey(P[i]['n']).split(' ')[-1] == k.split(' ')[-1] and pk(P[i].get('p')) == pk(p) and firstok(n, P[i]['n'])]
    return hit[0] if len(hit) == 1 else None
def office_long(mode, st, d, cityname):
    s = NAMES.get(st, st)
    if mode == 'gov': return 'Governor of ' + s
    if mode == 'senate': return 'U.S. Senate in ' + s
    if mode == 'house': return 'U.S. House in %s (at-large)' % s if d == 'AL' else "U.S. House in %s's district %s" % (s, d)
    return 'Mayor of %s, %s' % (cityname, st)
def basic(c, mode, st, d, city, wt, cityname):
    f = {'id': c['id'], 'n': c['n'], 'p': c['p'], 'race': {'mode': mode, 'st': st, 'd': d or None, 'city': city or None}, 'updated': time.strftime('%Y-%m-%d'), 'auto': True}
    if not wt: return f
    j = call(API, dict(action='query', format='json', formatversion=2, redirects=1, prop='extracts|pageimages|pageprops|description|info', inprop='url', exintro=1, explaintext=1, piprop='thumbnail|name', pithumbsize=320, titles=wt))
    pg = (j or {}).get('query', {}).get('pages', [{}])[0]
    if not pg or pg.get('missing') or (pg.get('pageprops') or {}).get('disambiguation') is not None: return f
    ex = pg.get('extract') or ''; place = cityname if mode == 'mayor' else NAMES.get(st, st)
    if not (nkey(re.sub(r'\(.*?\)', '', pg['title'])) == nkey(c['n']) or nkey(c['n']).split(' ')[-1] in nkey(pg['title'])) or place not in ex + ' ' + (pg.get('description') or ''):
        return f
    url = pg.get('fullurl') or 'https://en.wikipedia.org/wiki/' + pg['title'].replace(' ', '_')
    para = ex.split('\n')[0]; ss = re.split(r'(?<=[a-z0-9\)\]"”])\.\s+(?=[A-Z])', re.sub(r'\s+', ' ', para).strip()); out = []
    for i, s in enumerate(ss[:3]):
        s = s if s.endswith('.') else s + '.'
        if BAN.search(s):
            if i == 0: out = None; break
            continue
        if out and sum(len(x) for x in out) + len(s) > 480: break
        out.append(s)
    bio = ' '.join(out) if out else '%s is a candidate for %s.' % (c['n'], office_long(mode, st, d, cityname))
    f.update({'bio': bio, 'bioSrc': url, 'wiki': url})
    if pg.get('thumbnail'): f['img'] = pg['thumbnail']['source']; f['imgSrc'] = 'https://en.wikipedia.org/wiki/File:' + (pg.get('pageimage') or '').replace(' ', '_')
    q = (pg.get('pageprops') or {}).get('wikibase_item')
    if q:
        f['qid'] = q
        e = ((call(WD, dict(action='wbgetentities', format='json', ids=q, props='claims')) or {}).get('entities') or {}).get(q) or {}
        cl = e.get('claims') or {}
        site = [x['mainsnak'].get('datavalue', {}).get('value') for x in cl.get('P856', []) if x['mainsnak'].get('datavalue')]
        if site and not re.search(r'(senate|house)\.gov', site[0]): f['site'] = site[0]; f['siteKind'] = 'official'
        pos = []
        for x in cl.get('P39', []):
            v = x['mainsnak'].get('datavalue', {}).get('value', {}).get('id')
            if not v: continue
            def yr(p):
                try: return x['qualifiers'][p][0]['datavalue']['value']['time'][1:5]
                except Exception: return None
            pos.append((v, yr('P580'), yr('P582')))
        if pos:
            labs = (call(WD, dict(action='wbgetentities', format='json', ids='|'.join(sorted(set(p[0] for p in pos)))[:2000], props='labels', languages='en')) or {}).get('entities') or {}
            offs = []
            for v, s0, e0 in pos:
                l = ((labs.get(v) or {}).get('labels') or {}).get('en', {}).get('value')
                if l and re.search(r'senat|represent|governor|mayor|attorney|secretary|legislat|assembly|house|council|commission|judge|justice|treasurer|auditor|comptroller|lieutenant|member|sheriff|delegate|speaker|leader', l, re.I):
                    t = l[0].upper() + l[1:] + (' (%s–%s)' % (s0, e0 or 'present') if s0 else '')
                    if t not in offs: offs.append(t)
            if offs: f['offices'] = offs[:6]
    return f
def main():
    os.makedirs(D + '/c', exist_ok=True)
    idx = json.load(open(D + '/index.json'))
    G = json.load(open('data/officials.json'))
    try: pend = json.load(open(D + '/pending-positions.json'))
    except Exception: pend = {'note': 'Candidates whose sourced Key positions have not been generated yet (the AI step runs outside GitHub).', 'items': []}
    try: cityname = {c['id']: c['city'] for c in S.get(SITE + 'data/mayors.json', timeout=30).json().get('cities', [])}
    except Exception: cityname = {}
    new = 0; seen = set()
    for mode, st, d, city, n, p, wt in results():
        rk = rkey(mode, st, d, city)
        L = idx['races'].setdefault(rk, [])
        if find(L, n, p) or (rk, nkey(n)) in seen: continue
        seen.add((rk, nkey(n)))
        cid = rk + '_' + nkey(n).replace(' ', '-'); k = 2
        while any(e['id'] == cid for e in L): cid = rk + '_' + nkey(n).replace(' ', '-') + str(k); k += 1
        e = {'id': cid, 'n': n, 'p': p, 'new': time.strftime('%Y-%m-%d')}
        m = match_official(G, mode, st, d, n, p) if mode != 'mayor' else None
        if m: e['m'] = m
        else:
            f = basic(e, mode, st, d, city, wt, cityname.get(city, ''))
            s = json.dumps(f, ensure_ascii=False, separators=(',', ':'))
            open(D + '/c/' + cid + '.json', 'w').write(s); e['f'] = 1; e['u'] = hashlib.md5(s.encode()).hexdigest()[:8]
            if pk(p) in ('D', 'R') or mode == 'mayor':
                pend['items'].append({'id': cid, 'n': n, 'p': p, 'race': rk, 'wt': wt, 'added': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
        L.append(e); new += 1
        print('new candidate:', rk, n, p, '->', e.get('m') or 'profile')
        time.sleep(0.3)
    if not new:
        print('no new candidates'); return
    idx['updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    open(D + '/index.json', 'w').write(json.dumps(idx, ensure_ascii=False, separators=(',', ':')))
    open(D + '/pending-positions.json', 'w').write(json.dumps(pend, ensure_ascii=False, indent=1))
    print('added', new)
if __name__ == '__main__':
    main()
