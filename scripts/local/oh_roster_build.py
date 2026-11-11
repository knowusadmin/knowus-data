#!/usr/bin/env python3
"""KnowUS local officials, Ohio: build data/officials-local/OH.json from the Ohio Secretary of State's Official Roster of
Ohio (ohioroster.ohiosos.gov, Local Government: City_Officials, Village_Officials and Townships_Officials spreadsheets,
edition 2024-2025), which each city, village and township reports to the Secretary of State. Names and titles exactly as
listed (all-capital entries in normal capitalization). Any official whose listed term has already ended is left out, and so
is a mayor / council member / trustee / commissioner with no term listed: the roster predates the Nov 2025 local elections,
so it cannot say who holds those seats now. Appointed officers with no term (manager, finance director, solicitor, clerk)
are kept. Contact: the city/village/township office telephone and the roster's office street address and website, labelled
as the office's main contact (no personal lines or emails are in the roster).
usage: oh_roster_build.py <dir with the three xlsx> <site data/local/OH.json> <out.json>   (needs pandas + openpyxl)"""
import json,re,sys,os,datetime as dt
import pandas as pd
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
U={'city':'https://ohioroster.ohiosos.gov/download_documents/City_Officials2024-2025.xlsx',
   'village':'https://ohioroster.ohiosos.gov/download_documents/Village_Officials2024-2025.xlsx',
   'township':'https://ohioroster.ohiosos.gov/download_documents/Townships_Officials2024-2025.xlsx'}
FILES={'city':'City_Officials2024-2025.xlsx','village':'Village_Officials2024-2025.xlsx','township':'Townships_Officials2024-2025.xlsx'}
ELECTED=re.compile(r'(?i)mayor|president of council|council|trustee|auditor|treasurer|law director|director of law|clerk-treasurer|fiscal officer|president')
APPOINTED_OVERRIDE=re.compile(r'(?i)finance director|manager|administrator|solicitor|clerk of council|safety|service director|deputy')
def nm(s): s=' '+str(s).lower()+' '; s=s.replace(' saint ',' st ').replace(' st. ',' st ').replace(' mount ',' mt ').replace(' mt. ',' mt ').replace('&','and'); return re.sub(r'[^a-z]','',s)
def tc(n):
    if not n.isupper() and not n.islower(): return n
    def w(x):
        x=x.capitalize()
        if re.match(r"^Mc[a-z]",x): x='Mc'+x[2:].capitalize()
        if re.match(r"^O'[a-z]",x): x="O'"+x[2:].capitalize()
        return '-'.join(y[:1].upper()+y[1:] for y in x.split('-'))
    return ' '.join(w(x) for x in n.split())
def s(v): return v.strip() if isinstance(v,str) and v.strip() and v.strip().lower()!='nan' else ''
def parse(kind):
    x=pd.read_excel(os.path.join(src,FILES[kind]),header=0,dtype=str); x.columns=[re.sub(r'\.\d+$','',c).strip() for c in x.columns]
    cols=list(x.columns); R={}
    namecol=[c for c in cols if c.endswith('Name') and c.split()[0] in ('City','Village','Township')][0]
    for row in x.itertuples(index=False):
        r=dict(zip(range(len(cols)),row)); g=lambda c: s(r[cols.index(c)]) if c in cols else ''
        rec={'name':g(namecol),'county':g('County') or g('County Name'),'tel':g('Telephone'),'web':g('Website'),
             'addr':g('Street Address') or g('Street Mailing Address'),'city':g('City'),'zip':g('ZIP code') or g('ZIP Code'),'off':[]}
        i=cols.index('Website')+1
        while i<len(cols):
            c=cols[i]
            if c in ('First Name','Middle Name','Last Name','Term Expiration','Term Ending'): i+=1; continue
            title=s(r[i]); fn=s(r[i+1]) if i+1<len(cols) else ''; mn=s(r[i+2]) if i+2<len(cols) else ''; ln=s(r[i+3]) if i+3<len(cols) else ''
            j=i+4; term=''
            if j<len(cols) and cols[j].startswith('Term'): term=s(r[j])[:10]; j+=1
            if fn and ln: rec['off'].append(((title or c),fn,mn,ln,term))
            i=j
        R.setdefault(nm(rec['name']),[]).append(rec)
    return R
