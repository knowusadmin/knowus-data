# Tarrant County TX, Nov 3 2026: ballot data + map for the app (publisher 774cbf5c, v75).
# Inputs in DIR: subprecincts_4326.json (VotingSubPrecincts layer), lookup.json (tarrant_lookup.py: Find My Ballot answer at 1-2
# interior points per sub-precinct), verify.json (tarrant_verify.py: 8 more points in each sub-precinct whose first answers were not
# one ballot of its own precinct, + 600 random county points), parsed_*.json (tarrant_parse.py over the 788 English-Spanish PDFs).
# A sub-precinct gets the ballot the service gives inside it when all its answers agree; mixed or empty ones are labelled (ok:false).
# Sub-precincts of one precinct with the same printed contests are one piece. Pieces under 10 m2 (map slivers) are left out.
# python3 tarrant_build.py DIR SITE
import json,re,sys,glob,collections
import numpy as np, shapely, pyproj
import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.validation import make_valid
D=sys.argv[1]; R=sys.argv[2]
TP=[]
for f in sorted(glob.glob(D+'/parsed_*.json')): TP+=json.load(open(f))
for p in TP: assert 'error' not in p and p['nbox']==p['nopt'],p['file']
PRDT={p['file']:p for p in TP}
TRm=pyproj.Transformer.from_crs(4326,32614,always_xy=True)
def to_m(g): return shapely.transform(g,lambda xy: np.column_stack(TRm.transform(xy[:,0],xy[:,1])))
def rpoly(g):
    ps=[make_valid(sg.Polygon(r)) for r in g['rings'] if len(r)>=4]; u=ps[0]
    for p in ps[1:]: u=u.symmetric_difference(p)
    return make_valid(u)
G4={f['attributes']['SUB_ID']:rpoly(f['geometry']) for f in json.load(open(D+'/subprecincts_4326.json'))}
LK=json.load(open(D+'/lookup.json')); VF=json.load(open(D+'/verify.json'))
def es(r): return sorted({p.split('/')[-1] for p in r if '/English-Spanish/' in p})
FINAL={}
for x in LK:
    sub=x['sub']; pr=sub[:4]; sets=[tuple(es(r)) for r in x['res'] if es(r)]
    own=set(s for s in sets if all(f[3:7]==pr for f in s))
    if len(own)==1:
        FINAL[sub]=next(iter(own))[0]; continue
    ans=[tuple(es(r)) for r in x['res']]+[tuple(a) for _,_,a in VF['prob'].get(sub,[]) if a is not None]
    ne=[a for a in ans if a]; u=set(ne)
    FINAL[sub]=next(iter(u))[0] if (len(u)==1 and len(next(iter(u)))==1) else None
PTY={'REP':'Republican','DEM':'Democratic','LIB':'Libertarian','GRN':'Green','IND':'Independent','':''}
def norm(t):
    if t=='United States Senator': return t,''
    for pat in (r'^(United States Representative|State Representative|State Senator|Member, State Board of Education),? (District \d+)$',
                r'^(Justice, Supreme Court|Judge, Court of Criminal Appeals|Justice, \d+\w\w Court of Appeals District), (Place \d+)$',
                r'^(District Judge), (\d+\w\w Judicial District)$',
                r'^(County Commissioner|Constable|Justice of the Peace),? (Precinct (?:No\. )?\d+(?:, Place \d+)?)$'):
        m=re.match(pat,t)
        if m: return m[1],m[2]
    return t,''
def t_norm(t):
    u=''
    m=re.match(r'^(.*?),?\s*\((Unexpired Term)\)$',t)
    if m: t,u=m[1].strip(' ,'),'Unexpired Term'
    t=re.sub(r'^(State Representative|State Senator) (District \d+)$',r'\1, \2',t)
    ti,d=norm(t)
    if u: d=(d+', '+u) if d else u
    return ti,d
def t_entity(g): return re.sub(r'\s+(General|Special)\s+Election.*$','',(g or '').split(' Elecci')[0]).strip() or None
def t_conv(c):
    if c['t']=='r':
        e=t_entity(c['grp']); t=c['title']
        if e and e not in ('Tarrant County','State Senate District 22','State Representative District 93') and t.startswith(e):
            rest=t[len(e):].strip(' ,'); u=''
            m=re.match(r'^(.*?)\s*\(?(Unexpired Term)\)?$',rest)
            if m and m[1]!=rest: rest,u=m[1].strip(' ,-'),'Unexpired Term'
            rest=re.sub(r'\s*-\s*Three-\s*Year Term$','',rest)
            m=re.match(r'^(Member of the Council|City Council(?:,)?(?: Council)?(?: Member)?|Trustee|Board of Directors -)?,?\s*((?:At-Large )?Place \d+)$',rest)
            if m: ti,d=e+', '+{'Trustee':'Trustee','Board of Directors -':'Board of Directors'}.get(m[1] or '','City Council'),m[2]
            else: ti,d=e+', '+rest,''
            if u: d=(d+', '+u) if d else u
        else: ti,d=t_norm(t)
        return dict(t='r',title=ti,d=d,vf=c['vf'],c=[[n,PTY.get(p,p)] for n,p in c['c']],wi=c['wi'],note=[])
    q=c['q']; m=re.search(r'\s(¿|ESTO ES|ESTE ES|ESTA ES|ESTO REPRESENTA|“La |"La |La reautorización|La emisión|Ratificar)',q); q=q[:m.start()].strip() if m else q
    pre=''
    m=re.match(r'^(THIS IS A (?:PROPERTY )?TAX INCREASE)[;.]?\s*(.*)$',q)
    if m: pre,q=m[1],m[2]
    q=re.sub(r'\s*THIS IS A (PROPERTY )?TAX INCREASE\.?$','',q).strip()
    return dict(t='q',title=re.sub(r'\s+Proposition (\w+)$',r', Proposition \1',c['title']),pre=pre,q=q.strip(' "“”'),r=c['r'])
