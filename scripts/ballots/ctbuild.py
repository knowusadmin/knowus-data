
import json,re,sys
from collections import Counter,defaultdict
H=sys.argv[1]
raw=json.load(open(H+'/ct_raw.json')); links=json.load(open(H+'/ct_links.json'))
def slug(n): return re.sub(r'[^a-z0-9]+','_',n.lower())
TOWNNAME={slug(n):n for n in links.values()}
URL={slug(n):u for u,n in links.items()}
CANON=[('Governor and Lieutenant Governor','governor(and|&)lieutenant|^governorvote'),('Representative in Congress','representativeincongress|^representativecongress'),('State Senator','^statesenat'),('State Representative','^state(r)?epresentative|^staterepresenta|^stateepresentative'),('Secretary of the State','^secretaryof(the)?state|^secretarythe'),('Treasurer','^treasurer'),('Comptroller','^comptroller'),('Attorney General','^attorneygeneral'),('Judge of Probate','^judgeofprobate'),('Registrar of Voters','^registrar(of)?(1\.)?voters|^registrarregistrador')]
def canon(h):
    z=re.sub(r'\s+','',h).lower()
    for name,key in CANON:
        if re.search(key,z): return name
    return None
NUMW={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'eleven':11,'twelve':12,'thirteen':13,'fourteen':14,'fifteen':15}
def votefor(h):
    m=re.search(r'up\s+to\s+(\w+)',h,re.I)
    if m and m.group(1).lower() in NUMW: return str(NUMW[m.group(1).lower()])
    m=re.search(r'Vote\s+for\s+(?:any\s+|up\s+to\s+)?(\w+)',h,re.I)
    if m:
        w=m.group(1).lower(); return str(NUMW.get(w,w))
    m=re.search(r'up\s+to\s+(\w+)',h,re.I)
    if m: return str(NUMW.get(m.group(1).lower(),m.group(1)))
    return None
# hand-checked spans for multi-column local contests (read from the PDFs' layout)
SPANS={'berlin':[((11,13),'Board of Education','3',True)],
       'darien':[((11,12),'Board of Education','2',False),((13,20),'Representative Town Meeting',None,True)],
       'stamford':[((10,12),'Board of Education','3',False)]}
import unicodedata
def nk(s):
    s=unicodedata.normalize('NFKD',s); s=''.join(ch for ch in s if not unicodedata.combining(ch))
    s=re.sub(r'\b[A-Za-z]\b\.?','',s)
    return re.sub(r'[^a-z]','',s.lower())
def lev(a,b):
    if abs(len(a)-len(b))>2: return 9
    d=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        p=d[:]; d[0]=i
        for j,cb in enumerate(b,1): d[j]=min(p[j]+1,d[j-1]+1,p[j-1]+(ca!=cb))
    return d[-1]
def clean_party(p):
    p=re.sub(r'\s+',' ',p).strip()
    if p=='san i No n t par': return 'Nonpartisan'
    return p
def party_short(p):
    return re.sub(r'\s+Party$','',p).strip()
