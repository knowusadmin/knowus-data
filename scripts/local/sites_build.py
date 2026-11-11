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
    import re,collections
    from urllib.parse import urlparse
    def nz(s): return re.sub(r'[^a-z0-9]','',(s or '').lower())
    def host(u): h=(urlparse(u).hostname or '').lower(); return h[4:] if h.startswith('www.') else h
    byh=collections.defaultdict(list)
    for pid,r in seen.items():
        if r.get('status')=='ok' and r.get('o'): byh[host(r.get('w') or r['o'][0]['u'])].append(pid)
    shared_drop=set()
    for h,pids in byh.items():
        if len(pids)>1:   # one site, several places: keep only the place the domain is named for (else none)
            lab=nz(h.split('.')[0] if h.count('.')>=2 and h.split('.')[-1] in ('gov','us') and len(h.split('.')[-2])<=5 else h.rsplit('.',1)[0])
            fits=sorted([p for p in pids if nz(seen[p]['n']) in lab],key=lambda p:-len(nz(seen[p]['n'])))
            keep=fits[0] if fits and (len(fits)==1 or len(nz(seen[fits[0]]['n']))>len(nz(seen[fits[1]]['n']))) else None
            shared_drop|={p for p in pids if p!=keep}

    SUFX=re.compile(r'^(jr|sr|ii|iii|iv|v|esq|phd|ph\.d|md|m\.d|cpa|ret)\.?$',re.I)
    def flip_name(nm):
        """'Last, First [Middle][, Jr.]' -> 'First [Middle] Last[ Jr.]'; 'First Last, Jr.' stays."""
        parts=[x.strip() for x in nm.split(',')]
        if len(parts)<2 or not parts[0] or not parts[1]: return nm
        if SUFX.match(parts[1].replace(' ','')): return nm
        suf=[x for x in parts[2:] if SUFX.match(x.replace(' ',''))]
        if len(parts)>2 and len(suf)!=len(parts)-2: return nm
        if len(parts[0].split())>2 or not re.match(r"^[A-Za-z][A-Za-z'\-. ]*$",parts[0]): return nm
        if not re.match(r"^[A-Za-z][A-Za-z'\-. \"()]*$",parts[1]): return nm
        return ' '.join([parts[1],parts[0]]+suf)
    
    n=0;o=0
    for pid,r in seen.items():
        if pid in shared_drop: continue
        if r.get('status')!='ok' or not r.get('o'): continue
        sp=site.get(pid)
        if not sp or sp.get('n')!=r['n']: continue
        if sp.get('o') and any(x.get('src')!='site' for x in sp['o']): continue   # filled since by another source
        for x in r['o']:
            fx=flip_name(x['n'])
            if fx!=x['n']: x['n']=fx; x['nf']=1
        e={'n':r['n'],'o':r['o']}
        if r.get('w'): e['w']=r['w']
        res['places'][pid]=e; n+=1; o+=len(r['o'])
    res['stats']={'crawled':len(seen),'places_filled':n,'officials':o}
    if n: json.dump(res,open(os.path.join(odir,st+'-sites.json'),'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    tot[st]=res['stats']
print(json.dumps(tot))
