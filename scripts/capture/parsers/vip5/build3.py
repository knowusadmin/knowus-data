# Generalized from scripts/ballots/nc/build3.py: writes the app's per-county ballot files (same format as data/ballots/nc).

import json,os,re,io,zipfile,collections,datetime
import pandas as pd
NC=os.environ.get('VIP_WORK') or os.getcwd()
S1=json.load(open(f'{NC}/stage1.json')); C=S1['contests']; S2=json.load(open(f'{NC}/stage2.json')); CO=json.load(open(f'{NC}/corder.json'))
OUT=os.environ.get('VIP_OUT',f'{NC}/out'); os.makedirs(OUT,exist_ok=True)
ST=os.environ.get('VIP_STATE','NC'); EL=os.environ.get('VIP_ELECTION','2026-11-03')
PDFURL=json.load(open(os.environ['VIP_PDF_URLS'])) if os.environ.get('VIP_PDF_URLS') else {}
VZ=zipfile.ZipFile(os.environ['VIP_FEED'])
_names={n.rsplit('/',1)[-1]:n for n in VZ.namelist()}
_ED=pd.read_csv(io.BytesIO(VZ.read(_names['electoral_district.txt'])),dtype=str,encoding='utf-8-sig',keep_default_na=False).apply(lambda s:s.str.strip())
EDT={r.id:(r.type,r.number) for r in _ED.itertuples()}
def edist(full,typ):
    for c in full:
        t,nu=EDT.get(C[c].get('ed'),('',''))
        if t==typ and nu.isdigit() and int(nu)>0: return str(int(nu))
    return None
SS=pd.read_csv(io.BytesIO(VZ.read(_names['street_segment.txt'])),dtype=str,encoding='utf-8-sig',keep_default_na=False,
  usecols=['address_direction','odd_even_both','precinct_id','start_house_number','end_house_number','street_direction','street_name','street_suffix','zip']).apply(lambda s:s.str.strip())
splitinfo={s['id']:s for s in S1['splits']}
def slug(co): return re.sub(r'[^a-z]+','-',co.lower()).strip('-')
def dnum(t,pat):
    m=re.search(pat,t); return str(int(m.group(1))) if m else None
B='https://dl.ncsbe.gov/'
from urllib.parse import quote
index={}
tot=collections.Counter()
SS['k']=(SS.street_direction+' '+SS.street_name+' '+SS.street_suffix+' '+SS.address_direction).str.split().str.join(' ')
SS['co']=SS.precinct_id.map(lambda p:splitinfo[p]['county'])
for co,styles in sorted(S2.items()):
    cids=sorted({c for s in styles for c in s['full']})
    cix={c:i for i,c in enumerate(cids)}
    cl=[]
    for c in cids:
        x=C[c]
        if x['k']=='c':
            cc=x['c']
            if c in CO and sorted(CO[c])==sorted(n for n,_ in cc): cc=sorted(cc,key=lambda y:CO[c].index(y[0]))
            cl.append({'t':x['o'],'vf':x['vf'],'c':cc,'n':(x.get('notes') or [])+(['No candidate filed for this office; the official ballot has a write-in line only.'] if x.get('wio') else [])})
        else: cl.append({'t':x['o'],'m':1,'q':x['q'],'r':x['resp']})
    sl=[];sp2s={}
    for i,s in enumerate(styles):
        ts=[C[c]['t'] for c in s['full']]
        sd=edist(s['full'],'state-senate') or next((dnum(t,r'^NC STATE SENATE DISTRICT (\d+)') for t in ts if t.startswith('NC STATE SENATE')),None)
        hd=edist(s['full'],'state-house') or next((dnum(t,r'^NC HOUSE OF REPRESENTATIVES DISTRICT (\d+)') for t in ts if t.startswith('NC HOUSE OF REP')),None)
        cd=edist(s['full'],'congressional') or next((dnum(t,r'^US HOUSE OF REPRESENTATIVES DISTRICT (\d+)') for t in ts if t.startswith('US HOUSE')),None)
        pr=sorted({(splitinfo[p]['number'],splitinfo[p]['name']) for p in s['splits']})
        sl.append({'o':[cix[c] for c in s['order']],'ok':1 if s['ok'] else 0,'why':s['why'],'pdf':(PDFURL.get(s['pdfs'][0]) or (B+quote(s['pdfs'][0]) if ST=='NC' and '/' in s['pdfs'][0] else '')) if s['pdfs'] else '',
                   'sd':sd,'hd':hd,'cd':cd,'p':[a+' '+b for a,b in pr]})
        for p in s['splits']: sp2s[p]=i
    spl=sorted({p for s in styles for p in s['splits']}); spix={p:j for j,p in enumerate(spl)}
    sp=[[sp2s[p],(splitinfo[p]['number']+' '+splitinfo[p]['name']).strip()] for p in spl]
    g=SS[SS.co==co]
    st={}
    for (k,z),grp in g.groupby(['k','zip']):
        segs=sorted({(int(a or 0),int(b or 0),{'odd':1,'even':2}.get(o,0),spix[p]) for a,b,o,p in zip(grp.start_house_number,grp.end_house_number,grp.odd_even_both,grp.precinct_id)})
        ss={x[3] for x in segs}
        if len(ss)==1: v=[min(x[0] for x in segs),max(x[1] for x in segs),next(iter(ss))]
        else:
            v=[]
            for lo,hi,par,si in segs:
                if v and v[-1][2]==par and v[-1][3]==si and lo<=v[-1][1]+2: v[-1][1]=max(v[-1][1],hi)
                else: v.append([lo,hi,par,si])
        st.setdefault(k,{})[z]=v
    pdfall=f'https://www.ncsbe.gov/voting/sample-ballots'
    D={'v':1,'state':ST,'county':co.title(),'election':EL,'read':datetime.date.today().isoformat(),
       'source':os.environ.get('VIP_SOURCE','North Carolina State Board of Elections'),'sourceUrl':os.environ.get('VIP_SOURCE_URL','https://www.ncsbe.gov/voting/sample-ballot'),
       'lookup':os.environ.get('VIP_LOOKUP','https://vt.ncsbe.gov/RegLkup/'),'c':cl,'s':sl,'sp':sp,'st':st}
    fn=f'{OUT}/{slug(co)}.json'
    json.dump(D,open(fn,'w'),separators=(',',':'),ensure_ascii=False)
    sz=os.path.getsize(fn); tot['bytes']+=sz; tot['styles']+=len(sl); tot['ok']+=sum(x['ok'] for x in sl); tot['streets']+=len(st)
    index[co.title()]={'f':slug(co),'styles':len(sl),'ok':sum(x['ok'] for x in sl),'kb':round(sz/1024)}
json.dump({'v':1,'election':EL,'source':os.environ.get('VIP_SOURCE','North Carolina State Board of Elections'),'counties':index},open(f'{OUT}/index.json','w'),separators=(',',':'))
print(dict(tot),flush=True)
print(sorted(index.items(),key=lambda x:-x[1]['kb'])[:6])
