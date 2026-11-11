# Dallas County TX, Nov 3 2026 General & Joint Election: ballot data + sub-precinct map for the app.
# Inputs (DIR): parsed.json (dparse.py over the county's 216 ballot-style PDFs), detailxml.zip (county's official precinct-level
# results, Clarity ENR 127396/386630), subprecincts.json (Dallas County Elections "2026 Sub Precincts (1,638)" layer), uncontested.json.
# Style per sub-precinct: the results list each of 914 precinct parts with the contests on its ballot; those 914 contest sets are
# exactly the 216 styles' contest sets (1:1). The other 724 parts (no results rows) get the style whose parts share their district codes.
# python3 dallas_build.py DIR SITE
import json,re,sys,collections,zipfile
import xml.etree.ElementTree as ET
import numpy as np, shapely, pyproj
import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.validation import make_valid
D=sys.argv[1]; R=sys.argv[2]
BASE='https://assets01.aws.connect.clarityelections.com/Assets/Connect/RootPublish/dallas-tx.connect.clarityelections.com/SampleBallots/2026/261103GeneralJoint/'
PART={'Rep':'Republican','Dem':'Democratic','Lib':'Libertarian','Grn':'Green','Ind':'Independent'}
PR=json.load(open(D+'/parsed.json'))
for p in PR:
    assert 'error' not in p and p['nov']==p['nopt'],p['file']
    for c in p['contests']:
        for o in c['opts']:
            m=re.match(r'^(.*\S)\s+(Rep|Dem|Lib|Grn|Ind)$',o[0])
            if m and not o[1]: o[0]=m[1]; o[1]=PART[m[2]]
STY={p['file'][:-4]:p for p in PR}
x=zipfile.ZipFile(D+'/detailxml.zip').read('detail.xml').decode('utf-8-sig')
XC=ET.fromstring(x).findall('Contest'); CN={i:c.get('text') for i,c in enumerate(XC)}
P2C=collections.defaultdict(set)
for i,c in enumerate(XC):
    for p in c.iter('Precinct'): P2C[p.get('name')].add(i)
def normq(t): return re.sub(r'\s*[-–]\s*',' ',t.upper()).replace('  ',' ').strip()
ENRT={v:k for k,v in CN.items()}; ENRQ={normq(v):k for k,v in CN.items()}
UNC=[k for k,v in CN.items() if v=='Uncontested Races'][0]
SIG={}
for st,p in STY.items():
    s=set()
    for c in p['contests']:
        s.add(UNC if c['t']=='u' else (ENRT[c['title']] if c['t']=='r' else ENRQ[normq(c['title'])]))
    SIG[st]=frozenset(s)
inv=collections.defaultdict(list)
for st,s in SIG.items(): inv[s].append(st)
assert all(len(v)==1 for v in inv.values()) and len(inv)==len(STY)
split2style={sp:inv[frozenset(cs)][0] for sp,cs in P2C.items()}
SUB=json.load(open(D+'/subprecincts.json')); SPA={f['attributes']['COMBO1']:f for f in SUB}
assert set(P2C)<=set(SPA)
def akey(a):
    com=int(a['DIST05_COM']); cit=a['DIST06_CIT']; sch=a['DIST08_SCH']; stb=int(a['DIST23_STB']); sts=int(a['DIST03_STS'])
    return (int(a['DIST02_USC']),sts if sts==2 else 0,int(a['DIST04_STR']),com if com in(2,4) else 0,int(a['DIST21_JP']),stb if stb in(9,13,14) else 0,
            cit if cit in('DA0','GA0','UP0','WY0') else '',sch if sch in('IR0','ME0') else '')
k2s=collections.defaultdict(set)
for sp,st in split2style.items(): k2s[akey(SPA[sp]['attributes'])].add(st)
assert all(len(v)==1 for v in k2s.values())
SUBSTY={}; how=collections.Counter(); unres=[]
for sp,f in SPA.items():
    if sp in split2style: SUBSTY[sp]=split2style[sp]; how['results']+=1; continue
    v=k2s.get(akey(f['attributes']))
    if v: SUBSTY[sp]=next(iter(v)); how['district codes']+=1
    else: unres.append(sp); how['unresolved']+=1
# district cross-check of every results part against the county layer
def expect(cs):
    e={}
    for c in cs:
        t=c['title']
        for pat,k in ((r'United States Representative, District (\d+)','USC'),(r'Member, State Board of Education, District (\d+)','STB'),(r'State Representative, District (\d+)','STR'),(r'State Senator, District (\d+)','STS'),(r'County Commissioner, Precinct No\. (\d+)','COM')):
            m=re.match(pat,t)
            if m: e[k]=int(m[1])
        m=re.match(r'(?:Justice of the Peace|Constable), Precinct No\. (\d+)',t)
        if m: e.setdefault('JP',set()).add(int(m[1]))
    return e
