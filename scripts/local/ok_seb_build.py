#!/usr/bin/env python3
"""KnowUS local officials, Oklahoma: winners of contested municipal elections (mayor, council / commission / trustees,
clerk, treasurer) from the Oklahoma State Election Board's official results (results.okelections.gov, "Results by entity
and office for all local races"), February 2025 through April 2026 (Tulsa: August/November 2024, its current terms). Oklahoma leaves unopposed candidates off the ballot,
so only seats that were contested appear; a place's other seats stay empty. Winners = top vote-getters for the number of
seats; a single-seat contest whose leader had 50% or less is used only from a general/runoff date (Mar/Apr/May/Sep/Nov),
never from a primary date. The latest contest for the same office replaces older ones. June-November 2026 winners are left
out (they take office in December or later). Names in normal capitalization.
usage: ok_seb_build.py <dir with <YYYYMMDD>.json> <site data/local/OK.json> <out.json>"""
import json,re,sys,os,glob,collections,datetime as dt
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
def U(d): return 'https://results.okelections.gov/OKER/?elecDate=%s'%d
def lab(d): return dt.date(int(d[:4]),int(d[4:6]),int(d[6:])).strftime('%B %-d, %Y')
site=json.load(open(sitef,encoding='utf-8')); P=site['places']
def nz(s): return re.sub(r'[^a-z]','',s.lower())
PL={}
for pid,p in P.items():
    if p.get('t')!='CDP': PL.setdefault(nz(p['n']),[]).append(pid)
NUM={'ONE':'1','TWO':'2','THREE':'3','FOUR':'4','FIVE':'5','SIX':'6','SEVEN':'7','EIGHT':'8','NINE':'9','TEN':'10'}
def tc(n):
    o=[]
    for x in n.split():
        if re.match(r'^(II|III|IV|JR\.?|SR\.?)$',x,re.I): o.append(x.upper() if x.upper().startswith('I') else x.capitalize()); continue
        if re.match(r'^[A-Z]\.?$',x): o.append(x); continue
        x='-'.join(y[:1].upper()+y[1:].lower() if not re.match(r"^Mc[A-Z]",y) else y for y in x.split('-'))
        if re.match(r"^Mc[a-z]",x): x='Mc'+x[2:].capitalize()
        if re.match(r"^O'[a-z]",x): x="O'"+x[2:].capitalize()
        o.append(x)
    return ' '.join(o)
def role_of(title):
    t=re.sub(r'^\s*FOR\s+','',title.upper()); t=re.sub(r'\s+',' ',t).strip()
    unexp='UNEXPIRED' in t; t=re.sub(r'\(?\s*UNEXPIRED TERM\s*\)?','',t).strip(' ,')
    for w,n in NUM.items(): t=re.sub(r'\b%s\b'%w,n,t)
    suf=[]
    for k,lb in (('WARD','Ward'),('DISTRICT','District'),('SEAT','Seat'),('POSITION','Position'),('OFFICE','Office'),('PLACE','Place')):
        m=re.search(r'\b%s\s*(?:NO\.?\s*)?#?\s*([0-9A-Z]{1,3})\b'%k,t)
        if m: suf.append('%s %s'%(lb,m.group(1)))
    m=re.search(r'\b(?:NO\.|NUMBER|#)\s*(\d+)\b',t)
    if m and not suf: suf.append('Seat %s'%m.group(1))
    if re.search(r'AT[- ]LARGE',t): suf.append('At-Large')
    if re.search(r'\bVICE[- ]MAYOR\b',t): base='Vice Mayor'; rk='gen_council'
    elif re.search(r'\bMAYOR\b',t): base='Mayor'; rk='gen_mayor'
    elif re.search(r'COUNCIL|ALDERM',t): base='Council Member'; rk='gen_council'
    elif re.search(r'COMMISSION',t): base='Commissioner'; rk='gen_council'
    elif re.search(r'TRUSTEE',t): base='Trustee'; rk='gen_council'
    elif re.search(r'CLERK',t) and re.search(r'TREASURER',t): base='Clerk-Treasurer'; rk=None
    elif re.search(r'CLERK',t): base='Clerk'; rk=None
    elif re.search(r'TREASURER',t): base='Treasurer'; rk=None
    else: return None
    if rk=='gen_mayor' and suf: return None
    return (base+(', '+', '.join(suf) if suf else '')),rk,unexp
