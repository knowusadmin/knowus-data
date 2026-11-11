#!/usr/bin/env python3
"""KnowUS local officials, Rhode Island: mayor / town manager / administrator, town or city clerk, and the town or city
council of all 39 municipalities, from the Rhode Island Department of State's Directory of Government Officials
(opengov.sos.ri.gov/GOVDirectoryPublic, "Cities & Towns"). Contact: the town/city hall address, office phone and website
listed there; an official's email only on the municipality's own domain, an official's phone only on the office line.
usage: ri_sos_build.py <dir with <EntityID>.html> <site data/local/RI.json> <out.json>"""
import json,re,sys,os,glob,collections,datetime as dt
from urllib.parse import urlparse
from bs4 import BeautifulSoup
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
def U(e): return 'https://opengov.sos.ri.gov/GOVDirectoryPublic/GOVDirectoryMeetingDetails?EntityID=%s'%e
site=json.load(open(sitef,encoding='utf-8')); P=site['places']
def nz(s): return re.sub(r'[^a-z]','',s.lower())
PL={}
for pid,p in P.items():
    if p.get('t')!='CDP': PL.setdefault(nz(p['n']),[]).append(pid)
def dom(u):
    h=(urlparse(u if '//' in u else 'http://'+u).hostname or '').lower(); return h[4:] if h.startswith('www.') else h
PH=re.compile(r'^\(?\d{2,3}\)?[- ]?\d{3}[- ]\d{4}(\s*x\s*\d+)?$')
def digits(s): return re.sub(r'\D','',re.sub(r'(?i)\s*x\s*\d+$','',s))[-10:]
def sameperson(a,b):
    a,b=[[w for w in re.sub(r',',' ',x).split() if not re.match(r'(?i)^(jr|sr|ii|iii|iv)\.?$',w)] for x in (a,b)]; return bool(a and b) and nz(a[-1])==nz(b[-1]) and nz(a[0])[:1]==nz(b[0])[:1]
