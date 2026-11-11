#!/usr/bin/env python3
"""KnowUS local officials, New Mexico: elected municipal officials (mayor, councilors / trustees / commissioners,
municipal judges) from the NM Secretary of State's official election results (electionresults.sos.nm.gov, "Media/Results
Exports" CSV): 2023 and 2025 Regular Local Elections (with their recounts and the Albuquerque runoffs), and the March 2024
and March 2026 Municipal Officers Elections (with the April 2024 Rio Rancho runoff). Plus the municipal clerk and the
municipal office contact for the cities, towns and villages on the SOS "Municipal Clerk Information" page.
Winners = the top vote-getters for the number of seats ("VoteFor"); a later recount or runoff of the same contest replaces
it; ties at the cut-off are left out; ranked-choice cities (Santa Fe, Las Cruces) only where the winner had a first-round
majority. Which election counts: the mayor from the place's latest mayoral contest; a district seat from its latest
contest; at-large seats (staggered 4-year terms) from the latest two cycles unless the same person or a 2-year term.
Names in normal capitalization (the results print them in capitals).
usage: nm_sos_build.py <dir with <eid>_STATE.csv + nm_sos_clerks.json> <site data/local/NM.json> <out.json>"""
import json,re,sys,os,csv,io,collections,unicodedata,datetime as dt
from urllib.parse import urlparse
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
# eid: (date label, cycle, kind, overrides)
EL={2858:('November 7, 2023','rle23','base'),2860:('December 4, 2023 (recount)','rle23','recount'),2859:('December 12, 2023 (Albuquerque runoff)','rle23','runoff'),
    2863:('March 5, 2024','moe24','base'),2877:('April 9, 2024 (Rio Rancho runoff)','moe24','runoff'),
    2897:('November 4, 2025','rle25','base'),2899:('December 2, 2025 (recount)','rle25','recount'),2898:('December 9, 2025 (Albuquerque runoff)','rle25','runoff'),
    2901:('March 3, 2026','moe26','base')}
ORDER={'rle23':1,'moe24':2,'rle25':3,'moe26':4}
def U(e): return 'https://electionresults.sos.nm.gov/Default.aspx?eid=%d'%e
CLU='https://www.sos.nm.gov/voting-and-elections/voter-information-portal-nmvote-org/municipal-clerk-information/'
site=json.load(open(sitef,encoding='utf-8')); P=site['places']
def nz(s):
    s=unicodedata.normalize('NFKD',s); s=''.join(c for c in s if not unicodedata.combining(c)); return re.sub(r'[^a-z]','',s.lower())
PLX={}
for pid,p in P.items():
    if p.get('t')!='CDP': PLX.setdefault(nz(p['n']),[]).append(pid)
def one(n): c=PLX.get(nz(n)); return c[0] if c and len(c)==1 else None
MANUAL={'MUNICIPAL DISTRICT 212':'Columbus','MUNICIPAL DISTRICT 113':'Deming','MUNICIPAL DISTRICT 031':'Mosquero','ALAMO CITY DISTRICT- ALL':'Alamogordo'}
STOP={'CITY','OF','TOWN','VILLAGE','MUNICIPAL','MUNICIPALITY','DISTRICT','COUNCIL','AT','LARGE','ALL','WARD','POSITION','COMM','COMMISSION','DIST'}
def area_place(a,rn):
    a0=a.strip().upper()
    if a0 in MANUAL: return one(MANUAL[a0])
    if re.match(r'^CITY COMM(ISSION)?\s+DIST',a0):
        if 'QUAY' in rn.upper(): return one('Tucumcari')
        if 'CURRY' in rn.upper(): return one('Clovis')
    a1=re.sub(r'\(CITY\)','',a0.replace('Ñ','N'))
    for cand in (a1,re.sub(r'^(CITY|TOWN|VILLAGE) OF ','',a1)):
        w=re.sub(r'[^A-Z ]',' ',cand).split()
        for k in range(len(w),0,-1):
            p=one(' '.join(w[:k]))
            if p: return p
    w=[x for x in re.sub(r'[^A-Z ]',' ',a1).split() if x not in STOP]
    for k in range(len(w),0,-1):
        p=one(' '.join(w[:k]))
        if p: return p
    return None
