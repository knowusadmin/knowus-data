#!/usr/bin/env python3
"""KnowUS local officials from each city's / town's OWN official website (states with no statewide official list).
For each municipality (largest first) with no officials yet: find its official website (the site file's 'w', else a web
search, accepted only when the homepage itself names the place), read the homepage and up to 4 council/mayor/elected-
officials pages on that site, and have a model list the officials those pages name. Every name is kept only if it appears
word for word on the page it is credited to (u = that page). Email kept only when printed on that page and on the
municipality's own domain. Results: one JSON line per place in <outdir>/<ST>.jsonl (resumable).
usage: site_crawl.py <W/final/site> <repo> <outdir> <pop.json> <ST,ST,...> [max_places]"""
import json,re,sys,os,time,threading,traceback,collections,datetime as dt,concurrent.futures as cf
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup
SITE,REPO,OUT,POPF,STS=sys.argv[1:6]; MAXP=int(sys.argv[6]) if len(sys.argv)>6 else 10**9
STS=STS.split(',')
TODAY=dt.date.today().isoformat()
UA={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36','Accept-Language':'en-US,en;q=0.9'}
VC=json.load(open('/home/user/tab/.vendor-capability.json')); MC=json.load(open('/home/user/tab/.model-capability.json'))
GEM=VC['base_url']+'/google-vertex/v1/projects/flik-ai-staging/locations/global/publishers/google/models/gemini-3.5-flash:generateContent'
SERP=MC['base_url'].rstrip('/')+'/serper/search' if 'base_url' in MC else None
POP=json.load(open(POPF))
NAMES={'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming'}
FIPS={'AL':'01','AK':'02','AZ':'04','AR':'05','CA':'06','CO':'08','CT':'09','DE':'10','FL':'12','GA':'13','HI':'15','ID':'16','IL':'17','IN':'18','IA':'19','KS':'20','KY':'21','LA':'22','ME':'23','MD':'24','MA':'25','MI':'26','MN':'27','MS':'28','MO':'29','MT':'30','NE':'31','NV':'32','NH':'33','NJ':'34','NM':'35','NY':'36','NC':'37','ND':'38','OH':'39','OK':'40','OR':'41','PA':'42','RI':'44','SC':'45','SD':'46','TN':'47','TX':'48','UT':'49','VT':'50','VA':'51','WA':'53','WV':'54','WI':'55','WY':'56'}
BAD=re.compile(r'(genweb|rootsweb|ancestry|findagrave|register\.com|gazette|herald|tribune|wikipedia|wikidata|facebook|instagram|twitter|(^|\.)x\.com$|linkedin|youtube|governmentjobs|yelp|tripadvisor|mapquest|city-data|niche\.com|ballotpedia|usa\.com|zillow|realtor|redfin|trulia|chamber|visit|tourism|countyoffice|municipalonlinepayments|nextdoor|google\.|bing\.|yahoo|opengov|govserv|civicweb|\.edu$|newspaper|news|patch\.com|weather|bestplaces|areavibes|uscities|citytowninfo|epodunk|homefacts|dnb\.com|bizapedia|manta|indeed|glassdoor|justia|municode|amlegal|ecode360|library|school|isd\.|usd\d|church|museum|county|parish|\.k12\.|pdffiller|scribd|issuu|reddit|tiktok|pinterest|govoffice\.com$|nlc\.org|mlct|lkm\.org|iowaleague|lonm|mocities|arml|masscities|wvml|tml1|tml\.org|alm\.org|masc\.sc|chamberofcommerce|vote|election)',re.I)
def nz(s): return re.sub(r'[^a-z0-9]','',(s or '').lower())
def dom(u):
    h=(urlparse(u if '//' in u else 'http://'+u).hostname or '').lower(); return h[4:] if h.startswith('www.') else h
SES=threading.local()
def sess():
    if not hasattr(SES,'s'): SES.s=requests.Session(); SES.s.headers.update(UA)
    return SES.s
BBU=os.environ.get('BB_FETCH','http://127.0.0.1:8795/fetch')
STAT={'direct':0,'bb':0,'bb_fail':0}
FSEM=threading.BoundedSemaphore(3)   # at most 3 fetches in flight (hang rule); place threads can wait on the model meanwhile
def fetch_direct(u,t=20):
    try:
        r=sess().get(u,timeout=(6,t),allow_redirects=True,stream=True)
        ct=r.headers.get('content-type','')
        if r.status_code!=200 or ('html' not in ct and 'text' not in ct): r.close(); return None,None,r.status_code
        b=b''
        for ch in r.iter_content(65536):
            b+=ch
            if len(b)>2_500_000: break
        r.close()
        h=b.decode(r.encoding or 'utf-8','replace')
        if len(h)<3000 and re.search(r'(?i)just a moment|cf-chl|captcha|access denied|enable javascript',h): return None,None,403
        return r.url,h,200
    except Exception: return None,None,0
def fetch_bb(u):
  with FSEM:
    try:
        j=requests.get(BBU,params={'u':u},timeout=90).json()
        if j.get('html') and (j.get('status') or 200)<400: STAT['bb']+=1; return j.get('url') or u,j['html']
    except Exception: pass
    return None,None
def fetch(u,t=12):
    with FSEM: fu,h,code=fetch_direct(u,t)
    if h and len(re.sub(r'<[^>]+>','',h))>400: STAT['direct']+=1; return fu,h
    if code==404: return None,None
    fu2,h2=fetch_bb(u)
    if h2: return fu2,h2
    STAT['bb_fail']+=1
    return (fu,h) if h else (None,None)
def text_of(html):
    s=BeautifulSoup(html,'lxml')
    for x in s(['script','style','noscript','svg','iframe']): x.decompose()
    t=s.get_text('\n',strip=True); t=re.sub(r'[ \t\u00a0]+',' ',t); return s,t
def serper(q):
    for i in range(3):
        try:
            r=requests.post(SERP,json={'q':q},headers={'X-API-KEY':MC['token'],'Content-Type':'application/json'},timeout=40)
            if r.status_code==200: return r.json().get('organic',[])
        except Exception: pass
        time.sleep(3)
    return []
def names_place(t,name,st,u=''):
    tl=t.lower(); n=name.lower()
    if n not in tl: return False
    tl=tl.replace(n,' ')+' '+n
    d_=dom(u); offl=re.search(r'\b(city|town|village|borough|township) of '+re.escape(n)+r'\b',tl)
    if n in tl and offl and (d_.endswith('.gov') or d_.endswith('.us')) and not re.search(r'\b(' + '|'.join(x.lower() for k,x in NAMES.items() if k!=st and x.lower() not in NAMES[st].lower()) + r')\b', tl[:3000]): return True
    return n in tl and (NAMES[st].lower() in tl or re.search(r'\b'+st.lower()+r'\b',tl) is not None or dom(u).endswith('.'+st.lower()+'.us') or ('-'+st.lower()+'.' in dom(u)) or (st.lower()+'.gov' in dom(u)))

QPRE=('west','east','north','south','new','old','lake','port','mount','mt','fort','saint','st','upper','lower','little','big','greater','grand')
QSUF=('valley','beach','heights','park','village','hills','springs','city','falls','lake','shores','township','twp','borough','junction','center','station','county','gardens','acres','ridge','estates','harbor','island','creek','grove')
ABBR={v:k for k,v in NAMES.items()}
def _label(u):
    h=dom(u); parts=h.split('.')
    if len(parts)>=3 and parts[-1] in ('gov','us') and (parts[-2] in [x.lower() for x in NAMES] or parts[-2] in [nz(x) for x in NAMES.values()] or len(parts[-2])==2): return parts[0]
    return parts[-2] if len(parts)>=2 else h
PLN=collections.defaultdict(set)   # (st) -> nz names of every non-CDP place in the state (filled in main)
KINDM={'town':r'townof','village':r'villageof','city':r'cityof','township':r'(twp|township)$|(twp|township)[a-z]{2}$|townshipof','borough':r'boroughof'}
def kind_marker(lab,tl):
    for k,rx in KINDM.items():
        if re.search(rx,lab): return k
    m=re.search(r'\b(town|village|city|township|borough) of\b',tl)
    return m.group(1) if m else ''
def wrong_place(p,st,u,title='',text=''):
    """reason string when the site at u is evidently a DIFFERENT place than p (a neighbour whose name contains p's
    name, the same name in another state, a town site for a city), else ''"""
    name=p['n']; n=nz(name); lab=nz(_label(u)); kind=p.get('t') or 'city'
    tl=(title or '').lower()
    others=PLN.get(st,set())
    for q in QPRE:
        if (q+n) in lab and (q+n) in others and (q+n)!=n: return 'domain is '+q+' '+name
    for q in QSUF:
        if (n+q) in lab and (n+q) in others and (n+q)!=n: return 'domain is '+name+' '+q
    for m_ in others:
        if m_!=n and n in m_ and m_ in lab: return 'domain names another place ('+m_+')'
    if n not in lab:
        for m_ in others:
            if m_!=n and len(m_)>=5 and m_ in lab: return 'domain names another place ('+m_+') not this one'
    ini=''.join(w[0] for w in re.findall(r'[a-z]+',name.lower()))
    if len(ini)>=2 and re.match(r'^[wens]'+re.escape(ini)+r'$',lab): return 'domain directional initials'
    for k,v in NAMES.items():
        if k==st: continue
        if lab.endswith(n+k.lower()) or (len(ini)>=2 and lab==ini+k.lower()) or lab.endswith(n+nz(v)): return 'domain other state '+k
        if re.search(re.escape(name.lower())+r',?\s+('+re.escape(v.lower())+r'|'+k.lower()+r')\b',tl): return 'title other state '+k
    km=kind_marker(lab,tl)
    if km and km!=kind and DUPN.get((st,n),1)>1: return 'site is the %s, place is a %s'%(km,kind)
    nm=re.escape(name.lower())
    for mm in re.finditer(r'\b('+'|'.join(QPRE)+r')\.? '+nm+r'\b|'+nm+r' ('+'|'.join(QSUF)+r')\b',tl):
        if nz(mm.group(0)) in others and nz(mm.group(0))!=n: return 'title neighbour '+mm.group(0)
    return ''

TRAVEL=re.compile(r'(?i)\b(visit|travel|tourism|things to do|utilities|chamber|convention|museum|library|school|real estate|homes for sale)\b|^(?!.*city and county).*\bcounty\b')
def find_site(p,st):
    kind={'city':'City','town':'Town','village':'Village','borough':'Borough','township':'Township'}.get(p.get('t'),'City')
    tok=[w for w in re.findall(r'[a-z]+',p['n'].lower()) if len(w)>=4 and w not in ('city','town','village','saint','fort','port','lake','north','south','east','west','mount','new')] or [nz(p['n'])]
    cands=[]
    if p.get('w'):
        d0=dom(p['w'])
        if not BAD.search(d0) and (d0.endswith('.gov') or d0.endswith('.us') or re.search(r'(cityof|townof|villageof|city|town|village|ci\.|twp)',d0)): cands.append((0,'w',p['w']))
    for i,o in enumerate(serper(f'{kind} of {p["n"]}, {NAMES[st]} official website')[:7]):
        u=o.get('link',''); d=dom(u); title=(o.get('title') or '')
        if not d or BAD.search(d) or TRAVEL.search(title): continue
        gov=d.endswith('.gov') or d.endswith('.us')
        ini=''.join(w[0] for w in re.findall(r'[a-z]+',p['n'].lower())) if len(p['n'].split())>1 else ''
        named=p['n'].lower() in title.lower() or any(w in d for w in tok) or (len(ini)>=2 and re.match(re.escape(ini)+r'[a-z]{0,3}\.(gov|us)$',d) is not None)
        official=re.search(r'(?i)\b(city|town|village|borough|township) of\b|official (web)?site|city hall|town hall|municipal',title) or re.search(r'(cityof|townof|villageof|city|town|village|ci\.|twp|gov)',d)
        if not named: continue
        if not gov and not official: continue
        hn=urlparse(u).netloc; lab=hn.split('.')
        if len(lab)>2 and lab[0]!='www' and not re.search(r'\.(ci|co|town|city|state)\.[a-z]{2}\.us$',hn): cands.append((1 if gov else 2+i,'s','https://www.'+'.'.join(lab[-2:])+'/'))
        cands.append((1 if gov else 2+i,'s',urlparse(u).scheme+'://'+hn+'/'))
    cands.sort(key=lambda x:x[0])
    seen=set()
    for _,how,u in cands[:4]:
        if u in seen: continue
        seen.add(u)
        fu,h=fetch(u)
        if not h or not fu: continue
        if BAD.search(dom(fu)): continue
        s,t=text_of(h)
        ttl=(s.title.get_text(' ',strip=True) if s.title else '')
        if wrong_place(p,st,fu,ttl,t) or wrong_place(p,st,u,ttl,t): continue
        if DUPN.get((st,nz(p['n'])),1)>1 and not dup_ok(p,st,t,fu,ttl): continue
        if names_place(t,p['n'],st,fu) and ((dom(fu).endswith('.gov') or dom(fu).endswith('.us')) or re.search(r'(?i)\b(city|town|village|borough|township) (of|council|hall|clerk|manager|board|commission)|\bmayor\b|aldermen|alderm|trustees|select ?board|municipal',t[:60000])): return fu,s,t,how
    return None
KW=re.compile(r'(council|mayor|alder|commission(er)?s?\b|board of (trustees|aldermen|selectmen|directors|mayor)|select ?board|elected|officials|governing|trustees|city hall|town hall|government|leadership|our city|meet the)',re.I)
NEG=re.compile(r'(agenda|minutes|meeting|calendar|video|archive|planning|zoning|park|library|police|fire|job|employment|bid|rfp|news|event|pdf$|\.pdf|facebook|twitter|instagram|youtube|mailto:|tel:|login|pay|utility|permit|form)',re.I)
def pick_links(base,s):
    bd=dom(base); sc={}
    for a in s.find_all('a',href=True):
        tx=' '.join(a.get_text(' ',strip=True).split())[:80]; href=a['href']
        u=urljoin(base,href).split('#')[0]
        if dom(u)!=bd or not u.startswith('http'): continue
        k=tx+' '+urlparse(u).path
        if not KW.search(k) or NEG.search(k): continue
        v=0
        if re.search(r'council|alder|commissioners|trustees|select ?board|board of (aldermen|trustees|selectmen|mayor)',k,re.I): v+=5
        if re.search(r'mayor',k,re.I): v+=4
        if re.search(r'elected|officials|governing',k,re.I): v+=4
        if re.search(r'government|city hall|town hall|leadership',k,re.I): v+=1
        sc[u]=max(sc.get(u,0),v)
    return [u for u,v in sorted(sc.items(),key=lambda x:-x[1]) if v>0][:4]
PROMPT="""These are pages from the official website of {name}, {state} (a {kind}). List the people these pages name as the CURRENT members of this municipality's own government: mayor, vice mayor / mayor pro tem, city/town council or commission members, aldermen, village trustees or village president, select board members, town supervisor and town board members, plus the city/town clerk and the city/town manager or administrator.
Rules: only names printed on these pages; copy each name EXACTLY as printed (same spelling, middle initials, suffixes; drop titles like "Mayor", "Councilmember", "Hon.", "Dr."). Do not include former officials, candidates, staff other than clerk/manager/administrator, county / school / state officials, or members of advisory boards (planning, parks, etc.). If a role includes a ward/district/seat, keep it in the role (e.g. "Council Member, Ward 2"). Give the page label (P1, P2, ...) where the name appears with that role. If the pages do not name the officials, return an empty list.
Return JSON: {{"officials":[{{"name":"...","role":"...","page":"P1","email":"... or empty"}}]}}

{pages}"""
def gem(prompt):
    for i in range(4):
        try:
            r=requests.post(GEM,headers={'Authorization':'Bearer '+VC['token']},json={'contents':[{'role':'user','parts':[{'text':prompt}]}],'generationConfig':{'responseMimeType':'application/json','temperature':0,'maxOutputTokens':12000,'thinkingConfig':{'thinkingBudget':512}}},timeout=120)
            if r.status_code==200:
                j=r.json(); tx=''.join(p_.get('text','') for p_ in j['candidates'][0]['content']['parts'] if not p_.get('thought'))
                return json.loads(tx)
            LASTERR[0]=f'{r.status_code} {r.text[:200]}'; time.sleep(5*(i+1))
        except Exception as e: LASTERR[0]=repr(e)[:200]; time.sleep(5)
    return None
LASTERR=['']
def sameperson(a,b):
    a,b=[[w for w in x.replace(',',' ').split() if not re.match(r'(?i)^(jr|sr|ii|iii|iv)\.?$',w)] for x in (a,b)]; return bool(a and b) and nz(a[-1])==nz(b[-1]) and nz(a[0])[:1]==nz(b[0])[:1]
def wsnorm(s): return re.sub(r'\s+',' ',s).strip()
def role_norm(r):
    R=r.strip(); L=R.lower()
    if re.search(r'\b(former|candidate|deputy clerk|assistant)\b',L): return None,None
    if re.search(r'vice[- ]mayor|mayor pro[- ]?tem|deputy mayor',L): return R,'gen_council'
    if re.search(r'^(the )?(city |town |village )?mayor$|^mayor\b',L): return 'Mayor','gen_mayor'
    if re.search(r'village president|president of the (village|board)',L): return R,'gen_mayor'
    if re.search(r'council|alder|commissioner|trustee|select|town board|board member|supervisor|councilor|councillor|board of',L): return R,'gen_council'
    if re.search(r'clerk|manager|administrator',L): return R,None
    return None,None
def do_place(st,pid,p):
    res={'pid':pid,'n':p['n'],'st':st,'at':time.strftime('%H:%M:%S')}
    f=find_site(p,st)
    if not f: res['status']='no_site'; return res
    home,s,t,how=f; res['w']=home; res['how']=how
    pages=[(home,t)]
    for u in pick_links(home,s):
        fu,h=fetch(u)
        if not h or dom(fu)!=dom(home) or NEG.search(urlparse(fu).path): continue
        s2,t2=text_of(h); pages.append((fu,t2))
        if len(pages)>=5: break
    if len(pages)==1: res['note']='no officials links'
    kind=p.get('t') or 'city'
    def extract(pages):
        body='\n\n'.join(f'=== P{i+1}: {u}\n{tx[:14000]}' for i,(u,tx) in enumerate(pages))
        j=gem(PROMPT.format(name=p['n'],state=NAMES[st],kind=kind,pages=body))
        if j is None: return None,0
        out=[];rej=0
        for o in (j.get('officials') or [])[:40]:
            nm=re.sub(r'^(Dr\.?|Hon\.?|Honorable|Mr\.?|Mrs\.?|Ms\.?|Rev\.?|Pastor|Judge)\s+','',wsnorm(o.get('name',''))); pg=o.get('page','')
            m=re.match(r'P(\d+)',pg or '')
            if not nm or len(nm.split())<2 or not m or int(m.group(1))>len(pages): rej+=1; continue
            u,tx=pages[int(m.group(1))-1]
            if nm not in wsnorm(tx): rej+=1; continue
            r_,rk=role_norm(o.get('role',''))
            if not r_: rej+=1; continue
            rec={'n':nm,'r':r_,'src':'site','u':u,'d':TODAY}
            if rk: rec['rk']=rk
            em=(o.get('email') or '').strip()
            if em and '@' in em and em in tx:
                ed=em.split('@')[-1].lower(); hd=dom(home)
                if ed==hd or hd.endswith('.'+ed) or ed.endswith('.'+hd): rec['ct']={'e':em,'src':u}
            if not any(sameperson(x['n'],rec['n']) for x in out): out.append(rec)
        return out,rej
    out,rej=extract(pages)
    if out is None: res['status']='llm_fail'; res['err']=LASTERR[0]; return res
    if not out:
        pr=[]
        for u,_ in pages[:4]:
            fu,h=fetch_bb(u)
            if h: pr.append((fu,text_of(h)[1]))
        if pr:
            o2,r2=extract(pr)
            if o2: out,rej,pages=o2,r2,pr; res['via']='rendered'
    if sum(1 for x in out if x.get('rk'))<3:
        have={u for u,_ in pages}; extra=[]
        for o in serper(f'site:{dom(home)} city council members mayor')[:5]:
            u=o.get('link','').split('#')[0]
            if u in have or dom(u)!=dom(home) or NEG.search(urlparse(u).path) or u.lower().endswith('.pdf'): continue
            fu,h=fetch(u)
            if not h or dom(fu)!=dom(home): continue
            extra.append((fu,text_of(h)[1])); have.add(u)
            if len(extra)>=2: break
        if extra:
            pages2=pages[:3]+extra
            o2,r2=extract(pages2)
            if o2 is not None and sum(1 for x in o2 if x.get('rk'))>sum(1 for x in out if x.get('rk')):
                out,rej,pages=o2,r2,pages2; res['via']='site_search'
    mayors=[x for x in out if x.get('rk')=='gen_mayor' and x['r']=='Mayor']
    if len(mayors)>1: res['status']='ambiguous_mayor'; res['o']=out; return res
    if len(out)>60: res['status']='too_many'; return res
    res['o']=out; res['rej']=rej; res['status']='ok' if out else 'none_named'; res['pages']=[u for u,_ in pages]
    if not out: res.pop('w',None)
    return res
DUPN=collections.Counter(); DUPK=collections.Counter(); CNAME={}
def dup_ok(p,st,t,u='',title=''):
    kind=p.get('t') or 'city'; km=kind_marker(nz(_label(u)),(title or '').lower())
    if km: return km==kind
    tl=t.lower(); nm=re.escape(p['n'].lower())
    cnt=collections.Counter(m.group(1) for m in re.finditer(r'\b(town|village|city|township|borough) of '+nm+r'\b',tl))
    if cnt and cnt.most_common(1)[0][0]!=kind: return False
    if cnt and DUPK.get((st,nz(p['n']),kind),1)<=1: return True
    names=[CNAME.get((st,f),'') for f in p.get('c',[])]
    return any(n and n.lower().replace(' county','').replace(' parish','') in tl for n in names)
def main():
    todo=[]
    for st in STS:
        D_=json.load(open(os.path.join(SITE,'data','local',st+'.json'),encoding='utf-8')); d=D_['places']
        for c_ in D_.get('counties',[]): CNAME[(st,c_['f'])]=c_['n']
        for p_ in d.values():
            if p_.get('t')!='CDP': DUPN[(st,nz(p_['n']))]+=1; DUPK[(st,nz(p_['n']),p_.get('t') or 'city')]+=1; PLN[st].add(nz(p_['n']))
        have=set()
        for fn in os.listdir(os.path.join(REPO,'data','officials-local')):
            if fn.endswith('.json') and (fn==st+'.json'):
                have|=set(json.load(open(os.path.join(REPO,'data','officials-local',fn)))['places'])
        done=set()
        jf=os.path.join(OUT,st+'.jsonl')
        if os.path.exists(jf):
            for l in open(jf):
                try: done.add(json.loads(l)['pid'])
                except Exception: pass
        for pid,p in d.items():
            if p.get('t')=='CDP' or p.get('o') or pid in have or pid in done: continue
            todo.append((POP.get(FIPS[st]+'|'+pid,0),st,pid,p))
    todo.sort(key=lambda x:-x[0]); todo=todo[:MAXP]
    print(json.dumps({'todo':len(todo),'first':[(x[1],x[3]['n'],x[0]) for x in todo[:10]]}),flush=True)
    lock=threading.Lock(); n=0
    def run(x):
        pop,st,pid,p=x
        try: r=do_place(st,pid,p)
        except Exception as e: r={'pid':pid,'n':p['n'],'st':st,'status':'error','err':repr(e)[:300]}
        r['pop']=pop
        with lock:
            open(os.path.join(OUT,st+'.jsonl'),'a').write(json.dumps(r,ensure_ascii=False)+'\n')
        return r
    with cf.ThreadPoolExecutor(6) as ex:
        for r in ex.map(run,todo):
            n+=1
            if n%10==0: print(time.strftime('%H:%M:%S'),n,r['st'],r['n'],r.get('status'),len(r.get('o') or []),json.dumps(STAT),flush=True)
    print('DONE',n,json.dumps(STAT),flush=True)
main()
