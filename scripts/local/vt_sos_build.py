#!/usr/bin/env python3
"""KnowUS local officials, Vermont: build data/officials-local/VT.json from the Vermont Secretary of State's
"Vermont Selectboard Members" listing (clerks report it after every town meeting, 17 V.S.A. 2665) and the SOS
"Town Clerk contact information" spreadsheet (both sos.vermont.gov, state .gov sources).
usage: vt_sos_build.py <selectboardinformation.pdf as `pdftotext -layout` text> <vermont_town_clerk_contact_information.xlsx> <site data/local/VT.json> <out.json>
Kept: Mayor, selectboard / city council members (with Chair / Vice Chair), Town Clerk.
Contacts: the town clerk's office phone and office address (the town office); a person's email only on the town's own
domain (never free mail). The selectboard list's mailing addresses are often homes and are never used."""
import json,re,sys,os,datetime as dt
from collections import Counter
import pandas as pd
sbt,clx,sitef,out=sys.argv[1:5]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
USB='https://outside.vermont.gov/dept/sos/Elections_Division/election_info_resources/town_meeting_local_elections/selectboardinformation.pdf'
UCL='https://outside.vermont.gov/dept/sos/Elections_Division/voters/vermont_town_clerk_contact_information.xlsx'
FREE=set('gmail.com yahoo.com hotmail.com outlook.com icloud.com aol.com comcast.net myfairpoint.net fairpoint.net together.net sover.net live.com msn.com me.com mac.com ymail.com tds.net gmavt.net charter.net consolidated.net vermontel.net shoreham.net wcvt.com kingcon.com protonmail.com mail.com yahoo.co.uk earthlink.net verizon.net att.net'.split())
def nm(s):
    s=s.lower().replace('saint ','st ').replace('st. ','st ')
    return re.sub(r'[^a-z]','',s)
def tkey(s):
    m=re.match(r'^(.*?)\s+(City|Town)$',s.strip())
    return (nm(m.group(1)),m.group(2).lower()) if m else (nm(s),None)
def look(D,p):
    b=nm(p['n']); return D.get((b,p['t'])) or D.get((b,None))
def base(d): p=d.lower().split('.'); return '.'.join(p[-2:])
def okdom(e,doms):
    if not e or '@' not in e: return False
    d=e.split('@')[1].lower()
    return d not in FREE and base(d) not in FREE and (base(d) in doms or d.endswith('.gov') or d.endswith('.vt.us'))
recs=[]
for l in open(sbt,encoding='utf-8',errors='replace').read().split('\n'):
    if not l.strip() or l[:1] in (' ','\x0c') or l.startswith(('Town/City','Vermont Selectboard','Vermont Secretary','Last Updated','Accessibility')): continue
    f=re.split(r'\s{2,}',l.strip())
    if len(f)>=2 and f[1].startswith('Note:'): continue
    if len(f)>=6 and f[-2]=='VT' and re.match(r'^\d{5}',f[-1]): core=f[:-4]
    else: core=f[:]
    em=''
    for i in range(len(core)-1,1,-1):
        if '@' in core[i]: em=core[i]; core=core[:i]; break
    if len(core)<4: continue
    recs.append(dict(town=core[0],body=core[1],pos=' '.join(core[2:-2]),first=core[-2],last=core[-1],email=em))
raw=pd.read_excel(clx,header=None,dtype=str); hi=[i for i in range(15) if 'Town Name' in raw.iloc[i].tolist()][0]
cl=pd.read_excel(clx,header=hi,dtype=str).fillna('')
CL={}
for r in cl.to_dict('records'):
    if r.get('Town Name'): CL[tkey(r['Town Name'])]=r
site=json.load(open(sitef,encoding='utf-8'))
by={}
for r in recs: by.setdefault(tkey(r['town']),[]).append(r)
res={'st':'VT','built':TODAY,'src':{'name':'Vermont Secretary of State, Elections Division: Selectboard Members listing and Town Clerk contact information (sos.vermont.gov)','note':'As each town clerk reports them to the Secretary of State; names exactly as listed.'},'places':{}}
st={'places':0,'filled':0,'officials':0,'no_listing':[],'clerk_only':0}
def role(r):
    b=r['body']; p=r['pos'].lower()
    if b.lower()=='mayor' or p=='mayor': return ('Mayor','gen_mayor',0)
    if 'vice' in p: return ((('Selectboard' if 'select' in b.lower() else 'City Council')+' Vice Chair'),'gen_council',2)
    if 'chair' in p or 'president' in p: return ((('Selectboard' if 'select' in b.lower() else 'City Council')+' Chair'),'gen_council',1)
    if 'alder' in p: return ('Alderman','gen_council',3)
    if 'select' in b.lower(): return ('Selectboard Member','gen_council',3)
    return ('City Council Member','gen_council',3)
for pid,p in site['places'].items():
    if p.get('k')=='u' or p.get('t') not in ('town','city'): continue
    st['places']+=1
    rs=look(by,p) or []; c=look(CL,p)
    if not rs and not c: st['no_listing'].append(p['n']); continue
    doms=set()
    if p.get('w'):
        m=re.match(r'https?://([^/]+)',p['w']); doms.add(base(m.group(1).replace('www.',''))) if m else None
    ph=c.get('Phone Number','').strip() if c else ''
    addr=''
    if c and c.get('Office Address'): addr='%s, %s, VT %s'%(c['Office Address'].strip(),c['Office City'].strip(),c['Office Zip'].strip())
    cem=c.get('Email','').strip() if c else ''
    if cem and not okdom(cem,doms): cem=''
    if cem: doms.add(base(cem.split('@')[1]))
    L=[]; seen=set()
    for r in rs:
        name=re.sub(r'\s+',' ',(r['first']+' '+r['last'])).strip()
        if name.lower() in seen or re.search(r'vacan|tbd',name,re.I): continue
        seen.add(name.lower()); rl,rk,order=role(r)
        ct={}
        if ph: ct['p']=[ph]
        g=1
        if okdom(r['email'],doms): ct['e']=r['email']; g=0
        elif cem: ct['e']=cem
        if addr: ct['a']=addr
        ct['src']=UCL if g else USB
        if g: ct['g']=1
        L.append({'n':name,'r':rl,'rk':rk,'src':'vtsos','u':USB,'d':TODAY,'ct':ct,'_o':order})
    if c and c.get('First Name'):
        name=(c['First Name'].strip()+' '+c['Last Name'].strip()).strip()
        if name and name.lower() not in seen:
            ct={}
            if ph: ct['p']=[ph]
            if cem: ct['e']=cem
            if addr: ct['a']=addr
            ct['src']=UCL; ct['g']=1
            L.append({'n':name,'r':c.get('Title') or 'Town Clerk','src':'vtsos','u':UCL,'d':TODAY,'ct':ct,'_o':5})
    L.sort(key=lambda x:(x['_o'],x['n'].split()[-1]))
    for x in L: x.pop('_o')
    if not rs: st['clerk_only']+=1
    ex=[o for o in (p.get('o') or []) if o.get('src')!='vtsos']
    def same(a,b):
        a,b=a.split(),b.split(); return nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
    add=[x for x in L if not any(same(x['n'],o['n']) for o in ex) and not (x['r']=='Mayor' and any(o.get('rk')=='gen_mayor' for o in ex))]
    if not add: continue
    res['places'][pid]={'n':p['n'],'o':ex+add}; st['filled']+=1; st['officials']+=len(add)
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:30])) for k,v in st.items()}))
