
# Michigan ballots: random-point checks (worker 448daed7). python3 mi_verify.py DIR OUTDIR N_per_precinct SEED
import json,sys,glob,random,collections,re,os
import shapely.geometry as sg, shapely
from shapely.ops import unary_union
sys.argv+=[]
D,O,NP,SEED=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
random.seed(SEED)
def dec(r,sc):
    pts=[];x=y=0
    for i in range(0,len(r),2): x+=r[i];y+=r[i+1];pts.append((x/sc,y/sc))
    return pts
def pip(X,Y,rings):
    ins=False
    for r in rings:
        x=y=0;pts=[]
        for i in range(0,len(r),2): x+=r[i];y+=r[i+1];pts.append((x,y))
        n=len(pts);j=n-1
        for i in range(n):
            xi,yi=pts[i];xj,yj=pts[j]
            if (yi>Y)!=(yj>Y) and X<(xj-xi)*(Y-yi)/(yj-yi)+xi: ins=not ins
            j=i
    return ins
def geoFind(G,x,y):
    sc=G['scale'];X=x*sc;Y=y*sc
    for p in G['p']:
        b=p[1]
        if X<b[0] or X>b[2] or Y<b[1] or Y>b[3]: continue
        if pip(X,Y,p[2]): return p[0]
    return None
sys.path.insert(0,D); 
PF=json.load(open(D+'/geo/precincts_4326.json'))
from mi_build_geo import rpoly
PG={x['attributes']['PrecinctID']:rpoly(x['geometry']) for x in PF}
from shapely.strtree import STRtree
ids=list(PG); tree=STRtree([PG[i] for i in ids])
res=dict(points=0,found=0,same_precinct=0,miss=[],wrong=[],ok_piece=0,labelled_piece=0)
for f in sorted(glob.glob(O+'/mi-*-precincts.json')):
    G=json.load(open(f)); B=json.load(open(f.replace('-precincts.json','-2026-11-03.json')))
    pids=sorted({v['pid'] for v in B['s'].values()})
    for pid in pids:
        g=PG[pid]
        if g.area==0: continue
        minx,miny,maxx,maxy=g.bounds;k=0;tries=0
        while k<NP and tries<200:
            tries+=1;x=random.uniform(minx,maxx);y=random.uniform(miny,maxy)
            if not g.contains(sg.Point(x,y)): continue
            # skip points within ~3 m of the precinct line
            bd=g.boundary if g.boundary is not None else unary_union([q.boundary for q in g.geoms if q.geom_type in ('Polygon','MultiPolygon')])
            if bd.distance(sg.Point(x,y))<0.00003: continue
            k+=1;res['points']+=1
            key=geoFind(G,x,y)
            if key is None: res['miss'].append([pid,x,y]);continue
            res['found']+=1
            S=B['s'][key]
            if S['pid']==pid: res['same_precinct']+=1
            else: res['wrong'].append([pid,S['pid'],x,y])
            res['ok_piece' if S['ok'] else 'labelled_piece']+=1
res['miss_n']=len(res['miss']);res['wrong_n']=len(res['wrong'])
json.dump(res,open(O+'/verify_points.json','w'))
print(json.dumps({k:v for k,v in res.items() if not isinstance(v,list)}))
