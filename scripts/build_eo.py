#!/usr/bin/env python3
"""Build KnowUS executive-order data from the Federal Register API (no key).
Usage: python3 build_eo.py <out_dir> [--raw-cache DIR] [--no-text] [--max-fetch N (new order texts fetched per run, default 80)]
  <out_dir> gets index.json, <pres>.json (list + status) and text/<pres>.json (verbatim opening text).
Hourly use (GitHub job): run with out_dir = data/eo of the knowus-data repo. It re-reads every EO's
disposition notes each run (2 API calls) so new EOs and new revocations show up; the verbatim text
is fetched only for EOs not already in text/<pres>.json.
Status comes ONLY from the Federal Register's executive_order_notes ("Revoked by:", "Revokes:", ...),
read in both directions. Nothing is inferred from news or from AI."""
import json, os, re, sys, time, html, collections, datetime
import urllib.request, urllib.parse
API = "https://www.federalregister.gov/api/v1/documents.json"
UA = {"User-Agent": "KnowUS-data/1.0 (knowusadmin@gmail.com)"}
FIELDS = ["executive_order_number","title","signing_date","publication_date","citation","html_url","pdf_url",
          "abstract","executive_order_notes","president","document_number","raw_text_url"]
PRES = [  # id, FR identifier, label, first EO number of the term
  ("trump47","donald-trump","Donald J. Trump (2025–)",14147),
  ("biden","joe-biden","Joseph R. Biden Jr. (2021–2025)",13985),
  ("trump45","donald-trump","Donald J. Trump (2017–2021)",13765),
  ("obama","barack-obama","Barack Obama (2009–2017)",13489),
  ("bush43","george-w-bush","George W. Bush (2001–2009)",13198),
  ("clinton","william-j-clinton","Bill Clinton (1994–2001)",12834),
]
def get(url, tries=5, timeout=60):
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if t == tries-1: raise
            time.sleep(3 + 4*t)
def fetch_all():
    out = []; page = 1
    while True:
        q = [("conditions[presidential_document_type]","executive_order"),("per_page","1000"),("page",str(page)),("order","oldest")] + [("fields[]",f) for f in FIELDS]
        j = json.loads(get(API + "?" + urllib.parse.urlencode(q)))
        out += j.get("results") or []
        if not j.get("next_page_url"): break
        page += 1
    return out
LABELS = {'revoked by':'revoked_by','rescinded by':'revoked_by','revoked in part by':'revoked_part_by','revoked (in part) by':'revoked_part_by',
 'revoked in part and supplemented by':'revoked_part_by','partially revoked by':'revoked_part_by',
 'superseded by':'superseded_by','superseded in part by':'superseded_part_by','superseded by (in part)':'superseded_part_by','partially superseded by':'superseded_part_by',
 'amended by':'amended_by','amend by':'amended_by','suspended by':'suspended_by','reinstated by':'reinstated_by','supplemented by':'supplemented_by','continued by':'continued_by',
 'revokes':'revokes','rescinds':'revokes','revokes in part':'revokes_part','partially revokes':'revokes_part','revokes in part and supplements':'revokes_part',
 'supersedes':'supersedes','suspersedes':'supersedes','supersedes in part':'supersedes_part','supersedes (in part)':'supersedes_part','partially supersedes':'supersedes_part',
 'supersedes or revokes':'supersedes','amends':'amends','suspends':'suspends','reinstates':'reinstates','see':'see','ee':'see','note':'note','continues':'continues',
 'supplements':'supplements','terminates':'terminates'}
LAB_RE = re.compile(r'(?:^|(?<=[\n;]))\s*(' + '|'.join(sorted((re.escape(k) for k in LABELS), key=len, reverse=True)) + r')\s*:?\s*(?=EO|\s)', re.I | re.M)
def parse_notes(n):
    out = collections.defaultdict(list)
    if not n: return out
    pos = [(m.start(), m.end(), LABELS[m.group(1).lower()]) for m in LAB_RE.finditer(n)]
    for i, (s, e, k) in enumerate(pos):
        seg = n[e:pos[i+1][0] if i+1 < len(pos) else len(n)]
        for m in re.finditer(r'EO\s*(\d{4,5})', seg):
            if m.group(1) not in out[k]: out[k].append(m.group(1))
    return out
