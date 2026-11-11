
# Collin County TX: random-point check of the encoded precinct/style map against the county precinct layer and the split layers.
import json,sys,random,re,collections
import numpy as np, shapely
from shapely.geometry import shape, Point
from shapely.validation import make_valid
from shapely.ops import unary_union
D=sys.argv[1]; SITE=sys.argv[2]
G=json.load(open(SITE+'/data/ballots/tx-collin-precincts.json')); B=json.load(open(SITE+'/data/ballots/tx-collin-2026-11-03.json'))
LY=json.load(open(D+'/layers.json')); ST=json.load(open(D+'/styles.json')); BLD=json.load(open(D+'/cc-build.json'))
def dec(r): return np.cumsum(np.array(r).reshape(-1,2),axis=0)
DEC=[(k,b,[dec(r) for r in rings]) for k,b,rings in G['p']]
def pip(X,Y,rings):
    ins=False
    for pts in rings:
        xs,ys=pts[:,0],pts[:,1]; xj,yj=np.roll(xs,1),np.roll(ys,1)
        c=((ys>Y)!=(yj>Y))&(X<(xj-xs)*(Y-ys)/np.where(yj-ys==0,1e-12,yj-ys)+xs); ins^=bool(c.sum()%2)
    return ins
def find(x,y):
    X,Y=x*1e5,y*1e5
    for k,b,r in DEC:
        if b[0]<=X<=b[2] and b[1]<=Y<=b[3] and pip(X,Y,r): return k
prec={f['properties']['PRECINCT']:make_valid(shape(f['geometry'])) for f in LY['prec']}
LAY={}
for f in LY['city']:
    if f.get('geometry'): LAY.setdefault('City of '+f['properties']['CITY_NAME'],[]).append(make_valid(shape(f['geometry'])))
for f in LY['isd']: LAY.setdefault(re.sub(r' ISD.*$','',f['properties']['NAME'])+' Independent School District',[]).append(make_valid(shape(f['geometry'])))
for f in LY.get('mud',[]): LAY.setdefault(re.sub(r'^Blue Meadow MUD (\d+)$',r'Blue Meadow Municipal Utility District No. \1 of Collin County',f['properties']['NAME']),[]).append(make_valid(shape(f['geometry'])))
LAY={k:make_valid(unary_union(v)) for k,v in LAY.items()}
# which local entities each printed style carries (from the contest titles)
def ents(o):
    s=set()
    for i in o:
        t=B['c'][i]['title']
        for e in LAY:
            if t.startswith(e): s.add(e)
    return s
byp=collections.defaultdict(set)
for b in ST: byp[b['precinct']].add(b['displayName'].replace(' ',''))
bs_o={v['bs']:v['o'] for v in BLD['S'].values() if v.get('bs')}
random.seed(7); tot=bad=lab=0; bl=[]
for pid,pg in prec.items():
    sts=[s for s in byp[pid] if s in bs_o]; E={s:ents(bs_o[s]) for s in sts}
    var=(set.union(*E.values())-set.intersection(*E.values())) if E else set()
    minx,miny,maxx,maxy=pg.bounds; n=t=0
    while n<30 and t<3000:
        t+=1; x,y=random.uniform(minx,maxx),random.uniform(miny,maxy); c=Point(x,y).buffer(0.00005)
        if not pg.contains(c): continue
        if any(LAY[e].intersects(c) and not LAY[e].contains(c) for e in var): continue
        n+=1; tot+=1; k=find(x,y)
        if k is None: bad+=1; bl.append((pid,'none')); continue
        s=B['s'][k]
        if s['p']!=str(pid): bad+=1; bl.append((pid,k)); continue
        if not s['ok']: lab+=1; continue
        st=[b for b,o in bs_o.items() if o==s['o'] and b in byp[pid]]
        have={e for e in var if LAY[e].contains(c)}
        if not any((E[b]&var)==have for b in st): bad+=1; bl.append((pid,k,sorted(have)))
print('points',tot,'wrong',bad,'labelled',lab,bl[:10],flush=True)
