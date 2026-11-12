
# Michigan, Nov 3 2026 State General: per-county ballot data + maps for the KnowUS app (hand-off worker 448daed7).
# Inputs (DIR): raw/cNN.jsonl.gz (MVIC PublicBallot GetMvicBallot answers, one per precinct, from mi crawl), raw/enum.json,
#   geo/precincts_4326.json (MI BOE 2026 Voting Precincts), geo/schools_4326.json (MDE/MGF School Districts v26),
#   geo/isd_4326.json, geo/villages_4326.json, geo/ccd_4326.json (Community College Districts).
# MVIC shows one ballot per precinct that carries every contest of every ballot style in that precinct. Contests that belong
# to one local unit (school district, ISD, community college, village) are kept only for the part of the precinct inside that
# unit (state layers); a precinct part is complete (ok) only when every such contest is placed. Contests of units with no state
# map (district libraries, metro districts, authorities, ...) leave the part labelled (ok:false) with the races confirmed.
# python3 mi_build.py DIR OUT [county ids...]
import json,re,sys,gzip,glob,collections,os,hashlib
import numpy as np, shapely, pyproj
import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.validation import make_valid
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import mi_parse
D=sys.argv[1]; OUT=sys.argv[2]; ONLY=[int(x) for x in sys.argv[3:]]
os.makedirs(OUT,exist_ok=True)
TRm=pyproj.Transformer.from_crs(4326,3078,always_xy=True); TRg=pyproj.Transformer.from_crs(3078,4326,always_xy=True)
def to_m(g): return shapely.transform(g,lambda xy: np.column_stack(TRm.transform(xy[:,0],xy[:,1])))
def to_g(g): return shapely.transform(g,lambda xy: np.column_stack(TRg.transform(xy[:,0],xy[:,1])))
def rpoly(g):
    """Esri rings -> polygon: clockwise rings are outer rings, counter-clockwise rings are holes of the smallest outer ring holding them."""
    ext=[];hol=[]
    for r in g['rings']:
        if len(r)<4: continue
        lr=sg.LinearRing(r)
        (hol if lr.is_ccw else ext).append(r)
    if not ext: return sg.Polygon()
    EP=[sg.Polygon(r) for r in ext]; H=[[] for _ in ext]
    for h in hol:
        pt=sg.Point(h[0]); best=None
        for j,p in enumerate(EP):
            if p.area>0 and p.covers(pt) and (best is None or p.area<EP[best].area): best=j
        if best is not None: H[best].append(h)
    return make_valid(unary_union([make_valid(sg.Polygon(e,hh)) for e,hh in zip(ext,H)]))
def polys(g):
    if g.is_empty: return sg.Polygon()
    if g.geom_type in ('Polygon','MultiPolygon'): return g
    return unary_union([x for x in getattr(g,'geoms',[g]) if x.geom_type in ('Polygon','MultiPolygon')]) if hasattr(g,'geoms') else sg.Polygon()
def layer(f,keyf):
    G=collections.defaultdict(list)
    for x in json.load(open(f)):
        if x.get('geometry'): G[keyf(x['attributes'])].append(to_m(rpoly(x['geometry'])))
    return {k:make_valid(unary_union(v)).buffer(0) for k,v in G.items()}
GEN=set('public publics schools school district districts community area areas consolidated the of sd s d unit agricultural rural local educational education service services agency isd resa resd esd esa intermediate college county village city township twp charter regional union joint no number board member members trustee trustees and inc proposal millage renewal'.split())
def toks(s): return [t for t in re.split(r'[^a-z0-9]+',s.lower().replace("'",'').replace('’','').replace('.','')) if t]
GEN2={'the','of','and','inc','no','number'}
class Core(frozenset):
    """a unit's distinctive name words; .cat = the same words run together in name order (Au Gres-Sims == AUGRES-SIMS)"""
    pass
def core1(s):
    t=[w for w in toks(s) if w not in GEN] or [w for w in toks(s) if w not in GEN2]
    c=Core(t); c.cat=''.join(t); return c
def core(s): return core1(s)
ALIAS={'Elkton-Pigeon-Bay Port Laker Schools':['Laker Schools'],'C.O.O.R. ISD':['Crawford Oscoda Ogemaw Roscommon ISD'],'Cheb-Otsego-Presque Isle ESD':['Cheboygan Otsego Presque Isle ESD']}
def ld(name,f,keyf,labf=None):
    L=layer(f,keyf); names=collections.defaultdict(set)
    for x in json.load(open(f)):
        a=x['attributes'];k=keyf(a);names[k].add(k)
        if labf and labf(a): names[k].add(labf(a))
    for k,v in ALIAS.items():
        if k in names: names[k].update(v)
    return L,{k:[core1(n) for n in sorted(names[k])] for k in L}
