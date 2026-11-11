#!/usr/bin/env python3
"""KnowUS local officials, Georgia: winners of the November 4, 2025 municipal general election and the December 2, 2025
runoffs, from the Georgia Secretary of State's official results site (app.enhancedvoting.com/results/public/Georgia, linked
from sos.ga.gov "Georgia Election Results"), county by county. A November winner needs a majority of the vote in a one-seat
race (Georgia law); otherwise the December runoff decides it. Municipal runoffs were run by the counties and are not on the
state site, so a race that went to a runoff is left out. Contests whose name does not say which city they are for are
left out too. Candidate names as
printed, with the incumbent / party markers removed. Only seats on the 2025 ballot are listed (cities elect in staggered
odd years; seats elected in 2023 are not included), so a council can show part of its members.
usage: ga_sos_build.py <site data/local/GA.json> <out.json>"""
import json,re,sys,os,collections,datetime as dt,requests,concurrent.futures as cf
sitef,out=sys.argv[1:3]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
B='https://app.enhancedvoting.com/results/public/api'
GEN='MunicipalGeneralSpecialElectionPSC11042025'; RUN='December2nd2025Runoffs'
PUB='https://app.enhancedvoting.com/results/public/%s/elections/%s'
H={'User-Agent':'Mozilla/5.0'}
def get(u):
    for k in range(3):
        try:
            r=requests.get(u,timeout=60,headers=H)
            if r.status_code==404: return None
            if r.ok: return r.json()
        except Exception: pass
    return None
site=json.load(open(sitef,encoding='utf-8'))
cname={c['f']:c['n'] for c in site.get('counties') or []}
def nm(s): return re.sub(r'[^a-z]','',s.lower())
bycounty=collections.defaultdict(list)
for pid,p in site['places'].items():
    if p.get('t') in ('city','town','village','CDP') :
        if p.get('t')=='CDP': continue
        for c in p.get('c') or []: bycounty[cname.get(c,'')].append(pid)
counties=get(B+'/jurisdictions/Georgia')['childLocalities']
def clean(n):
    n=re.sub(r'\s*\((?:I|Inc\.?|Incumbent|Rep|Dem|Lib|Ind|NP|Non-?Partisan)\)','',n,flags=re.I)
    return re.sub(r'\s+',' ',n).strip()
def place_of(contest,county):
    best=None
    for pid in bycounty.get(county,[]):
        n=site['places'][pid]['n']
        if re.search(r'(?<![A-Za-z])'+re.escape(n)+r'(?![A-Za-z])',contest,re.I) and (best is None or len(n)>len(site['places'][best]['n'])): best=pid
    return best
def role_of(contest,place):
    t=re.sub(r'(?i)\b(city|town) of\b','',contest); t=re.sub(re.escape(place),'',t,flags=re.I)
    t=re.sub(r'\s*[-–,]\s*',' - ',t).strip(' -')
    if re.search(r'(?i)\bmayor\b',t) and not re.search(r'(?i)pro\s*tem',t): return 'Mayor'
    if re.search(r'(?i)school|board of education|referend|question|sunday|sales|tax|homestead|judge|marshal|clerk|treasurer|utilit|housing|authority',t): return None
    if re.search(r'(?i)alder',t): r='Alderman'
    elif re.search(r'(?i)commission',t): r='Commissioner'
    elif re.search(r'(?i)council',t): r='Council Member'
    else: return None
    m=re.search(r'(?i)\b(post|ward|district|dist\.?|seat)\s*#?\s*(\w+)',t)
    m2=re.search(r'\bD(\d+)\b',t)
    if not m and m2: r+=', District %s'%m2.group(1); return r
    if m: r+=', %s %s'%({'dist':'District','dist.':'District'}.get(m.group(1).lower(),m.group(1).title()),m.group(2))
    elif re.search(r'(?i)at[- ]?large|\blrg\b',t): r+=', At-Large'
    return r
