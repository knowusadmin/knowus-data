
# Hidalgo County TX, Nov 3 2026 General and Local Entities Elections: ballot data + precinct-split map.
# Inputs (DIR): parsed.json (hparse.py over the county's 64 ballot-style PDFs), legend.pdf text pairs (legend.json: precinct-sub -> BS),
# tlc-hidalgo.geojson (Texas Legislative Council Precincts26P, Hidalgo County), layers.json (county City Limits 2025, TEA School Districts SY2025-26,
# City of Weslaco single-member districts), addrpts.json (county Address Points 2026). python3 hid_build.py DIR
import json,re,sys,collections,itertools
import numpy as np, shapely, pyproj
from shapely.geometry import shape, Point
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely.strtree import STRtree
D=sys.argv[1]
PJ={x['bs']:x for x in json.load(open(D+'/parsed.json'))}
LEG=json.load(open(D+'/legend.json')); LINKS=json.load(open(D+'/bslinks.json'))
LY=json.load(open(D+'/layers.json'))
TR=pyproj.Transformer.from_crs(4326,32614,always_xy=True)
def area(g): return shapely.transform(g,lambda xy: np.column_stack(TR.transform(xy[:,0],xy[:,1]))).area
PARTY={'REP':'Republican','DEM':'Democratic','LIB':'Libertarian','GRN':'Green','IND':'Independent'}
ISDN={'Hidalgo':'Hidalgo','Pharr-San Juan-Alamo':'Pharr-San Juan-Alamo','Weslaco':'Weslaco','Edinburg Consolidated':'Edinburg Consolidated',
 'Mercedes':'Mercedes','Donna':'Donna','Monte Alto':'Monte Alto','La Joya':'La Joya','Edcouch-Elsa':'Edcouch-Elsa','La Villa':'La Villa'}
def vf(s):
    if not s: return '1'
    n={'one':1,'two':2,'three':3,'four':4,'five':5}; w=re.findall(r'one|two|three|four|five|\((\d)\)',s.lower())
    return '1'
def norm_title(t):
    t=t.strip(); ent=None
    m=re.match(r"^For South Texas I\.S\.D\. School Board Trustee, Hidalgo County Commissioners' Pct\. #(\d)$",t)
    if m: return 'South Texas Independent School District Trustee','Hidalgo County Commissioners Precinct '+m[1],None
    m=re.match(r'^(?:For )?(?:School Board )?(?:School )?Trustee,? Place(?: No\.)? (\d+), (.+?)(?: Independent School District)?$',t)
    if m:
        isd=m[2]; return isd+' Independent School District Trustee','Place '+m[1],('isd',isd)
    m=re.match(r'^Council Place No\. (\d+), City of (\w+) (Full Term|Special Election Unexpired Term)$',t)
    if m: return 'City of %s Council'%m[2],'Place %s'%m[1]+(', Unexpired Term' if 'Unexpired' in m[3] else ''),('city',m[2])
    m=re.match(r'^Mayor, City of (\w+)(?: Full Term)?$',t)
    if m: return 'City of %s Mayor'%m[1],'',('city',m[1])
    m=re.match(r'^Council Member, Place (\d+), City of (\w+)$',t)
    if m: return 'City of %s Council Member'%m[2],'Place '+m[1],('city',m[2])
    m=re.match(r'^For Commissioner (At-Large|District \d+), City of (\w+)(?: \(Unopposed Candidate\))?$',t)
    if m: return 'City of %s Commissioner'%m[2],m[1],('city',m[2])
    m=re.match(r'^For Alderman, Place No\. (\d+), City of (\w+)$',t)
    if m: return 'City of %s Alderman'%m[2],'Place '+m[1],('city',m[2])
    m=re.match(r'^Board of Directors Place (\d+), Hidalgo County Appraisal District$',t)
    if m: return 'Hidalgo County Appraisal District Board of Directors','Place '+m[1],None
    m=re.match(r'^(Justice, Supreme Court|Judge, Court of Criminal Appeals), (Place \d+)(?: - (Unexpired Term))?$',t)
    if m: return m[1],m[2]+(', '+m[3] if m[3] else ''),None
    m=re.match(r'^(United States Representative|State Representative|State Senator|Member, State Board of Education), (District \d+)$',t)
    if m: return m[1],m[2],None
    m=re.match(r'^(Justice of the Peace|County Commissioner|Constable), (Precinct No\. \d+(?:, Place \d+)?)$',t)
    if m: return m[1],m[2],None
    return t,'',None
