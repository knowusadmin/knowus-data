#!/usr/bin/env python3
"""KnowUS local officials, Oregon: the mayor of every incorporated city, from the Oregon Secretary of State's Oregon Blue
Book "Incorporated Cities" pages (sos.oregon.gov/blue-book, one page per city; list updated spring 2026). Contact: the
city hall address, phone and website the Blue Book lists (the office's main contact); email only on the city's own domain.
usage: or_bluebook_build.py <or_bluebook.json> <site data/local/OR.json> <out.json>"""
import json,re,sys,os,collections,datetime as dt
from urllib.parse import urlparse
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
site=json.load(open(sitef,encoding='utf-8')); P=site['places']
def nz(s): return re.sub(r'[^a-z]','',re.sub(r'(?i)^mt\.?\s','mount ',s).lower())
PL={}
for pid,p in P.items():
    if p.get('t')!='CDP': PL.setdefault(nz(p['n']),[]).append(pid)
def dom(u):
    h=(urlparse(u if '//' in u else 'http://'+u).hostname or '').lower(); return h[4:] if h.startswith('www.') else h
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nz(a[-1])==nz(b[-1]) and nz(a[0])[:1]==nz(b[0])[:1]
st={'pages':0,'no_mayor':[],'no_place':[],'places_filled':0,'officials':0}
res={'st':'OR','built':TODAY,'src':{'name':'Oregon Secretary of State, Oregon Blue Book: Incorporated Cities (sos.oregon.gov/blue-book)','note':'The mayor as listed on each city\'s Blue Book page; the city hall address, phone and website listed there.'},'places':{}}
for c in json.load(open(src,encoding='utf-8')):
    st['pages']+=1; b=c.get('block','')
    m=re.search(r'\nMayor( Pro-Tem)?:\s*([^\n]+)',b)
    if not m: st['no_mayor'].append(c['title']); continue
    name=re.sub(r'\s+',' ',m.group(2)).strip(); role='Mayor' if not m.group(1) else 'Mayor Pro Tem'
    if len(name.split())<2: st['no_mayor'].append(c['title']); continue
    pids=PL.get(nz(c['title']),[])
    if len(pids)!=1: st['no_place'].append(c['title']); continue
    pid=pids[0]; p=P[pid]
    ct={}
    a=re.search(r'\nAddress:\s*([^\n]+)',b); ph=re.search(r'\nPhone:\s*([^\n]+)',b); w=re.search(r'\nWeb:\s*\n?([^\n]+)',b); em=re.search(r'\nEmail:\s*\n?([^\n]+)',b)
    if ph: ct['p']=[ph.group(1).strip()]
    if a:
        parts=[x.strip() for x in a.group(1).split(',')]
        z=[x for x in parts if re.fullmatch(r'\d{5}(-\d{4})?',x)]
        street=[x for x in parts if not re.match(r'(?i)p\.?\s*o\.?\s*box',x) and x not in z]
        pob=len(street)<len([x for x in parts if x not in z])
        if street: ct['a']='%s, %s, OR%s'%(', '.join(street),p['n'],(' '+z[0]) if z and not pob else '')
    wd=''
    if w and '.' in w.group(1):
        wu=w.group(1).strip(); wd=dom(wu); ct['w']=wu if wu.startswith('http') else 'https://'+wu
    if em and wd and em.group(1).strip().lower().endswith('@'+wd): ct['e']=em.group(1).strip()
    o={'n':name,'r':role,'src':'orbb','u':c['url'],'d':TODAY}
    if role=='Mayor': o['rk']='gen_mayor'
    else: o['rk']='gen_council'
    if ct: ct['src']=c['url']; ct['g']=1; o['ct']=ct
    ex=[x for x in (p.get('o') or []) if x.get('src')!='orbb']
    if any(sameperson(name,x['n']) for x in ex): continue
    if role=='Mayor' and any(x.get('rk')=='gen_mayor' for x in ex): continue
    res['places'][pid]={'n':p['n'],'o':ex+[o]}; st['places_filled']+=1; st['officials']+=1
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps(st))
