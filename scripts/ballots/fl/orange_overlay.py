
import json,sys,re
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid
OD=sys.argv[1]
def load(f,key):
    out=[]
    for ft in json.load(open(OD+'/'+f))['features']:
        if not ft.get('geometry'): continue
        g=make_valid(shape(ft['geometry'])).buffer(0); out.append((g,ft['properties']))
    return out
P=load('pcts.geojson',0); CD=load('cd26.geojson',0); CC=load('cc26.geojson',0); SUB=load('subs-geo.json',0)
VL=unary_union([g for g,p in load('spc.geojson',0) if p.get('SPC_INT')==7])
BL=json.load(open(OD+'/ballots.json'))  # list of {label,pct,d}
cont=json.load(open(OD+'/contested.json'))
byp={}
for b in BL: byp.setdefault(b['pct'],[]).append(b)
def inter(g,layer):
    t=STRtree([x[0] for x in layer]); out=[]
    for i in t.query(g):
        h=g.intersection(layer[i][0])
        if h.area>0: out.append((h,layer[i][1]))
    return out
res={}; rep=[]
for g,pp in P:
    pct=pp['Precinct']; A=g.area; pieces=[]
    for h1,p1 in inter(g,CD):
        for h2,p2 in inter(h1,CC):
            for h3,p3 in inter(h2,SUB):
                for vl,h4 in ((1,h3.intersection(VL)),(0,h3.difference(VL))):
                    if h4.area<=0: continue
                    att={'CNG':p1['DISTRICT'],'CC':p2['DIST'],'HSE':p3['HSE'],'SEN':p3['SEN'],'SW':p3['SW'],'SB':p3['SB']}
                    e={k:v for k,v in att.items() if v in cont[k]}
                    if vl: e['CDD']=1
                    pieces.append((h4,e,att,p3['CC']))
    cov=sum(x[0].area for x in pieces)/A
    bs=byp.get(pct,[])
    pr=[]
    for h,e,att,oldcc in pieces:
        m=[b['label'] for b in bs if b['d']==e]
        pr.append(dict(frac=h.area/A,e=e,m=m,ccdiff=oldcc!=att['CC']))
    big=[x for x in pr if x['frac']>=0.01]
    # assign
    asg={}
    for (h,e,att,oc),x in zip(pieces,pr):
        if len(x['m'])==1: asg.setdefault(x['m'][0],[]).append(h)
    ok_big=all(len(x['m'])==1 for x in big)
    res[pct]=dict(n=len(bs),cov=cov,ok_big=ok_big,big=[(round(x['frac'],3),x['e'],x['m']) for x in big],
                  unmatched_frac=round(sum(x['frac'] for x in pr if len(x['m'])!=1),4),
                  used=sorted(asg), geo={k:mapping(unary_union(v).simplify(0.00002)) for k,v in asg.items()}, pts={k:list(max(v,key=lambda z:z.area).representative_point().coords[0]) for k,v in asg.items()})
json.dump(res,open(OD+'/overlay.json','w'))
print('DONE',len(res),flush=True)
