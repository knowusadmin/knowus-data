# Bexar County TX, Nov 3 2026 General Election: ballot data + precinct-part map for the app (publisher 774cbf5c, v73).
# Inputs in DIR (all from the Bexar County Elections Department's public map services, maps.bexar.org, read 2026-11-11):
#   ballots_table.json  EL/VoterRegSearch/MapServer/3 (PrecinctGroup -> individual sample ballot Sample_N.pdf, 1,268 groups, 941 PDFs)
#   parsed.json         bexar_parse.py over the 941 PDFs (every PDF's option count equals its printed ovals)
#   precincts.json      EL/VoterRegSearch/MapServer/1 (806 voter precincts)
#   streets.json        EL/Streets/MapServer/1 (55,911 street address ranges -> precinct + group; the Precinct Finder's own table)
#   reps.json           EL/VoterRegSearch/MapServer/4 (each precinct group's districts: city, ISD + SMD, CD/SD/HD/SBOE/commissioner/JP)
#   county_layers.json  LocalJurisdictions, SchoolDistricts (maps.bexar.org)
#   parcels/<prec>.json CC/Parcels_WGS84 parcel situs + centroid for the 276 precincts with more than one group
#   geocoded_extra.json single-address groups placed with the county locator (Locators/BeCoMultiRole)
# A precinct whose groups all print the same ballot is one piece. Otherwise each parcel is given its group by the street table
# (number in range, odd/even, ZIP), and the precinct is split (a) by the county's ISD x city cells when each cell's group set prints
# one ballot and >=99.5% of labelled parcels agree, else (b) by the labelled parcels themselves (Voronoi, outliers with no same-ballot
# neighbour among their 6 nearest dropped), with layer cells carved for ballots that have no matched parcel. Gaps are given to the
# neighbouring piece. python3 bexar_build.py DIR SITE
import json,re,sys,collections,pickle
import numpy as np, shapely, pyproj
import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import STRtree

D=sys.argv[1]; R=sys.argv[2]
rows=json.load(open(D+'/ballots_table.json')); PR=json.load(open(D+'/parsed.json'))
for p in PR: assert 'error' not in p and p['nov']==p['nopt'],p['file']
PRD={p['file']:p for p in PR}
PC={f['attributes']['PRECINCT']:f for f in json.load(open(D+'/precincts.json'))}
STR=[r for r in json.load(open(D+'/streets.json')) if r['Precinct'] is not None]
RG=collections.defaultdict(set)
for a in json.load(open(D+'/reps.json')): RG[a['PrecGrp']].add(a['Name'])
LY=json.load(open(D+'/county_layers.json'))
def esri_poly(geom):
    outers=[];holes=[]
    for r in geom['rings']:
        if len(r)<4: continue
        (holes if sg.LinearRing(r).is_ccw else outers).append(r)
    polys=[sg.Polygon(o) for o in outers]
    for h in holes:
        hp=sg.Polygon(h)
        for i,p in enumerate(polys):
            if p.contains(hp.representative_point()): polys[i]=sg.Polygon(p.exterior.coords,[*[x.coords for x in p.interiors],h]); break
    return make_valid(sg.MultiPolygon(polys) if len(polys)>1 else polys[0])
TRm=pyproj.Transformer.from_crs(4326,32614,always_xy=True)
def to_m(g): return shapely.transform(g,lambda xy: np.column_stack(TRm.transform(xy[:,0],xy[:,1])))
PG={k:esri_poly(f['geometry']) for k,f in PC.items()}
ISD=[(f['attributes']['NAME'],esri_poly(f['geometry'])) for f in LY['SchoolDistricts']]
CITY=[(f['attributes']['JURIS'],esri_poly(f['geometry'])) for f in LY['LocalJurisdictions']]
ISDT=STRtree([g for _,g in ISD]); CITYT=STRtree([g for _,g in CITY])
def sig(p): return json.dumps([[c['t'],c['title'],c.get('grp'),c.get('c') or c.get('r'),c['wi']] for c in p['contests']])
SG={p['file']:sig(p) for p in PR}
PGB={r['PrecinctGroup']:r['Sample_Ballot'].split('/')[-1] for r in rows}
GS={pg:SG[f] for pg,f in PGB.items()}
byP=collections.defaultdict(dict)
for g,f in PGB.items(): byP[g[:4]][g[4:]]=f
stg=set((int(r['Precinct']),r['GRP']) for r in STR)
def nz(s): return re.sub(r'\s+',' ',(s or '').upper()).strip()
SIDX=collections.defaultdict(list)
for r in STR:
    full=nz(' '.join([r['PreDirectional'] or '',r['Street'] or '',r['PostDirectional'] or '']))
    try: lo,hi=int(r['LowRange']),int(r['HighRange'])
    except: continue
    SIDX[full].append((lo,hi,r['OddEven'],r['ZipCode'],str(int(r['Precinct'])),r['GRP']))
