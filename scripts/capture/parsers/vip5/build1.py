# Generalized from scripts/ballots/nc (KnowUS v49 NC pipeline) for any VIP 5 CSV feed captured by scripts/capture.
# Env: VIP_WORK (work dir), VIP_FEED (feed zip). Optional: VIP_RESULTS (canvass zip, post-election only), VIP_REFS (referendum PDFs, comma-separated).

import json,os,re,io,zipfile,gzip,collections,unicodedata,datetime
import pandas as pd
NC=os.environ.get('VIP_WORK') or os.getcwd()
VZ=zipfile.ZipFile(os.environ['VIP_FEED'])
_names={n.rsplit('/',1)[-1]:n for n in VZ.namelist()}
def df(n): return pd.read_csv(io.BytesIO(VZ.read(_names[n])),dtype=str,encoding='utf-8-sig',keep_default_na=False).apply(lambda s:s.str.strip())
P=df('precinct.txt'); CC=df('candidate_contest.txt'); BM=df('ballot_measure_contest.txt'); CS=df('candidate_selection.txt'); CA=df('candidate.txt')
ED=df('electoral_district.txt'); PA=df('party.txt'); BMS=df('ballot_measure_selection.txt'); LOC=df('locality.txt')
HAVE_RESULTS=bool(os.environ.get('VIP_RESULTS'))
if HAVE_RESULTS:
    _rz=zipfile.ZipFile(os.environ['VIP_RESULTS'])
    R=pd.read_csv(_rz.open([n for n in _rz.namelist() if n.endswith('.txt')][0]),sep='\t',dtype=str,keep_default_na=False)
else:  # before the election: no canvass yet; precinct checks are skipped (styles still have to match a printed ballot)
    R=pd.DataFrame(columns=['Contest Name','Real Precinct','County','Precinct','Choice','Vote For'])
R['CN']=R['Contest Name'].str.upper().str.strip()
Ry=R[R['Real Precinct']=='Y']
party={r.id:r.name.title() for r in PA.itertuples()}
edtype=dict(zip(ED.id,ED.type))
P['county']=P.locality_id.map(dict(zip(LOC.id,LOC.name.str.replace(r'(?i)\s+(COUNTY|PARISH)\b.*$','',regex=True))))
# ---- referendum texts with punctuation (official referendum list PDF)
import subprocess
reft={}
for fn in [x for x in os.environ.get('VIP_REFS','').split(',') if x]:
    t=subprocess.run(['timeout','-k','5','60','pdftotext','-layout',fn,'-'],capture_output=True,text=True,timeout=70).stdout
    county='*';title=None;buf=None;mode=None
    for ln in t.splitlines():
        s=ln.strip()
        if not s: 
            if buf is not None and mode=='For': reft.setdefault((county,title),' '.join(buf)); buf=None
            continue
        if re.match(r'^(CONT_CAND|Page \d|[A-Z][a-z]{2} \d\d, \d{4})',s) or 'BOARD OF ELECTIONS' in s or s.startswith('REFERENDUM CHOICES') or s.startswith('CRITERIA') or s.startswith('CHOICE'): continue
        m=re.match(r'^(For|Against|Yes|No)\s{2,}(.*)$',s)
        if m:
            if buf is not None and mode=='For': reft.setdefault((county,title),' '.join(buf))
            mode=m.group(1); buf=[m.group(2)] if mode in('For','Yes') else None; continue
        if buf is not None and ln.startswith(' '*20): buf.append(s); continue
        if buf is not None and mode=='For': reft.setdefault((county,title),' '.join(buf)); buf=None
        if s.isupper() and len(s.split())<=3 and not any(ch.isdigit() for ch in s) and 'AMENDMENT' not in s and 'REFERENDUM' not in s and 'ELECTION' not in s and 'BONDS' not in s:
            county=s; continue
        title=s.upper(); mode=None
def rtext(county,title):
    return reft.get((county,title)) or reft.get(('*',title))
# ---- contests
csel=CS.set_index('id'); cand=CA.set_index('id')
res_names=collections.defaultdict(set)
for cn,ch in zip(R.CN,R['Choice'].str.strip()): res_names[cn].add(ch)
def nz(s): return re.sub(r'[^A-Z0-9]','',unicodedata.normalize('NFKD',s).upper())
ACR={'NC','US','ABC','II','III','IV','ID'}
SMALL={'of','and','the','for','to','in','at','on'}
def tc(s):
    out=[]
    for i,w in enumerate(s.split()):
        u=w.upper()
        if u in ACR or re.match(r'^\d+[A-Z]?$',u): out.append(u)
        elif re.match(r'^\d',w): out.append(w.upper())
        elif i>0 and w.lower() in SMALL: out.append(w.lower())
        else: out.append('-'.join(x[:1].upper()+x[1:].lower() for x in w.split('-')))
    s=' '.join(out); s=re.sub(r'\((\w)',lambda m:'('+m.group(1).upper(),s); return s
def nm_print(title,nm):
    rs=res_names.get(title.upper(),set())
    if nm in rs: return nm
    k=nz(nm)
    for x in rs:
        if nz(x)==k: return x
    return nm
