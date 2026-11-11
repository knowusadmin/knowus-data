#!/usr/bin/env python3
"""KnowUS local officials, Indiana: winners of the November 7, 2023 municipal general election (mayor, city clerk /
clerk-treasurer, city common council, town clerk-treasurer, town council) from the Indiana Election Division's official
results archive (enr.indianavoters.in.gov/archive/2023General), for terms that began Jan 1, 2024. Names as printed on
the ballot (all-capital names in normal capitalization), with party. Only races that were on the ballot are listed
(many towns' uncontested offices were not), so a town can show part of its council.
usage: in_enr_build.py <site data/local/IN.json> <out.json>"""
import json,re,sys,os,datetime as dt,urllib.request
sitef,out=sys.argv[1:3]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
B='https://enr.indianavoters.in.gov/archive/2023General/'
U=B+'index.html'
CATS={'1002':('city','Mayor'),'1014':('city','clerk'),'1032':('city','council'),'1001':('town','clerk'),'1037':('town','council')}
PARTY={'R':'Republican','D':'Democratic','L':'Libertarian','I':'Independent'}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=60) as r: return json.load(r)
def nm(s): return re.sub(r'[^a-z]','',s.lower())
def tc(n):
    if not n.isupper(): return n
    def w(x):
        x=x.capitalize()
        if re.match(r"^Mc[a-z]",x): x='Mc'+x[2:].capitalize()
        if re.match(r"^O'[a-z]",x): x="O'"+x[2:].capitalize()
        if x.lower() in ('ii','iii','iv'): x=x.upper()
        if x.startswith('(') and len(x)>1: x='('+x[1:].capitalize()
        return '-'.join(y[:1].upper()+y[1:] for y in x.split('-'))
    return ' '.join(w(x) for x in n.split())
site=json.load(open(sitef,encoding='utf-8'))
P={'city':{},'town':{}}
for pid,p in site['places'].items():
    if p.get('t') in P: P[p['t']].setdefault(nm(p['n']),[]).append(pid)