SUF=set('AVE ST DR RD LN CT BLVD PKWY WAY TRL CIR PL HWY LOOP PASS PATH RUN XING TER TRCE CV PT SQ PLZ ROW WALK BND HL HLS VW GLN CRK CRST FWY EXPY PARK RDG SPGS VLY MDWS HTS GRV GDNS ALY OVAL CTR LNDG KNL MNR ESTS PNE PNES BLF CYN FLDS HOLW MTN ISLE STA PRT FRK GTWY PIKE SPUR EST CRES MDW PNT VIS VLG'.split())
def lookup(st):
    c=SIDX.get(st)
    if c: return c
    w=st.split()
    if len(w)>1 and w[-1] in SUF: return SIDX.get(' '.join(w[:-1]))
    return None
def label(situs):
    if not situs: return None
    l1=situs.split('\n')[0].strip(); m=re.match(r'^(\d+)[A-Z]?\s+(.*)$',nz(l1))
    if not m: return None
    n=int(m[1]); st=m[2]; z=re.search(r'(\d{5})\s*$',situs); z=z[1] if z else None
    st=re.sub(r'\s+(UNIT|APT|STE|#|BLDG|SP|LOT)\b.*$','',st).strip()
    c=lookup(st)
    if not c: return ('nostreet',)
    def hits_(usez):
        h=set()
        for lo,hi,oe,zz,p,g in c:
            if lo<=n<=hi and (oe=='B' or (oe=='E')==(n%2==0)):
                if usez and z and zz and zz!=z: continue
                h.add((p,g))
        return h
    h=hits_(True) or hits_(False)
    return tuple(sorted(h)) if h else ('norange',)
ISDMAP={'SOUTHSIDE':'Southside ISD','SOUTH SIDE':'Southside ISD','EAST CENTRAL':'East Central ISD','SOUTHWEST':'Southwest ISD','SAN ANTONIO':'San Antonio ISD','HARLANDALE':'Harlandale ISD','SOUTH SAN ANTONIO':'South San Antonio ISD','MEDINA VALLEY':'Medina Valley ISD','LACKLAND':'Lackland ISD','EDGEWOOD':'Edgewood ISD (Bexar)','JUDSON':'Judson ISD','FT SAM HOUSTON':'Fort Sam Houston ISD','SCHERTZ-CIBOLO':'Schertz-Cibolo-Universal City ISD','NORTHEAST':'Northeast ISD','ALAMO HEIGHTS':'Alamo Heights ISD','RANDOLPH':'Randolph Field ISD','COMAL':'Comal ISD','SOMERSET':'Somerset ISD','BOERNE':'Boerne ISD','NORTHSIDE':'Northside ISD','FLORESVILLE':'Floresville ISD'}
CITYN={n.upper():n for n,_ in CITY}; CITYN.update({'ST HEDWIG':'St. Hedwig','LACKLAND AFB':'Lackland AFB','RANDOLPH AFB':'Randolph AFB'})
def rkey(pg):
    isd=set(); city=set()
    for n in RG.get(pg,()):
        m=re.match(r'^(.*?)(?: ISD)? - (?:ALL|SMD ?\d+)$',n) or re.match(r'^(.*?) SMD ?\d+$',n)
        if m and m[1] in ISDMAP: isd.add(ISDMAP[m[1]]); continue
        if re.match(r'^SA CITY DISTRICT \d+$',n): city.add('San Antonio'); continue
        if n in CITYN: city.add(CITYN[n])
    return (tuple(sorted(isd)),tuple(sorted(city)) or ('Unincorporated',))