def tc(n):
    out=[]
    for x in n.split():
        if re.match(r'^(II|III|IV|JR\.?|SR\.?)$',x): out.append(x if x.startswith('I') else x.capitalize()); continue
        x='-'.join(y.capitalize() for y in x.split('-'))
        if re.match(r"^Mc[a-z]",x): x='Mc'+x[2:].capitalize()
        if re.match(r"^O'[a-z]",x): x="O'"+x[2:].capitalize()
        out.append(x)
    return ' '.join(out)
NONMUNI=re.compile(r'SCHOOL|COLLEGE|BOARD MEMBER|COUNTY COMMISSION|SOIL|HOSPITAL|FLOOD|PROBATE|MAGISTRATE|DISTRICT JUDGE|DISTRICT COURT|METROPOLITAN|COURT OF APPEALS|SUPREME|EDUCATION|REGULATION|CONSERVANCY|WATER|SANITATION|ZONING|TAX INCREMENT|IMPROVEMENT|SHALL|QUESTION|BOND',re.I)
def role_of(rn,area):
    r=re.sub(r'\s+-\s+[A-Za-z /]+(\s+-\s+[A-Za-z ]+)?$','',rn).strip()
    R=r.upper(); A=area.upper().strip(); dist=''
    m=re.search(r'\b(?:DISTRICT|POSITION|WARD)\s*0*(\d+)\b',R)
    if m and not re.search(r'POSITION 1 AND POSITION 2',R): dist=m.group(1)
    term2=bool(re.search(r'2[- ]YEAR|UNEXPIRED',R))
    if re.search(r'MAYOR',R): return 'Mayor','gen_mayor',None,term2,None
    if re.search(r'JUDGE',R): return 'Municipal Judge',None,None,term2,None
    if re.search(r'TRUSTEE',R): base='Trustee'
    elif re.search(r'COMMISSION|\bCOMM\b',R+' '+A) and not re.search(r'TRUSTEE',R): base='Commissioner'
    elif re.search(r'COUNCIL',R): base='Councilor'
    else: return None,None,None,term2,None
    an=None
    m2=re.search(r'(?:DISTRICT|DIST|WARD|COUNCIL)\s*(?:\d+-)?0*(\d+)\s*(?:COUNCILOR)?$',A)
    if m2 and not re.search(r'MUNICIPAL(ITY)?\s+(DISTRICT\s+)?\d+$|MUNICIPALITY\s+\d+$',A): an=m2.group(1)
    if re.search(r'(COUNCIL|COMM|COMMISSION|WARD)\s+(DISTRICT\s+|DIST\s+)?(\d+-)?\d+\s*(COUNCILOR)?$',A) or re.search(r'DISTRICTED',rn.upper()): strong=True
    else: strong=False
    al=', At-Large' if re.search(r'AT LARGE',R) else ''
    return base+al,'gen_council',dist or None,term2,(an,strong)
st={'contests':0,'unplaced':collections.Counter(),'tie':0,'rcv_skipped':[],'places_filled':0,'officials':0,'clerks':0}
C={}   # (eid, raceid) -> contest
for e in EL:
    f=os.path.join(src,'%d_STATE.csv'%e)
    for r in csv.DictReader(io.StringIO(open(f,encoding='utf-8',errors='replace').read())):
        rn=r['RaceName']; a=r['AreaNum']
        if len(rn)>90 or NONMUNI.search(rn+' '+a) or not re.search(r'MAYOR|COUNCIL|TRUSTEE|COMMISSION|JUDGE',rn,re.I): continue
        pid=area_place(a,rn)
        if not pid: st['unplaced'][a.strip()]+=1; continue
        role,rk,dk,t2,an=role_of(rn,a)
        if not role: continue
        c=C.setdefault((e,r['RaceID']),{'pid':pid,'role':role,'rk':rk,'dk':dk,'t2':t2,'an':an,'seats':int(r['VoteFor'] or 1),'votes':{},'e':e})
        n=re.sub(r'(?i)\s*\(write[- ]?in\)\s*','',r['CandidateName']).strip()
        if not n or n.upper() in ('WRITE-IN','WRITE IN','OVER VOTES','UNDER VOTES','YES','NO'): continue
        v=int(float(r['CandidateVotes'] or 0)); c['votes'][n]=max(c['votes'].get(n,0),v)