faces=[]; problems=[]
for town,pages in raw.items():
    for pg in pages:
        g=pg['grid']; m=pg['meta']; issues=[]
        if not (m['cd'] and m['sd'] and m['ad']): issues.append('district header not read')
        colmap={}
        spans=SPANS.get(town,[])
        for (a,b),name,vf,np in spans:
            for n in range(a,b+1): colmap[n]=(name,vf,np,a)
        for n in g['cols']:
            if n in colmap: continue
            h=g['hdr'].get(str(n),'')
            c=canon(h)
            if not c: issues.append(f'column {n} header not recognised: {h[:60]}'); continue
            colmap[n]=(c,votefor(h) or '1',False,n)
        # local span vote-for read from that face's headers
        for (a,b),name,vf,np in spans:
            if vf is None:
                hh=' '.join(g['hdr'].get(str(n),'') for n in range(a,b+1))
                mm2=re.search(r'to\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen)\b',hh,re.I)
                v=(str(NUMW[mm2.group(1).lower()]) if mm2 else None) or (lambda mm: str(NUMW.get(mm.group(1).lower(),mm.group(1))) if mm else None)(re.search(r'to\s+(\w+)',hh))
                if not v: issues.append(f'{name}: vote-for not read')
                for n in range(a,b+1): colmap[n]=(name,v,np,a)
        contests={}; order=[]
        for c in g['cells']:
            party=clean_party(c['party'])
            if c['col'] in colmap and colmap[c['col']][2]: party='Nonpartisan'
            if party.lower().startswith('write-in'):
                issues.append(f'candidate text in write-in row, col {c["col"]}: {c["text"][:40]}'); continue
            if c['col'] not in colmap: issues.append(f'cell in unmapped column {c["col"]}'); continue
            name,vf,np,key=colmap[c['col']]
            if c['pdist']>30 and not colmap[c['col']][2]: issues.append(f'party far from cell {c["label"]}')
            if key not in contests: contests[key]=dict(office=name,voteFor=vf,cands=[]); 
            nm=re.sub(r'\s+',' ',c['text'].replace('\u25cf','')).strip()
            nm=re.sub(r'\s+\.','.',nm); nm=re.sub(r'(\w)- (\w)',r'\1-\2',nm)
            ex=[x for x in contests[key]['cands'] if nk(x['n'])==nk(nm)]
            ps=party_short(party)
            if ex:
                if ps not in ex[0]['p']: ex[0]['p'].append(ps)
            else: contests[key]['cands'].append(dict(n=nm,p=[ps],y=c['y'],col=c['col']))
        # contests that exist on the ballot face (columns) but no candidates -> still record (rare)
        for n,(name,vf,np,key) in colmap.items():
            if key not in contests: contests[key]=dict(office=name,voteFor=vf,cands=[])
        cs=[]
        for key in sorted(contests):
            C=contests[key]
            C['cands'].sort(key=lambda x:(x['y'],x['col']))
            cs.append(dict(t=C['office'],vf=C['voteFor'] or '1',c=[[x['n'],' / '.join(x['p'])] for x in C['cands']]))
        # questions
        ql=[l for l in g['qlines'] if l.strip()]
        qs=[]; cur=None; auto=0
        for l in ql:
            if re.match(r'^(Vote on the Question|Vote sobre la|Vota sobre|Question #|Pregunta|Sheet \d|P[aá]gina|Be sure|Asegúrese|ballot\.$|Voting District)',l): continue
            if re.match(r'^(Yes|Sí|Si|YES)\b',l) or re.match(r'^(No|NO)\b',l): cur=None; continue
            mm=re.match(r'^(\d{1,2})\.\s*(.*)$',l)
            body=mm.group(2) if mm else l
            b0=body.lstrip('"\u201c ')
            spanish=b0.startswith('¿') or re.match(r'^(Se |Debe|Deber|Aprobar|Autoriz)',b0)
            if mm or (cur is None and re.match(r'^Shall\b',b0)):
                if spanish: cur='ES'; continue
                num=mm.group(1) if mm else None
                cur=dict(num=num,lines=[body]); qs.append(cur); continue
            if cur=='ES' or cur is None: continue
            if '¿' in l: cur='ES'; continue
            cur['lines'].append(l)
        for i,q in enumerate(qs):
            if q['num'] is None: q['num']=str(i+1)
        qs2=[]
        for q in qs:
            t=re.sub(r'\s+',' ',' '.join(q['lines'])).strip()
            t=re.sub(r'\s*Yes(/Sí)?\s+No(/No)?\s*$','',t).strip()
            if len(t)>1 and t[0] in '"\u201c' and t[-1] in '"\u201d': t=t[1:-1].strip()
            qs2.append(dict(num=q['num'],text=t))
        nums=[q['num'] for q in qs2]
        if nums and nums!=[str(i) for i in range(1,len(nums)+1)]: issues.append(f'question numbering {nums}')
        if g['qlines'] and any('Question' in l for l in g['qlines']) and not qs2: issues.append('question area present but no question read')
        nz=lambda x: str(int(x)) if x else x
        faces.append(dict(town=town,name=TOWNNAME.get(town,town),page=m['page'],cd=nz(m['cd']),sd=nz(m['sd']),ad=nz(m['ad']),vd=m['vd'],contests=cs,questions=qs2,issues=issues,url=URL.get(town)))
