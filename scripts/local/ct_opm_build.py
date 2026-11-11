#!/usr/bin/env python3
"""KnowUS local officials, Connecticut: the chief executive of each of the 169 towns and cities (mayor, first selectman /
selectwoman / selectperson, town council chair where the council chair is the CEO) and the appointed town / city manager or
administrator, from the CT Office of Policy and Management's "Chief Executive Officer List" (OPM-IGPP municipal directory,
portal.ct.gov/opm/-/media/opm/igpp/municipal-directories/chief-executive-officer-listing.pdf, dated 10/7/2026).
Contact: the office phone listed beside the official, and the email listed there unless it is a free-mail / ISP address.
Boroughs and the City of Groton (separate list section) are skipped unless the site has a place of that name.
Towns missing from the site file are carried with an "add" block (geography from ct_towns_base.json) that
apply_local_officials.py inserts.
usage: ct_opm_build.py <ct.txt (pdftotext -layout)> <site data/local/CT.json> <out.json>"""
import json,re,sys,os,datetime as dt
src,sitef,out=sys.argv[1:4]
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
U='https://portal.ct.gov/opm/-/media/opm/igpp/municipal-directories/chief-executive-officer-listing.pdf'
def nz(s): return re.sub(r'[^a-z]','',s.lower())
site=json.load(open(sitef,encoding='utf-8')); P=dict(site['places'])
BASE=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'ct_towns_base.json'),encoding='utf-8'))['places']
ADD={k:v for k,v in BASE.items() if k not in P}
P.update(ADD)
PL={}
for pid,p in P.items():
    if p.get('t')!='CDP': PL.setdefault(nz(p['n']),[]).append(pid)
FREE=re.compile(r'@(gmail|yahoo|aol|hotmail|outlook|msn|live|icloud|me|comcast|sbcglobal|snet|att|cox|verizon|charter|optonline|frontier|earthlink|juno|protonmail)\.',re.I)
PHR=re.compile(r'^\(?\d{3}\)?[-\. ]*\d{3}-\d{4}')
def role(t):
    T=t.upper()
    if re.search(r'ASSISTANT|DEPUTY|CHIEF OF STAFF|EXECUTIVE ASSISTANT|SECRETARY|DIRECTOR|CHIEF ADMINISTRATIVE',T): return None
    if re.match(r'^(ACTING )?MAYOR$',T): return ('Mayor' if 'ACTING' not in T else 'Acting Mayor','gen_mayor')
    if re.search(r'FIRST SELECT',T): return (t.strip().title().replace('Firstselect','First Select'),'gen_mayor')
    if re.search(r'(TOWN|CITY|BOROUGH) (MANAGER|ADMINISTRATOR)',T): return (t.strip().title(),None)
    if re.search(r'CHAIR.*(COUNCIL|SELECTMEN|SELECT BOARD|BOARD OF SELECT)|^CHAIRPERSON$|^CHAIRMAN$|^CHAIR$',T): return (t.strip().title().replace(' Of ',' of ').replace(' The ',' the '),'gen_council')
    if re.match(r'^(ACTING )?WARDEN$|^PRESIDENT$',T): return (t.strip().title(),None)
    return None
st={'rows':0,'kept':0,'no_place':[],'skipped_titles':[],'free_email_dropped':0,'places_filled':0,'officials':0}
res={'st':'CT','built':TODAY,'src':{'name':'Connecticut Office of Policy and Management, Chief Executive Officer List (OPM-IGPP municipal directory, 10/7/2026)','note':"Each town's or city's chief executive (mayor or first selectman) and its town manager or administrator, with the office phone and email the state lists."},'places':{}}
section='town'
for line in open(src,encoding='utf-8',errors='replace').read().split('\n'):
    if re.match(r'^\s*BOROUGH\s{2,}NAME',line): section='borough'; continue
    c=[x.strip() for x in re.split(r'\s{2,}',line.strip())]
    if len(c)<3 or c[0] in ('MUNICIPALITY','BOROUGH') or line.startswith('OPM-IGPP') or 'Chief Executive Officer List' in line: continue
    muni,name,title=c[0],c[1],c[2]; rest=c[3:]
    if not re.search(r'[a-z]',name) or len(name.split())<2: continue
    st['rows']+=1
    ph=next((x for x in rest if PHR.match(x)),None); em=next((x for x in rest if '@' in x),None)
    r=role(title)
    if not r: st['skipped_titles'].append(title); continue
    mn=re.sub(r'\s+Borough$','',muni) if section=='borough' else muni
    if section=='borough': mn=re.sub(r'^City of ','',mn)
    pids=PL.get(nz(mn),[])
    if len(pids)>1:   # a town and a borough/city of the same name: the town list names the town, the borough list the borough or city
        want=('borough','city') if section=='borough' else ('town',)
        pids=[x for x in pids if P[x].get('t') in want] or pids
    if section=='borough' and not pids: continue
    if len(pids)!=1: st['no_place'].append(muni); continue
    pid=pids[0]
    o={'n':re.sub(r'\s+',' ',name),'r':r[0],'src':'ctopm','u':U,'d':TODAY}
    if r[1]: o['rk']=r[1]
    ct={}
    if ph: ct['p']=[re.sub(r'\)-',') ',re.sub(r'^\((\d{3})\)(\d)',r'(\1) \2',ph))]
    if em:
        if FREE.search(em): st['free_email_dropped']+=1
        else: ct['e']=em
    w=P[pid].get('w') or (P[pid].get('ct') or {}).get('w')
    if ct:
        ct['src']=U; ct['g']=1; o['ct']=ct
    pl=res['places'].setdefault(pid,{'n':P[pid]['n'],'o':[]})
    if not any(nz(x['n'])==nz(o['n']) and x['r']==o['r'] for x in pl['o']): pl['o'].append(o); st['kept']+=1
def sameperson(a,b):
    a,b=[[w for w in x.replace(',',' ').split() if not re.match(r'(?i)^(jr|sr|ii|iii|iv)\.?$',w)] for x in (a,b)]; return bool(a and b) and nz(a[-1])==nz(b[-1]) and nz(a[0])[:1]==nz(b[0])[:1]
for pid,pl in list(res['places'].items()):
    ex=[o for o in (P[pid].get('o') or []) if o.get('src')!='ctopm']
    ours=pl['o']
    if any(o.get('rk')=='gen_mayor' for o in ours):
        ex=[o for o in ex if o.get('rk')!='gen_mayor' or any(sameperson(o['n'],x['n']) for x in ours)]
    LL=[o for o in ours if not any(sameperson(o['n'],x['n']) for x in ex)]
    if not LL: del res['places'][pid]; continue
    pl['o']=ex+LL; st['places_filled']+=1; st['officials']+=len(LL)
    if pid in ADD: pl['add']=ADD[pid]; st['towns_added']=st.get('towns_added',0)+1
st['skipped_titles']=sorted(set(st['skipped_titles']))
res['stats']=st
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps(st))