def keyat2(pt):
    i=[ISD[j][0] for j in ISDT.query(pt,predicate='intersects')]; c=[CITY[j][0] for j in CITYT.query(pt,predicate='intersects')]
    return (i[0] if len(i)==1 else None, c[0] if len(c)==1 else None)
def layer_cell(p,key):
    isd,city=key; g=PG[p]
    if isd:
        ig=[gg for n,gg in ISD if n==isd]
        if not ig: return None
        g=g.intersection(ig[0])
    else: g=g.difference(unary_union([gg for _,gg in ISD]))
    cg=[gg for n,gg in CITY if n==city]
    if cg: g=g.intersection(cg[0])
    g=make_valid(g)
    return g if not g.is_empty and to_m(g).area>1 else None
def plabels(p):
    pts=[]
    try: P=json.load(open(D+'/parcels/%s.json'%p))
    except FileNotFoundError: P=[]
    for oid,si,x,y in P:
        if not PG[p].contains(sg.Point(x,y)): continue
        L_=label(si); g=None
        if L_ and not isinstance(L_[0],str):
            mine=[b for a,b in L_ if a==p]
            if mine and len(mine)==len(L_) and len(set(GS.get(p+b) for b in mine))==1: g=mine[0]
        pts.append((x,y,g))
    return pts
def dedupe(pts):
    d=collections.defaultdict(collections.Counter)
    for x,y,s in pts: d[(round(x,5),round(y,5))][s]+=1
    return [(x,y,c.most_common(1)[0][0]) for (x,y),c in d.items() if c.most_common(1)[0][1]==sum(c.values())]
def voronoi_split(p,pts):
    from scipy.spatial import cKDTree
    pts=dedupe(pts); xy=np.array([(x,y) for x,y,_ in pts]); S_=[s for _,_,s in pts]; cnt=collections.Counter(S_); keep=list(range(len(pts)))
    if len(pts)>8:
        kd=cKDTree(xy); _,nn=kd.query(xy,k=min(7,len(pts)))
        keep=[i for i in range(len(pts)) if cnt[S_[i]]<=3 or any(S_[j]==S_[i] for j in nn[i][1:])]
    xy=xy[keep]; S_=[S_[i] for i in keep]
    vor=shapely.voronoi_polygons(sg.MultiPoint([tuple(a) for a in xy]),extend_to=PG[p].envelope.buffer(0.01))
    tree=STRtree([sg.Point(a) for a in xy]); bys=collections.defaultdict(list)
    for c in vor.geoms:
        ids=tree.query(c,predicate='contains')
        if len(ids): bys[S_[ids[0]]].append(c)
    return {s:make_valid(unary_union(v).intersection(PG[p])) for s,v in bys.items()}