D={k:parse(k) for k in FILES}
site=json.load(open(sitef,encoding='utf-8'))
CN={c['f']:nm(re.sub(r' County$','',c['n'])) for c in (site.get('counties') or [])}
res={'st':'OH','built':TODAY,'src':{'name':'Ohio Secretary of State, Official Roster of Ohio: City, Village and Township Officials, 2024-2025 edition (ohioroster.ohiosos.gov)','note':'Officials as each city, village and township reports them to the Secretary of State; names and titles exactly as listed. Mayors, council members, trustees and commissioners are shown only when the roster lists a term that has not ended.'},'places':{}}
st={'dropped_no_term':0,'places':0,'filled':0,'officials':0,'dropped_term_ended':0,'no_roster':[],'ambig':[],'empty_after_terms':[]}
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
for pid,p in site['places'].items():
    t=p.get('t')
    kind={'city':'city','village':'village','township':'township'}.get(t)
    if not kind: continue
    st['places']+=1
    key=nm(re.sub(r'(?i)\s+township$','',p['n']))
    rows=D[kind].get(key,[])
    if len(rows)>1:
        cty=set(CN.get(c) for c in (p.get('c') or []))
        rows=[r for r in rows if nm(r['county']) in cty]
    if len(rows)!=1: (st['ambig'] if rows else st['no_roster']).append(p['n']); continue
    r=rows[0]; ct={}
    if re.search(r'\d{3}\D*\d{4}',r['tel']): ct['p']=[r['tel']]
    if r['addr'] and r['city'] and not re.search(r'(?i)p\.?o\.? box',r['addr']): ct['a']='%s, %s, OH %s'%(r['addr'],r['city'],r['zip'][:5])
    web=r['web']
    if web and not web.startswith('http'): web='https://'+web
    if web: ct['w']=web
    if kind=='township' and not web: ct.pop('a',None)   # a township without its own website often lists an officer's home
    if ct: ct['src']=U[kind]; ct['g']=1
    L=[]
    for title,fn,mn,ln,term in r['off']:
        name=tc(re.sub(r'\s+',' ',' '.join(x for x in (fn,mn,ln) if x)))
        name=re.sub(r'\s(?:Lll|lll|LLL)$',' III',name).replace(' Ll ',' II ')
        if re.search(r'(?i)vacan|tbd|unknown',name) or len(name.split())<2: continue
        if not re.search(r'[A-Za-z]{3}',title) or title.strip().lower() in ('yes','no','x'): continue
        board=bool(re.search(r'(?i)mayor|council|trustee|commission|president',title)) and not APPOINTED_OVERRIDE.search(title)
        if term and term<TODAY: st['dropped_term_ended']+=1; continue
        if board and not term: st['dropped_no_term']+=1; continue
        if any(sameperson(name,x['n']) for x in L): continue
        o={'n':name,'r':title.strip(),'src':'ohroster','u':U[kind],'d':TODAY}
        tl=title.lower()
        if tl.startswith('mayor') or (kind=='township' and False): o['rk']='gen_mayor'
        elif 'council' in tl or 'trustee' in tl: o['rk']='gen_council'
        if term: o['s']='term ends %s'%dt.date.fromisoformat(term).strftime('%B %-d, %Y')
        if ct: o['ct']=dict(ct)
        L.append(o)
    if not L: st['empty_after_terms'].append(p['n']); continue
    ex=[o for o in (p.get('o') or []) if o.get('src')!='ohroster']
    L=[o for o in L if not any(sameperson(o['n'],x['n']) for x in ex) and not (o.get('rk')=='gen_mayor' and any(x.get('rk')=='gen_mayor' for x in ex))]
    if not L: continue
    w={'n':p['n'],'o':ex+L}
    if web and not p.get('w'): w['w']=web
    res['places'][pid]=w; st['filled']+=1; st['officials']+=len(L)
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:25])) for k,v in st.items()}))