EN={}; NB={}
for bs,x in PJ.items():
    out=[]; es=set()
    for c in x['contests']:
        if c['title'].startswith('PROPOSITION'):
            m=re.match(r'^PROPOSITION (\w+), City of (\w+)$',c['title'])
            out.append(dict(t='q',title='City of %s, Proposition %s'%(m[2],m[1]),pre='',q=c['body'],r=[o.title() for o in c['opts']])); es.add(('city',m[2])); continue
        ti,d,e=norm_title(c['title'])
        if e: es.add(e)
        if ti=='City of Weslaco Commissioner' and d.startswith('District'): es.add(('wd',d))
        cands=[];wi=0
        for o in c['opts']:
            if not o.strip(): wi+=1; continue
            m=re.match(r'^(.*?)\s+(REP|DEM|LIB|GRN|IND)$',o)
            cands.append([m[1],PARTY[m[2]]] if m else [o,''])
        note=['Unopposed candidate'] if 'Unopposed' in c['title'] else []
        out.append(dict(t='r',title=ti,d=d,vf='1',c=cands,wi=wi,note=note))
    NB[bs]=out; EN[bs]=es
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
# precinct map (TLC, Lambert -> 4326)
G=json.load(open(D+'/tlc-hidalgo.geojson'))
prj=open(D+'/../tlc/Precincts26P.prj').read(); T2=pyproj.Transformer.from_crs(pyproj.CRS.from_wkt(prj),4326,always_xy=True)
def to4326(g): return shapely.transform(g,lambda xy: np.column_stack(T2.transform(xy[:,0],xy[:,1])))
prec={int(f['properties']['PREC']):make_valid(to4326(make_valid(shape(f['geometry'])))) for f in G['features']}
LAY={}
CITY_SRC=sys.argv[2] if len(sys.argv)>2 else 'county'
for f in LY['city']:
    if not f.get('geometry'): continue
    n=f['properties']['MUNI_NM'].title(); LAY.setdefault(('city',n),[]).append(make_valid(shape(f['geometry'])))
if CITY_SRC=='weslaco':
    LAY[('city','Weslaco')]=[make_valid(shape(f['geometry'])) for f in LY['wes_city']]
ISD_SRC=sys.argv[3] if len(sys.argv)>3 else 'tea'
if ISD_SRC=='tea':
    for f in LY['isd']:
        n=re.sub(r' ISD$','',f['properties']['NAME']).replace(' Cons',' Consolidated')
        LAY.setdefault(('isd',n),[]).append(make_valid(shape(f['geometry'])))
else:
    M={'PSJA':'Pharr-San Juan-Alamo','EDINBURG':'Edinburg Consolidated','EDCOUCH ELSA':'Edcouch-Elsa'}
    for f in LY['isd_county']:
        n=f['properties']['SCH_DIST_N'].replace(' ISD',''); n=M.get(n,n.title())
        LAY.setdefault(('isd',n),[]).append(make_valid(shape(f['geometry'])))
for f in LY['wes_smd']:
    LAY.setdefault(('wd',f['properties']['District_N']),[]).append(make_valid(shape(f['geometry'])))
LAY={k:make_valid(unary_union(v)) for k,v in LAY.items()}
# a Weslaco commission district is a part of the city
for k in list(LAY):
    if k[0]=='wd': LAY[k]=make_valid(LAY[k].intersection(LAY[('city','Weslaco')]))
