#!/usr/bin/env python3
"""KnowUS stale-sites sweep (publisher 774cbf5c, Nov 11 2026). apply_local_officials.py only adds/replaces, so a place the
city-website crawl later REMOVED from data/officials-local/<ST>-sites.json (wrong site: Spring Hill TN showed Spring Hill KS's
officials in v71) kept that crawl's officials in a cumulative build. A place is swept only when it is absent from every current
<ST>-sites.json AND its officials list equals, exactly, a list some earlier commit of that <ST>-sites.json gave it (git history),
so officials from any other source are never touched. A swept place gets back the pre-crawl build's list (base_site_dir, the
v38 build) or none. Idempotent. Runs right after apply_local_officials.py.
usage: sites_stale.py <site_dir> <officials_local_dir> [base_site_dir]"""
import json,sys,os,glob,subprocess,collections
site,src=sys.argv[1],sys.argv[2]; base=sys.argv[3] if len(sys.argv)>3 else None
repo=subprocess.run(['git','-C',src,'rev-parse','--show-toplevel'],capture_output=True,text=True,timeout=30).stdout.strip()
rel=os.path.relpath(os.path.abspath(src),repo)
cur={}
for f in glob.glob(os.path.join(src,'*-sites.json')):
    D=json.load(open(f,encoding='utf-8')); cur.setdefault(D['st'],set()).update(D.get('places',{}).keys())
hist=collections.defaultdict(set)
cms=subprocess.run(['git','-C',repo,'log','--format=%h','--',rel+'/*-sites.json'],capture_output=True,text=True,timeout=60).stdout.split()
for cm in cms:
    for fn in subprocess.run(['git','-C',repo,'ls-tree','--name-only',cm,rel+'/'],capture_output=True,text=True,timeout=60).stdout.split():
        if not fn.endswith('-sites.json'): continue
        t=subprocess.run(['git','-C',repo,'show',cm+':'+fn],capture_output=True,text=True,timeout=60).stdout
        try: D=json.loads(t)
        except Exception: continue
        for pid,p in D.get('places',{}).items(): hist[(D['st'],pid)].add(json.dumps(p.get('o'),sort_keys=True))
# HOLD: places the crawl dropped by mistake whose last crawl officials were checked correct by the publisher; kept until the crawl re-adds them.
HOLD={}
out=[]
for lf in sorted(glob.glob(os.path.join(site,'data','local','*.json'))):
    st=os.path.basename(lf)[:-5]
    if len(st)!=2: continue
    d=json.load(open(lf,encoding='utf-8')); ch=0; bd=None
    for pid,p in d.get('places',{}).items():
        if pid in cur.get(st,()) or not p.get('o') or (st,pid) in HOLD: continue
        if json.dumps(p['o'],sort_keys=True) not in hist.get((st,pid),()): continue
        if bd is None:
            bf=base and os.path.join(base,'data','local',st+'.json'); bd=json.load(open(bf,encoding='utf-8')) if bf and os.path.exists(bf) else {}
        p['o']=(bd.get('places',{}).get(pid) or {}).get('o') or []; ch+=1; out.append([st,pid,p.get('n'),len(p['o'])])
    if ch: json.dump(d,open(lf,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({'stale_swept':out,'history_commits':len(cms)}))