AN=collections.defaultdict(set)
for (e,rid),c in C.items():
    if c['rk']=='gen_council' and c['an'] and c['an'][0]: AN[(e,c['pid'])].add(c['an'][0])
for (e,rid),c in C.items():
    if c['rk']=='gen_council' and not c['dk'] and c['an'] and c['an'][0] and (c['an'][1] or len(AN[(e,c['pid'])])>1): c['dk']=c['an'][0]
    if c['dk']:
        c['role']=re.sub(r', At-Large$','',c['role'])+', District '+c['dk']
# recount / runoff replace the same contest (same RaceID for a recount; same place+role for a runoff)
final={}
for (e,rid),c in sorted(C.items(),key=lambda kv:{'base':0,'recount':1,'runoff':2}[EL[kv[0][0]][2]]):
    kind=EL[e][2]; cyc=EL[e][1]
    if kind=='recount':
        for k in list(final):
            if k[0]==cyc and k[1]==rid: final[k]=c
        continue
    if kind=='runoff':
        for k in list(final):
            if k[0]==cyc and final[k]['pid']==c['pid'] and final[k]['role']==c['role']: del final[k]
    final[(cyc,rid)]=c
# an existing site record the city's own site contradicts: Santa Fe's site names Michael J. Garcia Alcalde-Mayor (took office 2026)
STALE={('Santa Fe','Alan Webber')}
RCV={one('Santa Fe'),one('Las Cruces')}
by=collections.defaultdict(list)
for (cyc,rid),c in final.items():
    st['contests']+=1
    v=sorted(c['votes'].items(),key=lambda x:-x[1]); n=c['seats']; tot=sum(x[1] for x in v)
    if not v or tot==0: continue
    if len(v)>n and v[n-1][1]==v[n][1]: st['tie']+=1; continue
    if c['pid'] in RCV and n==1 and v[0][1]*2<=tot: st['rcv_skipped'].append((P[c['pid']]['n'],c['role'],cyc)); continue
    c['win']=[x[0] for x in v[:n] if x[1]>0]; c['cyc']=cyc
    by[c['pid']].append(c)
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nz(a[-1])==nz(b[-1]) and nz(a[0])[:1]==nz(b[0])[:1]
CL={}
for k in json.load(open(os.path.join(src,'nm_sos_clerks.json'),encoding='utf-8')):
    pid=one(k['name']) or one(k['name'].replace('Espanola','Española'))
    if pid: CL[pid]=k
def dom(u):
    try: h=(urlparse(u if '//' in u else 'http://'+u).hostname or '').lower()
    except Exception: return ''
    return h[4:] if h.startswith('www.') else h
def office_ct(pid):
    k=CL.get(pid)
    if not k: return None
    p=P[pid]; ct={}
    if re.search(r'\d{3}\D*\d{4}',k.get('phone','')): ct['p']=[k['phone']]
    if k.get('addr') and not re.match(r'(?i)^p\.?\s*o\.?\s*box',k['addr']): ct['a']=k['addr']
    pd=dom(p.get('w','')); wd=dom(k.get('web',''))
    good={d for d in (pd,wd) if d and 'county' not in d and (d==pd or nz(p['n'])[:5] in nz(d))}
    if good: ct['w']='https://'+sorted(good,key=lambda d:d!=pd)[0]+'/'
    em=k.get('email','')
    if em and '@' in em and em.split('@')[1].lower() in good|{'www.'+g for g in good}: ct['e']=em
    if not ct: return None
    ct['src']=CLU; ct['g']=1; return ct
