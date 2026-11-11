#!/usr/bin/env python3
"""KnowUS local officials, Illinois: build data/officials-local/IL.json from
 (1) the Illinois Secretary of State's 2025-2026 Illinois Blue Book, "Incorporated Cities, Towns & Villages of Illinois"
     (ilsos.gov): every municipality's Mayor/President and Clerk, names exactly as printed; and
 (2) the Illinois Comptroller's Local Government Contact Information file (files.illinoiscomptroller.gov/LocGov/UnitData.csv),
     self-reported by each unit on its Annual Financial Report: the chief executive's title (Mayor / President), and
     for townships the Township Supervisor.
usage: il_build.py <bluebook text> <UnitData.csv> <site data/local/IL.json> <out.json>
Contacts: a person's own line/email as the unit reports it to the Comptroller, only for the same named person, a phone on
the unit's office line or exchange, an email never on free mail; no addresses (AFR addresses are often a clerk's home); never a free-mail address."""
import json,re,sys,os,datetime as dt
import csv
bbt,csvf,sitef,out=sys.argv[1:5]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
UBB='https://www.ilsos.gov/content/dam/publications/illinois-bluebook/2025-26/incorporated-cities-towns-villages.pdf'
UCO='https://illinoiscomptroller.gov/constituent-services/local-government/contact-information-for-local-govts'
FREE=set('gmail.com yahoo.com hotmail.com outlook.com icloud.com aol.com comcast.net live.com msn.com me.com mac.com ymail.com charter.net att.net sbcglobal.net frontier.com frontiernet.net mchsi.com earthlink.net verizon.net protonmail.com mail.com netzero.net juno.com wildblue.net hughes.net centurytel.net windstream.net yahoo.co rocketmail.com bellsouth.net'.split())
def nm(s): s=' '+s.lower()+' '; s=s.replace(' saint ',' st ').replace(' st. ',' st ').replace(' sainte ',' ste ').replace(' ste. ',' ste ').replace(' mount ',' mt ').replace(' mt. ',' mt ').replace('&','and'); return re.sub(r'[^a-z]','',s)
def base(d): p=d.lower().split('.'); return '.'.join(p[-2:])
def okem(e):
    if not e or '@' not in e: return False
    d=e.strip().split('@')[1].lower(); return d not in FREE and base(d) not in FREE and not re.search(r'(yahoo|gmail|hotmail|aol|outlook)\.',d)
rx=re.compile(r'^(.+?) ([ctv]) (.+?)\s*\.{2,}\s*([\d,]+)\s+(.+?)(?:\s*\.{2,}\s*(.*))?$')
rx2=re.compile(r'^(.+?) ([ctv]) ((?:[A-Z][A-Za-z. ]+, )*[A-Z][A-Za-z. ]+?)([\d,]+) (.+?)\s*\.{2,}\s*(.*)$')
SUF=re.compile(r'\s*(STATE & LOCAL GOVERNMENT FACTS \| \d+|\d+ \| 2025-2026 ILLINOIS BLUE BOOK)\s*$')
lines=[SUF.sub('',l.strip()).strip() for l in open(bbt,encoding='utf-8').read().split('\n')]
lines=[l for l in lines if l and not l.startswith(('City (c)','or Village (v)','Incorporated Cities','456 |'))]
BB={}; i=0
while i<len(lines):
    l=lines[i]; m=rx.match(l)
    if not m and l.endswith(',') and i+1<len(lines): m=rx.match(l+' '+lines[i+1]); i+=1 if m else 0
    if not m: m=rx2.match(l)
    if m:
        g=[(x or '').strip() for x in m.groups()]
        BB.setdefault((nm(g[0]),g[1]),dict(n=g[0],t=g[1],county=g[2],mayor=g[4],clerk=g[5]))
    i+=1
CO={}
for r in csv.DictReader(open(csvf,encoding='latin-1',newline='')):
    r={k:(v or '') for k,v in r.items()}
    k={'City':'c','Village':'v','Town':'t','Township':'w'}.get(r['Description'])
    if not k: continue
    CO.setdefault((nm(re.sub(r'\s+\d+$','',r['UnitName'])),k),[]).append(r)
def fix(s): return re.sub(r'\s+',' ',s).strip()
def sameperson(a,b):
    a,b=a.split(),b.split()
    return bool(a and b) and nm(a[-1].rstrip('.'))==nm(b[-1].rstrip('.')) and nm(a[0])[:1]==nm(b[0])[:1]
def pick(rows,countyfips_names):
    if len(rows)==1: return rows[0]
    rr=[r for r in rows if nm(r['County']) in countyfips_names]
    return rr[0] if len(rr)==1 else None
site=json.load(open(sitef,encoding='utf-8'))
CN={c['f']:re.sub(r' County$','',c['n']) for c in (site.get('counties') or [])}
res={'st':'IL','built':TODAY,'src':{'name':'Illinois Secretary of State, 2025-2026 Illinois Blue Book (Incorporated Cities, Towns & Villages) and Illinois Comptroller Local Government Contact Information','note':'Mayor/president and clerk exactly as printed in the Blue Book; township supervisors as each township reports them to the Comptroller.'},'places':{}}
st={'municipal':0,'muni_filled':0,'townships':0,'twp_filled':0,'officials':0,'no_bb':[],'title_conflict':[],'twp_none':[],'ambig':[]}
TY={'city':'c','village':'v','town':'t'}
def digits(x): return re.sub(r'\D','',x or '')[-10:]
def owndom(e,doms,town):
    if not okem(e): return False
    d=e.strip().split('@')[1].lower(); t=nm(re.sub(r'(?i)\s+township$','',town))
    return base(d) in doms or d.endswith(('.gov','.il.us')) or (len(t)>=4 and t[:min(len(t),8)] in nm(d))