st={'races':0,'matched':0,'unmatched':[],'places_filled':0,'officials':0,'ambiguous':[]}
add={}
for cid,(kind,what) in CATS.items():
    races=get(B+'data/OffCatC_%s_A.json'%cid)['Root']['StatewideSummary']['Race']
    if isinstance(races,dict): races=[races]
    for r in races:
        title=re.sub(r'\s+',' ',r['OFFICE_TITLE']).strip()
        if re.search(r'(?i)ordinance|referend|question|judge',title): continue
        st['races']+=1
        low=' '+re.sub(r'(?i)\bmt\.?\s',' mount ',title.lower())+' '
        best=None
        for key,pids in P[kind].items():
            for pid in pids:
                n=site['places'][pid]['n'].lower()
                if re.search(r'(?<![a-z])'+re.escape(n)+r'(?![a-z])',low) and (best is None or len(n)>len(site['places'][best[0]]['n'])): best=(pid,pids)
        if not best:
            for key,pids in P['town' if kind=='city' else 'city'].items():
                for pid in pids:
                    n=site['places'][pid]['n'].lower()
                    if re.search(r'(?<![a-z])'+re.escape(n)+r'(?![a-z])',low) and (best is None or len(n)>len(site['places'][best[0]]['n'])): best=(pid,pids)
        if not best: st['unmatched'].append(title); continue
        if len(best[1])>1: st['ambiguous'].append(title); continue
        pid=best[0]; st['matched']+=1
        c=r['Candidates']['Candidate']; c=c if isinstance(c,list) else [c]
        dist=''
        m=re.search(r'(?i)(ward|district|dist\.?)\s*(\d+)',title) or re.search(r'(?i)council\s+(\d+)$',title)
        if m: dist=('Ward ' if m.group(0).lower().startswith('ward') else 'District ')+m.group(m.lastindex)
        elif re.search(r'(?i)at[- ]large',title): dist='At-Large'
        if what=='Mayor': role='Mayor'
        elif what=='clerk': role='Clerk-Treasurer' if re.search(r'(?i)treas',title) else ('City Clerk' if kind=='city' else 'Clerk-Treasurer')
        else: role=('City Council Member' if kind=='city' else 'Town Council Member')+(', '+dist if dist else '')
        for x in c:
            if x.get('isWinner')!='T': continue
            name=tc(re.sub(r'\s+',' ',x['NAME_ON_BALLOT']).strip())
            if len(name.split())<2: continue
            o={'n':name,'r':role,'src':'inenr','u':U,'d':TODAY,'s':'elected November 7, 2023'}
            if what=='Mayor': o['rk']='gen_mayor'
            elif what=='council': o['rk']='gen_council'
            if x.get('PARTY') in PARTY: o['p']=PARTY[x['PARTY']]
            add.setdefault(pid,[]).append(o)
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
res={'st':'IN','built':TODAY,'src':{'name':'Indiana Election Division, official results of the November 7, 2023 municipal general election (enr.indianavoters.in.gov)','note':'Winners of the 2023 municipal election, whose terms began January 1, 2024; names as on the ballot. Uncontested offices that were not on the ballot are not listed.'},'places':{}}
# Mayors are checked against the city's own website (the site file's 'w'): a 2023 winner whose last name does not appear on
# the city's home page (or its /mayor page) while the page names a different "Mayor <Name>" is left out, so a mayor who
# died, resigned or was replaced mid-term (e.g. Fort Wayne, 2024) is not shown. Otherwise the election result stands.
import concurrent.futures as cf
def page_text(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120'}),timeout=20) as r:
            return r.read(2_000_000).decode('utf-8','replace')
    except Exception as e: return None
STOP={'city','town','clerk','attorney','departments','department','welcome','revives','treasurer','office','council','court','pro','tem','and','of','the','news','message','updates','page','board','services','contact','staff','government','about','home','meet','mayors'}
def mayor_ok(pid,o):
    w=site['places'][pid].get('w')
    if not w: return pid,o,'no_site'
    last=nm(o['n'].split()[-1] if not re.match(r'(?i)^(jr|sr|ii|iii|iv)\.?$',o['n'].split()[-1]) else o['n'].split()[-2])
    texts=[t for t in (page_text(w), page_text(w.rstrip('/')+'/mayor')) if t]
    if not texts: return pid,o,'site_unreachable'
    if any(last in nm(re.sub(r'<[^>]+>',' ',t)) for t in texts): return pid,o,'ok'
    other=set()
    for t in texts:
        tx=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',t))
        for m in re.finditer(r'Mayor\s+([A-Z][a-z]+(?:\s[A-Z]\.)?\s[A-Z][a-zA-Z\'\-]+)',tx):
            cand=m.group(1); ws=cand.split()
            if any(w_.lower() in STOP for w_ in ws) or nm(ws[0])==nm(o['n'].split()[0]) or nm(cand).startswith(nm(site['places'][pid]['n'])): continue
            other.add(cand)
    return pid,o,('other_mayor_on_site:'+'|'.join(sorted(other)[:3]) if other else 'name_not_found_kept')
jobs=[(pid,o) for pid,Lx in add.items() for o in Lx if o.get('rk')=='gen_mayor']
st['mayor_check']={}
with cf.ThreadPoolExecutor(3) as ex_:
    for pid,o,v in ex_.map(lambda a: mayor_ok(*a), jobs):
        k=v.split(':')[0]; st['mayor_check'][k]=st['mayor_check'].get(k,0)+1
        if k=='other_mayor_on_site':
            add[pid].remove(o); st.setdefault('mayor_dropped',[]).append(site['places'][pid]['n']+': '+o['n']+' (site: '+v.split(':',1)[1]+')')
# Known mid-term changes, each from the city's own website: the 2023 winner is replaced.
OVERRIDE={'Fort Wayne':{'drop':['Thomas C Henry','Sharon Tucker'],'add':[{'n':'Sharon Tucker','r':'Mayor','rk':'gen_mayor','src':'inenr','p':'Democratic',
  'u':'http://cityoffortwayne.org/CivicAlerts.aspx?AID=770','d':TODAY,'s':'sworn in April 23, 2024 after Mayor Tom Henry died (engage.cityoffortwayne.org/24in2024)'}]}}
for pid in list(add):
    ov=OVERRIDE.get(site['places'][pid]['n'])
    if ov and site['places'][pid].get('t')=='city':
        add[pid]=ov['add']+[o for o in add[pid] if o['n'] not in ov['drop']]
ORD={'Mayor':0,'City Clerk':1,'Clerk-Treasurer':1}
for pid,L in add.items():
    p=site['places'][pid]; ex=[o for o in (p.get('o') or []) if o.get('src')!='inenr']
    seen=[]; LL=[]
    for o in sorted(L,key=lambda o:(ORD.get(o['r'],2),o['r'],o['n'])):
        if any(sameperson(o['n'],s) for s in seen) or any(sameperson(o['n'],e['n']) for e in ex): continue
        if o.get('rk')=='gen_mayor' and any(e.get('rk')=='gen_mayor' for e in ex): continue
        seen.append(o['n']); LL.append(o)
    if not LL: continue
    res['places'][pid]={'n':p['n'],'o':ex+LL}; st['places_filled']+=1; st['officials']+=len(LL)
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:20])) for k,v in st.items()}))