GE=collections.defaultdict(list)
for e in json.load(open(D+'/geocoded_extra.json')): GE[e['p']].append((e['x'],e['y'],e['g']))
PIECES={}; notes={}
for p in sorted(byP):
    gs={g:f for g,f in byP[p].items() if (int(p),g) in stg} or byP[p]
    sigs=collections.defaultdict(list)
    for g,f in gs.items(): sigs[SG[f]].append(g)
    if len(sigs)==1:
        s=next(iter(sigs)); PIECES['Precinct '+p]=dict(g=PG[p],sig=s,groups=sorted(sigs[s]),p=p); notes[p]=('whole',); continue
    lab=plabels(p)+[q for q in GE.get(p,[]) if PG[p].contains(sg.Point(q[0],q[1]))]
    pts=[(x,y,GS[p+g]) for x,y,g in lab if g and g in gs]; cnt=collections.Counter(s for _,_,s in pts)
    k2s=collections.defaultdict(set)
    for g,f in gs.items():
        k=rkey(p+g); k2s[(k[0][0] if len(k[0])==1 else None,k[1][0])].add(SG[f])
    lay=None
    if all(len(v)==1 for v in k2s.values()):
        cells={k:layer_cell(p,k) for k in k2s}
        if all(v is not None for v in cells.values()):
            a=sum(1 for x,y,s in pts if (lambda kk: kk in k2s and s in k2s[kk])(keyat2(sg.Point(x,y)))); n=len(pts)
            cov=to_m(unary_union(list(cells.values()))).area/to_m(PG[p]).area
            if (n==0 or a/n>=0.995) and cov>0.995:
                bys=collections.defaultdict(list)
                for k,c in cells.items(): bys[next(iter(k2s[k]))].append(c)
                lay={s:make_valid(unary_union(v)) for s,v in bys.items()}; notes[p]=('layers',a,n)
    if lay is None:
        missing=[s for s in sigs if cnt.get(s,0)==0]
        if not missing: lay=voronoi_split(p,pts); notes[p]=('streets',len(pts))
        else:
            carve={}
            for s in missing:
                c=[layer_cell(p,k) for k,v in k2s.items() if v=={s}]; c=[x for x in c if x is not None]
                if c: carve[s]=make_valid(unary_union(c))
            if len(carve)==len(missing) and cnt:
                vor=voronoi_split(p,pts); rest=unary_union(list(carve.values()))
                lay={s:make_valid(g.difference(rest)) for s,g in vor.items()}; lay.update(carve); notes[p]=('streets+layers',len(pts))
            elif len(carve)==len(missing): lay=carve; notes[p]=('layers-only',)
            else: raise Exception('unplaced ballot in precinct '+p)
    for s,geom in lay.items():
        if geom is None or geom.is_empty or to_m(geom).area<1: continue
        grp=sorted(sigs[s]); PIECES['Precinct '+', '.join(p+'-'+g for g in grp)]=dict(g=geom,sig=s,groups=grp,p=p)
    ks=[k for k,v in PIECES.items() if v['p']==p]
    u=unary_union([PIECES[k]['g'] for k in ks]); gap=make_valid(PG[p].difference(u))
    if not gap.is_empty and to_m(gap).area>=1:
        for comp in getattr(gap,'geoms',[gap]):
            if comp.geom_type not in ('Polygon','MultiPolygon'): continue
            best=max(ks,key=lambda k:(PIECES[k]['g'].buffer(1e-6).intersection(comp.buffer(1e-6)).area,-PIECES[k]['g'].distance(comp)))
            PIECES[best]['g']=make_valid(unary_union([PIECES[best]['g'],comp]))
# contests
SMALL={'of','the','and','for','a','an','in','on','to','at','by','no.'}
def tcase(t):
    if t!=t.upper(): return t
    out=[]
    for i,x in enumerate(t.lower().split()):
        if x in ('isd','sid','mud','esd','pid','tif'): out.append(x.upper()); continue
        out.append(x if (i>0 and x in SMALL) else '-'.join(y[:1].upper()+y[1:] for y in x.split('-')))
    return ' '.join(out)
def entity(grp): return re.sub(r'\s*-\s*(General|Special|Bond|Confirmation|Joint|Charter|Tax Ratification|Tax|Directors?)\b.*Election$','',grp).strip() if grp else None
def norm(t):
    if t=='United States Senator': return t,''
    for pat,f in ((r'^(United States Representative|State Representative|State Senator|Member, State Board of Education),? (District \d+)$',None),
                  (r'^(Justice, Supreme Court), (Place \d+) - (Unexpired Term)$','u'),
                  (r'^(Justice, Supreme Court|Judge, Court of Criminal Appeals|Justice, \d+\w\w Court of Appeals District), (Place \d+)$',None),
                  (r'^(District Judge), (\d+\w\w Judicial District)$',None),
                  (r'^(County Commissioner|Constable|Justice of the Peace),? (Precinct (?:No\. )?\d+(?:, Place \d+)?)$',None)):
        m=re.match(pat,t)
        if m: return m[1],(m[2]+', '+m[3] if f=='u' else m[2])
    return t,''
