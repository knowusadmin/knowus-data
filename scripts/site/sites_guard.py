#!/usr/bin/env python3
"""KnowUS sites guard (publisher 774cbf5c, Nov 11 2026): after apply_local_officials.py, drop city-website officials
(data/officials-local/<ST>-sites.json) that a crawl put on the wrong place. Found live in v70: Rochester NY showed the Town
of Rochester (Ulster Co.) board, Kansas City KS showed Kansas City MO, Des Moines showed West Des Moines, Melbourne FL showed
West Melbourne, Spokane showed Spokane Valley, Hamilton Twp (Mercer NJ) showed Hamilton Twp (Atlantic).
Rules: (1) one source host used by several places -> only the place KEEP names (or whose name is the longest one inside
the host) keeps it; (2) a city whose source host is a 'townof'/'villageof'/'township' site -> dropped.
A dropped place gets back its state-directory officials when the state file has it, else no officials (empty beats wrong).
usage: sites_guard.py <site_dir> <officials_local_dir>"""
import json,sys,os,glob,re,collections
from urllib.parse import urlparse
site,src=sys.argv[1],sys.argv[2]
KEEP={'wdm.iowa.gov':('IA','p83910'),'kcmo.gov':('MO','p38000'),'hamiltonatlnj.gov':('NJ','t00129280'),'spokanevalleywa.gov':('WA','p67167'),'westmelbourne.gov':('FL','p76500')}
def host(u): h=urlparse(u or '').netloc.lower().split(':')[0]; return h[4:] if h.startswith('www.') else h
S={}
for f in glob.glob(os.path.join(src,'*-sites.json')):
    D=json.load(open(f)); 
    for pid,p in D.get('places',{}).items(): S[(D['st'],pid)]=p
byh=collections.defaultdict(set)
for k,p in S.items():
    for o in p.get('o',[]):
        h=host(o.get('u'))
        if h: byh[h].add(k)
drop={}
for h,ks in byh.items():
    if len(ks)<2: continue
    if h in KEEP and KEEP[h] in ks: keep={KEEP[h]}
    else:
        sl={k:re.sub(r'[^a-z]','',S[k]['n'].lower()) for k in ks}; inh=[k for k in ks if sl[k] and sl[k] in h.replace('.','').replace('-','')]
        keep={max(inh,key=lambda k:len(sl[k]))} if inh else set()
    for k in ks-keep: drop[k]='host %s belongs to another place'%h
loc={}
def L(st):
    if st not in loc:
        f=os.path.join(site,'data','local',st+'.json'); loc[st]=json.load(open(f)) if os.path.exists(f) else None
    return loc[st]
for k,p in S.items():
    st,pid=k; d=L(st); sp=d and d['places'].get(pid)
    if not sp: continue
    hs={host(o.get('u')) for o in p.get('o',[])}
    if sp.get('t')=='city' and 'town' not in sp.get('n','').lower() and any(re.search(r'townof|villageof|township',h) for h in hs): drop[k]='city sourced from a town/village site'

# (3) Nov 11 2026 (v73): a source host that names ANOTHER state -> dropped (v71 had Spring Hill TN from springhillks.gov).
# The host's first label, minus cityof/townof/villageof/www, is the place's own slug plus another state's postal code
# (springhill+ks), or ends in another state's full name (e.g. ...kansas.gov on a Missouri place).
STATES={'AL':'alabama','AK':'alaska','AZ':'arizona','AR':'arkansas','CA':'california','CO':'colorado','CT':'connecticut','DE':'delaware','DC':'districtofcolumbia','FL':'florida','GA':'georgia','HI':'hawaii','ID':'idaho','IL':'illinois','IN':'indiana','IA':'iowa','KS':'kansas','KY':'kentucky','LA':'louisiana','ME':'maine','MD':'maryland','MA':'massachusetts','MI':'michigan','MN':'minnesota','MS':'mississippi','MO':'missouri','MT':'montana','NE':'nebraska','NV':'nevada','NH':'newhampshire','NJ':'newjersey','NM':'newmexico','NY':'newyork','NC':'northcarolina','ND':'northdakota','OH':'ohio','OK':'oklahoma','OR':'oregon','PA':'pennsylvania','RI':'rhodeisland','SC':'southcarolina','SD':'southdakota','TN':'tennessee','TX':'texas','UT':'utah','VT':'vermont','VA':'virginia','WA':'washington','WV':'westvirginia','WI':'wisconsin','WY':'wyoming'}
def other_state(st,pname,h):
    lab=re.sub(r'^(www\d?\.)','',h).split('.')[0]; lab=re.sub(r'^(cityof|townof|villageof|townshipof|boroughof|ci|co)','',lab)
    slug=re.sub(r'[^a-z]','',(pname or '').lower())
    own=STATES.get(st,'')
    for code,name in STATES.items():
        if code==st: continue
        if slug and lab==slug+code.lower(): return code
        if lab.endswith(name) and not (own and own in lab) and name not in slug: return code
    return None
for k,p in S.items():
    st,pid=k
    for o in p.get('o',[]):
        h=host(o.get('u')); oc=h and other_state(st,p.get('n'),h)
        if oc: drop[k]='host %s names another state (%s)'%(h,oc); break

# (4) Wrong-place matches reported by the crawler (9a95f029) after a push, until its next batch removes them: (st, place id) -> host.
BLOCK={('NY','t07532688'):'hohny.gov',('MO','t20757548'):'bowlinggreen-mo.gov',('AR','p57260'):'pnpartnership.org',('NY','t05508246'):'townofbrighton.net',('NJ','p68460'):'downtownsomerville.org'}
for k,hb in BLOCK.items():
    if k in S and any(host(o.get('u'))==hb for o in S[k].get('o',[])): drop[k]='host %s reported as another place'%hb
out=[]
for (st,pid),why in sorted(drop.items()):
    d=L(st); sp=d and d['places'].get(pid)
    if not sp or sp.get('o')!=S[(st,pid)].get('o'): continue
    stf=os.path.join(src,st+'.json'); base=json.load(open(stf))['places'].get(pid) if os.path.exists(stf) else None
    if base and base.get('n')==sp.get('n'): sp['o']=base['o']
    else: sp.pop('o',None)
    hs={host(o.get('u')) for o in S[(st,pid)].get('o',[])}
    if sp.get('w') and host(sp['w']) in hs: sp.pop('w')
    out.append([st,pid,sp.get('n'),why])
for st,d in loc.items():
    if d is not None and any(x[0]==st for x in out): json.dump(d,open(os.path.join(site,'data','local',st+'.json'),'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({'dropped':out}))