SCH,SCHc=ld('school',D+'/geo/schools_4326.json',lambda a:a['Name'],lambda a:a['Label'])
ISD,ISDc=ld('isd',D+'/geo/isd_4326.json',lambda a:a['Name'])
VIL,VILc=ld('village',D+'/geo/villages_4326.json',lambda a:a['Name'])
CCD,CCDc=ld('ccd',D+'/geo/ccd_4326.json',lambda a:a['Label'])
CDL=layer(D+'/geo/cd_4326.json',lambda a:int(a['NAME'])); SDL=layer(D+'/geo/sd_4326.json',lambda a:int(a['Name'])); HDL=layer(D+'/geo/hd_4326.json',lambda a:int(a['Name']))
DIST={'Representative in Congress':'CD','STATE SENATOR':'SD','REPRESENTATIVE IN STATE LEGISLATURE':'HD'}
LAY={'CD':(CDL,{},True),'SD':(SDL,{},True),'HD':(HDL,{},True),'Local School District':(SCH,SCHc,True),'Intermediate School District':(ISD,ISDc,True),'Village':(VIL,VILc,False),'Community College':(CCD,CCDc,False)}
WHOLE={'State','Congressional','Legislative','State Boards','State Boards - Continued','County','Judicial','City','Township'}
# ---- precinct layer and MVIC precinct list
PF=json.load(open(D+'/geo/precincts_4326.json'))
PA={x['attributes']['PrecinctID']:x['attributes'] for x in PF}; PG={x['attributes']['PrecinctID']:x['geometry'] for x in PF}
E=json.load(open(D+'/raw/enum.json'))
def jk(s):
    s=s.lower().replace('.','').replace("'",'').replace('’','');s=re.sub(r'\b(charter|of|the)\b',' ',s);return ' '.join(sorted(s.split()))
def jk2(s):
    s=s.lower().replace('.','').replace("'",'').replace('’','').replace(',',' ');s=re.sub(r'\btwp\b','township',s)
    s=re.sub(r'\b(charter|of|the|district|ward|michigan|a|\d+\w*|village)\b',' ',s);s=re.sub(r'\d','',s);return ' '.join(sorted(set(s.split())))
def jname(a): return re.sub(r',\s*(Ward|Precinct)\b.*$','',a['PrecinctLongName'])
OVR={('Macomb County','Macomb Township','00023'):'WP-099-50480-00023',('Washtenaw County','Manchester City','00001'):None}
K1={};K2=collections.defaultdict(list);K3=collections.defaultdict(list)
for pid,a in PA.items():
    w5=a['Ward']+a['Precinct'];K1[(a['CountyFIPS'],jk(jname(a)),w5)]=pid;K2[(a['CountyFIPS'],jk2(jname(a)),w5)].append(pid);K3[(a['CountyFIPS'],jk2(jname(a)),a['Precinct'].lstrip('0'))].append(pid)
def mvic2pid(e):
    fips='%03d'%(2*int(e['countyID'])-1)
    if (e['county'],e['juris'],e['wpv']) in OVR:
        v=OVR[(e['county'],e['juris'],e['wpv'])]
        if v: return v,'override'
        c=[p for p,a in PA.items() if a['CountyFIPS']==fips and a['MCDFIPS']=='50660']; return c[0],'override-mcd'
    k=(fips,jk(e['juris']),e['wpv'])
    if k in K1: return K1[k],'exact'
    c=K2.get((fips,jk2(e['juris']),e['wpv']),[])
    if len(c)==1: return c[0],'name'
    c=K3.get((fips,jk2(e['juris']),e['wpv'][2:].lstrip('0')),[])
    if len(c)==1: return c[0],'noward'
    return None,'none'
# fix the one known PrecinctID for Macomb Twp 23 from the layer itself
for pid,a in PA.items():
    if a['CountyFIPS']=='099' and a['PrecinctLongName'].startswith('3Macomb Township') and a['Precinct']=='023': OVR[('Macomb County','Macomb Township','00023')]=pid
