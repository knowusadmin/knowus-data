
# Fort Bend County TX, Nov 3 2026 General: build the app's ballot data + precinct-split map from the county's official
# per-ballot-style sample PDFs (parsed by fbparse.py) and the county's official GIS layers.
# python3 fortbend_build.py parsed.json links.json precincts.geojson outdir
import json,re,sys,collections,requests
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.validation import make_valid
import shapely,pyproj
P=json.load(open(sys.argv[1])); LINKS=dict(json.load(open(sys.argv[2]))); G=json.load(open(sys.argv[3])); OUT=sys.argv[4]
B='https://gisportal.fortbendcountytx.gov/arcgis/rest/services/InteractiveMap/'
def fetch(svc,lid,where='1=1'):
    out=[];off=0
    while True:
        r=requests.get(B+svc+'/%d/query'%lid,params={'where':where,'outFields':'*','outSR':4326,'f':'geojson','resultOffset':off,'resultRecordCount':1000},timeout=60).json()
        fs=r.get('features',[]); out+=fs
        if len(fs)<1000: break
        off+=len(fs)
    return out
U=lambda fs: make_valid(unary_union([make_valid(shape(f['geometry'])) for f in fs]))
# City of Houston: full-purpose city limits + Houston's limited-purpose annexations (their residents vote on charter amendments, Tex. Loc. Gov't Code 43.130)
HOU=make_valid(unary_union([U([f for f in fetch('Boundaries_Public/MapServer',4) if f['properties']['CityName']=='HOUSTON']),
                            U([f for f in fetch('Boundaries_Public/MapServer',17) if f['properties']['CITYNAME']=='HOUSTON'])]))
FBI=U([f for f in fetch('Schools_Public/MapServer',2) if f['properties']['schooldistname']=='FT BEND ISD'])
BUR=U([f for f in fetch('Water_Districts_Public/MapServer',1) if f['properties']['MUD_NAME']=='Burney Road MUD'])
TR=pyproj.Transformer.from_crs(4326,32615,always_xy=True)
def area(g): return shapely.transform(g,lambda xy: __import__('numpy').column_stack(TR.transform(xy[:,0],xy[:,1]))).area
SMALL={'OF','THE','AND','AT','FOR','DE'}
def nc(w):
    if re.fullmatch(r'(II|III|IV|JR\.?|SR\.?)',w): return w.title() if w.startswith(('JR','SR')) else w
    if re.fullmatch(r'[A-Z]\.?',w): return w
    def cap(s):
        s=s.lower()
        s=re.sub(r"^(\W*)(\w)",lambda m:m[1]+m[2].upper(),s)
        s=re.sub(r"^(\W*)(mc)(\w)",lambda m:m[1]+'Mc'+m[3].upper(),s,flags=re.I)
        s=re.sub(r"^(\W*o')(\w)",lambda m:m[1].title()+m[2].upper(),s)
        return s
    return '-'.join(cap(p) for p in w.split('-'))
def name(s): return ' '.join(nc(w) for w in s.split())
def tc(s):
    out=[]
    for i,w in enumerate(s.split()):
        m=re.fullmatch(r'(\d+)(ST|ND|RD|TH)(,?)',w)
        if m: out.append(m[1]+m[2].lower()+m[3]); continue
        if w.rstrip(',') in SMALL and i: out.append(w.lower()); continue
        if w in ('MUD','ISD'): out.append(w); continue
        out.append('-'.join(p[:1]+p[1:].lower() for p in w.split('-')))
    return ' '.join(out)
PARTY={'REP':'Republican','DEM':'Democratic','LIB':'Libertarian','GRE':'Green','IND':'Independent','':''}
def split_title(t):
    t=t.replace(', —',' —')
    m=re.match(r'^(.*?)(?:,| —)\s*((?:DISTRICT|PLACE|PRECINCT)\b.*)$',t) or re.match(r'^(STATE REPRESENTATIVE|JUDGE, COURT OF CRIMINAL APPEALS) ((?:DISTRICT|PLACE) \d+)$',t)
    if t.startswith(('FORT BEND INDEPENDENT','FORT BEND CENTRAL','BURNEY')):
        a,b=t.split(' — ',1); a=a.replace(' DIRECTORS ELECTION','').replace('INDEPENDENT SCHOOL DISTRICT TRUSTEE','INDEPENDENT SCHOOL DISTRICT')
        b=re.sub(r'^TRUSTEE, ','',b)
        if a.startswith('BURNEY'): return 'Burney Road Municipal Utility District Directors',''
        if a.startswith('FORT BEND INDEPENDENT'): return 'Fort Bend Independent School District Trustee',tc(b)
        return 'Fort Bend Central Appraisal District Board of Directors',tc(b).replace('No. ','No. ')
    if re.match(r'^(JUDGE, COUNTY COURT AT LAW|DISTRICT JUDGE|DISTRICT ATTORNEY|CHIEF JUSTICE, \d)',t): m=None
    if t.startswith('JUSTICE OF THE PEACE') or t.startswith('COUNTY COMMISSIONER'):
        m=re.match(r'^(JUSTICE OF THE PEACE|COUNTY COMMISSIONER) (PRECINCT \d+(?:, PLACE \d+)?)$',t)
        return tc(m[1]),tc(m[2])
    if m:
        d=re.sub(r'\s+-\s+',', ',m[2]); return tc(m[1]),tc(d)
    return tc(t),''
