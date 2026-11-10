#!/usr/bin/env python3
"""KnowUS candidate profiles from OFFICIAL sources only (owner's source policy, Nov 9 2026: no Wikipedia, Wikidata,
Wikimedia, AP or Reuters; news only from the allowlist in sources-policy.json).

Who is a candidate: the names in the app's own official results data, which the elections builder copies from each
state's election office (Secretary of State / state board of elections) and each city's/county's election office:
  data/statewide.json (Senate, Governor; "namesOnly" = an official candidate list where no counts are posted yet),
  data/districts/<ST>.json (U.S. House: "off" official counts, "cl" official candidate lists), data/mayors.json.
Federal candidates are matched to the FEC's candidate master file (fec.gov bulk data, cnYY.zip) to record their FEC id.
With FEC_API_KEY set (a free api.data.gov key; repo secret), the principal campaign committee's website from its FEC
Form 1 is recorded as the candidate's campaign site.
Profile text: a short "About" is copied word for word from the candidate's own campaign/official site (only sentences
that name the candidate and state a plain fact: office held, career, education, service, home), with the page as its
source. No photo is stored unless it comes from an official government page (none are fetched here: initials show).
Clean mode (--clean, run once for the policy change): every existing profile loses encyclopedia fields (bio/bioSrc from
Wikipedia, wiki, qid, Wikimedia img/imgSrc, Wikidata offices); a site found through Wikidata is kept only if the site
itself names the candidate; index entries for names that are not in the official data are removed (listed in the report).
Free: no AI calls. Writes only when something changed.
Usage: python3 scripts/build_candidates.py [--clean] [--site-dir DIR | KNOWUS_SITE=https://knowus.sites.tab.bot/]"""
import json, os, re, sys, time, hashlib, unicodedata, io, zipfile, concurrent.futures as cf
from urllib.parse import urljoin, urlparse
import requests
from lxml import html as LH
ARGS = sys.argv[1:]
CLEAN = '--clean' in ARGS
SITE_DIR = ARGS[ARGS.index('--site-dir') + 1] if '--site-dir' in ARGS else os.environ.get('KNOWUS_SITE_DIR')
SITE = os.environ.get('KNOWUS_SITE', 'https://knowus.sites.tab.bot/').rstrip('/') + '/'
D = os.environ.get('KNOWUS_CAND_DIR', 'data/candidates')
YEAR = os.environ.get('KNOWUS_ELECTION_YEAR', '2026')
FEC_KEY = os.environ.get('FEC_API_KEY', '')
S = requests.Session(); S.headers.update({'User-Agent': 'KnowUS-candidates/2.0 (+https://github.com/knowusadmin/knowus-data)'})
NAMES = {'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','DC':'District of Columbia','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming'}
BAN = re.compile(r"\b(racis[mt]|extremis[mt]|far[- ]right|far[- ]left|radical|authoritarian|controversial|divisive|conspirac(y|ies)|baseless|debunked|false(ly)? claim(s|ed)?|insurrection|misinformation|disinformation|demagogue|white nationalis[mt]|populis[mt]|socialist|maga|terroris[mt]|bigot|hate group|fringe)\b", re.I)
FACT = re.compile(r"\b(serv(ed|es|ing)|born|raised|grew up|graduat\w*|degree|elected|represent\w*|work(ed|s)|career|veteran|attorney|lawyer|teacher|nurse|doctor|physician|engineer|farmer|rancher|business|owner|founded|lives|resides|married|father|mother|member of|former|currently|years|army|navy|marine|air force|police|sheriff|prosecutor|judge|mayor|council|senator|representative|legislat\w*|commissioner|university|college|school)\b", re.I)
PROMO = re.compile(r"\b(donate|contribute|volunteer|sign up|join (us|the team)|paid for by|chip in|subscribe|cookie|privacy policy)\b", re.I)
BANNED_HOST = re.compile(r'(^|\.)(wikipedia|wikidata|wikimedia)\.org$|(^|\.)(apnews\.com|ap\.org|reuters\.com)$')
SUF = {'jr', 'sr', 'ii', 'iii', 'iv'}