st={'contests':0,'no_place':set(),'tie':0,'primary_no_majority':0,'places_filled':0,'officials':0}
C={}
for f in sorted(glob.glob(os.path.join(src,'2*.json'))):
    d=os.path.basename(f)[:8]
    if d>='20260601': continue
    if d<'20250201' and d not in ('20240827','20241105'): continue
    j=json.load(open(f,encoding='utf-8'))
    res={r['raceID']:r for r in j['results']}
    for r in j['races']:
        ent=r['entityDesc'].upper()
        m=re.match(r'^(CITY|TOWN) OF (.+?)(\s+\d+)?$',ent.strip())
        if not m: continue
        c_=PL.get(nz(m.group(2)),[])
        if len(c_)!=1: st['no_place'].add(ent); continue
        pid=c_[0]
        title=r['raceTitle'].upper().replace(ent.strip(),'')
        title=re.sub(r'\s+(CITY|TOWN) OF\s+.*$','',title)
        ro=role_of(title)
        if not ro or re.search(r'PROPOSITION|QUESTION|RECALL',title): continue
        role,rk,unexp=ro
        if d<'20250201' and nz(P[pid]['n'])!='tulsa': continue
        rr=res.get(r['raceID'])
        if not rr: continue
        votes=[(cn['candName'],x['totalVotes']) for cn,x in zip(r['raceCandidates'],rr['candResults'])]
        C[(pid,role)]=max(C.get((pid,role),(None,'')),( {'d':d,'role':role,'rk':rk,'unexp':unexp,'n':int(r['voteFor'] or 1),'votes':votes},d),key=lambda x:x[1])
by=collections.defaultdict(list)
for (pid,role),(c,d) in C.items():
    st['contests']+=1
    v=sorted([x for x in c['votes'] if x[1]>0 and not re.search(r'(?i)write',x[0])],key=lambda x:-x[1]); n=c['n']; tot=sum(x[1] for x in c['votes'])
    if not v: continue
    if len(v)>n and v[n-1][1]==v[n][1]: st['tie']+=1; continue
    if n==1 and v[0][1]*2<=tot and d[4:6] not in ('03','04','05','09','11'): st['primary_no_majority']+=1; continue
    by[pid].append((c,[x[0] for x in v[:n]]))
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nz(a[-1])==nz(b[-1]) and nz(a[0])[:1]==nz(b[0])[:1]
res={'st':'OK','built':TODAY,'src':{'name':'Oklahoma State Election Board, official municipal election results, February 2025 - April 2026; Tulsa 2024 (results.okelections.gov)','note':'Winners of contested municipal races; Oklahoma does not put unopposed candidates on the ballot, so uncontested seats are not listed. Names as printed in the results, in normal capitalization.'},'places':{}}
ORD={'gen_mayor':0,'gen_council':1,None:2}
for pid,L in by.items():
    p=P[pid]; outl=[]
    for c,w in sorted(L,key=lambda x:(ORD[x[0]['rk']],x[0]['role'])):
        for n_ in w:
            o={'n':tc(n_),'r':c['role'],'src':'okseb','u':U(c['d']),'d':TODAY,'s':'elected %s'%lab(c['d'])+(' (unexpired term)' if c['unexp'] else '')}
            if c['rk']: o['rk']=c['rk']
            if any(sameperson(o['n'],x['n']) for x in outl): continue
            outl.append(o)
    ex=[o for o in (p.get('o') or []) if o.get('src')!='okseb']; LL=[]
    for o in outl:
        if any(sameperson(o['n'],x['n']) for x in ex+LL): continue
        if o.get('rk')=='gen_mayor' and any(x.get('rk')=='gen_mayor' for x in ex): continue
        LL.append(o)
    if not LL: continue
    res['places'][pid]={'n':p['n'],'o':ex+LL}; st['places_filled']+=1; st['officials']+=len(LL)
st['no_place']=sorted(st['no_place'])
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:40])) for k,v in st.items()}))
