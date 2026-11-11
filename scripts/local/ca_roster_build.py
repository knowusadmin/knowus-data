#!/usr/bin/env python3
"""KnowUS local officials, California: build data/officials-local/CA.json from the California Secretary of State's
California Roster 2026, "Incorporated City and Town Officials" (admin.cdn.sos.ca.gov/ca-roster/2026/cities-towns.pdf),
which each city reports to the Secretary of State. Kept: Mayor, Vice Mayor / Mayor Pro Tempore, City Council members,
City Manager, City Clerk, Treasurer; names exactly as printed. Contact: the city hall's own telephone, address and
email (email only on the city's own domain), labelled as the office's main contact.
usage: ca_roster_build.py <cities-towns.pdf> <site data/local/CA.json> <out.json>   (needs pdftotext)"""
import json,re,sys,os,subprocess,datetime as dt
pdf,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
U='https://admin.cdn.sos.ca.gov/ca-roster/2026/cities-towns.pdf'
n=int(re.search(r'Pages:\s+(\d+)',subprocess.run(['pdfinfo',pdf],capture_output=True,text=True,timeout=30).stdout).group(1))
txt=[]
for pg in range(1,n+1):
    for x in (0,306):
        txt.append(subprocess.run(['pdftotext','-f',str(pg),'-l',str(pg),'-x',str(x),'-y','0','-W','306','-H','792',pdf,'-'],capture_output=True,text=True,timeout=30).stdout)
lines=[l.strip() for l in '\n'.join(txt).split('\n')]
lines=[l for l in lines if l and l not in ('California Roster 2026','Incorporated Cities and Town Officials') and not l.startswith(('Please Note','ecretary of State'))]
ents=[]; cur=None
for i,l in enumerate(lines):
    nxt=lines[i+1] if i+1<len(lines) else ''
    if nxt.startswith('(County of') and ':' not in l and len(l)<70:
        m=re.match(r'^(City and County|City|Town) of (.+)$',l)
        cur={'kind':m.group(1) if m else 'City','name':(m.group(2) if m else l).strip(),'lines':[]}; ents.append(cur); continue
    if cur: cur['lines'].append(l)
KEYS=['Address','Telephone','Website','Email','Office Hours','Mayor','Vice Mayor/Mayor Pro Tempore','City Council','Town Council','Board of Supervisors','City Manager','Town Manager','City Administrator','City Clerk','Town Clerk','City Attorney','Town Attorney','Treasurer','City Treasurer','Police Chief','Fire Chief','School Superintendent','Incorporated','Legislative Districts','Chartered City Population','General Law City Population','Population']
KRX=re.compile(r'^('+'|'.join(re.escape(k) for k in sorted(KEYS,key=len,reverse=True))+r')\s*:\s*(.*)$')
SCHED=re.compile(r'(?i)\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|every|month|meet|p\.?m\.?|a\.?m\.?|\d|recess|except|regular|session|held|weekly)\b')
def fields(e):
    F={}; k=None
    for l in e['lines']:
        m=KRX.match(l)
        if m: k=m.group(1); F.setdefault(k,[]).append(m.group(2)); continue
        if l.startswith('(County of'): F['county']=[l]; k=None; continue
        if k in ('City Council','Town Council'):
            if SCHED.search(l): k='_sched'; continue
            F[k].append(l)
        elif k in ('Office Hours','Address','Legislative Districts','_sched'): pass
        elif k in ('Mayor','Vice Mayor/Mayor Pro Tempore','City Manager','City Clerk','Town Clerk','Treasurer','City Treasurer','Town Manager','City Administrator'):
            pass
    return F