# ---- contests
def ckey(c):
    if c['t']=='r': return json.dumps(['r',c['div'],c['title'],c['lines'],c['vf'],c['c']],ensure_ascii=False)
    return json.dumps(['q',c['div'],c['title'],c['sub'],c['body']],ensure_ascii=False)
def app_contest(c):
    if c['t']=='r':
        if c['c']==[['No candidates on ballot','','']]:   # MVIC prints this (with "Vote for not more than -1") for a seat nobody filed for
            return dict(t='r',title=c['title'],d=', '.join(c['lines']),vf='' if int(c['vf'])<1 else c['vf'],c=[],wi=0,note=['No candidates on ballot'])
        assert int(c['vf'])>=1,c
        return dict(t='r',title=c['title'],d=', '.join(c['lines']),vf=c['vf'],c=[[n,p or ds] for n,p,ds in c['c']],wi=0,note=[])
    pre=' '.join(c['sub']); q='\n\n'.join(c['body'])
    return dict(t='q',title=c['title'],pre=pre,q=q,r=['Yes','No'])
def ent_text(c):
    if c['t']=='r': return [' '.join(c['lines'][:1]),c['title']]
    return [c['title']+' '+' '.join(c['sub']),' '.join(c['body'][:2])]
def nmatch(cs_,tt,cat):
    """length of the longest name of the unit that the text carries whole (0 = none)"""
    best=0
    for c in cs_:
        if c and (c<=tt or (len(c.cat)>=5 and c.cat in cat)): best=max(best,len(c.cat))
    return best
def pick(c,cands,Lc):
    """entity of contest c among the layer entities intersecting the precinct (cands)"""
    for txt in ent_text(c):
        tt=set(toks(txt)); cat=''.join(toks(txt))
        if c['div']=='Village':
            m=re.findall(r'village of ([a-z][a-z .\'’-]+?)(?:,|\s+(?:county|shall|adopt|be|to|in|for|michigan)\b|$)',txt.lower())
            hit=[k for k in cands if any(core(n)==cc for n in m for cc in Lc[k])]
            if len(hit)==1: return hit[0]
        sc={k:nmatch(Lc[k],tt,cat) for k in cands}; mx=max(sc.values(),default=0)
        if mx:
            hit=[k for k,v in sc.items() if v==mx]
            return hit[0] if len(hit)==1 else None
    # no whole-name match: the one intersecting unit sharing most of its name with the contest's own unit line / title
    tt=set(toks(ent_text(c)[0]))
    sc=sorted(((max(len(cc&tt)/len(cc) for cc in Lc[k] if cc),k) for k in cands if any(Lc[k])),reverse=True)
    if sc and sc[0][0]>=0.5 and (len(sc)==1 or sc[1][0]<sc[0][0]): return sc[0][1]
    return None
