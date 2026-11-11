#!/usr/bin/env python3
"""KnowUS local officials, Michigan: the city or township clerk of every Michigan city and township, from the Michigan
Department of State's clerk directory on Michigan.gov/Vote (mvic.sos.state.mi.us, "Your clerk": SearchByCounty then
LocalClerk for each jurisdiction), which the Bureau of Elections keeps from the Qualified Voter File. Name and title
exactly as listed. Contact: the clerk's office phone as listed; email only on the city's or township's own domain (free-mail
addresses are dropped); the office street address only for cities (a small township's listed address can be a home).
Villages are not in the directory (their elections are run by the township).
usage: mi_mvic_build.py <mi_all.json from mi_mvic_fetch.mjs> <site data/local/MI.json> <out.json>"""
import json,re,sys,os,html,datetime as dt
from bs4 import BeautifulSoup
dump,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
U='https://mvic.sos.state.mi.us/Voter/Index#yourclerk'
FREE=re.compile(r'(?i)@(gmail|yahoo|hotmail|aol|outlook|live|msn|comcast|att|sbcglobal|charter|frontier|icloud|me|mac|ymail|centurytel|tds|chartermi|juno|earthlink|protonmail|cmsinter|frontiernet|bresnan|wowway|mail)\.')
site=json.load(open(sitef,encoding='utf-8'))
cname={c['f']:re.sub(r'\s+County$','',c['n']).lower() for c in site.get('counties') or []}
def nm(s): return re.sub(r'[^a-z]','',s.lower().replace('saint ','st ').replace('st. ','st '))
IDX={}
for pid,p in site['places'].items():
    t=p.get('t')
    if t in ('city','township','charter township'):
        kind='city' if t=='city' else 'township'
        for c in p.get('c') or [cname.get('',None)]:
            IDX.setdefault((kind,nm(p['n']),cname.get(c,'')),[]).append(pid)
D=json.load(open(dump,encoding='utf-8'))
st={'jurisdictions':0,'matched':0,'unmatched':[],'no_name':0,'places_filled':0,'officials':0}
res={'st':'MI','built':TODAY,'src':{'name':'Michigan Department of State, clerk directory (Michigan.gov/Vote, mvic.sos.state.mi.us)','note':'The city or township clerk as listed by the Bureau of Elections; office phone; email only on the local government\'s own domain.'},'places':{}}
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
for ck,cv in D.items():
    soup=BeautifulSoup(cv.get('county',''),'lxml')
    h2=soup.find('h1') or soup.find('h2'); ctext=soup.get_text(' ',strip=True)
    m=re.match(r'\s*(.+?) County city/township clerks',ctext,re.I); county=(m.group(1) if m else '').lower()
    for jk,hv in cv.get('locals',{}).items():
        st['jurisdictions']+=1
        code,jname=jk.split('|',1)
        sp=BeautifulSoup(hv,'lxml'); body=sp.find('div',class_='card-body')
        if not body: continue
        lines=[x.strip() for x in body.get_text('\n').split('\n') if x.strip()]
        if not lines or ',' not in lines[0]: st['no_name']+=1; continue
        segs=[x.strip() for x in lines[0].split(',')]
        name,title=segs[0],segs[-1] if len(segs)>1 else ''
        for x in segs[1:-1]:
            if re.match(r'(?i)^(jr|sr)\.?$|^(ii|iii|iv)$',x): name+=', '+x if x.lower().startswith(('jr','sr')) else ' '+x
        if re.match(r'(?i)^other$',title): title=''
        if not name or re.search(r'(?i)vacant|tbd|unknown',name) or len(name.split())<2: st['no_name']+=1; continue
        mm=re.match(r'(?i)^(.*?)\s+(charter township|township|city|village)$',jname.strip())
        if not mm: st['unmatched'].append(jname); continue
        base,kind=mm.group(1),('city' if mm.group(2).lower()=='city' else 'township')
        if kind=='city': base=re.sub(r'(?i)^city of\s+','',base)
        pids=IDX.get((kind,nm(base),county),[])
        if len(pids)!=1:
            alt=[k for k in IDX if k[0]==kind and k[1]==nm(base)]
            pids=IDX[alt[0]] if len(alt)==1 and len(IDX[alt[0]])==1 else []
        if len(pids)!=1: st['unmatched'].append(jname+' ('+county+')'); continue
        pid=pids[0]; st['matched']+=1
        ct={}
        hi=lambda i:sp.find('input',id=i).get('value','').strip() if sp.find('input',id=i) else ''
        tx=body.get_text(' ',strip=True)
        ph=re.search(r'Phone:\s*(\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}(?:\s*(?:x|ext\.?)\s*\d+)?)',tx)
        if ph: ct['p']=[ph.group(1)]
        em=body.find('a',href=re.compile('^mailto:',re.I))
        if em:
            e=em['href'][7:].strip()
            dom=e.split('@')[-1].lower()
            w=(site['places'][pid].get('w') or '').lower()
            wd=re.sub(r'^https?://(www\.)?','',w).split('/')[0]
            own=dom.endswith('.gov') or dom.endswith('.mi.us') or (wd and (dom==wd or dom.endswith('.'+wd) or wd.endswith('.'+dom))) or nm(base)[:6] in nm(dom)
            if '@' in e and not FREE.search(e) and own: ct['e']=e
        if kind=='city' and hi('hfClerkAddress') and not re.search(r'(?i)p\.?\s*o\.?\s*box',hi('hfClerkAddress')):
            ct['a']='%s, %s'%(hi('hfClerkAddress'),re.sub(r'\s+',' ',hi('hfClerkCityStateZip')).replace(', Michigan',', MI'))
        o={'n':name,'r':title or ('City Clerk' if kind=='city' else 'Township Clerk'),'src':'mimvic','u':U,'d':TODAY}
        if ct: ct['src']=U; ct['g']=1; o['ct']=ct
        p=site['places'][pid]
        if pid in res['places']: continue
        ex=[x for x in (p.get('o') or []) if x.get('src')!='mimvic']
        if any(sameperson(o['n'],x['n']) for x in ex): continue
        res['places'][pid]={'n':p['n'],'o':ex+[o]}; st['places_filled']+=1; st['officials']+=1
st['unmatched_n']=len(st['unmatched']); st['unmatched']=st['unmatched'][:40]
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps(st))
