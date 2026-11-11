
# Brazoria County TX, Nov 3 2026 General & Joint Election: ballot data + precinct-split map.
# Inputs (DIR): parsed.json (bparse.py over the county clerk's 89 per-precinct sample-ballot PDFs), links.json (PDF urls),
# county_layers.json (Brazoria County GIS: Voter Precincts 2026, City Limits, School Districts), addrpts.json (county Address Points).
# python3 brazoria_build.py DIR
import json,re,sys,collections,itertools
import numpy as np, shapely, pyproj
from shapely.geometry import Point
import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely.strtree import STRtree
D=sys.argv[1]
PJ={x['file'][:-4]:x for x in json.load(open(D+'/parsed.json'))}
LINKS=dict(json.load(open(D+'/links.json')))
LY=json.load(open(D+'/county_layers.json'))
TR=pyproj.Transformer.from_crs(4326,32615,always_xy=True)
def area(g): return shapely.transform(g,lambda xy: np.column_stack(TR.transform(xy[:,0],xy[:,1]))).area
def esri_poly(geom):
    outers=[];holes=[]
    for r in geom['rings']:
        (holes if sg.LinearRing(r).is_ccw else outers).append(r)
    polys=[sg.Polygon(o) for o in outers]
    for h in holes:
        hp=sg.Polygon(h)
        for i,p in enumerate(polys):
            if p.contains(hp.representative_point()): polys[i]=sg.Polygon(p.exterior.coords,[*[x.coords for x in p.interiors],h]); break
    return make_valid(sg.MultiPolygon(polys) if len(polys)>1 else polys[0])
PARTY={'REP':'Republican','DEM':'Democratic','LIB':'Libertarian','GRN':'Green','IND':'Independent','NP':''}
def norm(c):
    t=c['title'].strip(); h=c['header'] or ''
    if h.startswith('Brazoria Central Appraisal District'):
        m=re.match(r'^Director, Position (\d+)$',t); return 'Brazoria Central Appraisal District Board of Directors','Position '+m[1]
    if t=='U.S. Senator': return 'United States Senator',''
    m=re.match(r'^U\.S\. Representative District (\d+)$',t)
    if m: return 'United States Representative','District '+m[1]
    m=re.match(r'^(State Representative|State Senator),? District (\d+)$',t)
    if m: return m[1],'District '+m[2]
    m=re.match(r'^Member, State Board of Education, District (\d+)$',t)
    if m: return 'Member, State Board of Education','District '+m[1]
    m=re.match(r'^(Justice, Supreme Court|Judge, Court of Criminal Appeals|Justice, \d+\w\w Court of Appeals District), Place (\d+)\s*(?:-\s*(Unexpired Term))?$',t)
    if m: return m[1],'Place '+m[2]+(', Unexpired Term' if m[3] else '')
    m=re.match(r'^District Judge, (\d+\w\w Judicial District)$',t)
    if m: return 'District Judge',m[1]
    m=re.match(r'^County Commissioner Precinct (\d+)$',t)
    if m: return 'County Commissioner','Precinct No. '+m[1]
    m=re.match(r'^Justice of the Peace Precinct (\d+), Place (\d+)$',t)
    if m: return 'Justice of the Peace','Precinct No. %s, Place %s'%(m[1],m[2])
    m=re.match(r'^County Constable Precinct (\d+)\s*-\s*(Unexpired Term)$',t)
    if m: return 'Constable','Precinct No. %s, Unexpired Term'%m[1]
    if t=='Criminal District Attorney Brazoria County': return 'Criminal District Attorney',''
    m=re.match(r'^Judge, County Court at Law No\. (\d+)$',t)
    if m: return 'Judge, County Court at Law','No. '+m[1]
    return t,''
