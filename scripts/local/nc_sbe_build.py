#!/usr/bin/env python3
"""KnowUS local officials, North Carolina: winners of the November 4, 2025 and November 7, 2023 municipal elections from
the NC State Board of Elections' official precinct results files (dl.ncsbe.gov/ENRS/<date>/results_pct_<date>.zip).
Votes are summed across precincts and counties; winners are the top vote-getters for the number of seats ("Vote For");
write-ins and ties at the cut-off are left out. Names as printed in the results.
Which election counts: a mayor from the place's most recent mayoral contest. A council / board seat from 2025; a 2023
contest is used only when the place had no contest of the same name in 2025 (then the 2023 seat runs to 2027), so a
staggered board may show only the seats elected at its latest election.
usage: nc_sbe_build.py <dir with nc_<date>.zip> <site data/local/NC.json> <out.json>"""
import json,re,sys,os,csv,io,zipfile,collections,datetime as dt
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
EL={'2025_11_04':'November 4, 2025','2023_11_07':'November 7, 2023'}
def U(d): return 'https://s3.amazonaws.com/dl.ncsbe.gov/ENRS/%s/results_pct_%s.zip'%(d,d.replace('_',''))
site=json.load(open(sitef,encoding='utf-8'))
def nm(s): return re.sub(r'[^a-z]','',s.lower().replace('saint ','st ').replace('st. ','st '))
PL={}
for pid,p in site['places'].items():
    if p.get('t') in ('city','town','village'): PL.setdefault(nm(p['n']),[]).append(pid)
st={'contests':0,'no_place':set(),'tie':0,'places_filled':0,'officials':0}
def tc(s):
    s=s.title()
    s=re.sub(r"\b(Of|And|The|At)\b",lambda m:m.group(1).lower(),s)
    return s[:1].upper()+s[1:]
def role_of(off):
    off=re.sub(r'\s*\(UNEXPIRED\)','',off).strip()
    m=re.search(r'\b(WARD|DISTRICT|SEAT|PRECINCT)\s+0*(\w+)$',off); suf=''
    if m: suf=', %s %s'%(m.group(1).title(),m.group(2).lstrip('0') or m.group(2)); off=off[:m.start()].strip()
    o=off.upper()
    if o=='MAYOR': return 'Mayor'
    if re.search(r'COMMISSIONER',o): r='Commissioner'
    elif re.search(r'ALDERM|ALDERPERSON',o): r='Alderman'
    elif re.search(r'COUNCIL',o): r='Council Member'
    else: r=tc(off)
    if re.search(r'AT[- ]LARGE',o) and not suf: suf=', At-Large'
    return r+suf
C={}   # (date, pid, contest) -> {'seats':n,'votes':Counter,'office':...}
for d in EL:
    f=os.path.join(src,'nc_%s.zip'%d)
    z=zipfile.ZipFile(f); t=z.read(z.namelist()[0]).decode('utf-8','replace')
    for r in csv.DictReader(io.StringIO(t),delimiter='\t'):
        cn=r['Contest Name'].strip()
        m=re.match(r'^(CITY|TOWN|VILLAGE) OF (.+)$',cn)
        if not m: continue
        rest=m.group(2); pid=None; office=None
        words=rest.split()
        for k in range(len(words)-1,0,-1):
            cand=nm(' '.join(words[:k]))
            if len(PL.get(cand,[]))==1:
                pid=PL[cand][0]; office=' '.join(words[k:]); break
        if not pid: st['no_place'].add(cn); continue
        if not re.search(r'MAYOR|COUNCIL|COMMISSIONER|ALDERM|ALDERPERSON|BOARD',office) or re.search(r'EDUCATION|SCHOOL|REFERENDUM|BOND|SALE|TAX',office): continue
        key=(d,pid,cn)
        c=C.setdefault(key,{'seats':int(r['Vote For'] or 1),'votes':collections.Counter(),'office':office})
        ch=r['Choice'].strip()
        if not ch or ch.lower().startswith('write-in'): continue
        c['votes'][ch]+=int(r['Total Votes'] or 0)
by=collections.defaultdict(list)
for (d,pid,cn),c in C.items():
    st['contests']+=1
    v=c['votes'].most_common(); n=c['seats']
    if not v: continue
    if len(v)>n and v[n-1][1]==v[n][1]: st['tie']+=1; continue
    win=[x for x in v[:n] if x[1]>0]
    by[pid].append((d,cn,c['office'],win))
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
res={'st':'NC','built':TODAY,'src':{'name':'NC State Board of Elections, official municipal election results, November 4, 2025 and November 7, 2023 (dl.ncsbe.gov)','note':'Mayors from the most recent mayoral contest; board seats from 2025, or from 2023 where the place held no contest of the same name in 2025. Names as printed in the results.'},'places':{}}
for pid,L in by.items():
    p=site['places'][pid]; out_=[]
    ms=[x for x in L if role_of(x[2])=='Mayor']
    if ms:
        d,cn,off,win=max(ms,key=lambda x:x[0])
        for n_,v in win[:1]: out_.append({'n':n_,'r':'Mayor','rk':'gen_mayor','src':'ncsbe','u':U(d),'d':TODAY,'s':'elected %s'%EL[d]+(' (unexpired term)' if 'UNEXPIRED' in off else '')})
    names25={re.sub(r'\s*\(UNEXPIRED\)','',cn) for d,cn,off,win in L if d=='2025_11_04'}
    for d,cn,off,win in sorted(L,key=lambda x:(x[0]!='2025_11_04',x[1])):
        if role_of(off)=='Mayor': continue
        if d=='2023_11_07' and re.sub(r'\s*\(UNEXPIRED\)','',cn) in names25: continue
        for n_,v in win:
            out_.append({'n':n_,'r':role_of(off),'rk':'gen_council','src':'ncsbe','u':U(d),'d':TODAY,'s':'elected %s'%EL[d]+(' (unexpired term)' if 'UNEXPIRED' in off else '')})
    ex=[o for o in (p.get('o') or []) if o.get('src')!='ncsbe']; LL=[]
    for o in out_:
        if any(sameperson(o['n'],x['n']) for x in ex+LL): continue
        if o['rk']=='gen_mayor' and any(x.get('rk')=='gen_mayor' for x in ex): continue
        LL.append(o)
    if not LL: continue
    res['places'][pid]={'n':p['n'],'o':ex+LL}; st['places_filled']+=1; st['officials']+=len(LL)
st['no_place']=sorted(st['no_place'])
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:30])) for k,v in st.items()}))