mism=[]
for sp,st in split2style.items():
    a=SPA[sp]['attributes']; e=expect(STY[st]['contests'])
    if e.get('USC')!=int(a['DIST02_USC']) or e.get('STR')!=int(a['DIST04_STR']) or e.get('JP')!={int(a['DIST21_JP'])}: mism.append(sp)
    if int(a['DIST23_STB']) in (9,13,14) and e.get('STB')!=int(a['DIST23_STB']): mism.append(sp)
    if (int(a['DIST05_COM']) in (2,4))!=('COM' in e) or ('COM' in e and e['COM']!=int(a['DIST05_COM'])): mism.append(sp)
    if (int(a['DIST03_STS'])==2)!=('STS' in e): mism.append(sp)
print('district mismatches',len(mism),mism[:10],flush=True)
# contests
def norm(t):
    if t=='United States Senator': return t,''
    for pat,f in ((r'^(United States Representative|Member, State Board of Education|State Senator|State Representative), (District \d+)$',None),
                  (r'^(Justice, Supreme Court), (Place \d+) - (Unexpired Term)$','u'),
                  (r'^(Justice, Supreme Court|Judge, Court of Criminal Appeals|Justice, \d+\w\w Court of Appeals District), (Place \d+)$',None),
                  (r'^(District Judge), (\d+\w\w Judicial District)$',None),
                  (r'^(County Commissioner|Constable), (Precinct No\. \d+)$',None),
                  (r'^(Justice of the Peace), (Precinct No\. \d+, Place \d+)$',None)):
        m=re.match(pat,t)
        if m: return m[1],(m[2]+', '+m[3] if f=='u' else m[2])
    return t,''
def qtitle(t):
    t=re.sub(r'\s*[-–]\s*',' ',t).strip()
    fix={'DALLAS COUNTY PROPOSITION A':'Dallas County, Proposition A','CITY OF DALLAS PROPOSITION A':'City of Dallas, Proposition A','City of Garland Proposition A':'City of Garland, Proposition A',
         'MESQUITE INDEPENDENT SCHOOL DISTRICT PROPOSITION A':'Mesquite Independent School District, Proposition A','CITY OF UNIVERSITY PARK PROPOSITION A':'City of University Park, Proposition A'}
    if t in fix: return fix[t]
    m=re.match(r'^IRVING ISD PROPOSITION (\w)$',t)
    if m: return 'Irving Independent School District, Proposition '+m[1]
    m=re.match(r'^CITY OF WYLIE, TEXAS PROPOSITION (\w)$',t)
    if m: return 'City of Wylie, Proposition '+m[1]
    raise Exception('prop title '+t)
UL=json.load(open(D+'/uncontested.json'))
uq=' '.join('%s: %s.'%(g,'; '.join('%s, %s (Democratic)'%(d,n) for d,n in v)) for g,v in UL)
def conv(c):
    if c['t']=='r':
        ti,d=norm(c['title']); vf={'Vote for One':'1'}[c['vf']]
        return dict(t='r',title=ti,d=d,vf=vf,c=[[o,p] for o,p in c['opts']],wi=c['wi'],note=[])
    if c['t']=='u':
        return dict(t='q',title='Uncontested Races',pre='The following candidates are uncontested. You may vote for all uncontested candidates by choosing “Vote for All” or vote for none of the uncontested candidates by choosing “Vote for None.”',q=uq,r=[o for o,_ in c['opts']])
    b=c['body'].strip(); m=re.match(r'^(THIS IS A (?:PROPERTY )?TAX INCREASE)\.?\s+(.*)$',b)
    pre,q=(m[1],m[2]) if m else ('',b)
    q=q.strip().strip('"“”').strip()
    return dict(t='q',title=qtitle(c['title']),pre=pre,q=q,r=[o for o,_ in c['opts']])
NB={st:[conv(c) for c in p['contests']] for st,p in STY.items()}
C=[];IX={}
def ck(c): return json.dumps(c,sort_keys=True)
for k in sorted(NB,key=lambda k:-len(NB[k])):
    prev=-1
    for c in NB[k]:
        key=ck(c)
        if key not in IX:
            C.insert(prev+1,c); IX={kk:(v if v<=prev else v+1) for kk,v in IX.items()}; IX[key]=prev+1
        prev=IX[key]