PRE=re.compile(r"^(?:and\s+|&\s+)?(?:(MPT|Members|Deputy Mayor|Vice Mayor|Mayor Pro Tem(?:pore)?|Mayor|Council Members?|Councilmembers|The remaining members|Elected City Clerk|Elected|Town Administrator|Esq\.|(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth) Ward|Council ?Member|Councilmember|Councilwoman|Councilman|City Clerk|Town Clerk|City Treasurer|Treasurer|City Manager|Town Manager|City Administrator|City Adminstrator|Admin(?:istrator)?|Interim|Acting|Dr\.|Hon\.|Honorable|Captain|Chief)\b[\s:,.\-]*)+",re.I)
POST=re.compile(r"(?:\s*[,\-\u2013(]\s*(?:District|Dist\.?|Ward|Seat|Vice Mayor|Mayor Pro Tem\w*|Mayor|Interim|Acting|Council ?Member|Councilmember|City Manager|City Clerk|Treasurer)[^,]*\)?$|\s+\d+(?:st|nd|rd|th)?$)",re.I)
GEN=re.compile(r"(?i)^(council ?member|councilmember|city (manager|clerk|council|treasurer|administrator)|mayor( pro tem\w*)?|vice mayor|vacant|members?|none|tbd)$")
def tc(n):
    if not n.isupper(): return n
    def w(x):
        x=x.capitalize()
        if re.match(r"^Mc[a-z]",x): x='Mc'+x[2:].capitalize()
        if re.match(r"^O'[a-z]",x): x="O'"+x[2:].capitalize()
        x='"'.join(y[:1].upper()+y[1:] for y in x.split('"'))
        return '-'.join(y[:1].upper()+y[1:] for y in x.split('-'))
    return ' '.join(w(x) for x in n.split())
def clean(p):
    """-> (name, title word found before it or None)"""
    p=re.sub(r'\s+',' ',p).strip().strip('.,;:-').strip()
    p=re.sub(r'^(?:and|&)\s+','',p)
    p=re.sub(r'(?i),?\s+(MMC|CMC|PsyD|Ph\.?\s?D\.?|Esq\.?|CPA|MPA|At Large|effective\b.*)$','',p).strip()
    p=re.sub(r'(?i)^(Financial Officer|Finance Director|Chief Financial Officer)\s+','',p)
    m=PRE.match(p); pre=None
    if m:
        pre=(m.group(1) or '').lower(); p=p[m.end():].strip()
    for _ in range(3): p=POST.sub('',p).strip().strip('.,;:-').strip()
    p=re.sub(r'\s*\([^)]*\)\s*',' ',p).strip()
    p=re.sub(r'(?i)\s+(Councilmember|Council Member|District)$','',p).strip()
    if pre and ('deputy' in pre and 'mayor' not in pre or pre.startswith('dty')): return None,None
    if re.search(r'(?i)deputy|dty |appointed|duties|director|rotation|services|/|\bcheif\b',p): return None,None
    if re.search(r'(?i)\b(mayor|council|city|district|member|town|ward)$',p): return None,None
    if not p or GEN.match(p) or re.search(r'\d|@|www\.|https?:',p) or len(p.split())<2 or len(p.split())>4 or len(p)>45: return None,None
    return tc(p),pre
def names(vals):
    pieces=[]; carry=''
    for line in vals:
        line=re.sub(r'\s+',' ',(carry+' '+line).strip()); carry=''
        ps=[x.strip() for x in re.split(r',\s*|\s+and\s+|;\s*|\s+&\s+|^and\s+|^&\s+',line) if x and x.strip()]
        if len(ps)==1 and len(ps[0].split())==1 and pieces and not carry: pieces[-1]+=' '+ps[0]; continue
        if ps and len(ps[-1].split())==1 and not line.rstrip().endswith(','): carry=ps.pop()
        pieces+=ps
    if carry: pieces.append(carry)
    outp=[]
    for p in pieces:
        if SCHED.search(p) and not re.search(r'(?i)district|ward|seat',p): continue
        if re.search(r'(?i)vacan|\btbd\b|\btba\b|n/a|\bnone\b',p): continue
        c,pre=clean(p)
        if c: outp.append((c,pre))
    return outp
def one(v):
    if not v: return None
    s=re.sub(r'\s+',' ',v[0]).strip()
    if re.search(r'(?i)vacan|\btbd\b|contract|n/a|\bnone\b',s): return None
    return clean(s)[0]
def nm(s): return re.sub(r'[^a-z]','',s.lower().replace('saint ','st ').replace('st. ','st '))
def base(d): p=d.lower().split('.'); return '.'.join(p[-2:])
E={}
for e in ents: E.setdefault(nm(e['name']),e)
site=json.load(open(sitef,encoding='utf-8'))
res={'st':'CA','built':TODAY,'src':{'name':'California Secretary of State, California Roster 2026: Incorporated City and Town Officials (sos.ca.gov)','note':'Officials as each city reports them to the Secretary of State; names exactly as printed.'},'places':{}}
STALE={'San Francisco'}  # the 2026 roster still lists the former mayor (London Breed); Daniel Lurie took office Jan 8, 2025
st={'stale_skipped':[],'cities':0,'filled':0,'officials':0,'no_roster':[],'roster_entries':len(ents)}
def sameperson(a,b):
    a,b=a.split(),b.split(); return nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
