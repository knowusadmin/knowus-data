
import select
def _sl(t): select.select([],[],[],t)
import json,sys,time,requests,random
import shapely.geometry as sg
from shapely.validation import make_valid
D=sys.argv[1]; s=requests.Session(); s.headers['User-Agent']='Mozilla/5.0 (KnowUS civic data; ballots)'
def gj(u,d,tries=6):
    for i in range(tries):
        try: return s.post(u,data=d,timeout=90).json()
        except Exception as e: _sl(3+i*3)
    raise Exception('fail '+u)
L='https://mapit.tarrantcounty.com/arcgis/rest/services/Dynamic/VotingSubPrecincts/MapServer/0/query'
import os
feats=json.load(open(D+'/subprecincts_2276.json')) if os.path.exists(D+'/subprecincts_4326.json') else []
lo=-1
while not feats or False:
    q=gj(L,{'where':'OBJECTID_1>%d'%lo,'outFields':'*','returnGeometry':'true','outSR':2276,'orderByFields':'OBJECTID_1','f':'json'})
    fs=q.get('features',[])
    if not fs: break
    feats+=fs; lo=max(f['attributes']['OBJECTID_1'] for f in fs); print('feats',len(feats),flush=True)
json.dump(feats,open(D+'/subprecincts_2276.json','w'))
q=gj(L,{'where':'1=1','outFields':'OBJECTID_1','returnGeometry':'true','outSR':4326,'geometryPrecision':7,'f':'json','resultRecordCount':1})
feats4=[];lo=-1
while True:
    q=gj(L,{'where':'OBJECTID_1>%d'%lo,'outFields':'OBJECTID_1,SUB_ID,Precinct,Pct_Sub','returnGeometry':'true','outSR':4326,'geometryPrecision':7,'orderByFields':'OBJECTID_1','f':'json'})
    fs=q.get('features',[])
    if not fs: break
    feats4+=fs; lo=max(f['attributes']['OBJECTID_1'] for f in fs)
json.dump(feats4,open(D+'/subprecincts_4326.json','w'))
def poly(g):
    ps=[sg.Polygon(r) for r in g['rings'] if len(r)>=4]
    u=ps[0]
    for p in ps[1:]: u=u.symmetric_difference(p)
    return make_valid(u)
out=[]  # RESUME
import os
if os.path.exists(D+'/lookup.part.json'): out=json.load(open(D+'/lookup.part.json'))
done={x['oid'] for x in out}
for f in feats:
    if f['attributes']['OBJECTID_1'] in done: continue
    g=poly(f['geometry']); pts=[g.representative_point()]
    c=g.centroid
    if g.contains(c): pts.append(c)
    res=[]
    for p in pts:
        for i in range(5):
            try:
                t=s.post('https://gisit.tarrantcounty.com/findmyballot/Home/GetBallotByLocation',data={'X':p.x,'Y':p.y,'SpatialReference':2276,'ElectionID':522},timeout=60).text
                res.append([b['FilePath'] for b in json.loads(json.loads(t)).get('Ballots',[]) if b.get('Exists')]); break
            except Exception as e: _sl(3+3*i)
        _sl(0.1)
    out.append(dict(sub=f['attributes']['SUB_ID'],oid=f['attributes']['OBJECTID_1'],res=res))
    if len(out)%100==0: print('lk',len(out),flush=True); json.dump(out,open(D+'/lookup.part.json','w'))
json.dump(out,open(D+'/lookup.json','w')); print('DONE',flush=True)