def strip(s):
    s = unicodedata.normalize('NFD', str(s or '')); return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
def nkey(n):
    s = strip(n); s = re.sub(r'["“”][^"“”]*["“”]', ' ', s); s = re.sub(r'\([^)]*\)', ' ', s)
    s = re.sub(r"[^a-z\s]", ' ', s.replace("'", '').replace('’', '')); t = [w for w in s.split() if w not in SUF and len(w) > 1]
    return '' if not t else (t[0] + ' ' + t[-1] if len(t) > 1 else t[0])
def last(n): return (nkey(n).split(' ') or [''])[-1]
def lev(a, b):
    if a == b: return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1): cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]
SUFFIX = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}
def lastn(n):
    t = [x for x in nkey(n).split(' ') if x and x not in SUFFIX]
    return t[-1] if t else ''
def firsts(n):
    """first name plus any quoted nickname: 'Robert C. "Bobby" Scott' -> {'robert', 'bobby'}"""
    s = {x for x in [nkey(n).split(' ')[0]] if x}
    for q in re.findall(r'[“"]([^”"]+)[”"]', n or ''): s.add(nkey(q).split(' ')[0])
    return s
def same_person(off_n, off_p, e_n, e_p):
    """official name vs an existing entry in the same race: same name key, or same last name (party agreeing), or the
    same party and first name with a last name within 2 letters (a misspelling in the old list: Krichner/Kirchner)."""
    a, b = nkey(off_n), nkey(e_n)
    if a == b: return 'same'
    pa = (not off_p or not e_p or pk(off_p) == pk(e_p))
    if last(off_n) == last(e_n) and pa and (' ' not in a or ' ' not in b or a[0] == b[0]): return 'same'
    if pa and off_p and e_p and a.split(' ')[0] == b.split(' ')[0] and len(last(off_n)) > 3 and lev(last(off_n), last(e_n)) <= 2: return 'spelling'
    # nickname / suffix forms of the same name: 'Thomas "Jay" Feely IV' = 'Jay Feely'; 'Robert C. "Bobby" Scott' = 'Bobby Scott'
    if pa and off_p and e_p and lastn(off_n) == lastn(e_n) and lastn(off_n) and (firsts(off_n) & firsts(e_n)): return 'spelling'
    return None
def pk(p):
    p = p or ''
    if re.match(r'^(Democratic|DFL|Democrat)', p, re.I): return 'D'
    if re.match(r'^Republican', p, re.I): return 'R'
    return 'X' if p else ''
def host(u):
    h = (urlparse(u or '').hostname or '').lower(); return h[4:] if h.startswith('www.') else h
def banned_url(u): return bool(u) and bool(BANNED_HOST.search(host(u)))
def junk(n): return bool(re.search(r'^(write-?ins?|scattering|over ?votes?|under ?votes?|blank)|write-?ins? \(|added together|\b(unofficial|unassigned|uncertified) write-?in', n or '', re.I))

def getjson(rel):
    if SITE_DIR: return json.load(open(os.path.join(SITE_DIR, rel)))
    r = S.get(SITE + rel, params={'x': int(time.time())}, timeout=40); r.raise_for_status(); return r.json()