byp=collections.defaultdict(set)
for ps,bs in LEG.items(): byp[int(ps.split('-')[0])].add(bs)
assert set(byp)==set(prec), (set(byp)^set(prec))
missing_lay={e for s in EN.values() for e in s if e not in LAY}
print('entities with no layer',missing_lay,flush=True)
S={}; pieces=[]; rep=collections.Counter(); unresolved=[]
def url(bs): return LINKS[str(bs)]
for pid in sorted(byp):
    sty={}
    for bs in sorted(byp[pid]): sty.setdefault(json.dumps(O[bs]),bs)
    styles=list(sty.values())
    if len(styles)==1:
        k='Precinct %d'%pid; S[k]=dict(o=O[styles[0]],pdf=url(styles[0]),ok=True,p=str(pid),bs=styles[0]); pieces.append((k,prec[pid])); rep['single']+=1; continue
    rep['multi']+=1
    allE=set.union(*[EN[s] for s in styles]); comE=set.intersection(*[EN[s] for s in styles])
    rel=sorted(allE-comE)
    common=sorted(set.intersection(*[set(O[s]) for s in styles]))
    for combo in itertools.product((0,1),repeat=len(rel)):
        g=prec[pid]
        for e,inn in zip(rel,combo): g=g.intersection(LAY[e]) if inn else g.difference(LAY[e])
        g=make_valid(g)
        if g.geom_type=='GeometryCollection': g=unary_union([x for x in g.geoms if x.geom_type in ('Polygon','MultiPolygon')])
        if g.is_empty or area(g)<=0: continue
        want={e for e,inn in zip(rel,combo) if inn}
        match=[s for s in styles if EN[s]&set(rel)==want]
        if len(match)==1:
            s=match[0]; k='Precinct %d, ballot style %d'%(pid,s); S[k]=dict(o=O[s],pdf=url(s),ok=True,p=str(pid),bs=s)
        else:
            k='Precinct %d (part)'%pid; S.setdefault(k,dict(o=common,pdf=None,ok=False,p=str(pid),common=common)); unresolved.append((pid,sorted(want),len(match),round(area(g))))
        pieces.append((k,g))
# styles the legend lists for a precinct that got no area
noarea=[(int(p),bs) for p in map(str,sorted(byp)) for bs in sorted(byp[int(p)]) if not any(v.get('bs')==bs and v['p']==p for v in S.values()) and len(byp[int(p)])>1 and json.dumps(O[bs]) in {json.dumps(O[b]) for b in byp[int(p)]} and not any(v.get('bs') is not None and O[v['bs']]==O[bs] and v['p']==p for v in S.values())]
print('legend styles with no area on the map',noarea,flush=True)
# district check against TLC precinct attributes is not available (TLC precincts carry no districts); check vs TLC 26P district table instead (precincts26p_districts.xls) when present
mg=collections.defaultdict(list)
for k,g in pieces: mg[k].append(g)
# address points per piece (verification of the splits)
pts=json.load(open(D+'/addrpts.json')); PT=[Point(x,y) for x,y in pts]; tree=STRtree(PT)
cnt=collections.Counter()
for k,gs in mg.items():
    g=make_valid(unary_union(gs)); cnt[k]=len(tree.query(g,predicate='intersects'))
unres_pts=sum(v for k,v in cnt.items() if not S[k]['ok']); tot=sum(cnt.values())
print('address points',len(PT),'in pieces',tot,'in unresolved parts',unres_pts,flush=True)
SC=100000
def enc(coords):
    dd=[];px=py=0;last=None
    for x,y in coords:
        x,y=round(x*SC),round(y*SC)
        if (x,y)==last: continue
        dd+=[x-px,y-py];px,py=x,y;last=(x,y)
    return dd
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
json.dump(dict(C=C,S=S,geo=[x for _,x in OUT],unresolved=unresolved,report=rep,pts=dict(cnt),noarea=noarea),open(D+'/hid-build-%s-%s.json'%(CITY_SRC,ISD_SRC),'w'),ensure_ascii=False)
print(json.dumps(rep),len(C),len(S),sum(not v['ok'] for v in S.values()),flush=True)
for u in unresolved: print(u, flush=True)
