
# Collin County TX, Nov 3 2026 Joint General and Special: ballot data + precinct-split map.
# Inputs: parsed.json (ccparse.py over every ballot-style PDF), styles.json (the county Elections API: precinct/sub-precinct -> ballot style),
# layers.json (county Voting_Precincts + Cities layers, TEA School Districts 2026). python3 collin_build.py DIR
import json,re,sys,collections,itertools
import numpy as np, shapely, pyproj
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.validation import make_valid
D=sys.argv[1]
P={x['file'][:-4]:x for x in json.load(open(D+'/parsed.json'))}
ST=json.load(open(D+'/styles.json')); LY=json.load(open(D+'/layers.json'))
TR=pyproj.Transformer.from_crs(4326,32614,always_xy=True)
def area(g): return shapely.transform(g,lambda xy: np.column_stack(TR.transform(xy[:,0],xy[:,1]))).area
ENT=re.compile(r'^(City of [A-Za-z .]+?, Texas|Town of [A-Za-z .]+?, Texas|[A-Za-z .]+ Independent School District|[A-Za-z .\d]+? Municipal Utility District(?: No\. \d+)?(?: of Collin County)?|[A-Za-z ]+ Municipal Development District|Collin County Appraisal District|Collin County Community College District|Collin County, Texas)')
LOCAL=re.compile(r'^(Board of Trustees|City Council|Alderman|Councilmember|Council Member|Mayor|Directors|School Trustees|Trustee|Bond Election|Maintenance Tax Election|Road Refunding Bond Election|Utility Bond Election|Utility Refunding Bond Election|Fire Protection Plan Election|Confirmation Election|Directors Election|Voter-Approval Tax Rate Election)')
def clean_title(t):
    t=re.sub(r'^(Legend of Party Affiliation )?(Federal )?','',t)
    t=re.sub(r'\s*\((?:[^()]*)\)\s*$','',t).strip()
    t=re.sub(r'^(Collin County Appraisal District )(?=Collin County Appraisal District)','',t)
    return t
def vf(s):
    n={'One':1,'Two':2,'Three':3,'Four':4,'Five':5,'Six':6}; return str(max(n[x] for x in re.findall(r'One|Two|Three|Four|Five|Six',s)))
def split_d(t):
    m=re.match(r'^(.*?),?\s+((?:Place|District|Precinct No\.|Ward) [\w-]+(?:,? Unexpired Term)?)$',t)
    if m and not re.match(r'^(District Judge|Justice, \d|Chief Justice, \d)',t): return m[1].replace(', Texas ',' '),m[2]
    return t.replace(', Texas ',' '),''
EOF={}
def norm(x):
    out=[]; ent=None; es=set()
    for c in x['contests']:
        t=clean_title(c['title']); m=ENT.match(t)
        if m: ent=m[1]; es.add(ent.replace(', Texas',''))
        elif LOCAL.match(t) and ent: t=ent+' '+t; es.add(ent.replace(', Texas',''))
        if c['kind']=='r':
            ti,d=split_d(t); out.append(dict(t='r',title=ti,d=d,vf=vf(c['vf']),c=[[n,p] for n,p in c['c']],wi=c['wi'],note=[]))
        else:
            body=' '.join(c['body']); mm=re.search(r'\bPropositi?on ([A-Z0-9]+)\b',body)
            if mm and mm.start()<60:
                pre=body[:mm.start()].strip(); q=body[mm.end():].strip(); ti=t.replace(', Texas','').strip()+(', Proposition '+mm[1] if 'Proposition' not in t else '')
            else: pre='';q=body;ti=t
            out.append(dict(t='q',title=ti,pre='',q=q,r=c['opts']))
    EOF[x['file'][:-4]]=es
    return out
NB={k:norm(v) for k,v in P.items()}
def ents(cs):
    s=set()
    for c in cs:
        m=ENT.match(c['title'].replace(' City Council',', Texas City Council'))
        m=ENT.match(c['title']) or m
        if m: s.add(m[1].replace(', Texas',''))
    return s
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
EN=EOF
url={b['displayName'].replace(' ',''):'https://api.collincountytx.gov/Elections2APIProxy/'+b['ballotStyleContentUrl'] for b in ST}
byp=collections.defaultdict(set)
for b in ST: byp[b['precinct']].add(b['displayName'].replace(' ',''))
prec={f['properties']['PRECINCT']:make_valid(shape(f['geometry'])) for f in LY['prec']}
LAY={}
for f in LY['city']:
    if not f.get('geometry'): continue
    n='City of '+f['properties']['CITY_NAME']; LAY.setdefault(n,[]).append(make_valid(shape(f['geometry'])))
for f in LY['isd']:
    n=re.sub(r' ISD.*$','',f['properties']['NAME'])+' Independent School District'; LAY.setdefault(n,[]).append(make_valid(shape(f['geometry'])))
for f in LY.get('mud',[]):
    n=re.sub(r'^Blue Meadow MUD (\d+)$',r'Blue Meadow Municipal Utility District No. \1 of Collin County',f['properties']['NAME']); LAY.setdefault(n,[]).append(make_valid(shape(f['geometry'])))