def official_rows():
    """(mode, st, d, city, name, party, source-name) from the app's official results data."""
    out = []
    sw = getjson('data/statewide.json')
    for m in ('gov', 'senate'):
        for st, L in (sw.get(m) or {}).items():
            for o in L:
                for c in o.get('cands', []):
                    if not c.get('w'): out.append((m, st, '', '', c['n'], c.get('p', ''), (o.get('src') or {}).get('name', '')))
        for st, o in ((sw.get('namesOnly') or {}).get(m) or {}).items():
            for c in o.get('cands', []):
                    if not c.get('w'): out.append((m, st, '', '', c['n'], c.get('p', ''), (o.get('src') or {}).get('name', '')))
    for st in NAMES:
        if st == 'DC': continue
        try: j = getjson('data/districts/%s.json' % st)
        except Exception as e: print('districts', st, e); continue
        for layer in ('off', 'cl'):
            L = j.get(layer) or {}
            for d, v in (L.get('r') or {}).items():
                dd = 'AL' if len(j.get('d', {})) == 1 else d
                for c in v.get('cands', []):
                    if not c.get('w'): out.append(('house', st, dd, '', c['n'], c.get('p', ''), (L.get('src') or {}).get('name', '')))
            for d, cs in (L.get('unoppCands') or {}).items():   # unopposed: on the state's candidate list, no vote count
                dd = 'AL' if len(j.get('d', {})) == 1 else d
                for c in cs: out.append(('house', st, dd, '', c['n'], c.get('p', ''), (L.get('src') or {}).get('name', '')))
    my = getjson('data/mayors.json')
    for c in my.get('cities', []):
        for x in c.get('cands', []): out.append(('mayor', c['st'], '', c['id'], x['n'], x.get('p', ''), (c.get('src') or {}).get('name', '')))
    return [r for r in out if r[4] and not junk(r[4]) and nkey(r[4])]
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

# ---------- FEC (official) ----------
def fec_master():
    yy = YEAR[2:]
    try:
        r = S.get('https://www.fec.gov/files/bulk-downloads/%s/cn%s.zip' % (YEAR, yy), timeout=90); r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content)); rows = z.read(z.namelist()[0]).decode('latin1').splitlines()
    except Exception as e:
        print('FEC master unavailable', e); return []
    out = []
    for ln in rows:
        f = ln.split('|')
        if len(f) < 10 or f[3] != YEAR or f[5] not in ('H', 'S'): continue
        nm = f[1]; m = re.match(r'^([^,]+),\s*(.*)$', nm); disp = (m.group(2) + ' ' + m.group(1)) if m else nm
        out.append({'id': f[0], 'n': disp.title(), 'k': nkey(disp), 'last': last(disp), 'party': f[2], 'st': f[4], 'office': f[5], 'd': f[6].lstrip('0') or '0', 'pcc': f[9]})
    return out
def fec_match(F, mode, st, d, n):
    if mode not in ('house', 'senate'): return None
    off = 'H' if mode == 'house' else 'S'; dd = '0' if d == 'AL' else str(d)
    L = [x for x in F if x['st'] == st and x['office'] == off and (off == 'S' or x['d'] == dd or (dd == '0' and x['d'] in ('0', '1')))]
    k = nkey(n); hit = [x for x in L if x['k'] == k]
    if len(hit) != 1: hit = [x for x in L if x['last'] == last(n) and x['k'][:1] == k[:1]]
    return hit[0] if len(hit) == 1 else None
def fec_site(pcc):
    if not FEC_KEY or not pcc: return None
    try:
        r = S.get('https://api.open.fec.gov/v1/committee/%s/' % pcc, params={'api_key': FEC_KEY}, timeout=30)
        w = ((r.json().get('results') or [{}])[0].get('website') or '').strip()
        if not w: return None
        return w if w.lower().startswith('http') else 'https://' + w.lower()
    except Exception: return None

# ---------- the candidate's own site ----------
def fetch(u):
    try:
        r = S.get(u, timeout=20, allow_redirects=True)
        if r.status_code == 200 and 'html' in r.headers.get('content-type', ''): return r.url, r.text
    except Exception: pass
    return None, None
def paras(html):
    try: doc = LH.fromstring(html)
    except Exception: return [], doc if False else None
    for bad in doc.xpath('//script|//style|//nav|//footer|//header|//form|//noscript'): bad.drop_tree()
    ps = []
    for el in doc.iter('p', 'li', 'h2', 'h3', 'div'):
        if el.tag == 'div' and len(el): continue
        t = re.sub(r'\s+', ' ', el.text_content()).strip()
        if 40 <= len(t) <= 1200: ps.append(t)
    return ps, doc