def vf(s):
    if not s: return '1'
    n={'One':1,'Two':2,'Three':3,'Four':4,'Five':5}
    w=re.findall(r'One|Two|Three|Four|Five',s); return str(max(n[x] for x in w))
# contests, in ballot order (the order of the longest ballot, then any others in place)
C=[];IX={}
def key(c): return (c['title'],json.dumps(c.get('c')),json.dumps(c.get('opts')))
order=sorted(P,key=lambda q:-len(q['contests']))
for q in order:
    prev=-1
    for c in q['contests']:
        k=key(c)
        if k not in IX:
            if c['kind']=='r':
                t,d=split_title(c['title'])
                e=dict(t='r',title=t,d=d,vf=vf(c['vf']),c=[[name(n),PARTY[p]] for n,p in c['c']],wi=c['wi'],note=[])
            else:
                body=' '.join(c['body']).replace('law- enforcement','law-enforcement')
                e=dict(t='q',title='City of Houston, Proposition A',pre='',q=body,r=[o.title() for o in c['opts']])
            C.insert(prev+1,e); IX={kk:(v if v<=prev else v+1) for kk,v in IX.items()}; IX[k]=prev+1
        prev=IX[k]
def flags(q):
    t={c['title'] for c in q['contests']}
    return ('PROPOSITION A' in t, any(x.startswith('FORT BEND INDEPENDENT') for x in t), any(x.startswith('BURNEY') for x in t))
byp=collections.defaultdict(list)
for q in P: byp[q['hdr'][0]].append(q)
prec={f['properties']['PRECINCTID']:make_valid(shape(f['geometry'])) for f in G}
assert set(prec)==set(byp)
S={}; pieces=[]; report=collections.Counter(); unresolved=[]
def url(q): return LINKS[q['hdr'][0]+'BS'+q['hdr'][1]]
for pid in sorted(byp):
    sty={}
    for q in sorted(byp[pid],key=lambda q:int(q['hdr'][1])):
        sty.setdefault(json.dumps(sorted(IX[key(c)] for c in q['contests'])),[]).append(q)
    styles=[v[0] for v in sty.values()]
    if len(styles)==1:
        q=styles[0]; k='Precinct '+pid
        S[k]=dict(o=[IX[key(c)] for c in q['contests']],pdf=url(q),ok=True,p=pid); pieces.append((k,prec[pid])); report['single']+=1; continue
    report['multi']+=1
    fl={flags(q):q for q in styles}
    common=sorted(set.intersection(*[set(IX[key(c)] for c in q['contests']) for q in styles]))
    pg=prec[pid]; bits={}
    for h in (0,1):
        a=pg.intersection(HOU) if h else pg.difference(HOU)
        for s in (0,1):
            b=a.intersection(FBI) if s else a.difference(FBI)
            for m in (0,1):
                c=b.intersection(BUR) if m else b.difference(BUR)
                c=make_valid(c)
                c=unary_union([x for x in getattr(c,'geoms',[c]) if x.geom_type in ('Polygon','MultiPolygon')]) if c.geom_type=='GeometryCollection' else c
                if not c.is_empty and area(c)>0: bits[(bool(h),bool(s),bool(m))]=c
    for f,c in bits.items():
        q=fl.get(f)
        if q is None:
            k='Precinct %s (part)'%pid
            S.setdefault(k,dict(o=common,pdf=None,ok=False,p=pid,common=common)); unresolved.append((pid,f,round(area(c))))
        else:
            k='Precinct %s, ballot style %s'%(pid,q['hdr'][1])
            S[k]=dict(o=[IX[key(cc)] for cc in q['contests']],pdf=url(q),ok=True,p=pid)
        pieces.append((k,c))
# merge pieces per key, encode smallest first
mg=collections.defaultdict(list)
for k,c in pieces: mg[k].append(c)
SC=100000
def enc_ring(coords):
    pts=[(round(x*SC),round(y*SC)) for x,y in coords]
    dd=[];px=py=0;last=None
    for x,y in pts:
        if (x,y)==last: continue
        dd+= [x-px,y-py]; px,py=x,y; last=(x,y)
    return dd
OUTP=[]
for k,cs in mg.items():
    g=make_valid(unary_union(cs)); polys=[x for x in getattr(g,'geoms',[g]) if x.geom_type=='Polygon']
    polys=[p for x in polys for p in ([x] if x.geom_type=='Polygon' else x.geoms)]
    rings=[]
    for p in polys:
        if area(p)<0.5: continue
        rings.append(enc_ring(p.exterior.coords)); rings+=[enc_ring(i.coords) for i in p.interiors]
    rings=[r for r in rings if len(r)>=8]
    if not rings: continue
    b=g.bounds; OUTP.append((area(g),[k,[int(b[0]*SC)-1,int(b[1]*SC)-1,int(b[2]*SC)+1,int(b[3]*SC)+1],rings]))
OUTP.sort(key=lambda x:x[0])
used=set(k for _,(k,_,_) in OUTP)
for k in list(S):
    if k not in used: report['style with no area on the map']+=1
S={k:v for k,v in S.items() if k in used}
json.dump(dict(C=C,S=S,unresolved=unresolved,report=report,
  geo=[x for _,x in OUTP]),open(OUT+'/fb-build.json','w'),ensure_ascii=False)
print(json.dumps(report),len(C),len(S),len(OUTP),unresolved)
