#!/usr/bin/env python3
"""KnowUS local officials, Maine: the municipal clerk of every Maine city, town and plantation, from the Maine Secretary of
State's "Find a Municipal Clerk or Registrar" list (maine.gov/sos, the "download this list (CSV)" file, updated 10/30/26).
Names exactly as listed. Contact: the listed work phone (the municipal office); the street address only for cities (a small
town's listed address can be a home).
usage: me_sos_build.py <FULLFILE_CVR_Clerk_Info csv> <site data/local/ME.json> <out.json>"""
import json,re,sys,os,csv,datetime as dt
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
U='https://www.maine.gov/sos/elections-voting/find-a-municipal-clerk-or-registrar'
site=json.load(open(sitef,encoding='utf-8'))
def nm(s): return re.sub(r'[^a-z]','',re.sub(r'(?i)\b(plantation|plt|twp|township|town|city|of)\b','',s.lower()))
IDX={}
for pid,p in site['places'].items():
    if p.get('t')!='CDP': IDX.setdefault(nm(p['n']),[]).append(pid)
st={'rows':0,'matched':0,'unmatched':[],'ambiguous':[],'places_filled':0}
res={'st':'ME','built':TODAY,'src':{'name':'Maine Secretary of State, Find a Municipal Clerk or Registrar (list updated 10/30/26)','note':'The municipal clerk as listed by the Secretary of State; the municipal office phone.'},'places':{}}
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
for r in csv.DictReader(open(src,encoding='utf-8-sig')):
    st['rows']+=1
    mun=(r.get('Municipality') or '').strip(); name=re.sub(r'\s+',' ',(r.get('Clerk Name') or '')).strip()
    if not mun or len(name.split())<2 or re.search(r'(?i)vacant|unorganized',name): continue
    pids=IDX.get(nm(mun),[])
    if len(pids)>1:
        plt=bool(re.search(r'(?i)\b(plt|plantation)\b',mun))
        pids=[p for p in pids if (site['places'][p].get('t')=='plantation')==plt]
    if len(pids)!=1: (st['ambiguous'] if pids else st['unmatched']).append(mun); continue
    pid=pids[0]; p=site['places'][pid]; st['matched']+=1
    ct={}
    ph=(r.get('Work Phone') or '').strip()
    if re.search(r'\d{3}\D*\d{4}',ph): ct['p']=[ph]
    a1=(r.get('Address Line 1') or '').strip()
    if p.get('t')=='city' and a1 and not re.search(r'(?i)p\.?\s*o\.?\s*box',a1): ct['a']='%s, %s'%(a1,re.sub(r'\s+',' ',r.get('CityStateZip') or ''))
    o={'n':name,'r':'Municipal Clerk','src':'mesos','u':U,'d':TODAY}
    if ct: ct['src']=U; ct['g']=1; o['ct']=ct
    if pid in res['places']: continue
    ex=[x for x in (p.get('o') or []) if x.get('src')!='mesos']
    if any(sameperson(name,x['n']) for x in ex): continue
    res['places'][pid]={'n':p['n'],'o':ex+[o]}; st['places_filled']+=1
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:40])) for k,v in st.items()}))
