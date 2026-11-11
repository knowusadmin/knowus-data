
import json,sys,numpy as np,shapely,pyproj,collections
from shapely.geometry import shape
from shapely.validation import make_valid
D=sys.argv[1]
G=json.load(open(D+'/tlc-hidalgo.geojson')); prj=open(D+'/../tlc/Precincts26P.prj').read()
T2=pyproj.Transformer.from_crs(pyproj.CRS.from_wkt(prj),4326,always_xy=True)
TR=pyproj.Transformer.from_crs(4326,32614,always_xy=True)
A=lambda g: shapely.transform(g,lambda xy: np.column_stack(TR.transform(xy[:,0],xy[:,1]))).area
P={int(f['properties']['PREC']):make_valid(shapely.transform(make_valid(shape(f['geometry'])),lambda xy: np.column_stack(T2.transform(xy[:,0],xy[:,1])))) for f in G['features']}
CM={int(f['properties']['DISTRICT']):make_valid(shape(f['geometry'])) for f in json.load(open(D+'/commissioners.geojson'))['features']}
need=json.load(open(D+'/need.json')); bad=[]; split=[]
for p,g in P.items():
    ar={d:A(g.intersection(c)) for d,c in CM.items()}; tot=A(g); best=max(ar,key=ar.get)
    if ar[best]/tot<0.98: split.append((p,{d:round(a/tot,3) for d,a in ar.items() if a>0}))
    cm=need[str(p)][0][0]
    want=['Precinct No. %d'%best] if best in (2,4) else []
    if cm!=want: bad.append((p,cm,best,round(ar[best]/tot,3)))
print('bad',bad); print('split',split)
