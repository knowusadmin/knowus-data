#!/usr/bin/env python3
"""KnowUS local officials, Pennsylvania: build data/officials-local/PA.json from the PA Department of Community &
Economic Development (DCED) Municipal Statistics "Local Government Official Information" statewide report
(apps.dced.pa.gov/munstats-public, a state .gov source the municipalities themselves update; refreshed nightly).
usage: pa_dced_build.py <LocalOfficial statewide csv> <site data/local/PA.json> <out.json>
Kept: Mayor, Council/Board President or Chair, Council Member, Township Supervisor, Commissioner, Manager, Secretary.
Party is the affiliation DCED records. No addresses (DCED's address column is often the official's home).
A phone is kept only when it is the municipality's own shared office line (used by 2+ of its officials);
an email only when it is not free/ISP mail and is the shared office address or on the municipality's own domain."""
import csv,json,re,sys,os,datetime as dt
from collections import Counter,defaultdict
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
U='https://apps.dced.pa.gov/munstats-public/ReportInformation2.aspx?report=LocalOfficial_Excel'
FREE=set('gmail.com yahoo.com hotmail.com outlook.com icloud.com aol.com comcast.net verizon.net att.net live.com msn.com me.com mac.com ymail.com windstream.net frontier.com frontiernet.net ptd.net epix.net atlanticbb.net pa.net zoominternet.net embarqmail.com centurylink.net sbcglobal.net earthlink.net juno.com netzero.net cox.net charter.net rcn.com breezeline.net armstrongonewire.com dejazzd.com pennswoods.net yahoo.co protonmail.com mail.com gmx.com bellsouth.net hughes.net'.split())
def nm(s):
    s=' '+s.lower()+' '; s=s.replace(' mount ',' mt ').replace(' mt. ',' mt ').replace('saint','st').replace('st.','st')
    return re.sub(r'[^a-z]','',s)
def base(h):
    p=h.lower().split('.'); return '.'.join(p[-2:])
def host(u):
    m=re.match(r'(?:https?://)?([^/]+)',(u or '').strip()); return m.group(1).lower().replace('www.','',1) if m and '.' in m.group(1) else ''
def digits(p): d=re.sub(r'\D','',p or ''); return d[-10:] if len(d)>=10 else ''
def fmt(d): return '(%s) %s-%s'%(d[:3],d[3:6],d[6:])
TYPE={'BORO':'borough','BOROUGH':'borough','TWP':'township','TOWNSHIP':'township','CITY':'city','TOWN':'town'}
rows=list(csv.DictReader(open(src,encoding='utf-8',errors='replace')))
M=defaultdict(list)
for r in rows:
    if r['MUNICIPALITY CLASS']=='Counties': continue
    M[r['MUNICIPALITY_ID']].append(r)
site=json.load(open(sitef,encoding='utf-8'))
cn={c['f']:re.sub(r' County$','',c['n']).upper() for c in site['counties']}
# index DCED munis by (county, base name)
idx=defaultdict(list)
for mid,rs in M.items():
    full=rs[0]['MUNICIPALITY_NAME'].strip(); parts=full.split(); suf=parts[-1] if parts[-1] in TYPE else ''
    basen=' '.join(parts[:-1]) if suf else full
    idx[(rs[0]['COUNTY_NAME'].strip().upper(),nm(basen))].append((TYPE.get(suf,''),mid,rs[0]['MUNICIPALITY CLASS']))
    if suf=='CITY': idx[(rs[0]['COUNTY_NAME'].strip().upper(),nm(full))].append(('city',mid,rs[0]['MUNICIPALITY CLASS']))
import difflib
byc=defaultdict(list)
for (cty,k),v in idx.items(): byc[cty].append(k)
def role(r,cls):
    t=r['TITLE'].strip()
    if t=='Mayor / Executive': return ('Mayor','gen_mayor',0)
    if t=='President / Chairperson':
        if 'Township' in cls: return ('Chair, Board of Supervisors' if 'Second' in cls else 'President, Board of Commissioners','gen_council',1)
        return ('Council President','gen_council',1)
    if t=='Council Member': return ('Council Member','gen_council',2)
    if t=='Supervisor': return ('Township Supervisor','gen_council',2)
    if t=='Commissioner': return ('Township Commissioner' if 'Township' in cls else 'Commissioner','gen_council',2)
    if t=='Manager / Chief Administrator': return ('Manager',None,3)
    if t=='Secretary': return ('Secretary',None,4)
    return None
