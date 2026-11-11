
import os,sys,json,re,time,threading,queue,requests,traceback
from urllib.parse import urljoin,urlparse
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
JOBS,OUT=sys.argv[1],sys.argv[2]
mc=json.load(open("/home/user/tab/.model-capability.json"))
MURL=mc["base_url"].rstrip("/")+"/openai/v1/chat/completions"; MH={"Authorization":"Bearer "+mc["token"],"x-tab-task":os.environ.get("TAB_TASK_ID","")}
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36","Accept-Language":"en-US,en;q=0.9"}
FREEMAIL=re.compile(r"@(gmail|googlemail|yahoo|ymail|aol|hotmail|outlook|live|msn|icloud|me|mac|comcast|att|sbcglobal|verizon|protonmail|proton|gmx|charter|bellsouth|cox|earthlink|frontier|windstream|mail|zoho|hey|fastmail|centurylink|embarqmail|optonline|roadrunner|rr|twc|juno|netzero|q)\.",re.I)
BAD_HOST=re.compile(r"(wikipedia|wikidata|spokeo|whitepages|beenverified|truepeoplesearch|fastpeoplesearch|radaris|intelius|peoplefinders|mylife|nuwber|cnn\.com|nytimes|washingtonpost|apnews|reuters)",re.I)
PH=re.compile(r"(?:\+?1[\s.\-]*)?\(?\b([2-9]\d{2})\)?[\s.\-]*([2-9]\d{2})[\s.\-]*(\d{4})\b")
EM=re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
done=set()
if os.path.exists(OUT):
    for l in open(OUT):
        try: done.add(json.loads(l)["jid"])
        except: pass
lock=threading.Lock(); msem=threading.Semaphore(2)
def fetch(u):
    try:
        r=requests.get(u,headers=UA,timeout=(10,20),stream=True,allow_redirects=True)
        b=b""
        for ch in r.iter_content(65536):
            b+=ch
            if len(b)>2500000: break
        r.close()
        if r.status_code!=200: return None,"HTTP %d"%r.status_code
        ct=r.headers.get("content-type","")
        if "html" not in ct and "text" not in ct: return None,"not html: "+ct[:40]
        return (r.url,b.decode(r.encoding or "utf-8","replace")),None
    except Exception as e: return None,type(e).__name__
def parse(url,html):
    sp=BeautifulSoup(html,"lxml")
    links=[]
    for a in sp.find_all("a",href=True):
        h=a["href"].strip()
        if h.startswith("#") or h.lower().startswith("javascript"): continue
        if h.lower().startswith("mailto:"): links.append((h,a.get_text(" ",strip=True)));continue
        if h.lower().startswith("tel:"): links.append((h,a.get_text(" ",strip=True)));continue
        links.append((urljoin(url,h),a.get_text(" ",strip=True)[:80]))
    for t in sp(["script","style","noscript","svg"]): t.decompose()
    txt=sp.get_text("\n")
    lines=[re.sub(r"[ \t\xa0]+"," ",l).strip() for l in txt.split("\n")]
    lines=[l for l in lines if l]
    return lines,links
def context(lines,links,names):
    keep=set()
    nm=[n for n in names if n]
    for i,l in enumerate(lines):
        hit=PH.search(l) or "@" in l or re.search(r"(?i)\b(phone|tel|fax|email|e-mail|contact|address|office|suite|room|p\.?o\.? box|\d{5}(-\d{4})?$)",l) or any(n.lower() in l.lower() for n in nm)
        if hit:
            for j in range(max(0,i-3),min(len(lines),i+4)): keep.add(j)
    out=[];size=0
    for i in sorted(keep):
        s=lines[i][:300]; out.append(s); size+=len(s)+1
        if size>11000: break
    lk=[]
    for h,t in links:
        if h.lower().startswith(("mailto:","tel:")) or re.search(r"(?i)contact|email|reach|facebook\.com|x\.com|twitter\.com|instagram\.com|youtube\.com",h+" "+t):
            if (h,t) not in lk: lk.append((h,t))
    return "\n".join(out),lk[:40]
SYS=("You extract PUBLIC OFFICIAL contact details for named government officials (or, if kind=campaign, a candidate's CAMPAIGN contact) from web page text. "
"Copy values EXACTLY as they appear. Never guess or construct values. Rules: only contact routes for the person's OFFICE or role "
"(an office phone, office email, contact form URL, office mailing address) or, for kind=campaign, the campaign's. A phone or email that is clearly specific to the person (listed next to their name/role) is 'personal_to_role' = true; "
"a general office/city hall/county/department main number or address (not next to their name) is 'general' = true. "
"NEVER return: home addresses, residential addresses, anything labelled home, cell, mobile or personal, any email at gmail/yahoo/aol/hotmail/outlook/icloud/comcast or other personal mail services. "
"If the page lists several people, assign values ONLY to the person they are printed next to. A general office contact (general=true) may be used for the named official only when it is the main contact of the office or government body they lead or sit on (e.g. the Governor's office, the city hall for a council member), never a contact for some other staff member, division, program or service (press office, solicitor general, HR, records requests, a hotline, a braille or voter form). If nothing qualifies, return empty fields. "
"Social: only accounts the page itself links as the office's/person's official (or campaign) accounts. "
"Return JSON: {\"people\":[{\"key\":...,\"phone\":[...],\"email\":\"\",\"form\":\"\",\"address\":\"\",\"social\":{\"x\":\"\",\"fb\":\"\",\"ig\":\"\",\"yt\":\"\"},\"general\":false,\"note\":\"\"}]}")
def model(user):
    body={"model":"gpt-5.4-mini","messages":[{"role":"system","content":SYS},{"role":"user","content":user}],"response_format":{"type":"json_object"},"reasoning_effort":"low"}
    for att in range(4):
        try:
            with msem:
                r=requests.post(MURL,headers=MH,json=body,timeout=(10,110))
            if r.status_code==200:
                t=r.json()["choices"][0]["message"]["content"]; t=re.sub(r"^```(?:json)?|```$","",t.strip()).strip()
                return json.loads(t),None
            last="HTTP %d %s"%(r.status_code,r.text[:100])
            if r.status_code in (400,401,403): return None,last
        except Exception as e: last=type(e).__name__
        time.sleep(5*(att+1))
    return None,last