st={'pages':0,'no_place':[],'places_filled':0,'officials':0}
res={'st':'RI','built':TODAY,'src':{'name':'Rhode Island Department of State, Directory of Government Officials: Cities & Towns (opengov.sos.ri.gov)','note':'The chief executive, clerk and council of each city and town as listed in the state directory; town/city hall contact.'},'places':{}}
for f in sorted(glob.glob(os.path.join(src,'*.html'))):
    eid=os.path.basename(f)[:-5]; st['pages']+=1
    t=BeautifulSoup(open(f,encoding='utf-8').read(),'lxml').get_text('\n',strip=True)
    m=re.search(r'\n([A-Z][A-Za-z ]+), (Town|City) of\n',t)
    if not m: continue
    name=m.group(1); is_city=m.group(2)=='City'
    pids=PL.get(nz(name),[])
    if len(pids)!=1: st['no_place'].append(name); continue
    pid=pids[0]; p=P[pid]
    body=t[m.end():]
    ci=body.find('Contact Information'); ad=body.find('Administration'); co=re.search(r'\n(City |Town )?Council\n',body); sc=body.find('\nSchool Committee')
    contact=body[ci:ad]
    ct={}
    lines=[x.strip() for x in contact.split('\n')]
    if len(lines)>1 and re.search(r'\d',lines[1]) and not re.search(r'(?i)p\.?\s*o\.?\s*box',lines[1]): ct['a']=re.sub(r'\s+',' ',lines[1])
    office=None
    for i_,l_ in enumerate(lines):
        if l_.startswith('Office Phone') and i_+1<len(lines): office=lines[i_+1]; ct['p']=[office]
        if l_.startswith('Web') and i_+1<len(lines) and '.' in lines[i_+1]: w=lines[i_+1]; ct['w']=w if w.startswith('http') else 'https://'+w
    good={d for d in (dom(p.get('w','')),dom(ct.get('w',''))) if d}
    def person(lines_):
        ph=em=None
        for l_ in lines_:
            if '@' in l_ and not em: em=l_.strip()
            elif PH.match(l_.strip()) and not ph: ph=l_.strip()
        c=dict(ct)
        if em and em.split('@')[-1].lower().removeprefix('www.') in good: c['e']=em
        if ph and office and digits(ph)==digits(office): c['p']=[ph]
        if c: c['src']=U(eid); c['g']=1
        return c
    outl=[]
    adm=body[ad+len('Administration'):co.start() if co else (sc if sc>0 else len(body))]
    blocks=re.split(r'\n(?=[A-Z][^\n,]{1,60}, [A-Z][^\n]+\n?)',adm)
    for b in blocks:
        ls=[x.strip() for x in b.strip().split('\n') if x.strip()]
        if not ls or ',' not in ls[0]: continue
        role,nm_=ls[0].split(',',1); role=role.strip(); nm_=re.sub(r'\s+',' ',nm_).strip()
        R=role.upper()
        if re.search(r'DEPUTY|ASSISTANT|CHIEF OF STAFF',R): continue
        if R=='MAYOR': r_,rk='Mayor','gen_mayor'
        elif re.search(r'(TOWN|CITY) (MANAGER|ADMINISTRATOR)',R): r_,rk=role.title().replace('Of','of'),None
        elif re.search(r'^(TOWN|CITY) CLERK$',R): r_,rk=role.title(),None
        elif re.search(r'COUNCIL PRESIDENT',R): r_,rk='Council President','gen_council'
        else: continue
        if len(nm_.split())<2: continue
        o={'n':nm_,'r':r_,'src':'risos','u':U(eid),'d':TODAY}
        if rk: o['rk']=rk
        c=person(ls[1:])
        if c: o['ct']=c
        outl.append(o)
    if co:
        cb=body[co.end():sc if sc>co.end() else len(body)]
        cb=re.split(r'\n(Annual Meetings|Upcoming Meetings|Boards|Other)',cb)[0]
        ls=[x.strip() for x in cb.split('\n') if x.strip()]
        cur=None; grp=[]
        for l_ in ls+['@@END']:
            if l_=='@@END' or (not PH.match(l_) and '@' not in l_):
                if cur:
                    nm_=re.sub(r'\s+',' ',cur); role='Council Member'
                    mm=re.match(r'^(.*?),\s*(President|Vice President|Council President)$',nm_)
                    if mm: nm_=mm.group(1); role='Council '+mm.group(2).replace('Council ','')
                    if len(nm_.split())>=2 and not any(sameperson(nm_,x['n']) for x in outl):
                        o={'n':nm_,'r':role,'rk':'gen_council','src':'risos','u':U(eid),'d':TODAY}
                        c=person(grp)
                        if c: o['ct']=c
                        outl.append(o)
                cur=l_; grp=[]
            else: grp.append(l_)
    ex=[o for o in (p.get('o') or []) if o.get('src')!='risos']; LL=[]
    if any(o.get('rk')=='gen_mayor' for o in outl):
        ex=[o for o in ex if o.get('rk')!='gen_mayor' or any(sameperson(o['n'],x['n']) for x in outl)]
    exc=[x for x in ex if x.get('rk')=='gen_council']; ours=[o for o in outl if o.get('rk')=='gen_council']
    if exc and sum(1 for x in exc if any(sameperson(x['n'],o['n']) for o in ours))*2<len(exc):
        outl=[o for o in outl if o.get('rk')!='gen_council']   # the town's own site (newer) disagrees with the directory: keep the site's council
    for o in outl:
        if any(sameperson(o['n'],x['n']) for x in ex+LL): continue
        LL.append(o)
    if not LL: continue
    res['places'][pid]={'n':p['n'],'o':ex+LL}; st['places_filled']+=1; st['officials']+=len(LL)
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps(st))
