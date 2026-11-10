
import sys,json,os,time,glob,traceback
sys.path.insert(0,'/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'); from photolib import *
from concurrent.futures import ThreadPoolExecutor
S='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/final/site'; STG='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'; os.makedirs(STG+'/contact_local',exist_ok=True)
def log(*a): print(time.strftime('%H:%M:%S'),*a,flush=True)
KW=re.compile(r'mayor|council|elected|officials|government|commission|selectm|alder|trustee|supervisor|board-of|leadership|meet-the|our-city|directory',re.I)
def page(u,cache):
    if u in cache: return cache[u]
    try:
        r=requests.get(u,headers=H,timeout=10,verify=False); v=(r.text,r.url) if r.status_code==200 and 'html' in r.headers.get('content-type','') else (None,'http %s'%r.status_code)
    except Exception as e: v=(None,'fetch '+type(e).__name__)
    cache[u]=v; return v
def subpages(html,base):
    soup=bs4.BeautifulSoup(html,'lxml'); out=[]
    for a in soup.find_all('a',href=True):
        u=urljoin(base,a['href']).split('#')[0]
        if urlparse(u).netloc!=urlparse(base).netloc or re.search(r'\.(pdf|jpe?g|png|docx?|xlsx?)$',u,re.I): continue
        if KW.search(a.get_text(' ',strip=True)) or KW.search(urlparse(u).path): out.append(u)
    return list(dict.fromkeys(out))[:6]
def do_entity(a):
    st,pk,ent,offs,prev=a; cache={}; res={}; con={}
    names=[o['n'] for o in offs]
    urls=list(dict.fromkeys([o.get('u') for o in offs if o.get('u')]+([ent.get('w')] if ent.get('w') else [])))
    pages=[]
    for u in urls:
        if BAN.search(u): continue
        h,b=page(u,cache)
        if h: pages.append((h,b))
    extra=[]
    need=any(not prev.get(pk+'-'+slug(o['n']),{}).get('f') for o in offs)
    for h,b in (pages[:2] if need else []):
        for su in subpages(h,b):
            if len(extra)>=3: break
            if su in cache: continue
            h2,b2=page(su,cache)
            if h2: extra.append((h2,b2))
    pages+=extra
    parsed=[(bs4.BeautifulSoup(h,'lxml'),b,candidates_on(h,b)) for h,b in pages]
    for o in offs:
        key=pk+'-'+slug(o['n']); pv=prev.get(key,{})
        # contact from the official's own source page first, then the others
        order=sorted(parsed,key=lambda x: 0 if x[1]==o.get('u') else 1)
        for soup,b,c in order:
            ct=contacts_for(soup,b,o['n'],names)
            if ct: con[key]=dict(ct,n=o['n']); break
        if pv.get('f'): continue
        got=None
        if pv.get('img') and str(pv.get('miss','')).startswith('faces'):
            p,info=make_photo(pv['img'],key,referer=pv.get('u'),out=STG+'/img/'+st)
            if p: got={'n':o['n'],'f':key+'.webp','src':pv.get('u') or o.get('u'),'img':pv['img'],'kb':round(info/1024,1),'why':'retry'}
        if not got:
            for soup,b,c in order:
                m=match(o['n'],c,names)
                if not m: continue
                p,info=make_photo(m[1],key,referer=b,out=STG+'/img/'+st)
                if p: got={'n':o['n'],'f':key+'.webp','src':b,'img':m[1],'kb':round(info/1024,1),'why':m[2][:100]}; break
        res[key]=got or {'n':o['n'],'miss':'no matching photo on %d official pages'%len(parsed),'pages':[x[1] for x in parsed][:8]}
    return res,con
for f in sorted(glob.glob(S+'/data/local/*.json'),key=lambda f:(not f.endswith('OH.json'),f)):
    st=os.path.basename(f)[:2]
    if os.path.exists(STG+'/res_local_'+st+'.json'): continue
    try:
        d=json.load(open(f)); prev=json.load(open(STG+'/local/'+st+'.json')) if os.path.exists(STG+'/local/'+st+'.json') else {}
        os.makedirs(STG+'/img/'+st,exist_ok=True)
        args=[(st,'c'+c['f'],c,[o for o in c.get('o',[]) if o.get('g')!='b'],prev) for c in d['counties'] if c.get('o')]
        args+=[(st,k,p,[o for o in p.get('o',[]) if o.get('g')!='b'],prev) for k,p in d['places'].items() if p.get('o')]
        R={};C={}
        with ThreadPoolExecutor(3) as ex:
            for i_,(r_,c_) in enumerate(ex.map(do_entity,args)):
                R.update(r_); C.update(c_)
                if i_%25==0: log(st,'progress',i_,len(args))
        json.dump(R,open(STG+'/res_local_'+st+'.json','w'),indent=0); json.dump(C,open(STG+'/contact_local/'+st+'.json','w'),indent=0)
        log(st,'entities',len(args),'new photos',sum(1 for v in R.values() if v.get('f')),'of',len(R),'contacts',len(C))
    except Exception: log(st,'ERR',traceback.format_exc()[-500:])
log('DONE')