for pid,p in site['places'].items():
    if p.get('t') not in ('city','town') or p.get('k')=='u': continue
    st['cities']+=1
    e=E.get(nm(p['n'])) or E.get(nm(re.sub(r'\s*\(.*\)','',p['n']))) or (E.get(nm(re.search(r'\((.*)\)',p['n']).group(1))) if '(' in p['n'] else None) or E.get(nm(p['n']+' Camp'))
    if not e: st['no_roster'].append(p['n']); continue
    if p['n'] in STALE: st['stale_skipped'].append(p['n']); continue
    F=fields(e); ct={}
    tel=one(F.get('Telephone')) or (F.get('Telephone') or [''])[0].strip()
    if re.search(r'\(?\d{3}\)?[ .-]?\d{3}-\d{4}',tel or ''): ct['p']=[re.search(r'\(?\d{3}\)?[ .-]?\d{3}-\d{4}',tel).group(0)]
    ad=' '.join(F.get('Address') or []).strip()
    if ad and re.search(r'\d',ad) and not re.search(r'(?i)p\.?o\.? box',ad): ct['a']=ad
    web=(F.get('Website') or [''])[0].strip()
    doms=set()
    if web:
        m=re.match(r'(?:https?://)?([^/\s]+)',web); doms.add(base(m.group(1).replace('www.',''))) if m else None
    if p.get('w'):
        m=re.match(r'https?://([^/]+)',p['w']); doms.add(base(m.group(1).replace('www.',''))) if m else None
    em=(F.get('Email') or [''])[0].strip()
    if '@' in em and base(em.split('@')[1]) in doms: ct['e']=em
    if web and not web.startswith('http'): web='https://'+web
    if web: ct['w']=web
    if ct: ct['src']=U; ct['g']=1
    L=[]
    def add(nmv,role,rk=None):
        if not nmv or any(sameperson(nmv,x['n']) for x in L): return
        o={'n':nmv,'r':role,'src':'caroster','u':U,'d':TODAY}
        if rk: o['rk']=rk
        if ct: o['ct']=dict(ct)
        L.append(o)
    tk='Town' if e['kind']=='Town' else 'City'
    add(one(F.get('Mayor')),'Mayor','gen_mayor')
    add(one(F.get('Vice Mayor/Mayor Pro Tempore')),'Vice Mayor / Mayor Pro Tem','gen_council')
    for x,pre in names((F.get('City Council') or [])+(F.get('Town Council') or [])):
        if pre=='mayor': add(x,'Mayor','gen_mayor')
        elif pre and (pre.startswith('vice') or pre.startswith('deputy mayor') or 'pro tem' in pre): add(x,'Vice Mayor / Mayor Pro Tem','gen_council')
        else: add(x,tk+' Council Member','gen_council')
    add(one(F.get('City Manager') or F.get('Town Manager') or F.get('City Administrator')),tk+' Manager' if (F.get('City Manager') or F.get('Town Manager')) else 'City Administrator')
    add(one(F.get('City Clerk') or F.get('Town Clerk')),tk+' Clerk')
    add(one(F.get('Treasurer') or F.get('City Treasurer')),tk+' Treasurer')
    if not L: continue
    ex=[o for o in (p.get('o') or []) if o.get('src')!='caroster']
    L=[o for o in L if not any(sameperson(o['n'],x['n']) for x in ex) and not (o.get('rk')=='gen_mayor' and any(x.get('rk')=='gen_mayor' for x in ex))]
    if not L: continue
    w={'n':p['n'],'o':ex+L}
    if web and not p.get('w'): w['w']=web
    res['places'][pid]=w; st['filled']+=1; st['officials']+=len(L)
MAN=os.path.join(os.path.dirname(os.path.abspath(out)),'manual','CA-san-francisco.json')
if os.path.exists(MAN):
    mo=json.load(open(MAN,encoding='utf-8'))['o']
    for pid,p in site['places'].items():
        if p['n']=='San Francisco' and p.get('t')=='city':
            res['places'][pid]={'n':p['n'],'o':[o for o in (p.get('o') or []) if o.get('src')!='caroster' and o['n'] not in {m['n'] for m in mo}]+mo}; st['filled']+=1; st['officials']+=len(mo); st['manual']=['San Francisco']
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:30])) for k,v in st.items()}))