# what the actor does -> what the target receives
INV = {'revokes':'revoked_by','revokes_part':'revoked_part_by','supersedes':'superseded_by','supersedes_part':'superseded_part_by',
       'amends':'amended_by','suspends':'suspended_by','reinstates':'reinstated_by'}
FWD = {v:k for k,v in INV.items()}
REL_WORD = {'revoked_by':'Revoked by','revoked_part_by':'Revoked in part by','superseded_by':'Superseded by','superseded_part_by':'Superseded in part by',
            'amended_by':'Amended by','suspended_by':'Suspended by','reinstated_by':'Reinstated by'}
ACT_WORD = {'revokes':'Revokes','revokes_part':'Revokes in part','supersedes':'Supersedes','supersedes_part':'Supersedes in part',
            'amends':'Amends','suspends':'Suspends','reinstates':'Reinstates'}
def pres_of(num):
    for pid, _, _, first in PRES:
        if num >= first: return pid
    return None
def clean_text(raw):
    t = re.sub(r'<[^>]+>', '', raw); t = html.unescape(t)
    t = re.sub(r'\[\[Page \d+\]\]', ' ', t)
    return t
def excerpt(raw, num):
    """Verbatim text from the order: its Purpose / Policy / Findings section when it has one, else its first
    section that isn't Definitions, else its opening. Only whitespace and the GPO quote marks (`` '') are normalised;
    long text is cut at a sentence end with an ellipsis."""
    t = clean_text(raw)
    m = re.search(r'Executive Order\s+%s\s+of\s+[A-Z][a-z]+\s+\d{1,2},\s+\d{4}' % num, t)
    if m: t = t[m.end():]
    t = re.sub(r'[ \t]*\n[ \t]*', '\n', t)
    secs = [(x.start(), x.group(3) or '') for x in re.finditer(r'\n\s*(Section|Sec\.)\s+(\d+[a-z]?)\.\s+(?:([A-Z][^.\n]{0,90}?)\.)?', t)]
    def body_at(i):
        s = secs[i][0]; e = secs[i+1][0] if i+1 < len(secs) else len(t)
        return t[s:e]
    pick = None
    for i, (_, h) in enumerate(secs):
        if re.search(r'purpose|policy|findings|background', h, re.I): pick = body_at(i); break
    if pick is None:
        for i, (_, h) in enumerate(secs):
            if not re.search(r'definition', h, re.I): pick = body_at(i); break
    if pick is None:
        b0 = re.search(r'By the authority vested', t)
        pick = t[b0.start():secs[0][0] if secs else b0.start()+3000] if b0 else t[:3000]
    body = re.sub(r'\s+', ' ', pick).strip()
    body = body.replace("``", "\u201c").replace("''", "\u201d")
    body = re.sub(r'\s*\(Presidential Sig\.\).*$', '', body)
    body = re.sub(r'\s*\[FR Doc.*$', '', body)
    if not body: return ''
    LIM = 1400
    if len(body) > LIM:
        cut = body[:LIM]; k = max(cut.rfind('. '), cut.rfind('; '))
        body = (cut[:k+1] if k > 400 else cut.rsplit(' ', 1)[0]) + ' \u2026'
    return body

MON = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
VERB = re.compile(r'\b(?:is|are) hereby (?:revoked|rescinded)(?: in (?:its|their) entirety)?')
BAD = re.compile(r'\b(sections?|sec\.|subsections?|paragraphs?|parts? of|provisions?|amended by|to the extent|insofar|except|portions?|that part|other than|but not)\b', re.I)
LST = re.compile(r'(?:following (?:[Ee]xecutive [Oo]rders?|[Ee]xecutive actions|orders|actions|documents|[Pp]residential actions)[^.:]{0,120}?(?:are|is) hereby (?:revoked|rescinded)[^.:]{0,40}:|(?:I|we) hereby revoke the following[^:]{0,80}:)(.{0,20000}?)(?=\s+Sec\. \d|$)')
ITEM = re.compile(r'\(\w{1,4}\)\s+Executive Order (\d{5})(?: of ' + MON + r' \d{1,2}, \d{4})?(?: \([^()]{0,400}\))?\s*(?=[;.,]|and\b|$)')
def norm_text(raw): return re.sub(r'\s+', ' ', clean_text(raw))
def depar(t):
    for _ in range(3): t = re.sub(r'\s*\([^()]{0,500}\)', '', t)
    return t