def site_names_candidate(html, n):
    t = strip(re.sub(r'<[^>]+>', ' ', html or ''))
    w = re.sub(r'[^a-z\s]', ' ', t).split()
    if last(n) not in w: return False
    # v39d: the first name (or its first 3 letters, for Bob/Robert-style forms) must be on the page too,
    # so a same-surname site (e.g. a different Taylor) is not taken as this candidate's
    f = [x for x in re.sub(r'[^a-z\s]', ' ', strip(n)).split() if len(x) > 1]
    return not f or any(x == f[0] or (len(f[0]) > 3 and x.startswith(f[0][:3])) for x in w)
def bio_from_site(site, n, st):
    """Up to two consecutive sentences, verbatim, from the candidate's own site that name the candidate and state a fact."""
    u0, h0 = fetch(site)
    if not h0 or not site_names_candidate(h0, n): return None, None
    pages = [(u0, h0)]
    try:
        doc = LH.fromstring(h0); seen = set()
        for a in doc.iter('a'):
            href = a.get('href') or ''; lab = (a.text_content() or '') + ' ' + href
            if re.search(r'\b(about|meet|bio|biography|story)\b', lab, re.I):
                u = urljoin(u0, href)
                if host(u) == host(u0) and u not in seen and u != u0: seen.add(u)
        for u in list(seen)[:3]:
            uu, hh = fetch(u)
            if hh: pages.insert(0, (uu, hh))
    except Exception: pass
    L = last(n); first = (nkey(n).split(' ') or [''])[0]
    for u, h in pages:
        ps, _ = paras(h)
        for p in ps:
            ss = re.split(r'(?<=[a-z0-9\)\]"”’])[.!?]\s+(?=[A-Z“"])', p)
            for i, s in enumerate(ss):
                s = s.strip(); s = s if re.search(r'[.!?]$', s) else s + '.'
                k = strip(s)
                if L not in re.sub(r'[^a-z\s]', ' ', k).split(): continue
                if not (40 <= len(s) <= 320) or BAN.search(s) or PROMO.search(s) or not FACT.search(s): continue
                if re.search(r'\b(i|we|my|our|you)\b', s, re.I) and not re.search(r'\b(' + re.escape(first) + r')\b', k): continue
                out = [s]
                if i + 1 < len(ss):
                    s2 = ss[i + 1].strip(); s2 = s2 if re.search(r'[.!?]$', s2) else s2 + '.'
                    if 30 <= len(s2) <= 300 and not BAN.search(s2) and not PROMO.search(s2) and FACT.search(s2) and len(s) + len(s2) < 480: out.append(s2)
                return ' '.join(out), u
    return None, None

def clean_profile(f):
    """remove encyclopedia-derived fields; returns list of what was removed."""
    gone = []
    for k in ('wiki', 'qid'):
        if k in f: f.pop(k); gone.append(k)
    if f.get('bioSrc') and banned_url(f['bioSrc']) or (f.get('bio') and not f.get('bioSrc')):
        f.pop('bio', None); f.pop('bioSrc', None); gone.append('bio')
    if f.get('img') and (banned_url(f['img']) or banned_url(f.get('imgSrc'))):
        f.pop('img', None); f.pop('imgSrc', None); gone.append('img')
    if 'offices' in f and not f.get('officesSrc'):
        f.pop('offices'); gone.append('offices')   # these came from Wikidata
    for blk in f.get('issues') or []:
        for it in blk.get('items') or []:
            if banned_url(it.get('via')): it.pop('via', None)
    return gone