contests={}
for r in CC.itertuples():
    cs=[]
    for s in r.ballot_selection_ids.split():
        seq=int(csel.loc[s,'sequence_order'] or 0)
        for c in csel.loc[s,'candidate_ids'].split():
            fn=nm_print(r.ballot_title,cand.loc[c,'ballot_name'])
            m=re.match(r'^(.*?) \(for (.+)\)$',fn)
            cs.append((seq,m.group(2) if m else fn,party.get(cand.loc[c,'party_id'],''),fn if m else None))
    cs.sort(key=lambda x:x[0])
    notes=['The State Board of Elections lists this choice as \u201c%s\u201d.'%x[3] for x in cs if x[3]]
    vf=r.votes_allowed or r.number_elected or '1'
    contests[r.id]={'k':'c','t':r.ballot_title.upper(),'o':tc(r.ballot_title),'vf':int(vf),'c':[[n,p] for _,n,p,_ in cs],'notes':notes,'seq':int(r.sequence_order or 0),'ed':r.electoral_district_id}
for r in BM.itertuples():
    sels=[BMS.set_index('id').loc[s] for s in r.ballot_selection_ids.split()]
    sels=sorted(sels,key=lambda x:int(x.sequence_order or 0))
    contests[r.id]={'k':'m','t':r.ballot_title.upper(),'o':tc(r.ballot_title),'q':r.full_text,'resp':[x.selection for x in sels],'seq':int(r.sequence_order or 0),'ed':r.electoral_district_id}
ed2c=collections.defaultdict(list)
for cid,c in contests.items(): ed2c[c['ed']].append(cid)
P['cset']=P.electoral_district_ids.apply(lambda s: tuple(sorted(c for e in s.split() for c in ed2c.get(e,[]))))
# ---- results: contests per precinct; write-in-only contests absent from the feed
rp=Ry.groupby(['County','Precinct']).CN.apply(set).to_dict()
title2ids=collections.defaultdict(list)
for cid,c in contests.items(): title2ids[c['t']].append(cid)
problems=[]; added={}
for (co,pr),names in rp.items():
    for n in names:
        if n not in title2ids:
            vid='wi_'+re.sub(r'\W+','_',co+'_'+n)[:80]
            if vid not in contests:
                vf=R[(R.CN==n)]['Vote For'].iloc[0]
                contests[vid]={'k':'c','t':n,'o':tc(n),'vf':int(vf or 1),'c':[],'seq':None,'ed':None,'wio':True}
            added.setdefault(vid,set()).add((co,pr))
# attach write-in-only contests to splits
P['extra']=[() for _ in range(len(P))]
allpr=collections.defaultdict(set)
for (co,pr) in rp: allpr[co].add(pr)
for vid,prs in added.items():
    cos={c for c,_ in prs}
    if len(cos)==1 and {p for _,p in prs}==allpr[next(iter(cos))]:
        co=next(iter(cos))
        for i in P.index[P.county==co]: P.at[i,'extra']=P.at[i,'extra']+(vid,)
        continue
    for co,pr in prs:
        idx=P.index[(P.county==co)&(P.number==pr)]
        sets=P.loc[idx,'cset'].map(set)
        if len(set(P.loc[idx,'cset']))==1:
            for i in idx: P.at[i,'extra']=P.at[i,'extra']+(vid,)
        else:
            # municipal write-in contest: attach to the splits that carry the same municipality's other contests
            m=re.match(r'^((?:TOWN|CITY|VILLAGE) OF [A-Z .\-]+?) (MAYOR|COUNCIL|COMMISSIONER|ALDERM)',contests[vid]['t'])
            hit=[]
            if m:
                pre=m.group(1)
                hit=[i for i in idx if any(contests[c]['t'].startswith(pre+' ') for c in P.at[i,'cset'])]
            if hit:
                for i in hit: P.at[i,'extra']=P.at[i,'extra']+(vid,)
            else:
                problems.append(('unplaced write-in-only contest',co,pr,contests[vid]['t']))
                for i in idx: P.at[i,'bad']=True
P['full']=P.apply(lambda r: tuple(sorted(r.cset+r.extra)),axis=1)
# precinct check: union of splits == results
pchk={}
for (co,pr),g in P.groupby(['county','number']):
    u=set(contests[c]['t'] for s in g.full for c in s)
    r_=rp.get((co,pr))
    if not HAVE_RESULTS: pchk[(co,pr)]=None; continue
    pchk[(co,pr)]=(r_ is not None and u==r_)
    if not pchk[(co,pr)]: problems.append(('precinct contests differ from canvassed results',co,pr,sorted((r_ or set())^u)[:4]))
json.dump({'contests':contests,'splits':P[['id','county','number','name','precinct_split_name','full']].assign(full=P.full.map(list)).to_dict('records'),
  'pchk':{f'{k[0]}|{k[1]}':v for k,v in pchk.items()},'problems':problems,'reft_n':len(reft)},open(f'{NC}/stage1.json','w'))
print('contests',len(contests),'added write-in-only',len(added),'splits',len(P),'precinct ok',sum(bool(v) for v in pchk.values()),'/',len(pchk),'problems',len(problems),'reftexts',len(reft),flush=True)
for p in problems[:20]: print(p)
