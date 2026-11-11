#!/usr/bin/env python3
"""Add the official city/town website hosts the site crawl verified (data/officials-local/*-sites.json: each place's 'w'
and every official's 'u' host) to data/sources-policy.json local_gov_sites, when the policy does not already allow them.
A host is added only when it is the verified home site of a municipality (its homepage names the place; see site_crawl.py)
and is not on any banned/news list. usage: sites_policy.py <repo>"""
import json,sys,os,glob,re,collections
R=sys.argv[1]; PF=os.path.join(R,'data','sources-policy.json')
os.environ['KNOWUS_SOURCES_POLICY']=PF
sys.path.insert(0,os.path.join(R,'scripts')); from sources_policy import classify,dom
P=json.load(open(PF,encoding='utf-8'))
banned=set(P.get('news_banned',[]))|set(P.get('removed_references',{}).get('hosts',[]))|set(k for k,v in P.get('pending',{}).items() if v=='ban')
add=collections.OrderedDict()
for f in sorted(glob.glob(os.path.join(R,'data','officials-local','*-sites.json'))):
    D=json.load(open(f,encoding='utf-8'))
    for pid,p in D['places'].items():
        hs={dom(p['w'])} if p.get('w') else set()
        hs|={dom(o['u']) for o in p['o'] if o.get('u')}
        for h in hs:
            if not h or h in banned or any(h.endswith('.'+b) for b in banned): continue
            st,_=classify('https://'+h+'/',[])
            if st=='banned': add.setdefault(h,D['st']+' '+p['n'])
lg=set(P['local_gov_sites']); new=[h for h in add if h not in lg]
if new:
    P['local_gov_sites']=sorted(lg|set(new))
    P['_added_2026_11_11_localfill_sites']=("Added Nov 11 2026 (local officials from each municipality's own website, data/officials-local/*-sites.json, built by scripts/local/site_crawl.py): local_gov_sites + the official websites of cities and towns whose homepage names the place and from which the officials were read. Hosts so far: %d, e.g. %s." % (len(set(P.get('_localfill_hosts',[]))|set(new)), ', '.join('%s (%s)'%(h,add[h]) for h in new[:5])))
    P['_localfill_hosts']=sorted(set(P.get('_localfill_hosts',[]))|set(new))
    json.dump(P,open(PF,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    open(PF,'a').write('\n') if not open(PF).read().endswith('\n') else None
print(json.dumps({'new_hosts':len(new),'sample':new[:10]}))
