#!/usr/bin/env python3
"""KnowUS local officials, New Hampshire: town select boards, town administrators / managers and clerks, and city
managers / clerks, from the NH Department of Transportation's "City and Town Officials of the State of New Hampshire"
(September 2025; Bureau of Planning and Community Assistance; mm.nh.gov/files/uploads/dot/remote-docs/
nh-officials-directory.pdf, read from the Internet Archive's copy of that file because mm.nh.gov refuses this machine;
the archive's October 25, 2026 capture shows the live file unchanged). The directory's data are "current as of 9/1/2025",
so each record says so. Elected city officials (mayors, councils, aldermen) are NOT taken from it, because the cities
elected new councils in November 2025. Contact: the municipal office phone and website; an email only on the town's own
web domain; an official's own phone only when it is the office line. No addresses from PO boxes.
usage: nh_dot_build.py <nh.txt (pdftotext -layout)> <site data/local/NH.json> <out.json>"""
import json,re,sys,os,collections,datetime as dt
from urllib.parse import urlparse
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
U='https://mm.nh.gov/files/uploads/dot/remote-docs/nh-officials-directory.pdf'
site=json.load(open(sitef,encoding='utf-8')); P=site['places']
def nz(s): return re.sub(r'[^a-z]','',s.lower())
PL={}
for pid,p in P.items():
    if p.get('t')!='CDP': PL.setdefault(nz(p['n']),[]).append(pid)
ROLEW=re.compile(r'^(Mayor|Town Administrator.*|Town Manager.*|City Manager.*|Town Clerk.*|City Clerk.*|Board of Selectm[ae]n.*|Select ?Board.*|Selectm[ae]n.*|Selectperson.*|Aldermen.*|Alderman.*|City Council.*|Council.*|Town Council.*|Road Agent.*|Administrator.*|Board of Aldermen.*|Commissioner.*|Chair.*|Vice.*|Deputy.*|Director.*|Public Works.*|Highway.*|Finance.*|Assistant.*|Executive.*|Moderator.*|Treasurer.*|Tax Collector.*|Supervisor.*|Councilor.*|Ward.*|General Services.*|Data Current.*|address|.*Director)$')
PHR=r'\(?\d{3}\)?[-\. ]\d{3}-\d{4}(?:\s*(?:x|ext\.?)\s*\d+)?'
def toks(line): return [(m.start(),m.group(0).strip()) for m in re.finditer(r'\S+(?: \S+)*',line)]
txt=open(src,encoding='utf-8',errors='replace').read()
towns=[]; cur=None
for line in txt.split('\n'):
    if not line.strip() or 'Municipal Officials in New Hampshire' in line or re.search(r'Town Info\s+Town Officials',line) or re.search(r'Municipality\s+Municipality',line) or re.match(r'^\s*Address\s*$',line): continue
    tk=toks(line)
    if tk and tk[0][0]<6 and re.match(r"^[A-Z][A-Za-z\.' ]+$",tk[0][1]) and len(tk)>=2 and tk[1][0]<40:
        cur={'name':tk[0][1],'lines':[]}; towns.append(cur)
    if cur and tk: cur['lines'].append(tk)
def parse_town(t):
    roff=None
    for tk in t['lines']:
        for pos,tx in tk:
            if pos>100 and ROLEW.match(tx): roff=pos; break
        if roff: break
    left=[]; offs=[]
    for tk in t['lines']:
        L_=[x for p,x in tk if roff is None or p<roff-3]; R_=[(p,x) for p,x in tk if roff is not None and p>=roff-3]
        if L_ and L_[0]==t['name']: L_=L_[1:]
        left.append(' '.join(L_))
        if R_:
            pos_=R_[0][1]; name=ph=em=None
            for x in [x for p,x in R_[1:]]:
                if '@' in x and not em: em=x
                elif re.fullmatch(PHR,x) and not ph: ph=x
                elif not name and re.search(r'[A-Za-z]',x) and not re.search(r'email|website|address|stated',x,re.I): name=x
            offs.append({'pos':pos_,'name':name,'phone':ph,'email':em})
    L=' '.join(left)
    L=re.sub(r'Information contained within.*?websites','',L)
    phs=re.findall(PHR,L); web=re.findall(r'(https?://\S+|www\.\S+)',L); ems=re.findall(r'[\w\.\-]+@[\w\.\-]+\.[a-z]{2,}',L)
    a=L
    for x in phs+web+ems: a=a.replace(x,' ')
    a=re.sub(r'Page \d+ of \d+|Town Info|Town Officials','',a)
    a=re.sub(r'\s+',' ',a).strip(' ,')
    m=re.search(r'^(.*?,\s*NH\s*\d{5}(?:-\d{4})?)',a); a=m.group(1) if m else ''
    return {'addr':a,'phone':phs[0] if phs else None,'web':web[0] if web else None,'email':ems[0] if ems else None},offs