EN={}; NB={}
for k,x in PJ.items():
    assert x['nbox']==x['nopt'],(k,x['nbox'],x['nopt'])
    out=[]; es=set()
    for c in x['contests']:
        m=re.match(r'^(City of Freeport|Sweeny ISD) Proposition (\w+)$',c['title'])
        if m:
            ent='City of Freeport' if 'Freeport' in m[1] else 'Sweeny Independent School District'
            es.add(('city','FREEPORT') if 'Freeport' in m[1] else ('isd','Sweeny ISD'))
            out.append(dict(t='q',title='%s, Proposition %s'%(ent,m[2]),pre='',q=c['body'],r=[o for o,_ in c['opts']])); continue
        ti,d=norm(c)
        cands=[[o,PARTY.get(p,'')] for o,p in c['opts']]
        out.append(dict(t='r',title=ti,d=d,vf='1',c=cands,wi=c['wi'],note=[]))
    NB[k]=out; EN[k]=es
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
prec={int(f['attributes']['PRECINCT']):esri_poly(f['geometry']) for f in LY['vp']}
LAY={('city','FREEPORT'):make_valid(unary_union([esri_poly(f['geometry']) for f in LY['city'] if f['attributes']['Name']=='FREEPORT'])),
     ('isd','Sweeny ISD'):make_valid(unary_union([esri_poly(f['geometry']) for f in LY['isd'] if f['attributes']['Name']=='Sweeny ISD']))}
byp=collections.defaultdict(list)
for k in PJ: byp[int(k.split('-')[0])].append(k)
print('precincts on map with no ballot',sorted(set(prec)-set(byp)),'ballots with no precinct',sorted(set(byp)-set(prec)),flush=True)
S={}; pieces=[]; rep=collections.Counter(); unresolved=[]
for pid in sorted(prec):
    styles=sorted(byp.get(pid,[]))
    if not styles:
        k='Precinct %d'%pid; S[k]=dict(o=None,pdf=None,ok=False,p=str(pid)); pieces.append((k,prec[pid])); rep['noballot']+=1; continue
    if len(styles)==1:
        s=styles[0]; k='Precinct %s'%PJ[s]['prec']; S[k]=dict(o=O[s],pdf=LINKS[s],ok=True,p=str(pid),bs=s); pieces.append((k,prec[pid])); rep['single']+=1; continue
    rep['multi']+=1
    allE=set.union(*[EN[s] for s in styles]); comE=set.intersection(*[EN[s] for s in styles]); rel=sorted(allE-comE)
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
            s=match[0]; k='Precinct %s'%PJ[s]['prec']
            S[k]=dict(o=O[s],pdf=LINKS[s],ok=True,p=str(pid),bs=s)
        else:
            k='Precinct %d (part)'%pid; S.setdefault(k,dict(o=common,pdf=None,ok=False,p=str(pid),common=common)); unresolved.append((pid,sorted(want),len(match),round(area(g))))
        pieces.append((k,g))
mg=collections.defaultdict(list)
for k,g in pieces: mg[k].append(g)
pts=json.load(open(D+'/addrpts.json')); PT=[Point(x,y) for x,y in pts if x and y]; tree=STRtree(PT)
cnt=collections.Counter()
for k,gs in mg.items(): cnt[k]=len(tree.query(make_valid(unary_union(gs)),predicate='intersects'))
print('address points',len(PT),'in pieces',sum(cnt.values()),'in labelled pieces',{k:v for k,v in cnt.items() if not S[k]['ok']},flush=True)
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
        rings.append(enc(p.exterior.coords)); rings+=[enc(i.coords) for i in p.interiors if sg.Polygon(i).area>0]
    rings=[r for r in rings if len(r)>=8]
    if not rings: continue
    b=g.bounds; OUT.append((area(g),[k,[int(b[0]*SC)-1,int(b[1]*SC)-1,int(b[2]*SC)+1,int(b[3]*SC)+1],rings]))
OUT.sort(key=lambda x:x[0]); used={x[1][0] for x in OUT}
COM=sorted(set.intersection(*[set(v['o']) for v in S.values() if v['ok']]))
for v in S.values():
    if not v['ok']: v['o']=COM; v['common']=COM
S={k:v for k,v in S.items() if k in used}
json.dump(dict(C=C,S=S,geo=[x for _,x in OUT],unresolved=unresolved,report=rep,pts=dict(cnt)),open(D+'/bz-build.json','w'),ensure_ascii=False)
print(json.dumps(rep),len(C),len(S),sum(not v['ok'] for v in S.values()),flush=True)
for k,v in S.items():
    if '-' in k or not v['ok']: print(k,v['ok'],len(v['o']),cnt[k],flush=True)