res={'st':'NM','built':TODAY,'src':{'name':'New Mexico Secretary of State, official results of the 2023 and 2025 Regular Local Elections and the 2024 and 2026 Municipal Officers Elections (electionresults.sos.nm.gov); SOS Municipal Clerk Information','note':'Winners of the latest municipal contests (recounts and runoffs applied). Names as printed in the results, in normal capitalization. Office contact from the SOS municipal clerk list.'},'places':{}}
for pid in set(by)|set(CL):
    p=P[pid]; L=by.get(pid,[]); outl=[]; ct=office_ct(pid)
    def rec(n,role,rk,c):
        o={'n':n,'r':role,'src':'nmsos','u':U(c['e']),'d':TODAY,'s':'elected %s'%EL[c['e']][0]}
        if rk: o['rk']=rk
        if ct: o['ct']={k:v for k,v in ct.items() if k!='e'}
        return o
    ms=[c for c in L if c['rk']=='gen_mayor']
    if ms:
        c=max(ms,key=lambda c:ORDER[c['cyc']]); outl+= [rec(tc(c['win'][0]),'Mayor','gen_mayor',c)] if c['win'] else []
    js=[c for c in L if c['role']=='Municipal Judge']
    if js:
        c=max(js,key=lambda c:ORDER[c['cyc']]); outl+=[rec(tc(w),'Municipal Judge',None,c) for w in c['win'][:1]]
    seats=[c for c in L if c['rk']=='gen_council']
    D=collections.defaultdict(list)
    for c in seats:
        if c['dk']: D[c['dk']].append(c)
    for dk_ in sorted(D,key=lambda x:int(x)):
        cs=sorted(D[dk_],key=lambda c:-ORDER[c['cyc']]); last=cs[0]['cyc']
        lat=[c for c in cs if c['cyc']==last]
        prev=[c for c in cs if c['cyc']!=last and ORDER[c['cyc']]==max([ORDER[x['cyc']] for x in cs if x['cyc']!=last] or [0]) and not c['t2']]
        fam={'rle23':'rle','rle25':'rle','moe24':'moe','moe26':'moe'}
        keep=lat+([prev[0]] if len(lat)==1 and prev and fam[prev[0]['cyc']]==fam[last] else [])
        for c in keep:
            for w in c['win']:
                n=tc(w)
                if any(sameperson(n,x['n']) for x in outl): continue
                outl.append(rec(n,c['role'],'gen_council',c))
    al=sorted([c for c in seats if not c['dk']],key=lambda c:-ORDER[c['cyc']])
    if al:
        last=al[0]['cyc']; family={'rle23':'rle','rle25':'rle','moe24':'moe','moe26':'moe'}
        prev=[c for c in al if family[c['cyc']]==family[last] and ORDER[c['cyc']]<ORDER[last] and not c['t2']]
        keep=[c for c in al if c['cyc']==last]+prev
        for c in keep:
            for w in c['win']:
                n=tc(w)
                if any(sameperson(n,x['n']) for x in outl): continue
                outl.append(rec(n,c['role'],'gen_council',c))
    k=CL.get(pid)
    if k and len(k['clerk'].split())>=2:
        o={'n':k['clerk'],'r':'Municipal Clerk','src':'nmsos','u':CLU,'d':TODAY}
        if ct: o['ct']=dict(ct)
        outl.append(o); st['clerks']+=1
    ex=[o for o in (p.get('o') or []) if o.get('src')!='nmsos' and (p['n'],o['n']) not in STALE]; LL=[]
    for o in outl:
        if any(sameperson(o['n'],x['n']) for x in ex+LL): continue
        if o.get('rk')=='gen_mayor' and any(x.get('rk')=='gen_mayor' for x in ex): continue
        LL.append(o)
    if not LL: continue
    res['places'][pid]={'n':p['n'],'o':ex+LL}; st['places_filled']+=1; st['officials']+=len(LL)
st['unplaced']=dict(st['unplaced'])
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps(st)[:3000])