SLIV=2000.0
EN={'CD':'Congressional District %d','SD':'State Senate District %d','HD':'State House District %d'}
def efmt(t): return '%s: %s'%(t[0],EN[t[0]]%t[1] if t[0] in EN else t[1])
def build_precinct(pid,R,CW=frozenset()):
    P=to_m(rpoly(PG[pid])).buffer(0); A=P.area
    seen=set();cs=[]
    for c in R['contests']:
        c['div']=re.sub(r'\s*-\s*Continued$','',c['div'] or '')
        k=ckey(c)
        if k in seen: continue
        seen.add(k);cs.append(c)
    info=dict(dups=len(R['contests'])-len(cs))
    # classify
    whole=[];ent=collections.defaultdict(list);nolayer=[]
    # a whole-unit office printed for two districts: the precinct crosses that district line
    dn=lambda c: tuple(re.findall(r'(?:\b(?:WARD|DISTRICT|CIRCUIT)\s+(\w+)|(\d+)(?:st|nd|rd|th)\s+(?:DISTRICT|CIRCUIT|WARD))',' '.join(c['lines']).upper()))
    byt=collections.defaultdict(set)
    for c in cs:
        if c['t']=='r' and (c['div'] or '') in WHOLE: byt[(c['div'],c['title'])].add(dn(c))
    multi={k for k,v in byt.items() if len(v)>1}
    assign={};unres=[];splitd=set()
    for i,c in enumerate(cs):
        dv=c['div'] or ''
        if dv not in WHOLE and dv not in LAY and ckey(c) in CW: whole.append(i); continue  # on every ballot in the county
        if dv in WHOLE and (dv,c['title']) in multi:
            if c['title'] in DIST:
                m=re.search(r'(\d+)(?:st|nd|rd|th)\s+DISTRICT',' '.join(c['lines']))
                if m: assign[i]=(DIST[c['title']],int(m[1])); splitd.add(DIST[c['title']]); continue
            unres.append(i); continue
        if dv in WHOLE: whole.append(i)
        elif dv in LAY: ent[dv].append(i)
        else: nolayer.append(i)
    # which entities intersect
    cand={}
    for dv,ix in ent.items():
        L,Lc,part=LAY[dv]
        cands={k:g for k,g in L.items() if g.intersects(P)}
        cands={k:g for k,g in cands.items() if g.intersection(P).area>=1.0}
        cand[dv]=cands
        big=[k for k,g in cands.items() if (lambda x: x.area>=SLIV and not x.buffer(-5.0).is_empty)(g.intersection(P))]
        for i in ix:
            e=pick(cs[i],cands,Lc)
            if e is None and len(big)==1: e=big[0]
            if e is None: unres.append(i)
            else: assign[i]=(dv,e)
    # a unit with contests on this ballot whose map overlap with the precinct is only a sliver: the maps disagree, place nothing
    thin=set()
    for i,(dv,e) in list(assign.items()):
        if (dv,e) in thin or (lambda x: x.area<SLIV or x.buffer(-5.0).is_empty)(LAY[dv][0][e].intersection(P)):
            thin.add((dv,e)); unres.append(i); del assign[i]
    # two units of one kind whose maps overlap inside the precinct (more than a sliver): which one a voter there is in is not known
    for dv in sorted({d for d,e in assign.values() if LAY[d][2]}):   # partition maps only (one school district, ISD, district per spot)
        es=sorted({e for d,e in assign.values() if d==dv}); L=LAY[dv][0]
        bad=any((lambda x: x.area>=SLIV and not x.buffer(-5.0).is_empty)(L[a].intersection(L[b]).intersection(P)) for ii,a in enumerate(es) for b in es[ii+1:])
        if bad:
            for i,(d,e) in list(assign.items()):
                if d==dv: unres.append(i); del assign[i]
            thin.add((dv,'overlapping maps'))
    # pieces: overlay P with the entities that carry contests
    pieces=[(P,frozenset())]
    for dv in sorted(set(ent)|splitd):
        ents=sorted({e for i,(d,e) in assign.items() if d==dv})
        if not ents: continue
        L=LAY[dv][0]
        for e in ents:   # split every piece by this unit's map: the part inside carries the unit, the rest does not
            new=[]
            for g,tag in pieces:
                x=polys(make_valid(g.intersection(L[e]))); y=polys(make_valid(g.difference(L[e])))
                if x.area>0: new.append((x,tag|{(dv,e)}))
                if y.area>0: new.append((y,tag))
            pieces=new
    # merge slivers into the largest touching piece
    pieces=sorted(pieces,key=lambda z:-z[0].area)
    def sliver(g): return g.area<SLIV or g.buffer(-5.0).is_empty     # under 2,000 m2, or nowhere 10 m wide: map misalignment
    keep=[p for p in pieces if not sliver(p[0])]; small=[p for p in pieces if sliver(p[0])]
    if not keep: keep=pieces[:1];small=pieces[1:]
    keep=[list(p) for p in keep]
    for g,tag in small:
        best=max(range(len(keep)),key=lambda j:keep[j][0].buffer(0.5).intersection(g).area)
        keep[best][0]=unary_union([keep[best][0],g])
    out=[]
    for g,tag in keep:
        o=list(whole)+[i for i,(dv,e) in assign.items() if (dv,e) in tag]
        o=sorted(o)
        ok=not unres and not nolayer
        out.append(dict(g=g,o=o,ok=ok,ents=sorted(efmt(t) for t in tag),area=g.area))
    info.update(thin=sorted(efmt(t) if t[1]!='overlapping maps' else t[0]+': overlapping maps' for t in thin),unres=[cs[i]['div']+' | '+cs[i]['title'] for i in unres],nolayer=sorted({cs[i]['div'] for i in nolayer}),
                ents={dv:sorted(cand[dv]) for dv in cand},splitd=sorted(splitd),multi=sorted('%s | %s'%k for k in multi),area=A)
    return cs,out,info

SC=100000
def enc(coords):
    dd=[];px=py=0;last=None
    for x_,y_ in coords:
        x_,y_=round(x_*SC),round(y_*SC)
        if (x_,y_)==last: continue
        dd+=[x_-px,y_-py];px,py=x_,y_;last=(x_,y_)
    return dd
