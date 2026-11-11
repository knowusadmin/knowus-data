#!/usr/bin/env python3
"""Build data/officials-local/<ST>-sites.json from site_crawl.py results (<crawl dir>/<ST>.jsonl).
Only places the crawl marked ok; each official carries the official-site page it was read from (u).
No 'src.name' is set, so the state's officials_state line (from a statewide source file, when one exists) is untouched.
usage: sites_build.py <crawl dir> <site data/local dir> <out dir>"""
import json,sys,os,glob,datetime as dt
cdir,sdir,odir=sys.argv[1:4]; TODAY=dt.date.today().isoformat(); tot={}
for f in sorted(glob.glob(os.path.join(cdir,'*.jsonl'))):
    st=os.path.basename(f)[:-6]
    site=json.load(open(os.path.join(sdir,st+'.json'),encoding='utf-8'))['places']
    res={'st':st,'built':TODAY,'src':{'note':"Officials as listed on each city's or town's own official website; each official links the page they appear on."},'places':{}}
    seen={}
    for l in open(f,encoding='utf-8'):
        try: r=json.loads(l)
        except Exception: continue
        seen[r['pid']]=r
    n=0;o=0
    for pid,r in seen.items():
        if r.get('status')!='ok' or not r.get('o'): continue
        sp=site.get(pid)
        if not sp or sp.get('n')!=r['n'] or sp.get('o'): continue
        e={'n':r['n'],'o':r['o']}
        if r.get('w'): e['w']=r['w']
        res['places'][pid]=e; n+=1; o+=len(r['o'])
    res['stats']={'crawled':len(seen),'places_filled':n,'officials':o}
    if n: json.dump(res,open(os.path.join(odir,st+'-sites.json'),'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    tot[st]=res['stats']
print(json.dumps(tot))
