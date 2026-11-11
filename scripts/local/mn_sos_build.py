#!/usr/bin/env python3
"""KnowUS local officials, Minnesota: winners of city and town (township) offices in the Minnesota Secretary of State's
official election results files (electionresultsfiles.sos.mn.gov/<date>/local.txt) for the November general elections of
2022, 2023, 2024 and 2025. Names as printed in the results. Winners are the top vote-getters for the number of seats
("Elect N"); write-ins, ties at the cut-off and ranked-choice races (Minneapolis, St. Paul, etc., whose first-choice
counts do not decide the winner) are left out.
Which election counts: a mayor comes from the city's most recent mayoral race (a 2-year mayor elected in 2022 was
re-elected or replaced in 2024, so the latest race is the sitting term). Council members, township supervisors, clerks and
treasurers come only from each place's most recent general election in 2024 or 2025 (their terms run at least two years from
January), so a council shows the seats filled at that election and not the staggered seats from earlier years. March
township elections are not in these files.
usage: mn_sos_build.py <dir with mn_local_<date>.txt> <site data/local/MN.json> <out.json>"""
import json,re,sys,os,csv,datetime as dt,collections
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
DATES={'20221108':'November 8, 2022','20231107':'November 7, 2023','20241105':'November 5, 2024','20251104':'November 4, 2025'}
def U(d): return 'https://electionresultsfiles.sos.mn.gov/%s/local.txt'%d
site=json.load(open(sitef,encoding='utf-8'))
byfips={}
for pid,p in site['places'].items():
    if p.get('t') in ('city','township'): byfips.setdefault(pid[-5:],[]).append(pid)
def nm(s): return re.sub(r'[^a-z]','',s.lower())
st={'races':0,'rcv_skipped':0,'tie_skipped':0,'no_place':0,'places_filled':0,'officials':0}
races={}   # (pid, office_norm) -> list of (date, title, seats, [(name,votes)])
for d in sorted(DATES):
    f=os.path.join(src,'mn_local_%s.txt'%d)
    if not os.path.exists(f): continue
    R=collections.OrderedDict()
    for row in csv.reader(open(f,encoding='latin-1'),delimiter=';'):
        if len(row)<16: continue
        R.setdefault((row[3],row[4],row[5]),[]).append(row)
    for (oid,title,fips),rs in R.items():
        if re.search(r'(?i)question|hospital|school|park|sanitary|water|board member|commissioner|lake improvement',title): continue
        st['races']+=1
        if re.search(r'(?i)first choice|second choice|third choice|choice',title): st['rcv_skipped']+=1; continue
        pids=byfips.get(fips,[])
        place=re.search(r'\(([^()]+)\)',title); place=place.group(1) if place else ''
        pids=[p for p in pids if nm(site['places'][p]['n'])==nm(re.sub(r'(?i)\s+(township|unorg).*$','',place))] or ([pids[0]] if len(pids)==1 else [])
        if len(pids)!=1: st['no_place']+=1; continue
        pid=pids[0]
        seats=int((re.search(r'\(Elect (\d+)\)',title) or [0,1])[1])
        cands=sorted([(r[7].strip(),int(r[13] or 0)) for r in rs if r[10]!='WI' and r[7].strip().upper()!='WRITE-IN' and r[7].strip()],key=lambda x:-x[1])
        if not cands: continue
        if len(cands)>seats and cands[seats-1][1]==cands[seats][1]: st['tie_skipped']+=1; continue
        win=[c for c in cands[:seats] if c[1]>0]
        base=re.sub(r'\s*\([^()]*\)','',title).strip()
        base=re.sub(r'(?i)^special election for\s+','',base)
        races.setdefault(pid,[]).append((d,base,win,title))
res={'st':'MN','built':TODAY,'src':{'name':'Minnesota Secretary of State, official results of the 2022-2025 November general elections, city and township offices (electionresultsfiles.sos.mn.gov)','note':'Mayors from each city\'s most recent mayoral race; other offices from the place\'s most recent general election in 2024 or 2025. Names as printed in the results. Ranked-choice races are not included.'},'places':{}}
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
def tc(n):
    if not n.isupper(): return n
    return ' '.join(w[:1]+w[1:].lower() if not re.match(r'^(II|III|IV|JR\.?|SR\.?)$',w) else (w if len(w)<=3 and w.startswith('I') else w.capitalize()) for w in n.split())
for pid,rl in races.items():
    p=site['places'][pid]; L=[]
    mayor=[x for x in rl if re.match(r'(?i)mayor$',x[1])]
    if mayor:
        d,base,win,title=max(mayor,key=lambda x:x[0])
        for n_,v in win: L.append({'n':tc(n_),'r':'Mayor','rk':'gen_mayor','src':'mnsos','u':U(d),'d':TODAY,'s':'elected %s'%DATES[d]})
    rest=[x for x in rl if not re.match(r'(?i)mayor$',x[1]) and x[0]>='20241105']
    if rest:
        last=max(x[0] for x in rest)
        for d,base,win,title in [x for x in rest if x[0]==last]:
            role=re.sub(r'(?i)\bat large\b','At Large',base)
            for n_,v in win:
                o={'n':tc(n_),'r':role,'src':'mnsos','u':U(d),'d':TODAY,'s':'elected %s'%DATES[d]}
                if re.search(r'(?i)council|supervisor',role): o['rk']='gen_council'
                L.append(o)
    ex=[o for o in (p.get('o') or []) if o.get('src')!='mnsos']
    LL=[]
    for o in L:
        if any(sameperson(o['n'],x['n']) for x in ex+LL): continue
        if o.get('rk')=='gen_mayor' and any(x.get('rk')=='gen_mayor' for x in ex): continue
        LL.append(o)
    if not LL: continue
    res['places'][pid]={'n':p['n'],'o':ex+LL}; st['places_filled']+=1; st['officials']+=len(LL)
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps(st))
