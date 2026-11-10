
import sys,json,os,time,glob,traceback
sys.path.insert(0,'/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'); from photolib import *
from concurrent.futures import ThreadPoolExecutor
S='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/final/site'; OUT='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'+'/local'; os.makedirs(OUT,exist_ok=True)
def log(*a): print(time.strftime('%H:%M:%S'),*a,flush=True)
sts=[os.path.basename(f)[:2] for f in sorted(glob.glob(S+'/data/local/*.json'))]
order=['OH']+[s for s in sts if s!='OH']
PAGE={}
def page(u):
    if u in PAGE: return PAGE[u]
    try:
        r=fetch(u,H,20)
        v=(r.text,r.url) if r.status_code==200 and 'html' in r.headers.get('content-type','') else (None,'http %s'%r.status_code)
    except Exception as e: v=(None,'fetch '+type(e).__name__)
    PAGE[u]=v; return v
def person_links(html,base,n):
    f,l=nameparts(n); out=[]
    soup=bs4.BeautifulSoup(html,'lxml')
    for a in soup.find_all('a',href=True):
        t=norm(a.get_text(' ',strip=True)+' '+a.get('title','')).split()
        if l and l in t and (not f or f in t or len(t)<=3):
            u=urljoin(base,a['href'])
            if u.startswith('http') and urlparse(u).netloc==urlparse(base).netloc and not re.search(r'\.(pdf|jpe?g|png|docx?)$|mailto:',u,re.I): out.append(u)
    return list(dict.fromkeys(out))[:2]
def do_group(args):
    st,u,items,allnames=args; res={}
    if not u or BAN.search(u):
        for key,o in items: res[key]={'n':o['n'],'miss':'no official page url'}
        return res
    html,base=page(u)
    if not html:
        for key,o in items: res[key]={'n':o['n'],'miss':'page '+base,'u':u}
        return res
    c=candidates_on(html,base)
    for key,o in items:
        m=match(o['n'],c,allnames); where=base
        if not m:
            for pu in person_links(html,base,o['n']):
                h2,b2=page(pu)
                if not h2: continue
                c2=candidates_on(h2,b2)
                # on a person's own page, require name on the page text too
                if nameparts(o['n'])[1] not in norm(bs4.BeautifulSoup(h2,'lxml').get_text(' ')).split(): continue
                m=match(o['n'],c2,allnames)
                if m: where=b2; break
        if not m: res[key]={'n':o['n'],'miss':'no matching photo on page','u':u}; continue
        p,info=make_photo(m[1],key,referer=where,out='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'+'/img/'+st)
        if not p: res[key]={'n':o['n'],'miss':info,'img':m[1],'u':where}; continue
        res[key]={'n':o['n'],'f':key+'.webp','src':where,'img':m[1],'why':m[2][:120],'kb':round(info/1024,1)}
    return res
for st in order:
    outf=OUT+'/'+st+'.json'
    if os.path.exists(outf): continue
    try:
        d=json.load(open(S+'/data/local/'+st+'.json')); os.makedirs('/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'+'/img/'+st,exist_ok=True)
        groups={}
        ents=[('c'+c['f'],c,c.get('o',[])) for c in d['counties']]+[(k,p,p.get('o',[])) for k,p in d['places'].items()]
        if st=='OH':  # Cuyahoga county + its places first
            cu=[e for e in ents if e[0]=='c39035' or '39035' in (e[1].get('c') or [])]; ents=cu+[e for e in ents if e not in cu]
        for pk,e,L in ents:
            names=[o['n'] for o in L]
            for o in L:
                if o.get('g')=='b': continue
                key=pk+'-'+slug(o['n'])
                groups.setdefault(o.get('u'),[]).append((key,o))
        allnames={}
        args=[(st,u,items,[o['n'] for _,o in items]) for u,items in groups.items()]
        res={}
        with ThreadPoolExecutor(2) as ex:
            for r_ in ex.map(do_group,args): res.update(r_)
        json.dump(res,open(outf,'w'),indent=0)
        log(st,'officials',len(res),'photos',sum(1 for v in res.values() if 'f' in v))
    except Exception: log(st,'ERR',traceback.format_exc()[-500:])
    PAGE.clear()
log('DONE')