def main():
    os.makedirs(D + '/c', exist_ok=True)
    idx = json.load(open(D + '/index.json'))
    try: pend = json.load(open(D + '/pending-positions.json'))
    except Exception: pend = {'note': 'Candidates whose sourced Key positions have not been generated yet (the AI step runs outside GitHub).', 'items': []}
    G = json.load(open('data/officials.json')) if os.path.exists('data/officials.json') else None
    rows = official_rows()
    F = fec_master()
    rep = {'official_rows': len(rows), 'new': [], 'dropped_not_in_official_data': [], 'cleaned': {}, 'bios_from_own_site': 0, 'bios_removed': 0, 'photos_removed': 0, 'sites_kept': 0, 'sites_dropped': [], 'fec_matched': 0}
    official = {}
    for mode, st, d, city, n, p, srcname in rows:
        official.setdefault(rkey(mode, st, d, city), []).append((mode, st, d, city, n, p, srcname))
    changed = False
    # 1) drop index entries for names not in the official data (only in --clean, or for races the official data covers)
    for rk, L in list(idx['races'].items()):
        offn = official.get(rk)
        keep = []
        for e in L:
            m = [(same_person(x[4], x[5], e['n'], e.get('p')), x) for x in (offn or [])]
            m = [z for z in m if z[0]]
            if m and m[0][0] == 'same': keep.append(e)
            elif m:
                rep.setdefault('renamed_to_official_spelling', []).append((rk, e['n'], m[0][1][4])); e['n'] = m[0][1][4]; e['p'] = m[0][1][5] or e.get('p'); keep.append(e); changed = True
            elif not offn and not CLEAN: keep.append(e)
            else: rep['dropped_not_in_official_data'].append((rk, e['n'], e.get('p'))); changed = True
        if keep: idx['races'][rk] = keep
        else: idx['races'].pop(rk)
    # 2) add new official names
    seen = set()
    for rk, L0 in official.items():
        L = idx['races'].setdefault(rk, [])
        for mode, st, d, city, n, p, srcname in L0:
            if find(L, n, p) or (rk, nkey(n)) in seen: continue
            seen.add((rk, nkey(n)))
            cid = rk + '_' + nkey(n).replace(' ', '-'); k = 2
            while any(e['id'] == cid for e in L): cid = rk + '_' + nkey(n).replace(' ', '-') + str(k); k += 1
            e = {'id': cid, 'n': n, 'p': p, 'new': time.strftime('%Y-%m-%d')}
            f = {'id': cid, 'n': n, 'p': p, 'race': {'mode': mode, 'st': st, 'd': d or None, 'city': city or None}, 'updated': time.strftime('%Y-%m-%d'), 'auto': True, 'listSrc': srcname}
            s = json.dumps(f, ensure_ascii=False, separators=(',', ':'))
            open(D + '/c/' + cid + '.json', 'w').write(s); e['f'] = 1; e['u'] = hashlib.md5(s.encode()).hexdigest()[:8]
            if pk(p) in ('D', 'R') or mode == 'mayor':
                pend['items'].append({'id': cid, 'n': n, 'p': p, 'race': rk, 'added': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
            L.append(e); rep['new'].append((rk, n, p)); changed = True
    # 3) profiles: clean, FEC id, verified site, own-site bio
    byid = {e['id']: (rk, e) for rk, L in idx['races'].items() for e in L}
    files = sorted(os.listdir(D + '/c'))
    def work(fn):
        path = D + '/c/' + fn; f = json.load(open(path)); before = json.dumps(f, sort_keys=True)
        cid = f.get('id') or fn[:-5]
        if cid not in byid: return fn, 'orphan', None
        rk, e = byid[cid]; r = f.get('race') or {}
        if e['n'] != f.get('n'): f['n'] = e['n']; f['p'] = e.get('p', f.get('p'))
        gone = clean_profile(f) if CLEAN else []
        fx = fec_match(F, r.get('mode'), r.get('st'), r.get('d') or '', f['n']) if F else None
        if fx: f['fec'] = fx['id']; f['fecSrc'] = 'https://www.fec.gov/data/candidate/%s/' % fx['id']
        site = f.get('site')
        if fx and not site:
            w = fec_site(fx['pcc'])
            if w: site = w; f['site'] = w; f['siteKind'] = 'campaign'; f['siteSrc'] = 'FEC Form 1 (%s)' % fx['pcc']
        site_ok = None
        if site:
            u, h = fetch(site)
            site_ok = bool(h and site_names_candidate(h, f['n']))
            if not site_ok: f.pop('site', None); f.pop('siteKind', None); f.pop('siteSrc', None)
        if not f.get('bio') and site_ok:
            b, u = bio_from_site(site, f['n'], r.get('st'))
            if b and re.search(r'(?i)press release|follow up with|\bplan will\b|^the \w+ plan\b', b): b = None
            if b:
                # the bio page may sit on a second campaign domain the own site links/redirects to: keep it only when
                # that domain carries the candidate's own name (else it's someone else's site: no bio)
                sh = urlparse(site).hostname or ''; bh = urlparse(u).hostname or ''
                strip = lambda h: re.sub(r'^www\.', '', h.lower())
                if strip(sh) == strip(bh) or strip(bh).endswith('.' + strip(sh)): f['bio'] = b; f['bioSrc'] = u
                elif any(len(t) > 2 and t in strip(bh).replace('-', '') for t in nkey(f['n']).split()):
                    f['bio'] = b; f['bioSrc'] = u; f['siteAlt'] = sorted(set((f.get('siteAlt') or []) + ['https://' + strip(bh) + '/']))
        f['updated'] = time.strftime('%Y-%m-%d') if json.dumps(f, sort_keys=True) != before else f.get('updated')
        return fn, (gone, site, site_ok, bool(fx), bool(f.get('bio'))), f
    with cf.ThreadPoolExecutor(12) as ex:
        for fn, info, f in ex.map(work, files):
            if info == 'orphan':
                rep.setdefault('orphans', []).append(fn); continue
            gone, site, site_ok, fx, hasbio = info
            if gone: rep['cleaned'][f['id']] = gone
            if 'bio' in gone: rep['bios_removed'] += 1
            if 'img' in gone: rep['photos_removed'] += 1
            if site_ok: rep['sites_kept'] += 1
            elif site: rep['sites_dropped'].append((f['id'], site))
            if fx: rep['fec_matched'] += 1
            if hasbio and f.get('bioSrc') and not banned_url(f['bioSrc']): rep['bios_from_own_site'] += 1
            s = json.dumps(f, ensure_ascii=False, separators=(',', ':'))
            old = open(D + '/c/' + fn).read()
            if s != old:
                open(D + '/c/' + fn, 'w').write(s); changed = True
                e = byid[f['id']][1]; e['u'] = hashlib.md5(s.encode()).hexdigest()[:8]
    for fn in rep.get('orphans', []):
        if CLEAN: os.remove(D + '/c/' + fn); changed = True
    if CLEAN:
        pend['items'] = [x for x in pend.get('items', []) if x.get('id') in byid]
        for x in pend['items']: x.pop('wt', None)
    s_all = json.dumps(idx) + json.dumps(pend)
    for fn in os.listdir(D + '/c'): s_all += open(D + '/c/' + fn).read()
    left = sorted(set(h for h in re.findall(r'https?://([^/"\s]+)', s_all) if BANNED_HOST.search(h[4:] if h.startswith('www.') else h)))
    rep['banned_hosts_left'] = left
    if changed:
        idx['updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        idx['note'] = '2026 candidates, from the official results and candidate lists of the state and local election offices. m = existing official page id; f = has a profile file in c/.'
        open(D + '/index.json', 'w').write(json.dumps(idx, ensure_ascii=False, separators=(',', ':')))
        open(D + '/pending-positions.json', 'w').write(json.dumps(pend, ensure_ascii=False, indent=1))
    json.dump(rep, open(os.environ.get('KNOWUS_CAND_REPORT', '/tmp/candidates-report.json'), 'w'), indent=1, ensure_ascii=False)
    print('official rows', len(rows), '| new', len(rep['new']), '| dropped', len(rep['dropped_not_in_official_data']), '| bios from own site', rep['bios_from_own_site'], '| bios removed', rep['bios_removed'], '| photos removed', rep['photos_removed'], '| sites kept', rep['sites_kept'], 'dropped', len(rep['sites_dropped']), '| FEC matched', rep['fec_matched'], '| banned hosts left', left)
if __name__ == '__main__':
    main()