# --- cross-checks: statewide offices identical everywhere; district offices identical within their district
ACCEPT={('killingly','State Representative'):'Killingly\'s official ballots list petitioning candidate Ryan Cournoyer for the 51st; the Putnam and Thompson ballots do not. Each town shows its own printed ballot.'}
SWN=['Governor and Lieutenant Governor','Secretary of the State','Treasurer','Comptroller','Attorney General']
# statewide display names: the most common printed spelling
disp=defaultdict(Counter)
for f in faces:
    for c in f['contests']:
        if c['t'] in SWN:
            for n,p in c['c']: disp[c['t']][n]+=1
best={o:[n for n,k in disp[o].most_common() if k>=50] for o in SWN}
for f in faces:
    for c in f['contests']:
        if c['t'] not in SWN: continue
        merged=[]
        for n,p in c['c']:
            tgt=[b for b in best[c['t']] if nk(b)==nk(n) or lev(nk(b),nk(n))<=1]
            if tgt and tgt[0]!=n: f.setdefault('notes',[]).append(f'printed "{n}" read as {tgt[0]}')
            n2=tgt[0] if tgt else n
            ex=[m for m in merged if m[0]==n2]
            if ex:
                ex[0][1]=' / '.join(dict.fromkeys(ex[0][1].split(' / ')+p.split(' / ')))
            else: merged.append([n2,p])
        c['c']=merged
def cset(f,office): 
    x=[c for c in f['contests'] if c['t']==office]
    if not x: return 'null'
    return json.dumps(sorted([nk(n),'/'.join(sorted(p.split(' / ')))] for n,p in x[0]['c']))
SW=['Governor and Lieutenant Governor','Secretary of the State','Treasurer','Comptroller','Attorney General']
canonSW={o:Counter(cset(f,o) for f in faces).most_common(1)[0][0] for o in SW}
byd={'Representative in Congress':'cd','State Senator':'sd','State Representative':'ad'}
canonD={}
for o,k in byd.items():
    grp=defaultdict(Counter)
    for f in faces: grp[f[k]][cset(f,o)]+=1
    canonD[o]={d:c.most_common(1)[0] for d,c in grp.items()}
# a face with no district header: districts inferred from candidate sets unique to one district
for f in faces:
    if f['cd'] and f['sd'] and f['ad']: continue
    for o,k in byd.items():
        if f[k]: continue
        mine=cset(f,o); hits=[d for d,(best_,cnt) in canonD[o].items() if d and best_==mine]
        if len(hits)==1: f[k]=hits[0]; f.setdefault('notes',[]).append(f'{k} {hits[0]} inferred from the {o} candidates (no district header on this ballot)')
    if f['cd'] and f['sd'] and f['ad']:
        f['issues']=[i for i in f['issues'] if i!='district header not read']
for f in faces:
    offs=[c['t'] for c in f['contests']]
    for q in f['questions']:
        if not re.search(r'\?["\u201d]?\)?$',q['text']): f['issues'].append(f'question {q["num"]} text does not end in a question mark')
    for o in SW+list(byd):
        if o not in offs: f['issues'].append(f'missing {o}')
    for o in SW:
        if cset(f,o)!=canonSW[o]: f['issues'].append(f'{o} differs from the statewide set')
    for o,k in byd.items():
        if f[k] is None: f['issues'].append(f'{o}: district unknown'); continue
        if f[k] not in canonD[o]: continue
        best,cnt=canonD[o][f[k]]
        if cset(f,o)!=best:
            if (f['town'],o) in ACCEPT: f.setdefault('notes',[]).append(ACCEPT[(f['town'],o)])
            else: f['issues'].append(f'{o} differs from other ballots in district {f[k]}')
    if 'Judge of Probate' not in offs: f['issues'].append('no Judge of Probate column (check)')
    f['verified']=not f['issues']
json.dump(dict(faces=faces,canonSW={k:json.loads(v) for k,v in canonSW.items()}),open(H+'/ct_faces.json','w'),indent=1)
print('faces',len(faces),'verified',sum(f['verified'] for f in faces))
ic=Counter(i.split(':')[0] for f in faces for i in f['issues'])
print(ic.most_common(30))
print({k:json.loads(v) for k,v in canonSW.items()})