def digits(s): return re.sub(r"\D","",s)
def verify(p,blob,blobd,linkset,lines):
    out={}
    ph=[]
    for v in (p.get("phone") or [])[:3]:
        m=PH.search(v or "")
        if not m: continue
        d="".join(m.groups())
        if d not in blobd: continue
        # reject if labelled cell/home/mobile near it
        bad=False
        for l in lines:
            if d in digits(l) and re.search(r"(?i)\b(cell|mobile|home|personal|res\.?|residence)\b",l): bad=True
        if bad: continue
        f="(%s) %s-%s"%m.groups(); ext=re.search(r"(?i)(?:ext\.?|x)\s*(\d{1,6})",v)
        if ext: f+=" ext. "+ext.group(1)
        if f not in ph: ph.append(f)
    if ph: out["p"]=ph[:2]
    e=(p.get("email") or "").strip().lower().replace("mailto:","")
    if e and EM.fullmatch(e) and not FREEMAIL.search(e) and e in blob.lower(): out["e"]=e
    fo=(p.get("form") or "").strip()
    if fo and fo in linkset and fo.startswith("http") and not BAD_HOST.search(fo): out["f"]=fo
    a=re.sub(r"\s+"," ",(p.get("address") or "")).strip()
    if a and len(a)>10:
        an=re.sub(r"[^a-z0-9]","",a.lower())
        if an[:25] in re.sub(r"[^a-z0-9]","",blob.lower()) and not re.search(r"(?i)\bhome\b|residence",a): out["a"]=a
    so={}
    for k,v in (p.get("social") or {}).items():
        v=(v or "").strip()
        if k in ("x","fb","ig","yt") and v in linkset and re.search(r"(x\.com|twitter\.com|facebook\.com|instagram\.com|youtube\.com)",v,re.I) and not re.search(r"/(sharer|share|intent|plugins|dialog)",v,re.I): so[k]=v
    if so: out["s"]=so
    return out
def run(job):
    jid=job["jid"]
    pages=[];errs=[]
    for u in job["urls"][:2]:
        res,err=fetch(u)
        if res: pages.append(res)
        else: errs.append((u,err))
    if not pages:
        return {"jid":jid,"err":errs}
    # follow one contact link on same host
    allines=[];alllinks=[]
    for (fu,html) in pages:
        l,k=parse(fu,html); allines+=l; alllinks+=k
    if job.get("follow",True):
        h0=urlparse(pages[0][0]).netloc
        cl=[h for h,t in alllinks if urlparse(h).netloc==h0 and h.rstrip("/")!=pages[0][0].rstrip("/") and (re.fullmatch(r"(?i)\s*contact( us)?\s*",t or "") or re.search(r"(?i)/contact(-us|us|_us)?/?$",urlparse(h).path))]
        if not cl: cl=[h for h,t in alllinks if urlparse(h).netloc==h0 and re.search(r"(?i)contact",t or "") and not re.search(r"(?i)form|request|braille|press|media",h+" "+(t or "")) and h.rstrip("/")!=pages[0][0].rstrip("/")]
        if cl:
            res,err=fetch(cl[0])
            if res:
                pages.append(res); l,k=parse(*res); allines+=l; alllinks+=k
    names=[p["n"] for p in job["people"]]
    ctx,lk=context(allines,alllinks,names+[w for p in job["people"] for w in p["n"].split()[-1:]])
    blob="\n".join(allines)+"\n"+"\n".join(h for h,t in alllinks)
    blobd=digits(blob)
    linkset=set(h for h,t in alllinks)
    if not (PH.search(ctx) or "@" in ctx or lk):
        return {"jid":jid,"pages":[p[0] for p in pages],"people":{},"why":"no contact text on page"}
    user="kind: %s\nPeople (key: name, role, place):\n%s\n\nPage URLs: %s\n\nLinks (href | text):\n%s\n\nPage text (relevant lines):\n%s"%(job.get("kind","official"),
        "\n".join("%s: %s, %s, %s"%(p["key"],p["n"],p.get("r",""),p.get("place","")) for p in job["people"]),
        ", ".join(p[0] for p in pages),"\n".join("%s | %s"%(h,t) for h,t in lk),ctx)
    j,err=model(user)
    if not j: return {"jid":jid,"pages":[p[0] for p in pages],"err":err}
    res={}
    for p in j.get("people",[]):
        k=p.get("key")
        if k not in [q["key"] for q in job["people"]]: continue
        v=verify(p,blob,blobd,linkset,allines)
        if v:
            v["general"]=bool(p.get("general"))
            res[k]=v
    return {"jid":jid,"pages":[p[0] for p in pages],"people":res}
jobs=[json.loads(l) for l in open(JOBS)]
jobs=[j for j in jobs if j["jid"] not in done]
print("todo",len(jobs),flush=True)
n=0
with ThreadPoolExecutor(3) as ex:
    for r in ex.map(lambda j: (lambda: run(j))() if True else None, jobs):
        with lock:
            open(OUT,"a").write(json.dumps(r,ensure_ascii=False)+"\n")
            n+=1
            if n%25==0: print(time.strftime("%H:%M:%S"),n,flush=True)
print("DONE",n,flush=True)
