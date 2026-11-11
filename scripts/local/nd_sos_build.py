#!/usr/bin/env python3
"""KnowUS local officials, North Dakota: city officers elected at the June 11, 2024 and June 9, 2026 elections, from the
North Dakota Secretary of State's official Elected Candidate List (vip.sos.nd.gov/CandidateResultsList.aspx, jurisdiction
"City"). ND city officers serve four-year staggered terms, so the two elections together cover the sitting council or
commission; a mayor or commission president comes from the more recent of the two. Names as printed. Candidates' own
addresses, phones and emails in the list are NOT used (personal contacts).
usage: nd_sos_build.py <site data/local/ND.json> <out.json>"""
import json,re,sys,os,datetime as dt,requests
from bs4 import BeautifulSoup
sitef,out=sys.argv[1:3]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
EL={346:'June 9, 2026',329:'June 11, 2024'}
def U(eid): return 'https://vip.sos.nd.gov/CandidateResultsList.aspx?eid=%d'%eid
def fetch(eid):
    ss=requests.Session(); ss.headers['User-Agent']='Mozilla/5.0'
    sp=BeautifulSoup(ss.get(U(eid),timeout=60).text,'lxml')
    data={x.get('name'):x.get('value','') for x in sp.find_all('input') if x.get('type')=='hidden'}
    for sel in sp.find_all('select'):
        o=sel.find('option',selected=True) or sel.find('option'); data[sel.get('name')]=o.get('value') if o else ''
    data['ctl00$ContentPlaceHolder1$ddlJursdiction']='MUN'; data['ctl00$ContentPlaceHolder1$btnSearch']='Search'
    sp=BeautifulSoup(ss.post(U(eid),data=data,timeout=120).text,'lxml')
    rows=[]
    for rw in sp.find_all('table')[0].find_all('tr')[1:]:
        c=[x.get_text(' ',strip=True) for x in rw.find_all('td')]
        if len(c)>=9: rows.append({'contest':c[0],'office':c[1],'district':c[2],'name':re.sub(r'\s+',' ',c[4]).strip(),'party':c[8]})
    return rows
def nm(s): return re.sub(r'[^a-z]','',s.lower())
site=json.load(open(sitef,encoding='utf-8'))
C={}
for pid,p in site['places'].items():
    if p.get('t')=='city': C.setdefault(nm(p['n']),[]).append(pid)
def place(d):
    for k in (d, re.sub(r'(?i)^city of\s+','',d), d+' City', re.sub(r'(?i)\s+city$','',d)):
        if len(C.get(nm(k),[]))==1: return C[nm(k)][0]
KEEP=re.compile(r'(?i)^(mayor|council member|city council|commissioner|commission president|alderperson|alderman|alderwoman)')
st={'rows':0,'kept':0,'no_place':[],'places_filled':0,'officials':0}
add={}
for eid in sorted(EL,reverse=True):           # newest first
    for r in fetch(eid):
        st['rows']+=1
        if not KEEP.match(r['office']) or 'county' in r['office'].lower(): continue
        pid=place(r['district'])
        if not pid: st['no_place'].append(r['district']); continue
        role=r['office'].strip()
        head=bool(re.match(r'(?i)mayor|commission president',role))
        L=add.setdefault(pid,{'L':[],'head_from':None})
        if head and L['head_from'] and L['head_from']!=eid: continue   # older mayor/president superseded
        if head: L['head_from']=eid
        o={'n':r['name'],'r':role,'src':'ndsos','u':U(eid),'d':TODAY,'s':'elected %s'%EL[eid]}
        o['rk']='gen_mayor' if head else 'gen_council'
        L['L'].append(o); st['kept']+=1
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
res={'st':'ND','built':TODAY,'src':{'name':'North Dakota Secretary of State, Elected Candidate List, June 2024 and June 2026 elections (vip.sos.nd.gov)','note':'City officers elected in 2024 and 2026 (four-year staggered terms); the mayor or commission president from the more recent election. Names as printed.'},'places':{}}
ORD=lambda o:(0 if o['rk']=='gen_mayor' else 1, o['r'], o['n'])
for pid,v in add.items():
    p=site['places'][pid]; ex=[o for o in (p.get('o') or []) if o.get('src')!='ndsos']; LL=[]
    for o in sorted(v['L'],key=ORD):
        if any(sameperson(o['n'],x['n']) for x in ex+LL): continue
        if o['rk']=='gen_mayor' and any(x.get('rk')=='gen_mayor' for x in ex): continue
        LL.append(o)
    if not LL: continue
    res['places'][pid]={'n':p['n'],'o':ex+LL}; st['places_filled']+=1; st['officials']+=len(LL)
st['no_place']=sorted(set(st['no_place']))
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps(st))