def text_revocations(t, self_num=None):
    """High-precision scan of an order's own words for WHOLE revocations of other EOs:
    a clause whose subject is only orders/proclamations ("Executive Order 13780, and Proclamations 9645 ... are hereby revoked"),
    or a list introduced by "The following executive actions are hereby revoked:". Clauses naming sections, parts,
    "to the extent", "except" etc. are skipped (those are partial and stay with the Federal Register notes)."""
    t2 = depar(t); out = {}
    for m in VERB.finditer(t2):
        if re.match(r'\s*(to the extent|insofar|with respect to|as to|except|only|in part)', t2[m.end():m.end()+40], re.I): continue
        pre = t2[max(0, m.start()-500):m.start()]
        b = max(pre.rfind('. '), pre.rfind('; '), pre.rfind(': '))
        if b < 0: continue
        cl = re.sub(r'^(Revocations?|Revocation of [^.]{0,80})\.\s*', '', pre[b+2:])
        if len(cl) > 450 or BAD.search(cl): continue
        if not re.match(r'(?:the )?(?:Executive Orders?|Proclamations?|Presidential|National Security|Memorand)', cl): continue
        for g in re.finditer(r'Executive Orders?\s+((?:\d{5}(?: of ' + MON + r' \d{1,2}, \d{4})?,?\s*(?:and\s+)?)+)', cl):
            for n in re.findall(r'\b(\d{5})\b', re.sub(MON + r' \d{1,2}, \d{4}', '', g.group(1))):
                if n != self_num: out[n] = (cl + m.group(0)).strip()
    for m in LST.finditer(t):
        for it in ITEM.finditer(m.group(1)):
            n = it.group(1)
            if n != self_num and n not in out: out[n] = (m.group(0)[:160] + ' … ' + it.group(0)).strip()
    return out
OTHER_FIELDS = ["document_number","title","signing_date","publication_date","citation","html_url","raw_text_url","proclamation_number","subtype"]
def fetch_other():
    """Proclamations, memoranda and notices whose text mentions revoking an executive order (the disposition notes miss some of these)."""
    out = []
    for pt in ['proclamation', 'memorandum', 'notice', 'other', 'determination']:
        page = 1
        while True:
            q = [("conditions[type][]","PRESDOCU"),("conditions[presidential_document_type]",pt),("conditions[term]",'"Executive Order" revoked'),("per_page","200"),("page",str(page))] + [("fields[]",f) for f in OTHER_FIELDS]
            j = json.loads(get(API + "?" + urllib.parse.urlencode(q)))
            out += j.get("results") or []
            if not j.get("next_page_url"): break
            page += 1
    return out