def dom(u):
    h=(urlparse(u if '//' in u else 'http://'+u).hostname or '').lower(); return h[4:] if h.startswith('www.') else h
def role_of(pos,is_city):
    p=pos.strip(); P_=p.upper()
    if re.search(r'SELECT',P_):
        return ('Select Board Chair','gen_council') if re.search(r'CHAIR',P_) and not re.search(r'VICE',P_) else ('Select Board Vice Chair','gen_council') if re.search(r'VICE',P_) else ('Select Board Member','gen_council')
    if re.search(r'TOWN COUNCIL|COUNCILOR',P_) and not is_city: return ('Town Council Member'+(', '+re.sub(r'(?i).*?(ward|district)\s*','\\1 ',p).title() if re.search(r'WARD|DISTRICT',P_) else '')),'gen_council'
    if re.search(r'ADMINISTRATOR|MANAGER',P_) and not re.search(r'DIRECTOR|ASSISTANT|DEPUTY|FINANCE',P_):
        r_='City Manager' if is_city else ('Town Manager' if 'MANAGER' in P_ else 'Town Administrator')
        if re.search(r'CLERK',P_): r_+=' / Clerk'
        return r_,None
    if re.search(r'CLERK',P_) and not re.search(r'DEPUTY|ASSISTANT',P_): return ('City Clerk' if is_city else 'Town Clerk'),None
    return None,None
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nz(a[-1])==nz(b[-1]) and nz(a[0])[:1]==nz(b[0])[:1]
st={'towns':0,'no_place':[],'places_filled':0,'officials':0,'dropped_personal_email':0,'dropped_personal_phone':0}
res={'st':'NH','built':TODAY,'src':{'name':'NH Department of Transportation, City and Town Officials of the State of New Hampshire (September 2025; data current as of 9/1/2025)','note':'Select boards, town administrators/managers and clerks as reported by the municipalities; city managers and clerks. Office contacts only.'},'places':{}}
for t in towns:
    st['towns']+=1
    pids=PL.get(nz(t['name']),[])
    if len(pids)!=1: st['no_place'].append(t['name']); continue
    pid=pids[0]; p=P[pid]; is_city=p.get('t')=='city'
    info,offs=parse_town(t)
    good=set()
    for d in (dom(p.get('w','')),dom(info['web'] or '')):
        if d: good.add(d)
    base={}
    if info['phone']: base['p']=[info['phone']]
    if info['addr'] and not re.match(r'(?i)p\.?\s*o\.?\s*box',info['addr']) and not re.search(r'(?i)p\.?\s*o\.?\s*box',info['addr'].split(',')[0]) and re.search(r'\d',info['addr']): base['a']=re.sub(r',?\s*(?i:p\.?\s*o\.?\s*box)\s*\d*','',info['addr'])
    if info['web']: base['w']=info['web'] if info['web'].startswith('http') else 'https://'+info['web']
    if info['email'] and info['email'].split('@')[1].lower().removeprefix('www.') in good: base['e']=info['email']
    outl=[]
    for o_ in offs:
        if not o_['name'] or len(o_['name'].split())<2: continue
        role,rk=role_of(o_['pos'],is_city)
        if not role: continue
        ct=dict(base)
        if o_['email']:
            if o_['email'].split('@')[1].lower() in good: ct['e']=o_['email']
            else: st['dropped_personal_email']+=1
        if o_['phone'] and info['phone'] and re.sub(r'\D','',o_['phone'])[:10]==re.sub(r'\D','',info['phone'])[:10]: ct['p']=[o_['phone']]
        elif o_['phone']: st['dropped_personal_phone']+=1
        o={'n':re.sub(r'\s+',' ',o_['name']).strip(),'r':role,'src':'nhdot','u':U,'d':TODAY,'s':'as listed September 2025'}
        if rk: o['rk']=rk
        if ct: ct['src']=U; ct['g']=1; o['ct']=ct
        if any(sameperson(o['n'],x['n']) and o['r']==x['r'] for x in outl): continue
        outl.append(o)
    ex=[o for o in (p.get('o') or []) if o.get('src')!='nhdot']; LL=[]
    if any(x.get('rk')=='gen_council' for x in ex): outl=[o for o in outl if o.get('rk')!='gen_council']   # the town's own site is newer
    for o in outl:
        if any(sameperson(o['n'],x['n']) for x in ex+LL): continue
        LL.append(o)
    if not LL: continue
    res['places'][pid]={'n':p['n'],'o':ex+LL}; st['places_filled']+=1; st['officials']+=len(LL)
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:40])) for k,v in st.items()}))
