
import sys,json,os,time,glob,csv,io
sys.path.insert(0,'/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'); from photolib import *
from concurrent.futures import ThreadPoolExecutor
S='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/final/site'; STG='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'
DIRS={'OH':['https://ohiosenate.gov/members','https://ohiohouse.gov/members']}
def log(*a): print(time.strftime('%H:%M:%S'),*a,flush=True)
PAGE={}
def page(u):
    if u in PAGE: return PAGE[u]
    try:
        r=fetch(u,H,20); v=(r.text,r.url) if r.status_code==200 else (None,'http %s'%r.status_code)
    except Exception as e: v=(None,'fetch '+type(e).__name__)
    PAGE[u]=v; return v
sts=sys.argv[1:] or [os.path.basename(f)[:-5] for f in sorted(glob.glob(STG+'/leg/*.json'))]
for st in sts:
    outf=STG+'/res_leg_'+st+'.json'
    if os.path.exists(outf) and len(sys.argv)<2: continue
    L=json.load(open(STG+'/leg/'+st+'.json')); d=json.load(open(S+'/data/local/'+st+'.json'))
    urls={}
    for ch,dd in (d.get('leg') or {}).items():
        for dist,mm in dd.items():
            for m in mm: urls[ch+dist+'-'+slug(m['n'])]=m.get('u')
    dirc=[]
    for du in DIRS.get(st,[]):
        h,b=page(du)
        if h: dirc.append((b,candidates_on(h,b)))
    allnames=[v['n'] for v in L.values()]
    def one(kv):
        k,v=kv
        if v.get('f'): return None
        n=v['n']; u=urls.get(k); tried=[]
        cands=[]
        if u and not BAN.search(u):
            h,b=page(u); tried.append(u)
            if h: cands.append((b,candidates_on(h,b)))
        for b,c in cands+dirc:
            m=match(n,c,allnames)
            if m:
                p,info=make_photo(m[1],k,referer=b,out=STG+'/img/'+st)
                if p: return k,{'n':n,'f':k+'.webp','src':b,'img':m[1],'kb':round(info/1024,1)}
                tried.append('rejected '+str(info))
        return k,{'n':n,'miss':'no matching photo on member page','tried':tried}
    res={}
    with ThreadPoolExecutor(2) as ex:
        for r_ in ex.map(one,L.items()):
            if r_: res[r_[0]]=r_[1]
    json.dump(res,open(outf,'w'),indent=0); log(st,'misses',len(res),'filled',sum(1 for v in res.values() if v.get('f')))
    PAGE.clear()
log('DONE')