O={k:[IX[ck(c)] for c in v] for k,v in NB.items()}
nonsorted=sum(v!=sorted(v) for v in O.values())
# pieces: one per (precinct, style)
TR=pyproj.Transformer.from_crs(4326,32614,always_xy=True)
def area(g): return shapely.transform(g,lambda xy: np.column_stack(TR.transform(xy[:,0],xy[:,1]))).area
def esri_poly(geom):
    outers=[];holes=[]
    for r in geom['rings']: (holes if sg.LinearRing(r).is_ccw else outers).append(r)
    polys=[sg.Polygon(o) for o in outers]
    for h in holes:
        hp=sg.Polygon(h)
        for i,p in enumerate(polys):
            if p.contains(hp.representative_point()): polys[i]=sg.Polygon(p.exterior.coords,[*[x.coords for x in p.interiors],h]); break
    return make_valid(sg.MultiPolygon(polys) if len(polys)>1 else polys[0])
grp=collections.defaultdict(list)
for sp,st in SUBSTY.items(): grp[(SPA[sp]['attributes']['Precinct'],st)].append(sp)
nst=collections.Counter(p for p,_ in grp)
S={}; geoms={}
for (pc,st),sps in sorted(grp.items()):
    k='Precinct '+pc if nst[pc]==1 else 'Precinct '+', '.join(sorted(sps))
    S[k]=dict(o=O[st],pdf=BASE+st+'.pdf',ok=True,p=pc,bs=st,parts=sorted(sps))
    geoms[k]=make_valid(unary_union([esri_poly(SPA[s]['geometry']) for s in sps]))
SC=100000
def enc(coords):
    dd=[];px=py=0;last=None
    for x_,y_ in coords:
        x_,y_=round(x_*SC),round(y_*SC)
        if (x_,y_)==last: continue
        dd+=[x_-px,y_-py];px,py=x_,y_;last=(x_,y_)
    return dd
OUT=[]
for k,g in geoms.items():
    polys=[]
    for xx in getattr(g,'geoms',[g]):
        if xx.geom_type=='Polygon': polys.append(xx)
        elif xx.geom_type=='MultiPolygon': polys+=list(xx.geoms)
    rings=[]
    for p in polys:
        if area(p)<0.5: continue
        rings.append(enc(p.exterior.coords)); rings+=[enc(i.coords) for i in p.interiors if sg.Polygon(i).area>0]
    rings=[r for r in rings if len(r)>=8]
    if not rings: print('no rings',k,flush=True); continue
    b=g.bounds; OUT.append((area(g),[k,[int(b[0]*SC)-1,int(b[1]*SC)-1,int(b[2]*SC)+1,int(b[3]*SC)+1],rings]))
OUT.sort(key=lambda z:z[0]); used={z[1][0] for z in OUT}
S={k:v for k,v in S.items() if k in used}
common=sorted(set.intersection(*[set(v['o']) for v in S.values()]))
out=dict(read='2026-11-11',county='Dallas County, Texas',
 source='Dallas County Elections Department — the official ballot for each of the county’s 216 ballot styles (Nov 3, 2026 General and Joint Election), placed by the Elections Department’s 2026 sub-precinct map; each precinct part’s style is the one whose contests match that part in the county’s official precinct-level results, or, for parts with no results row, the style of parts with the same districts',
 sourceUrl='https://www.dallascountyvotes.org/voters/ballot/',lookup='https://www.dallascountyvotes.org/voters/ballot/',office='Dallas County Elections Department',c=C,s=S,common=common)
json.dump(out,open(R+'/data/ballots/tx-dallas-2026-11-03.json','w'),ensure_ascii=False,separators=(',',':'))
geo=dict(v=1,source=['Dallas County Elections Department — 2026 Sub Precincts (1,638), from the department’s public precinct map (Current_Sub_Precincts_1638_20260722), merged where parts of a precinct get the same ballot','https://services3.arcgis.com/zqe2kwz79KUqUvxC/arcgis/rest/services/Current_Sub_Precincts_1638_20260722/FeatureServer/13','2026-11-11'],
 scale=100000.0,note='Each polygon is a precinct, or the part of a precinct that gets one of its printed ballot styles. Smallest first.',p=[z for _,z in OUT])
json.dump(geo,open(R+'/data/ballots/tx-dallas-precincts.json','w'),ensure_ascii=False,separators=(',',':'))
json.dump(dict(how=how,unres=unres,mism=mism,substy=SUBSTY,keys={k:v['parts'] for k,v in S.items()}),open(D+'/dallas-build.json','w'))
print('ok',dict(how),'styles',len(STY),'contests',len(C),'pieces',len(S),'multi-style precincts',sum(1 for p,n in nst.items() if n>1),'common',len(common),flush=True)
