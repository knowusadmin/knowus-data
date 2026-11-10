
import re,os,io,json,time,urllib3
urllib3.disable_warnings()
import re,unicodedata,requests,bs4,cv2,numpy as np
from urllib.parse import urljoin,urlparse
from PIL import Image
STG='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36','Accept-Language':'en-US,en;q=0.9'}
import threading
_TL=threading.local()
def _fc():
    if not hasattr(_TL,'fc'): _TL.fc=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    return _TL.fc
BAN=re.compile(r'wiki(pedia|media|data)|apnews|reuters|\bap\.org',re.I)
def _get(url,h,t,verify):
    r=requests.get(url,headers=h,timeout=min(t,15),verify=verify,stream=True); buf=[]; t0=time.time(); n=0
    for ch in r.iter_content(65536):
        buf.append(ch); n+=len(ch)
        if time.time()-t0>t+10 or n>15_000_000: r.close(); raise requests.exceptions.Timeout('deadline')
    r._content=b''.join(buf); r._content_consumed=True; return r
def fetch(url,h=None,t=20):
    h=h or H
    for i in range(3):
        try: r=_get(url,h,t,True)
        except requests.exceptions.SSLError: r=_get(url,h,t,False)
        if r.status_code in (429,502,503,504) and i<2: time.sleep(3*(i+1)); continue
        return r
    return r
def norm(s): return re.sub(r'[^a-z ]','',unicodedata.normalize('NFD',s or '').encode('ascii','ignore').decode().lower().replace('-',' ').replace('_',' '))
SUFF={'jr','sr','ii','iii','iv','dr','hon','mr','mrs','ms'}
def nameparts(n):
    n=re.sub(r'\(.*?\)|".*?"','',n or '')
    w=[x for x in norm(n).split() if x not in SUFF and len(x)>1]
    return (w[0] if w else ''), (w[-1] if w else '')
def imgurl(im,base):
    for a in ['data-lazy-src','data-src','data-original','data-orig-file','data-srcset','data-lazy-srcset','srcset','src']:
        v=im.get(a)
        if v and not v.strip().startswith('data:'):
            v=v.split(',')[0].strip().split(' ')[0] if 'srcset' in a else v.strip()
            if v: return urljoin(base,v)
    return None
BADIMG=re.compile(r'logo|seal|icon|banner|flag|sprite|placeholder|default|avatar|blank|spacer|facebook|twitter|instagram|youtube|button|arrow|header|footer|background',re.I)
def candidates_on(html,base):
    soup=bs4.BeautifulSoup(html,'lxml'); out=[]
    for im in soup.find_all('img'):
        u=imgurl(im,base)
        if not u or not u.startswith('http'): continue
        fn=urlparse(u).path.rsplit('/',1)[-1].lower()
        if fn.endswith('.svg') or fn.endswith('.gif'): continue
        ctx=(im.get('alt','') or im.get('title',''))+'\x00'+urlparse(u).path.rsplit('/',1)[-1]
        p=im; near=''
        for _ in range(4):
            p=p.parent
            if p is None: break
            t=p.get_text(' ',strip=True)
            if len(t)<260: near=t
            else: break
        out.append((u,ctx,near))
    title=(soup.title.get_text(' ',strip=True) if soup.title else '')
    for mt in soup.find_all('meta',attrs={'property':'og:image'})+soup.find_all('meta',attrs={'name':'twitter:image'}):
        u=mt.get('content')
        if u and u.startswith('http'): out.append((u,'',title))
    for el in soup.find_all(style=re.compile(r'background(-image)?\s*:.*url\(',re.I)):
        mm=re.search(r'url\([\'"]?([^\'")]+)',el['style'])
        if mm:
            u=urljoin(base,mm.group(1)); p=el; near=el.get_text(' ',strip=True)
            for _ in range(5):
                p=p.parent
                if p is None: break
                t=p.get_text(' ',strip=True)
                if len(t)<200: near=t
                else: break
            out.append((u,el.get('aria-label','') or el.get('title',''),near))
    return out
def score(n,ctx,near,u=''):
    f,l=nameparts(n)
    if not l: return 0
    path=urlparse(u).path.lower() if u else ''
    fn=norm(re.sub(r'([a-z])([A-Z])',r'\1 \2',path.rsplit('/',1)[-1].rsplit('.',1)[0])).split()
    alt=norm(ctx.split('\x00')[0]).split()
    nr=norm(near).split(); sc=0
    if l in fn or (len(l)>=5 and l in ''.join(fn)): sc+=3
    elif l in alt and len(alt)<=7: sc+=2
    elif l in alt: sc+=0.5
    if f and (f in fn or (f in alt and len(alt)<=7)): sc+=0.5
    if l in nr and f and f in nr and len(nr)<=10: sc+=2
    elif l in nr and len(nr)<=25: sc+=1
    if re.search(r'headshot|portrait|official|people|staff|council|/bio|member|mayor|elected|commission|director',path): sc+=1
    if re.search(r'press|release|news|event|cover|graphic|slide|banner|flyer|story|blog|post|award|ribbon|meeting|group|team|calendar',path) or len(alt)>12: sc-=3
    return sc
def match(n,cands,others=()):
    best=None
    for u,ctx,near in cands:
        sc=score(n,ctx,near,u)
        if sc<3: continue
        if BADIMG.search(urlparse(u).path.rsplit('/',1)[-1]): continue
        if any(score(m,ctx,near,u)>=sc for m in others if m!=n and nameparts(m)[1]!=nameparts(n)[1]): continue
        if best is None or sc>best[0]: best=(sc,u,ctx,near)
    return best