LAY={k:make_valid(unary_union(v)) for k,v in LAY.items()}
S={}; pieces=[]; rep=collections.Counter(); unresolved=[]; nolayer=collections.Counter()
for pid in sorted(byp):
    sty={}
    for bs in sorted(byp[pid],key=lambda s:int(s[2:])): sty.setdefault(json.dumps(O[bs]),bs)
    styles=list(sty.values())
    if len(styles)==1:
        k='Precinct %d'%pid; S[k]=dict(o=O[styles[0]],pdf=url[styles[0]],ok=True,p=str(pid),bs=styles[0]); pieces.append((k,prec[pid])); rep['single']+=1; continue
    rep['multi']+=1
    allE=set.union(*[EN[s] for s in styles]); comE=set.intersection(*[EN[s] for s in styles])
    rel=sorted(e for e in allE-comE if e in LAY); 
    for e in allE-comE:
        if e not in LAY: nolayer[e]+=1
    common=sorted(set.intersection(*[set(O[s]) for s in styles]))
    for combo in itertools.product((0,1),repeat=len(rel)):
        g=prec[pid]
        for e,inn in zip(rel,combo): g=g.intersection(LAY[e]) if inn else g.difference(LAY[e])
        g=make_valid(g)
        if g.geom_type=='GeometryCollection': g=unary_union([x for x in g.geoms if x.geom_type in ('Polygon','MultiPolygon')])
        if g.is_empty or area(g)<=0: continue
        want={e for e,inn in zip(rel,combo) if inn}
        match=[s for s in styles if {e for e in EN[s] if e in rel}==want]
        if len(match)==1:
            s=match[0]; k='Precinct %d, ballot style %s'%(pid,s[2:]); S[k]=dict(o=O[s],pdf=url[s],ok=True,p=str(pid),bs=s)
        else:
            k='Precinct %d (part)'%pid; S.setdefault(k,dict(o=common,pdf=None,ok=False,p=str(pid),common=common)); unresolved.append((pid,sorted(want),len(match),round(area(g))))
        pieces.append((k,g))
# district check against the county precinct layer; a printed style whose districts disagree is not shown as verified
PA={f['properties']['PRECINCT']:f['properties'] for f in LY['prec']}
dmis=[]
for k,s in S.items():
    if not s['ok']: continue
    a=PA[int(s['p'])]; got={}
    for i in s['o']:
        c=C[i]
        if c['t']!='r': continue
        m_=re.search(r'(\d+)',c['d'] or '')
        for key,pre in (('cd','United States Representative'),('sd','State Senator'),('hd','State Representative'),('comm','County Commissioner'),('jp','Justice of the Peace')):
            if c['title'].startswith(pre) and m_: got[key]=int(m_[1])
    want={'cd':a['CONG'],'hd':a['SHR'],'jp':a['JPC']}
    if 'sd' in got: want['sd']=a['SEN']
    if a['COMMISH'] in (2,4): want['comm']=a['COMMISH']
    if got!=want: dmis.append((k,got,want))
for k,got,want in dmis:
    s=S.pop(k); nk='Precinct %s (districts differ from the map)'%s['p']; cm=sorted(set(s['o'])&set(COMMON)) if 'COMMON' in globals() else []
    S[nk]=dict(o=[],pdf=None,ok=False,p=s['p'],common=[]); pieces=[(nk if kk==k else kk,g) for kk,g in pieces]
print('district mismatches',dmis,flush=True)
SC=100000
def enc(coords):
    dd=[];px=py=0;last=None
    for x,y in coords:
        x,y=round(x*SC),round(y*SC)
        if (x,y)==last: continue
        dd+=[x-px,y-py];px,py=x,y;last=(x,y)
    return dd
mg=collections.defaultdict(list)
for k,g in pieces: mg[k].append(g)
OUT=[]
for k,gs in mg.items():
    g=make_valid(unary_union(gs)); polys=[]
    for x in getattr(g,'geoms',[g]):
        if x.geom_type=='Polygon': polys.append(x)
        elif x.geom_type=='MultiPolygon': polys+=list(x.geoms)
    rings=[]
    for p in polys:
        if area(p)<0.5: continue
        rings.append(enc(p.exterior.coords)); rings+=[enc(i.coords) for i in p.interiors]
    rings=[r for r in rings if len(r)>=8]
    if not rings: continue
    b=g.bounds; OUT.append((area(g),[k,[int(b[0]*SC)-1,int(b[1]*SC)-1,int(b[2]*SC)+1,int(b[3]*SC)+1],rings]))
OUT.sort(key=lambda x:x[0]); used={x[1][0] for x in OUT}
COM=sorted(set.intersection(*[set(v['o']) for v in S.values() if v['ok']]))
for v in S.values():
    if not v['ok']: v['o']=COM; v['common']=COM
S={k:v for k,v in S.items() if k in used}
json.dump(dict(C=C,S=S,geo=[x for _,x in OUT],unresolved=unresolved,report=rep,nolayer=nolayer),open(D+'/cc-build.json','w'),ensure_ascii=False)
print(json.dumps(rep),len(C),len(S),sum(not v['ok'] for v in S.values()),dict(nolayer),flush=True)
for u in unresolved: print(u)
