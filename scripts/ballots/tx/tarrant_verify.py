
import select
def _sl(t): select.select([],[],[],t)
import json,sys,requests,random
import shapely.geometry as sg, shapely
from shapely.validation import make_valid
D=sys.argv[1]; s=requests.Session(); s.headers['User-Agent']='Mozilla/5.0 (KnowUS civic data; ballots)'
feats=json.load(open(D+'/subprecincts_2276.json')); prob=set(json.load(open(D+'/problem_subs.json')))
def poly(g):
    ps=[sg.Polygon(r) for r in g['rings'] if len(r)>=4]; u=ps[0]
    for p in ps[1:]: u=u.symmetric_difference(p)
    return make_valid(u)
def ask(x,y):
    for i in range(5):
        try:
            t=s.post('https://gisit.tarrantcounty.com/findmyballot/Home/GetBallotByLocation',data={'X':x,'Y':y,'SpatialReference':2276,'ElectionID':522},timeout=60).text
            return sorted({b['FilePath'].split('/')[-1] for b in json.loads(json.loads(t)).get('Ballots',[]) if b.get('Exists') and '/English-Spanish/' in b['FilePath']})
        except Exception: _sl(3+3*i)
    return None
rng=random.Random(7); out={'prob':{},'rand':[]}
G={f['attributes']['SUB_ID']:poly(f['geometry']) for f in feats}
for sub in prob:
    g=G[sub]; minx,miny,maxx,maxy=g.bounds; pts=[]; n=0
    while len(pts)<8 and n<2000:
        n+=1; p=sg.Point(rng.uniform(minx,maxx),rng.uniform(miny,maxy))
        if g.contains(p): pts.append(p)
    out['prob'][sub]=[[p.x,p.y,ask(p.x,p.y)] for p in pts]; _sl(0.1)
print('prob done',flush=True)
U=shapely.union_all(list(G.values())); minx,miny,maxx,maxy=U.bounds
while len(out['rand'])<600:
    p=sg.Point(rng.uniform(minx,maxx),rng.uniform(miny,maxy))
    if not U.contains(p): continue
    out['rand'].append([p.x,p.y,ask(p.x,p.y)]); _sl(0.1)
    if len(out['rand'])%100==0: print('rand',len(out['rand']),flush=True); json.dump(out,open(D+'/verify.part.json','w'))
json.dump(out,open(D+'/verify.json','w')); print('DONE',flush=True)