def flat(im):
    if im.mode in ('RGBA','LA','P'):
        im=im.convert('RGBA'); bg=Image.new('RGB',im.size,(255,255,255)); bg.paste(im,mask=im.split()[3]); return bg
    return im.convert('RGB')
def faces(im):
    g=cv2.cvtColor(np.array(im),cv2.COLOR_RGB2GRAY)
    m=max(24,min(im.size)//10)
    return _fc().detectMultiScale(g,1.1,5,minSize=(m,m))
def make_photo(url,key,referer=None,need_face=True,max_faces=1,out=None):
    if BAN.search(url): return None,'banned host'
    h=dict(H)
    if referer: h['Referer']=referer
    try: r=fetch(url,h,25)
    except Exception as e: return None,'fetch '+type(e).__name__
    if r.status_code!=200 or len(r.content)<1500: return None,'http %s len %d'%(r.status_code,len(r.content))
    try: im=Image.open(io.BytesIO(r.content)); im.load(); im=flat(im)
    except Exception: return None,'decode'
    if im.width<70 or im.height<70: return None,'tiny'
    fs=faces(im)
    if need_face and len(fs)==0: return None,'noface'
    if len(fs)>max_faces:
        big=sorted(fs,key=lambda f:-f[2]*f[3]); X,Y,Wf,Hf=big[0]; others=0
        for x,y,w,h_ in big[1:]:
            if w*h_ < 0.45*Wf*Hf: continue
            if x < X+Wf and x+w > X: continue          # overlaps horizontally: duplicate / body false positive
            if abs((y+h_/2)-(Y+Hf/2)) > Hf: continue   # not at head height
            others+=1
        if others+1>max_faces: return None,'faces=%d'%(others+1)
    W_,H_=im.size
    if len(fs):
        x,y,w,hh=max(fs,key=lambda f:f[2]*f[3]); cx,cy=x+w/2,y+hh/2
        side=int(min(W_,H_,max(w*2.4,w))); l=int(min(max(cx-side/2,0),W_-side)); t=int(min(max(cy-side*0.45,0),H_-side))
    else:
        side=min(W_,H_); l=(W_-side)//2; t=0 if H_>W_ else (H_-side)//2
    im=im.crop((l,t,l+side,t+side)).resize((200,200),Image.LANCZOS)
    p=(out or STG+'/img')+'/'+key+'.webp'; im.save(p,'WEBP',quality=70,method=6)
    return p,os.path.getsize(p)
def slug(s): return re.sub(r'[^a-z0-9]+','-',norm(s)).strip('-')[:40]

FREEMAIL=re.compile(r'@(gmail|yahoo|hotmail|aol|outlook|icloud|me|mac|comcast|att|sbcglobal|verizon|msn|live|protonmail|ymail|charter|cox|earthlink|bellsouth|frontier|windstream|juno|gmx|mail)\.',re.I)
PHRE=re.compile(r'(?<!\d)\(?([2-9]\d{2})\)?[\s.\-]{0,2}(\d{3})[\s.\-](\d{4})(?:[,.]?\s*(?:x|ext\.?|extension)\s*(\d{1,5}))?(?!\d)',re.I)
def cfdecode(h):
    try:
        k=int(h[:2],16); return ''.join(chr(int(h[i:i+2],16)^k) for i in range(2,len(h),2))
    except Exception: return ''
def emails_in(el):
    out=[]
    for a in el.find_all('a',href=True):
        hr=a['href']
        if hr.lower().startswith('mailto:'): out.append(hr[7:].split('?')[0].strip())
        elif '/cdn-cgi/l/email-protection#' in hr: out.append(cfdecode(hr.split('#',1)[1]))
    for s in el.select('[data-cfemail]'): out.append(cfdecode(s['data-cfemail']))
    return [e for e in dict.fromkeys(out) if re.match(r'^[^@\s]+@[^@\s]+\.[a-z]{2,}$',e,re.I)]
def contacts_for(soup, base, n, others=()):
    f,l=nameparts(n)
    if not l: return None
    ol={nameparts(m)[1] for m in others if nameparts(m)[1]!=l}
    seen=set()
    for s in soup.find_all(string=True):
        t=norm(str(s)).split()
        if l not in t or (f and f not in t and len(t)>3): continue
        el=s.parent
        for depth in range(7):
            if el is None or id(el) in seen: break
            seen.add(id(el))
            txt=el.get_text(' ',strip=True)
            if len(txt)>900: break
            tw=set(norm(txt).split())
            if tw & ol: break
            em=[e for e in emails_in(el) if not FREEMAIL.search(e)]
            tel=[a['href'][4:].strip() for a in el.find_all('a',href=True) if a['href'].lower().startswith('tel:')]
            ph=[]
            for mm in PHRE.finditer(txt):
                pre=txt[max(0,mm.start()-25):mm.start()].lower()
                if re.search(r'cell|mobile|home|personal|fax|after hours',pre) or re.search(r'(^|\s)(f|c|m|h)\s*[:.]\s*$',pre): continue
                ph.append('(%s) %s-%s'%mm.groups()[:3]+(' ext. '+mm.group(4) if mm.group(4) else ''))
            if not ph and tel:
                for t_ in tel:
                    d=re.sub(r'\D','',t_)[-10:]
                    if len(d)==10: ph.append('(%s) %s-%s'%(d[:3],d[3:6],d[6:]))
            if em or ph:
                return {'e':em[0] if em else '','p':list(dict.fromkeys(ph))[:2],'src':base}
            el=el.parent
    return None