st={'counties':0,'contests':0,'no_place':0,'no_majority':0,'runoff_used':0,'places_filled':0,'officials':0}
def county_items(c):
    g=get('%s/elections/%s/%s/data'%(B,c['shortName'],GEN)); r=get('%s/elections/%s/%s/data'%(B,c['shortName'],RUN))
    return c,g,r
add=collections.defaultdict(list)
with cf.ThreadPoolExecutor(3) as ex:
    for c,g,r in ex.map(county_items,counties):
        if not g: continue
        st['counties']+=1; county=c['name'][0]['text']
        run={}
        for b in (r or {}).get('ballotItems',[]):
            run[nm(re.sub(r'(?i)\brun-?off\b','',b['name'][0]['text']))]=b
        for b in g['ballotItems']:
            name=b['name'][0]['text']
            if b.get('contestType')!='Candidate' or name.startswith('PSC'): continue
            pid=place_of(name,county)
            if not pid: st['no_place']+=1; st.setdefault('np',[]).append(county+': '+name); continue
            role=role_of(name,site['places'][pid]['n'])
            if not role: continue
            st['contests']+=1
            vf=int((re.search(r'\d+',(b['voteFor'] or [{'text':'1'}])[0]['text']) or ['1'])[0])
            opts=sorted([(clean(o['name'][0]['text']),o['voteCount'] or 0) for o in b['summaryResults']['ballotOptions'] if not re.search(r'(?i)write[- ]?in',o['name'][0]['text'])],key=lambda x:-x[1])
            tot=sum(v for _,v in opts)
            if not opts: continue
            win=None; src=(GEN,'November 4, 2025')
            if vf==1:
                if len(opts)==1 or opts[0][1]*2>tot: win=[opts[0][0]]
                else:
                    rb=run.get(nm(re.sub(r'(?i)\brun-?off\b','',name)))
                    if not rb: st.setdefault('runoff_missing',[]).append(county+': '+name+' | have: '+'; '.join(list(run)[:4]))
                    if rb:
                        ro=sorted([(clean(o['name'][0]['text']),o['voteCount'] or 0) for o in rb['summaryResults']['ballotOptions']],key=lambda x:-x[1])
                        if ro and (len(ro)==1 or ro[0][1]>ro[1][1]): win=[ro[0][0]]; src=(RUN,'December 2, 2025 (runoff)'); st['runoff_used']+=1
            else:
                if len(opts)<=vf or opts[vf-1][1]>opts[vf][1]: win=[n for n,_ in opts[:vf]]
            if not win: st['no_majority']+=1; continue
            for n_ in win:
                add[pid].append({'n':n_,'r':role,'rk':'gen_mayor' if role=='Mayor' else 'gen_council','src':'gasos','u':PUB%(c['shortName'],src[0]),'d':TODAY,'s':'elected %s'%src[1]})
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
res={'st':'GA','built':TODAY,'src':{'name':'Georgia Secretary of State, official results of the November 4, 2025 municipal general election and December 2, 2025 runoffs','note':'Winners of the seats on the 2025 municipal ballot (majority or runoff). Seats elected in 2023 are not included.'},'places':{}}
for pid,L in add.items():
    p=site['places'][pid]; ex_=[o for o in (p.get('o') or []) if o.get('src')!='gasos']; LL=[]
    for o in sorted(L,key=lambda o:(o['rk']!='gen_mayor',o['r'],o['n'])):
        if any(sameperson(o['n'],x['n']) for x in ex_+LL): continue
        if o['rk']=='gen_mayor' and any(x.get('rk')=='gen_mayor' for x in ex_+LL): continue
        LL.append(o)
    if not LL: continue
    res['places'][pid]={'n':p['n'],'o':ex_+LL}; st['places_filled']+=1; st['officials']+=len(LL)
st={k:(len(v) if isinstance(v,list) else v) for k,v in st.items()}
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:40])) for k,v in st.items()}))