def conv(c):
    if c['t']=='r':
        t=c['title']; e=entity(c.get('grp'))
        if e and not re.match(r'^(FEDERAL|STATE|COUNTY|DISTRICT)$',e):
            off=t[4:] if t.startswith('For ') else t
            m=re.match(r'^(.*?),? ((?:Place|District|Position|Single Member District|Ward|Seat)(?: No\.)? ?\S+)$',off)
            ti,d=(e+', '+m[1],m[2]) if m else (e+', '+off,'')
        else: ti,d=norm(t)
        return dict(t='r',title=ti,d=d,vf=c['vf'],c=[[o,p] for o,p in c['c']],wi=c['wi'],note=[])
    title=c['title']; pre=c['pre']
    m=re.match(r'^(.*?):\s*(THIS IS A .*)$',title)
    if m: title=m[1]; pre=(pre+' '+m[2]).strip()
    m=re.match(r'^(.*?)\s*[-–]\s*(PROPOSITION|Proposition) (\w+)$',title)
    title=(tcase(m[1])+', Proposition '+m[3]) if m else tcase(title)
    title=re.sub(r'\s*-\s*Proposition$',', Proposition',title)
    q=c['q'].strip()
    if c.get('sub'): q=tcase(c['sub'])+'. '+q
    return dict(t='q',title=title,pre=pre.rstrip('.'),q=q.strip(),r=list(c['r']))
NB={p['file']:[conv(c) for c in p['contests']] for p in PR}
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
BASEU='https://home.bexar.org/electionsresources/ballots/'
SC=100000
def enc(coords):
    dd=[];px=py=0;last=None
    for x_,y_ in coords:
        x_,y_=round(x_*SC),round(y_*SC)
        if (x_,y_)==last: continue
        dd+=[x_-px,y_-py];px,py=x_,y_;last=(x_,y_)
    return dd
SS={};OUT=[]
for k,v in PIECES.items():
    f=byP[v['p']][v['groups'][0]]
    SS[k]=dict(o=O[f],pdf=BASEU+f,ok=True,p=v['p'],bs=PRD[f]['bs'],parts=[v['p']+'-'+g for g in v['groups']])
    g=v['g'].simplify(0.000005,preserve_topology=True); polys=[]
    for xx in getattr(g,'geoms',[g]):
        if xx.geom_type=='Polygon': polys.append(xx)
        elif xx.geom_type=='MultiPolygon': polys+=list(xx.geoms)
    rings=[]
    for pg_ in polys:
        if to_m(pg_).area<0.5: continue
        rings.append(enc(pg_.exterior.coords)); rings+=[enc(i.coords) for i in pg_.interiors if sg.Polygon(i).area>0]
    rings=[r for r in rings if len(r)>=8]
    if not rings: print('no rings',k); continue
    b=g.bounds; OUT.append((to_m(g).area,[k,[int(b[0]*SC)-1,int(b[1]*SC)-1,int(b[2]*SC)+1,int(b[3]*SC)+1],rings]))
OUT.sort(key=lambda z:z[0]); used={z[1][0] for z in OUT}
SS={k:v for k,v in SS.items() if k in used}
common=sorted(set.intersection(*[set(v['o']) for v in SS.values()]))
out=dict(read='2026-11-11',county='Bexar County, Texas',
 source='Bexar County Elections Department — the official individual sample ballot for every precinct and precinct group (Nov 3, 2026 General Election; 941 sample ballots, maps.bexar.org Ballots table), placed by the department’s voter precinct map (806 precincts); where a precinct has more than one printed ballot, its parts follow the department’s street-address ranges (precinct group per address range) and, where those agree, the county’s school district and city limits layers',
 sourceUrl='https://elections.bexar.gov/163/Election-Information',lookup='https://elections.bexar.gov/174/Who-Represents-Me-Search',office='Bexar County Elections Department',c=C,s=SS,common=common)
json.dump(out,open(R+'/data/ballots/tx-bexar-2026-11-03.json','w'),ensure_ascii=False,separators=(',',':'))
geo=dict(v=1,source=['Bexar County Elections Department — Voter Precincts (806) from the department’s Precinct Finder map service, split where a precinct has more than one printed ballot by the department’s street-address range table (precinct groups), checked against the county’s School Districts and Cities layers','https://maps.bexar.org/arcgis/rest/services/EL/VoterRegSearch/MapServer/1','2026-11-11'],
 scale=100000.0,note='Each polygon is a precinct, or the part of a precinct that gets one of its printed ballots. Smallest first.',p=[z for _,z in OUT])
json.dump(geo,open(R+'/data/ballots/tx-bexar-precincts.json','w'),ensure_ascii=False,separators=(',',':'))
print('ok','pieces',len(SS),'contests',len(C),'common',len(common),dict(collections.Counter(v[0] for v in notes.values())),flush=True)
