#!/usr/bin/env python3
"""KnowUS local officials, Louisiana: every municipal elected official (mayor, aldermen / council members, elected
chief of police and marshal) from the Louisiana Secretary of State's Elected Officials database (voterportal.sos.la.gov/
ElectedOfficials, "Export to CSV" by parish). It is the state's current list of all elected officials, with party and term
expiration. Plus the consolidated governments: Baton Rouge (Mayor-President and Metro Council), Lafayette
(Mayor-President) and New Orleans (Orleans Parish = city; its Council). Names as listed (quoted nicknames kept).
No contact data: the database's address and phone are often the official's own.
usage: la_sos_build.py <dir with <parishId>.csv> <site data/local/LA.json> <out.json>"""
import json,re,sys,os,glob,csv,io,collections,datetime as dt
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
def U(pid): return 'https://voterportal.sos.la.gov/ElectedOfficials?parishId=%s'%pid
site=json.load(open(sitef,encoding='utf-8')); P=site['places']
def nz(s): return re.sub(r'[^a-z]','',s.lower().replace('saint ','st').replace('st. ','st').replace('ste. ','ste'))
PL={}
for pid,p in P.items():
    if p.get('t')!='CDP': PL.setdefault(nz(p['n']),[]).append(pid)
def one(n): c=PL.get(nz(n),[]); return c[0] if len(c)==1 else None
def name_of(r):
    f=r['FirstName'].strip(); l=r['LastName'].strip(); s=r['Suffix'].strip()
    if re.fullmatch(r"'[^']+'",f): f=f.strip("'")
    f=re.sub(r"'([^']+)'",r'"\1"',f)
    n=' '.join(x for x in (f,l) if x)
    if s: n+=(' '+s) if not re.match(r'^(Jr|Sr)\.?$',s) else ', '+s if False else ' '+s
    return re.sub(r'\s+',' ',n).strip()
def role_of(title,desc):
    t=title.strip(); T=t.upper(); seat=''
    m=re.search(r'(District|Division|Ward)\s+([0-9A-Z]{1,3})\b',desc)
    if m: seat='%s %s'%(m.group(1),m.group(2))
    al=bool(re.search(r'AT LARGE',T))
    if T=='MAYOR': return 'Mayor','gen_mayor'
    if T=='MAYOR-PRESIDENT': return 'Mayor-President','gen_mayor'
    if re.match(r'ALDERM[AE]N',T): base='Alderman'
    elif re.search(r'COUNCIL',T): base='Council Member'
    elif re.search(r'SELECTMAN',T): base='Selectman'
    elif re.search(r'BOARD OF TRUSTEES',T): base='Trustee'
    elif T=='CHIEF OF POLICE': return 'Chief of Police',None
    elif T in ('MARSHAL','CITY MARSHAL'): return 'Marshal',None
    else: return None,None
    m2=re.search(r'COUNCIL MEMBER (I{1,3}|IV)$',T)
    if m2: seat='Seat %s'%m2.group(1)
    r=base+(', '+seat if seat else '')+(', At-Large' if al and not seat else '')
    if al and seat: r=base+', At-Large '+seat
    return r,'gen_council'
st={'rows':0,'muni_rows':0,'no_place':collections.Counter(),'expired':0,'places_filled':0,'officials':0}
by=collections.defaultdict(dict)
BR=one('Baton Rouge'); LF=one('Lafayette'); NO=one('New Orleans')
for f in sorted(glob.glob(os.path.join(src,'*.csv')),key=lambda x:int(os.path.basename(x)[:-4])):
    par=os.path.basename(f)[:-4]
    for r in csv.DictReader(io.StringIO(open(f,encoding='utf-8',errors='replace').read())):
        r={(k or '').strip():(v or '').strip() for k,v in r.items()}
        st['rows']+=1
        title=r.get('OfficeTitle',''); desc=r.get('OfficeTitleDescription','')
        m=re.search(r'\b(City|Town|Village) of\s*(.+)$',desc)
        pid=None
        if m: pid=one(m.group(2).strip())
        if not m:
            if par=='18' and re.search(r'^Metro District',desc) and re.search(r'Councilmember',title): pid=BR
            elif par=='29' and title=='Mayor-President': pid=LF
            elif par=='37' and re.search(r'Councilmember',title): pid=NO
            else: continue
        if title=='Mayor-President' and par=='18': pid=BR
        role,rk=role_of(title,desc)
        if not role: continue
        st['muni_rows']+=1
        if not pid: st['no_place'][desc]+=1; continue
        ex=r.get('ExpDate','')
        try: exd=dt.datetime.strptime(ex,'%m/%d/%Y').date()
        except Exception: exd=None
        if exd and exd.isoformat()<TODAY: st['expired']+=1; continue
        n=name_of(r)
        if len(n.split())<2: continue
        o={'n':n,'r':role,'src':'lasos','u':U(par),'d':TODAY}
        if rk: o['rk']=rk
        pty=r.get('Party','')
        if pty: o['p']=pty
        if exd: o['s']='term ends '+exd.strftime('%B %-d, %Y')
        by[pid].setdefault((role,n),o)
def sameperson(a,b):
    a,b=a.split(),b.split(); return bool(a and b) and nz(a[-1])==nz(b[-1]) and nz(a[0])[:1]==nz(b[0])[:1]
ORD={'gen_mayor':0,'gen_council':1,None:2}
res={'st':'LA','built':TODAY,'src':{'name':'Louisiana Secretary of State, Elected Officials database (voterportal.sos.la.gov/ElectedOfficials)','note':"The state's current list of elected municipal officials, with party and term expiration. Names as listed."},'places':{}}
def skey(o):
    m=re.search(r'(\d+)$',o['r']); return (ORD[o.get('rk')],re.sub(r'\d+$','',o['r']),int(m.group(1)) if m else 0,o['r'],o['n'])
for pid,D in by.items():
    p=P[pid]; outl=sorted(D.values(),key=skey)
    ex=[o for o in (p.get('o') or []) if o.get('src')!='lasos']; LL=[]
    hasm=any(o.get('rk')=='gen_mayor' for o in outl)
    if hasm: ex=[o for o in ex if o.get('rk')!='gen_mayor' or any(sameperson(o['n'],x['n']) for x in outl)]
    for o in outl:
        if any(sameperson(o['n'],x['n']) for x in ex+LL): continue
        LL.append(o)
    if not LL: continue
    res['places'][pid]={'n':p['n'],'o':ex+LL}; st['places_filled']+=1; st['officials']+=len(LL)
st['no_place']=dict(st['no_place'])
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps(st)[:3000])
