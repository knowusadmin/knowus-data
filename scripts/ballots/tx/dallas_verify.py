import json,sys,random,collections
import numpy as np, shapely, pyproj, shapefile
import shapely.geometry as sg
from shapely.strtree import STRtree
from shapely.validation import make_valid
from shapely.geometry import shape
D=sys.argv[1]; R=sys.argv[2]
geo=json.load(open(R+'/data/ballots/tx-dallas-precincts.json')); bal=json.load(open(R+'/data/ballots/tx-dallas-2026-11-03.json'))
B=json.load(open(D+'/dallas-build.json')); SUBSTY=B['substy']
def dec(r,sc):
    x=y=0;pts=[]
    for i in range(0,len(r),2): x+=r[i];y+=r[i+1];pts.append((x/sc,y/sc))
    return pts
pieces=[]
for k,bb,rings in geo['p']:
    # rings: exterior then holes, polygon by polygon; rebuild by even-odd: point in piece iff inside odd number of rings
    pieces.append((k,[sg.Polygon(dec(r,geo['scale'])) for r in rings]))
def app_find(pt):
    for k,rs in pieces:  # smallest first, even-odd
        n=sum(1 for r in rs if r.contains(pt))
        if n%2==1: return k
    return None
def esri_poly(geom):
    outers=[];holes=[]
    for r in geom['rings']: (holes if sg.LinearRing(r).is_ccw else outers).append(r)
    polys=[sg.Polygon(o) for o in outers]
    for h in holes:
        hp=sg.Polygon(h)
        for i,p in enumerate(polys):
            if p.contains(hp.representative_point()): polys[i]=sg.Polygon(p.exterior.coords,[*[x.coords for x in p.interiors],h]); break
    return make_valid(sg.MultiPolygon(polys) if len(polys)>1 else polys[0])
SUB=json.load(open(D+'/subprecincts.json'))
SG=[esri_poly(f['geometry']) for f in SUB]; SID=[f['attributes']['COMBO1'] for f in SUB]; T=STRtree(SG)
r=shapefile.Reader(D+'/../tlc/Precincts26P.shp'); prj=open(D+'/../tlc/Precincts26P.prj').read()
TRL=pyproj.Transformer.from_crs(pyproj.CRS.from_wkt(prj),4326,always_xy=True)
TG=[];TP=[]
for i,rec in enumerate(r.iterRecords()):
    if rec['CNTY']==113:
        g=shapely.transform(shape(r.shape(i).__geo_interface__),lambda xy: np.column_stack(TRL.transform(xy[:,0],xy[:,1]))); TG.append(make_valid(g)); TP.append(rec['PREC'])
TT=STRtree(TG)
cu=shapely.unary_union(SG); minx,miny,maxx,maxy=cu.bounds
random.seed(70); N=int(sys.argv[3]); done=0; c=collections.Counter(); bad=[]
while done<N:
    pt=sg.Point(random.uniform(minx,maxx),random.uniform(miny,maxy))
    hit=[SID[i] for i in T.query(pt,predicate='within')]
    if len(hit)!=1: c['outside/edge']+=1; continue
    done+=1; sp=hit[0]; want=SUBSTY[sp]; k=app_find(pt)
    got=bal['s'][k]['bs'] if k else None
    if got!=want: c['style mismatch']+=1; bad.append((pt.x,pt.y,sp,want,k)); continue
    c['style ok']+=1
    th=[TP[i] for i in TT.query(pt,predicate='within')]
    if th and th[0]==sp.split('-')[0]: c['tlc precinct agrees']+=1
    elif th: c['tlc precinct differs']+=1; bad.append(('tlc',pt.x,pt.y,sp,th))
    else: c['tlc none']+=1
print(dict(c)); print(bad[:15])