NBT={p['file']:[t_conv(c) for c in p['contests']] for p in TP}
def ck(c): return json.dumps(c,sort_keys=True)
CT=[];IX={}
for k in sorted(NBT,key=lambda k:-len(NBT[k])):
    prev=-1
    for c in NBT[k]:
        key=ck(c)
        if key not in IX:
            CT.insert(prev+1,c); IX={kk:(v if v<=prev else v+1) for kk,v in IX.items()}; IX[key]=prev+1
        prev=IX[key]
OT={k:[IX[ck(c)] for c in v] for k,v in NBT.items()}
def tsig(f): return json.dumps(NBT[f])
byPrec=collections.defaultdict(list)
for sub in FINAL: byPrec[sub[:4]].append(sub)
PIE={}
for pr,subs in byPrec.items():
    grp=collections.defaultdict(list)
    for sub in subs: b=FINAL[sub]; grp[('ok',tsig(b)) if b else ('none',sub)].append(sub)
    if len(grp)==1 and next(iter(grp))[0]=='ok': PIE['Precinct '+pr]=dict(subs=sorted(subs),f=FINAL[subs[0]])
    else:
        for k,ss in grp.items(): PIE['Precinct '+', '.join(sorted(ss))]=dict(subs=sorted(ss),f=FINAL[ss[0]] if k[0]=='ok' else None)
okk=[v for v in PIE.values() if v['f']]
common=sorted(set.intersection(*[set(OT[v['f']]) for v in okk]))
TBASE='https://gisit.tarrantcounty.com/ballots/English-Spanish/'; SC=100000
def enc(coords):
    dd=[];px=py=0;last=None
    for x_,y_ in coords:
        x_,y_=round(x_*SC),round(y_*SC)
        if (x_,y_)==last: continue
        dd+=[x_-px,y_-py];px,py=x_,y_;last=(x_,y_)
    return dd
ST={};OUT=[]
for k,v in PIE.items():
    g=make_valid(unary_union([G4[s] for s in v['subs']]))
    if to_m(g).area<10: continue
    ST[k]=dict(o=OT[v['f']],pdf=TBASE+v['f'],ok=True,p=k,bs=PRDT[v['f']]['prec'],parts=v['subs']) if v['f'] else dict(o=common,pdf=None,ok=False,p=k,parts=v['subs'])
    gs=g.simplify(0.000005,preserve_topology=True); polys=[]
    for xx in getattr(gs,'geoms',[gs]):
        if xx.geom_type=='Polygon': polys.append(xx)
        elif xx.geom_type=='MultiPolygon': polys+=list(xx.geoms)
    rings=[]
    for pg in polys:
        if to_m(pg).area<0.5: continue
        rings.append(enc(pg.exterior.coords)); rings+=[enc(i.coords) for i in pg.interiors if sg.Polygon(i).area>0]
    rings=[r for r in rings if len(r)>=8]
    if not rings: ST.pop(k); continue
    b=gs.bounds; OUT.append((to_m(g).area,[k,[int(b[0]*SC)-1,int(b[1]*SC)-1,int(b[2]*SC)+1,int(b[3]*SC)+1],rings]))
OUT.sort(key=lambda z:z[0])
out=dict(read='2026-11-11',county='Tarrant County, Texas',
 source='Tarrant County Elections Administration — the official sample ballot for every voting sub-precinct (Nov 3, 2026 Joint General and Special Elections; 788 ballot styles from the county’s Find My Ballot service, each placed by asking that service for the ballot at a point inside the sub-precinct), on the county’s Voting Sub-Precincts map (1,703 sub-precincts)',
 sourceUrl='https://www.tarrantcountytx.gov/en/elections.html',lookup='https://gisit.tarrantcounty.com/findmyballot',office='Tarrant County Elections Administration',c=CT,s=ST,common=common)
json.dump(out,open(R+'/data/ballots/tx-tarrant-2026-11-03.json','w'),ensure_ascii=False,separators=(',',':'))
geo=dict(v=1,source=['Tarrant County — Voting Sub-Precincts (1,703), the map behind the county’s Find My Ballot service','https://mapit.tarrantcounty.com/arcgis/rest/services/Dynamic/VotingSubPrecincts/MapServer/0','2026-11-11'],
 scale=100000.0,note='Each polygon is a precinct, or the sub-precincts of a precinct that share one printed ballot. Smallest first.',p=[z for _,z in OUT])
json.dump(geo,open(R+'/data/ballots/tx-tarrant-precincts.json','w'),ensure_ascii=False,separators=(',',':'))
print('ok',len(ST),sum(1 for v in ST.values() if not v['ok']),len(CT),len(common),flush=True)
