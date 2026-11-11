#!/usr/bin/env python3
"""KnowUS local officials, Wisconsin: municipal clerks of every town, village and city from the State of Wisconsin
Department of Administration's Municipal Data System clerk directory (mds.wi.gov/View/Clerks, CSV export), names
exactly as listed. Contacts: the clerk's email only on the municipality's own domain (or a .gov / .wi.us address), and
the listed phone only alongside such an email or when the municipality has its own website (town clerks often work
from home, so a bare number or address is never shown). No addresses.
usage: wi_mds_build.py <RadGridExport.csv> <site data/local/WI.json> <out.json>"""
import json,re,sys,os,csv,datetime as dt
csvf,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
U='https://mds.wi.gov/View/Clerks'
FREE=set('gmail.com yahoo.com hotmail.com outlook.com icloud.com aol.com live.com msn.com me.com mac.com ymail.com charter.net att.net sbcglobal.net frontier.com frontiernet.net earthlink.net verizon.net protonmail.com mail.com centurytel.net tds.net nornet.net wildblue.net hughes.net spectrum.net rr.com wi.rr.com new.rr.com wctc.net chorus.net baycountry.net cheqnet.net nwcwisconsin.net citizens-tel.net'.split())
def nm(s): s=' '+s.lower()+' '; s=s.replace(' saint ',' st ').replace(' st. ',' st ').replace(' mount ',' mt ').replace(' mt. ',' mt ').replace('&','and'); return re.sub(r'[^a-z]','',s)
def base(d): p=d.lower().split('.'); return '.'.join(p[-2:])
def owndom(e,doms,town):
    if not e or '@' not in e: return False
    d=e.strip().split('@')[1].lower()
    if d in FREE or base(d) in FREE or re.search(r'(yahoo|gmail|hotmail|aol|outlook|rr)\.',d): return False
    t=nm(town); return base(d) in doms or d.endswith(('.gov','.wi.us')) or (len(t)>=4 and t[:8] in nm(d))
def tc(n):
    if not n.isupper(): return n
    def w(x):
        x=x.capitalize()
        if re.match(r"^Mc[a-z]",x): x='Mc'+x[2:].capitalize()
        if re.match(r"^O'[a-z]",x): x="O'"+x[2:].capitalize()
        return '-'.join(y[:1].upper()+y[1:] for y in x.split('-'))
    return ' '.join(w(x) for x in n.split())
T={'T':'town','V':'village','C':'city'}
M={}
for r in csv.DictReader(open(csvf,encoding='utf-8-sig',newline='')):
    m=re.match(r'^([TVC]) (.+)$',r['Place Name'].strip())
    if not m: continue
    M.setdefault((T[m.group(1)],nm(m.group(2))),[]).append(r)
site=json.load(open(sitef,encoding='utf-8'))
CN={c['f']:nm(re.sub(r' County$','',c['n'])) for c in (site.get('counties') or [])}
res={'st':'WI','built':TODAY,'src':{'name':'State of Wisconsin Department of Administration, Municipal Data System: municipal clerk directory (mds.wi.gov)','note':'Clerks as each municipality reports them to the state; names exactly as listed.'},'places':{}}
st={'places':0,'filled':0,'officials':0,'with_contact':0,'no_listing':[],'ambig':[]}
for pid,p in site['places'].items():
    t=p.get('t')
    if t not in ('town','village','city'): continue
    st['places']+=1
    rows=M.get((t,nm(p['n'])),[])
    if len(rows)>1 and len(set(nm(r['Clerk Name']) for r in rows))==1: rows=rows[:1]
    if len(rows)>1:
        cty=set(CN.get(c) for c in (p.get('c') or []))
        rows=[r for r in rows if nm(r['County']) in cty]
    if len(rows)!=1:
        (st['ambig'] if rows else st['no_listing']).append(p['n']); continue
    r=rows[0]; name=tc(re.sub(r'\s+',' ',r['Clerk Name']).strip())
    if not name or re.search(r'vacan|unknown|tbd',name,re.I): st['no_listing'].append(p['n']); continue
    doms=set()
    if p.get('w'):
        m=re.match(r'https?://([^/]+)',p['w']); doms.add(base(m.group(1).replace('www.',''))) if m else None
    ex=[o for o in (p.get('o') or []) if o.get('src')!='wimds']
    if any(o['n'].split()[-1].lower()==name.split()[-1].lower() for o in ex): continue
    ct={}; e=r['Email'].strip()
    if owndom(e,doms,p['n']): ct['e']=e
    if r['Phone1'].strip() and (ct or doms): ct['p']=[r['Phone1'].strip()]
    o={'n':name,'r':{'town':'Town Clerk','village':'Village Clerk','city':'City Clerk'}[t],'src':'wimds','u':U,'d':TODAY}
    if ct: ct['src']=U; o['ct']=ct; st['with_contact']+=1
    res['places'][pid]={'n':p['n'],'o':ex+[o]}; st['filled']+=1; st['officials']+=1
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:25])) for k,v in st.items()}))