res={'st':'PA','built':TODAY,'src':{'name':'Pennsylvania Department of Community & Economic Development, Municipal Statistics: Local Government Official Information (apps.dced.pa.gov)','note':'Officials as each municipality reports them to DCED; names, titles and party exactly as recorded.'},'places':{}}
st={'places':0,'matched':0,'filled_new':0,'added_to_existing':0,'officials':0,'no_match':[],'empty':[],'ambiguous':[]}
used_mid=set()
for pid,p in site['places'].items():
    if p.get('k')=='u': continue
    st['places']+=1
    cand=[]
    for f in p.get('c',[]): cand+=idx.get((cn.get(f,''),nm(p['n'])),[])
    if not cand:
        for f in p.get('c',[]):
            cl=difflib.get_close_matches(nm(p['n']),byc.get(cn.get(f,''),[]),n=2,cutoff=0.88)
            if len(cl)==1: cand+=[c for c in idx[(cn[f],cl[0])] if c[0]==p['t']]
    c2=[c for c in cand if c[0]==p['t']] or ([c for c in cand] if p['t'] in ('municipality','town') else [])
    if len(set(c[1] for c in c2))!=1:
        (st['ambiguous'] if c2 else st['no_match']).append(p['n']+' ('+p['t']+')'); continue
    mid=c2[0][1]; cls=c2[0][2]; rs=M[mid]; used_mid.add(mid); st['matched']+=1
    keep=[(r,role(r,cls)) for r in rs]; keep=[(r,x) for r,x in keep if x and r['NAME'].strip() and not re.search(r'vacan|tbd|^n/?a$|none|unknown',r['NAME'],re.I)]
    ph=Counter(digits(r['PHONE']) for r,_ in keep if digits(r['PHONE']))
    office=[d for d,n in ph.most_common() if n>=2][:1]
    em=Counter(r['EMAIL'].strip().lower() for r,_ in keep if '@' in r['EMAIL'])
    webs=Counter(r['WEB_SITE'].strip() for r,_ in keep if host(r['WEB_SITE']))
    web=webs.most_common(1)[0][0] if webs else (p.get('w') or '')
    if web and not web.startswith('http'): web='http://'+web
    doms={base(host(web))} if host(web) else set()
    if p.get('w') and host(p['w']): doms.add(base(host(p['w'])))
    people={}
    for r,(rl,rk,order) in keep:
        name=re.sub(r'\s+',' ',r['NAME']).strip()
        if name.isupper() and len(name)>3: name=name.title()
        if name in people:
            q=people[name]; q['_rs'].append((order,rl)); q['order']=min(q['order'],order)
            if rk and not q.get('rk'): q['rk']=rk
            continue
        ct={}; g=1
        d=digits(r['PHONE'])
        if office: ct['p']=[fmt(office[0])]
        e=r['EMAIL'].strip(); el=e.lower(); dom=el.split('@')[-1] if '@' in el else ''
        if dom and dom not in FREE and base(dom) not in FREE and ' ' not in e:
            if em[el]>=2: ct['e']=e
            elif base(dom) in doms or dom.endswith('.gov') or dom.endswith('.pa.us'): ct['e']=e; g=0
        if web: ct['w']=web
        ct['src']=U
        if g: ct['g']=1
        o={'_rs':[(order,rl)],'n':name,'r':rl,'rk':rk,'src':'dced','u':U,'d':TODAY,'ct':ct,'order':order}
        pa_=r['POLITICAL_AFFILIATION'].strip()
        if rk and pa_ in ('Republican','Democrat','Independent'): o['p']=pa_
        try:
            y=int(float(r['YTE']))
            if rk and 2025<=y<=2040: o['s']='term ends %d'%y
        except: pass
        people[name]=o
    L=sorted(people.values(),key=lambda x:(x['order'],x['n'].split()[-1]))
    for x in L:
        x.pop('order'); x['r']=' / '.join(r for _,r in sorted(set(x.pop('_rs'))))
        if not x['rk']: x.pop('rk')
    if not L: st['empty'].append(p['n']); continue
    ex=[o for o in (p.get('o') or []) if o.get('src') not in ('dlg','dced','state')]  # ignore our own earlier fill (site file may already carry it)
    def same(a,b):
        a,b=a.split(),b.split(); return nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
    if ex:
        add=[x for x in L if not any(same(x['n'],o['n']) for o in ex) and not (x['r'].startswith('Mayor') and any(o.get('rk')=='gen_mayor' for o in ex))]
        if not add: continue
        res['places'][pid]={'n':p['n'],'o':ex+add}; st['added_to_existing']+=1; st['officials']+=len(add)
    else:
        res['places'][pid]={'n':p['n'],'o':L}; st['filled_new']+=1; st['officials']+=len(L)
    if web and not p.get('w'): res['places'][pid]['w']=web
st['dced_unmatched']=sorted(M[m][0]['MUNICIPALITY_NAME']+' / '+M[m][0]['COUNTY_NAME'] for m in M if m not in used_mid)

# compact: drop a contact block's website when it repeats the place's own site, and drop blocks with nothing to show
for pid,p in res['places'].items():
    w=p.get('w') or site['places'].get(pid,{}).get('w')
    for o in p['o']:
        ct=o.get('ct')
        if not ct: continue
        if o.get('src') in ('dced','dlg') and w and ct.get('w')==w: ct.pop('w')
        if not any(k in ct for k in ('p','e','f','a','w','s')): o.pop('ct')
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:25])) for k,v in st.items()}))