def merge_order(lists):
    CT=[];IX={}
    for k in sorted(lists,key=lambda k:(-len(lists[k]),k)):
        prev=-1
        for key in lists[k]:
            if key not in IX:
                CT.insert(prev+1,key); IX={kk:(v if v<=prev else v+1) for kk,v in IX.items()}; IX[key]=prev+1
            prev=IX[key]
    return CT
MVIC='https://mvic.sos.state.mi.us/PublicBallot/Index'
def slug(n): return re.sub(r'[^a-z]+','',n.lower().replace(' county',''))
REPORT={}
files=sorted(glob.glob(D+'/raw/c*.jsonl.gz'))
for f in files:
    cid=int(re.search(r'c(\d+)\.jsonl',f)[1])
    if ONLY and cid not in ONLY: continue
    rows=[json.loads(l) for l in gzip.open(f,'rt') if l.strip()]
    cname=rows[0]['county']; rep=dict(county=cname,precincts=len(rows),pieces=0,ok=0,labelled=0,split=0,dups=0,unres=collections.Counter(),nolayer=collections.Counter(),chk_fail=[],hdr_fail=[],multi_whole=[])
    PIECES=[];CK={}
    PR=[]
    for x in rows:
        j=json.loads(x['resp']); R=mi_parse.parse(j['Ballot'])
        for c in R['contests']: c['div']=re.sub(r'\s*-\s*Continued$','',c['div'] or '')
        PR.append({ckey(c) for c in R['contests']})
    CW=frozenset(set.intersection(*PR))
    for x in rows:
        j=json.loads(x['resp']); assert not j.get('DataIssue'),(x['juris'],x['wp'])
        assert hashlib.sha256(x['resp'].encode()).hexdigest()==x['sha256']
        R=mi_parse.parse(j['Ballot'])
        if not all(R['chk'].values()): rep['chk_fail'].append([x['juris'],x['wp'],R['chk']])
        h=R['hdr']
        if not (len(h)>=4 and h[2].upper()==(cname+', Michigan').upper() and re.sub(r'[\s,]+',' ',h[3].upper()).endswith(re.sub(r'[\s,]+',' ',x['wp'].upper()))): rep['hdr_fail'].append([x['juris'],x['wp'],h])
        pid,how=mvic2pid(x)
        cs,parts,info=build_precinct(pid,R,CW)
        rep['dups']+=info['dups']
        for u in info['unres']: rep['unres'][u.split(' | ')[0]]+=1
        if info['thin']: rep.setdefault('thin',[]).append([x['juris'],x['wp'],info['thin']])
        for u in info['nolayer']: rep['nolayer'][u]+=1
        # whole-unit offices printed more than once (would mean the precinct crosses a district line)
        tt=collections.Counter((c['div'],c['title']) for c in cs if c['t']=='r' and c['div'] in ('Congressional','Legislative'))
        if any(v>1 for (d_,t_),v in tt.items() if t_ not in ('United States Senator',)): rep['multi_whole'].append([x['juris'],x['wp']])
        keys=[ckey(c) for c in cs]
        for k_,c in zip(keys,cs): CK[k_]=c
        name=PA[pid]['PrecinctLongName'].replace('3Macomb','Macomb') if how!='override-mcd' else 'City of Manchester, Precinct 1'
        name='%s, %s'%(x['juris'],x['wp'])
        sig=collections.defaultdict(list)
        for p in parts: sig[(tuple(p['o']),p['ok'])].append(p)
        if len(sig)>1: rep['split']+=1
        for (o,ok),ps in sig.items():
            g=unary_union([p['g'] for p in ps])
            ents=sorted(set().union(*[set(p['ents']) for p in ps])) if len(sig)>1 else []
            # name a split piece by the units that differ between the pieces
            allents=[set(p['ents']) for pp in sig.values() for p in pp]
            diff=sorted(set().union(*allents)-set.intersection(*allents)) if len(sig)>1 else []
            mine=[e for e in diff if all(e in p['ents'] for p in ps)]
            lab=name if len(sig)==1 else name+' \u2014 '+(', '.join(e.split(': ',1)[1] for e in mine) if mine else 'outside '+', '.join(sorted({e.split(': ',1)[1] for e in diff})))
            PIECES.append(dict(key=lab,pid=pid,juris=x['juris'],wp=x['wp'],o=[keys[i] for i in o],ok=ok,g=g,u=mine,split=len(sig)>1,
                               unres=info['unres'],nolayer=info['nolayer']))
    # contest table
    CT=merge_order({p['key']:p['o'] for p in PIECES}); IX={k:i for i,k in enumerate(CT)}
    C=[app_contest(CK[k]) for k in CT]
    okp=[p for p in PIECES if p['ok']]
    common=sorted(set.intersection(*[set(IX[k] for k in p['o']) for p in (okp or PIECES)]))
    ST={};OUTG=[]
    for p in PIECES:
        g=to_g(p['g'])
        o=[IX[k] for k in p['o']]
        if p['ok']:
            ST[p['key']]=dict(o=o,pdf=MVIC,ok=True,p=p['key'],pid=p['pid'])
        else:
            why=[]
            if p['nolayer']: why.append('contests for '+', '.join(p['nolayer']).lower().replace('district library','a district library').replace('metropolitan district','a metropolitan district').replace('authority','an authority')+' that may cover only part of your precinct')
            if p['unres']: why.append('local contests that could not be placed by address')
            ST[p['key']]=dict(o=o,common=o,pdf=None,ok=False,p=p['key'],pid=p['pid'],why='; '.join(why))
        if p['split']: ST[p['key']]['u']=p['u']
        gs=g.simplify(0.000005,preserve_topology=True); pl=[]
        for xx in getattr(gs,'geoms',[gs]):
            if xx.geom_type=='Polygon': pl.append(xx)
            elif xx.geom_type=='MultiPolygon': pl+=list(xx.geoms)
        rings=[]
        for pg in pl:
            if to_m(pg).area<0.5: continue
            rings.append(enc(pg.exterior.coords)); rings+=[enc(i.coords) for i in pg.interiors if sg.Polygon(i).area>0]
        rings=[r for r in rings if len(r)>=8]
        if not rings: ST.pop(p['key']); continue
        b=gs.bounds; OUTG.append((p['g'].area,p['key'],[p['key'],[int(b[0]*SC)-1,int(b[1]*SC)-1,int(b[2]*SC)+1,int(b[3]*SC)+1],rings]))
    OUTG.sort(key=lambda z:(z[0],z[1]))
    sl=slug(cname)
    out=dict(read='2026-11-12',county=cname+', Michigan',
      source='Michigan Department of State, Bureau of Elections \u2014 the official ballot for every precinct in '+cname+' (Nov 3, 2026 State General Election), from the state\u2019s Michigan Voter Information Center (\u201cWhat\u2019s on the ballot?\u201d), placed on the Bureau of Elections\u2019 2026 Voting Precincts map; school, intermediate school, community college and village contests are kept only for the part of a precinct inside that unit (State of Michigan boundary maps)',
      sourceUrl=MVIC,lookup='https://mvic.sos.state.mi.us/Voter/Index',office='Michigan Bureau of Elections',c=C,s=ST,common=common)
    json.dump(out,open(OUT+'/mi-%s-2026-11-03.json'%sl,'w'),ensure_ascii=False,separators=(',',':'),sort_keys=False)
    geo=dict(v=1,source=['Michigan Bureau of Elections \u2014 2026 Voting Precincts ('+cname+'), split where a precinct crosses a school district, ISD, community college district or village boundary (State of Michigan maps)','https://gis-michigan.opendata.arcgis.com/datasets/Michigan::2026-voting-precincts-1','2026-11-12'],
      scale=100000.0,note='Each polygon is a precinct, or the part of a precinct that has one ballot. Smallest first.',p=[z for _,_,z in OUTG])
    json.dump(geo,open(OUT+'/mi-%s-precincts.json'%sl,'w'),ensure_ascii=False,separators=(',',':'))
    rep['pieces']=len(ST); rep['ok']=sum(1 for v in ST.values() if v['ok']); rep['labelled']=rep['pieces']-rep['ok']; rep['contests']=len(C); rep['slug']=sl
    rep['unres']=dict(rep['unres']); rep['nolayer']=dict(rep['nolayer'])
    REPORT[cid]=rep
    print(json.dumps(dict(cid=cid,**{k:v for k,v in rep.items() if k not in ('chk_fail','hdr_fail','multi_whole')},chk_fail=len(rep['chk_fail']),hdr_fail=len(rep['hdr_fail']),multi_whole=len(rep['multi_whole']))),flush=True)
json.dump(REPORT,open(OUT+'/report%s.json'%('-'+'-'.join(map(str,ONLY)) if ONLY else ''),'w'),indent=1)