def build(out_dir, raw_cache=None, want_text=True, max_fetch=80):
    fetched = [0]
    os.makedirs(os.path.join(out_dir, 'text'), exist_ok=True)
    A = json.load(open(os.path.join(raw_cache, 'all.json'))) if raw_cache and os.path.exists(os.path.join(raw_cache, 'all.json')) else fetch_all()
    log = {'skipped_no_number': [], 'duplicates': [], 'date_conflicts': [], 'one_sided': 0}
    byn = {}
    for a in A:
        n = a.get('executive_order_number')
        if not n or not str(n).isdigit():
            log['skipped_no_number'].append({'doc': a.get('document_number'), 'title': a.get('title'), 'pub': a.get('publication_date')}); continue
        if n in byn:
            log['duplicates'].append({'n': n, 'doc': a.get('document_number')})
            if str(a.get('document_number','')).startswith(('C1','R1')): continue
        byn[n] = a
    notes = {n: parse_notes(a.get('executive_order_notes')) for n, a in byn.items()}
    date = {n: (a.get('signing_date') or a.get('publication_date') or '') for n, a in byn.items()}
    # events on each target: rel -> {actor_key: info}
    ev = collections.defaultdict(lambda: collections.defaultdict(dict)); acts = collections.defaultdict(lambda: collections.defaultdict(set))
    def add(actor, rel, target, src, info=None):
        if actor == target: return
        ad = (info or {}).get('date') or date.get(actor, '')
        if ad and date.get(target) and ad < date[target]:
            log['date_conflicts'].append({'actor': actor, 'rel': rel, 'target': target, 'from_notes_of': src}); return
        cur = ev[target][rel].get(actor)
        if cur and cur.get('src') == 'notes': return
        ev[target][rel][actor] = dict(info or {}, src=('notes' if src != 'text' else 'text'), date=ad)
        if actor in byn: acts[actor][FWD[rel]].add(target)
    for n, p in notes.items():
        for k, rel in INV.items():
            for t in p.get(k, []):
                if t in byn: add(n, rel, t, n)
                else: acts[n][k].add(t)  # target older than this dataset (before 1994)
        for rel in INV.values():
            for actor in p.get(rel, []):
                if actor in byn: add(actor, rel, n, n)
    # second check: the orders' own words (whole revocations only), for links the notes don't carry yet
    tcache_p = os.path.join(out_dir, 'text-revocations.json')
    tcache = json.load(open(tcache_p)) if os.path.exists(tcache_p) else {}
    def raw_for(doc, url, sub='txt'):
        if raw_cache and os.path.exists(os.path.join(raw_cache, sub, doc + '.txt')):
            return open(os.path.join(raw_cache, sub, doc + '.txt')).read()
        if not url or not want_text or fetched[0] >= max_fetch: return None
        fetched[0] += 1
        try: return get(url, tries=3, timeout=40)
        except Exception: return None
    text_added = []
    for n, a in byn.items():
        doc = a.get('document_number')
        if doc not in tcache:
            raw = raw_for(doc, a.get('raw_text_url'))
            if raw is None: continue
            tcache[doc] = {'n': n, 'revokes': text_revocations(norm_text(raw), n)}
        for t, q in tcache[doc]['revokes'].items():
            if t in byn and t not in ev or not any(n in ev[t].get(r, {}) for r in ('revoked_by', 'revoked_part_by', 'superseded_by', 'superseded_part_by')):
                if t in byn and not any(n in ev.get(t, {}).get(r, {}) for r in ('revoked_by', 'revoked_part_by', 'superseded_by', 'superseded_part_by')):
                    add(n, 'revoked_by', t, 'text', {'quote': q[:600]}); text_added.append([n, t])
    try: other = json.load(open(os.path.join(raw_cache, 'other.json'))) if raw_cache and os.path.exists(os.path.join(raw_cache, 'other.json')) else fetch_other()
    except Exception as e: other = []; log['other_fetch_error'] = str(e)
    for d in other:
        doc = d.get('document_number')
        if doc not in tcache:
            raw = raw_for(doc, d.get('raw_text_url'), 'other')
            if raw is None: continue
            tcache[doc] = {'revokes': text_revocations(norm_text(raw))}
        kind = d.get('subtype') or 'Presidential document'
        label = (kind + ' ' + str(d.get('proclamation_number'))) if d.get('proclamation_number') else (kind + ' of ' + (d.get('signing_date') or d.get('publication_date') or ''))
        for t, q in tcache[doc]['revokes'].items():
            if t in byn and not any(ev.get(t, {}).get(r) for r in ('revoked_by', 'superseded_by')):
                add('doc:' + doc, 'revoked_by', t, 'text', {'label': label, 'title': d.get('title'), 'url': d.get('html_url'), 'date': d.get('signing_date') or d.get('publication_date') or '', 'quote': q[:600]})
                text_added.append([label, t])
    json.dump(tcache, open(tcache_p, 'w'), separators=(',', ':'), ensure_ascii=False)
    log['text_added'] = text_added
    # one-sided count (recorded only on one of the two orders)
    for n, p in notes.items():
        for k, rel in INV.items():
            for t in p.get(k, []):
                if t in notes and n not in notes[t].get(rel, []): log['one_sided'] += 1
    def okey(a, info): return (info.get('date', ''), int(a) if a.isdigit() else 0)
    def status(n):
        e = ev.get(n, {})
        def latest(rels):
            xs = [(a, i) for r in rels for a, i in e.get(r, {}).items()]
            return max(xs, key=lambda v: okey(*v)) if xs else None
        full = latest(['revoked_by', 'superseded_by']); rein = latest(['reinstated_by'])
        if full and not (rein and okey(*rein) > okey(*full)):
            return 'R' if full[0] in e.get('revoked_by', {}) else 'S'
        if rein: return 'I'
        if e.get('revoked_part_by'): return 'P'
        if e.get('superseded_part_by'): return 'SP'
        if e.get('suspended_by'): return 'U'
        if e.get('amended_by'): return 'M'
        return 'A'
    per = collections.defaultdict(list)
    for n, a in byn.items():
        pid = pres_of(int(n))
        if not pid: continue
        e = ev.get(n, {})
        by = []
        for r in REL_WORD:
            for x, info in e.get(r, {}).items():
                row = [x, r, info.get('date', '')]
                if info.get('src') == 'text' or info.get('label'):
                    row.append({k: v for k, v in info.items() if k in ('src', 'label', 'url', 'quote', 'title') and v})
                by.append(row)
        by.sort(key=lambda v: (v[2], int(v[0]) if v[0].isdigit() else 0))
        ac = sorted([[x, k] for k in ACT_WORD for x in acts.get(n, {}).get(k, ())], key=lambda v: int(v[0]))
        per[pid].append({'n': n, 't': a.get('title') or '', 's': a.get('signing_date') or '', 'd': a.get('publication_date') or '',
                         'c': a.get('citation') or '', 'u': a.get('html_url') or '', 'pdf': a.get('pdf_url') or '', 'doc': a.get('document_number') or '',
                         'st': status(n), 'by': by, 'acts': ac, 'notes': (a.get('executive_order_notes') or '').replace('\r\n', '\n').strip(),
                         'abs': a.get('abstract') or ''})
    now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    idx = {'asOf': now, 'source': 'Federal Register API (federalregister.gov), executive_order_notes / disposition notes',
           'sourceUrl': 'https://www.federalregister.gov/presidential-documents/executive-orders', 'presidents': [], 'counts': {}, 'log': {
               'skippedNoNumber': len(log['skipped_no_number']), 'dateConflicts': log['date_conflicts'], 'oneSidedLinks': log['one_sided']}}
    tot = collections.Counter(); stamps = []
    for pid, fr, label, first in PRES:
        L = sorted(per.get(pid, []), key=lambda r: -int(r['n']))
        fp = os.path.join(out_dir, pid + '.json'); asof = now
        try:
            prev = json.load(open(fp))
            if prev.get('items') == L: asof = prev.get('asOf') or now   # unchanged: keep the date so the hourly job commits nothing
        except Exception: pass
        stamps.append(asof)
        json.dump({'asOf': asof, 'pres': pid, 'items': L}, open(fp, 'w'), separators=(',', ':'), ensure_ascii=False)
        c = collections.Counter(r['st'] for r in L); tot.update(c)
        nums = [int(r['n']) for r in L]
        idx['presidents'].append({'id': pid, 'label': label, 'count': len(L), 'min': min(nums) if nums else 0, 'max': max(nums) if nums else 0, 'status': dict(c)})
        # verbatim text excerpts (cached)
        tp = os.path.join(out_dir, 'text', pid + '.json')
        old = json.load(open(tp)) if os.path.exists(tp) else {}
        if want_text:
            for r in L:
                if r['n'] in old: continue
                raw = None
                if raw_cache and os.path.exists(os.path.join(raw_cache, 'txt', r['doc'] + '.txt')):
                    raw = open(os.path.join(raw_cache, 'txt', r['doc'] + '.txt')).read()
                else:
                    raw = raw_for(r['doc'], byn[r['n']].get('raw_text_url'))
                if raw: old[r['n']] = excerpt(raw, r['n'])
        json.dump(old, open(tp, 'w'), separators=(',', ':'), ensure_ascii=False)
    idx['counts'] = dict(tot); idx['total'] = sum(tot.values()); idx['asOf'] = max(stamps) if stamps else now
    json.dump(idx, open(os.path.join(out_dir, 'index.json'), 'w'), separators=(',', ':'), ensure_ascii=False)
    json.dump(log, open(os.path.join(out_dir, '..', 'eo-build-log.json') if False else os.path.join(raw_cache or out_dir, 'eo-build-log.json'), 'w'), indent=1)
    return idx
if __name__ == '__main__':
    args = sys.argv[1:]
    out = args[0]; rc = args[args.index('--raw-cache')+1] if '--raw-cache' in args else None
    mx = int(args[args.index('--max-fetch')+1]) if '--max-fetch' in args else 80
    i = build(out, rc, '--no-text' not in args, mx)
    print(json.dumps({k: i[k] for k in ('asOf', 'total', 'counts')}), [(p['id'], p['count']) for p in i['presidents']])