def office_ok(r,doms,town):
    return bool(doms) or any(owndom(r.get(k,''),doms,town) for k in ('Email_GOV','CEOEmail','CFOEmail','FOIAEmail','PAEmail'))
def person_ct(r,pre,name,doms,town=''):
    """A person's own office line/email from the Comptroller file: kept only when the row names the same person, the
    phone is the unit's office line or on its office exchange, and the email is on the unit's own domain."""
    if r is None: return None
    F={'CEO':('CEOFName','CEOLName','CEOPhone','CEOEmail'),'FOIA':('FOIAFName','FOIALName','FOIAPhone','FOIAEmail'),
       '':('FirstName','LastName','Phone','Email_GOV'),'CFO':('CFOFName','CFOLName','CFOPhone','CFOEmail')}[pre]
    if not sameperson(name,fix(r[F[0]]+' '+r[F[1]])): return None
    ct={}; up=digits(r.get('Phone')); pp=digits(r.get(F[2]))
    if office_ok(r,doms,town) and len(pp)==10 and (pp==up or (len(up)==10 and pp[:6]==up[:6])): ct['p']=[r[F[2]].strip()]
    e=(r.get(F[3]) or '').strip()
    if owndom(e,doms,town): ct['e']=e
    if not ct: return None
    ct['src']=UCO; return ct
def find_ct(r,name,doms,town):
    for pre in ('CEO','FOIA','','CFO'):
        c=person_ct(r,pre,name,doms,town)
        if c: return c
    return None
for pid,p in site['places'].items():
    t=p.get('t')
    cty=set(nm(CN.get(c,'')) for c in (p.get('c') or []))
    doms=set()
    if p.get('w'):
        m=re.match(r'https?://([^/]+)',p['w']); doms.add(base(m.group(1).replace('www.',''))) if m else None
    ex=[o for o in (p.get('o') or []) if o.get('src') not in ('ilbb','ilco')]
    L=[]
    if t in TY:
        st['municipal']+=1; k=TY[t]; b=BB.get((nm(p['n']),k))
        if not b:
            for kk in 'cvt':
                if (nm(p['n']),kk) in BB: b=BB[(nm(p['n']),kk)]; break
        if not b: st['no_bb'].append(p['n']); continue
        rows=CO.get((nm(p['n']),b['t']),[]); r=pick(rows,cty) if rows else None
        mayor=fix(b['mayor']); clerk=fix(b['clerk'])
        if b['t']=='c': mr='Mayor'
        elif b['t']=='v': mr='Village President'
        else: mr='Town President'
        if r is not None and sameperson(mayor,fix(r['CEOFName']+' '+r['CEOLName'])) and r['CEOTitle'].strip().lower()=='mayor' and b['t']!='c': mr='Mayor'
        if mayor and not re.search(r'vacan',mayor,re.I):
            o={'n':mayor,'r':mr,'rk':'gen_mayor','src':'ilbb','u':UBB,'d':TODAY}
            ct=find_ct(r,mayor,doms,p['n'])
            if ct: o['ct']=ct
            L.append(o)
        if clerk and not re.search(r'vacan',clerk,re.I):
            o={'n':clerk,'r':{'c':'City Clerk','v':'Village Clerk','t':'Town Clerk'}[b['t']],'src':'ilbb','u':UBB,'d':TODAY}
            ct=find_ct(r,clerk,doms,p['n'])
            if ct: o['ct']=ct
            L.append(o)
        if not L: continue
        if any(o.get('rk')=='gen_mayor' for o in ex): L=[o for o in L if o.get('rk')!='gen_mayor']
        L=[o for o in L if not any(sameperson(o['n'],e['n']) for e in ex)]
        if not L: continue
        res['places'][pid]={'n':p['n'],'o':ex+L}; st['muni_filled']+=1; st['officials']+=len(L)
    elif t=='township':
        st['townships']+=1
        rows=CO.get((nm(re.sub(r'\s+township$','',p['n'],flags=re.I)),'w'),[])
        r=pick(rows,cty) if rows else None
        if rows and r is None: st['ambig'].append(p['n']); continue
        if r is None: st['twp_none'].append(p['n']); continue
        sup=None
        for f,l_,tt in (('CEOFName','CEOLName','CEOTitle'),('FirstName','LastName','Title'),('CFOFName','CFOLName','CFOTitle'),('FOIAFName','FOIALName','FOIATitle'),('PAFName','PALName','PATitle')):
            ti=r.get(tt,'').strip().lower()
            if ti.startswith('super') and ti!='superintendent':
                sup=fix(r[f]+' '+r[l_]); break
        if not sup: st['twp_none'].append(p['n']); continue
        if sup.isupper():
            def tc(w):
                w=w.capitalize()
                if re.match(r"^Mc[a-z]",w): w='Mc'+w[2:].capitalize()
                if re.match(r"^O'[a-z]",w): w="O'"+w[2:].capitalize()
                return '-'.join(x[:1].upper()+x[1:] for x in w.split('-'))
            sup=' '.join(tc(w) for w in sup.split())
        o={'n':sup,'r':'Township Supervisor','rk':'gen_mayor','src':'ilco','u':UCO,'d':TODAY}
        ct=find_ct(r,sup,doms,p['n'])
        if ct: o['ct']=ct
        if any(sameperson(sup,e['n']) for e in ex) or any(e.get('rk')=='gen_mayor' for e in ex): continue
        res['places'][pid]={'n':p['n'],'o':ex+[o]}; st['twp_filled']+=1; st['officials']+=1
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:25])) for k,v in st.items()}))
