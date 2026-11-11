
import json,sys,os,re,time,urllib.parse
from playwright.sync_api import sync_playwright
JOBS,OUT=sys.argv[1],sys.argv[2]
done=set()
if os.path.exists(OUT):
    for l in open(OUT):
        try: done.add(json.loads(l)["id"])
        except: pass
jobs=[json.loads(l) for l in open(JOBS)]; jobs=[j for j in jobs if j["id"] not in done]
print("todo",len(jobs),flush=True)
def allow(route):
    r=route.request; u=r.url
    if r.resource_type in ("image","media","font","stylesheet"): return route.abort()
    h=urllib.parse.urlparse(u).netloc
    if not (h.endswith("ballotpedia.org") or "awswaf" in h or "amazonaws" in h or "cloudfront" in h): return route.abort()
    return route.continue_()
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True,executable_path="/home/user/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome",args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx=b.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36")
    ctx.route("**/*",allow)
    p=ctx.new_page(); p.set_default_timeout(30000)
    n=0
    for j in jobs:
        res={"id":j["id"],"tried":[]}
        names=[j["n"]]+j.get("a",[])
        tries=[]
        for nm in names:
            nm=re.sub(r"\s+"," ",nm).strip()
            tries+= [nm, nm+" ("+j["stname"]+")"]
        for nm in tries[:4]:
            url="https://ballotpedia.org/"+urllib.parse.quote(nm.replace(" ","_"))
            try:
                p.goto(url,wait_until="domcontentloaded",timeout=40000)
                for k in range(12):
                    t=p.title()
                    if "Ballotpedia" in t: break
                    p.wait_for_timeout(1000)
                txt=p.inner_text("body")[:200000]
            except Exception as e:
                res["tried"].append([url,"err "+type(e).__name__]); continue
            t=p.title()
            if "There is currently no text" in txt or "does not have a page" in txt or t.startswith("Search results"):
                res["tried"].append([url,"nopage"]); continue
            if re.search(r"may refer to|disambiguation",txt[:5000],re.I):
                res["tried"].append([url,"disambig"]); continue
            OFFW={"house":"U.S. House","senate":"U.S. Senate","gov":"Governor","mayor":"Mayor"}
            ok=(j["stname"] in txt) and ("2026" in txt) and (OFFW[j["mode"]].lower() in txt.lower())
            if not ok: res["tried"].append([url,"no state/2026"]); continue
            links=p.eval_on_selector_all("a","as=>as.map(a=>[a.textContent.trim(),a.href]).filter(x=>/^(Campaign|Official|Personal) (website|Facebook|X|Twitter|Instagram|YouTube|TikTok|LinkedIn|email|e-mail|Email)$/i.test(x[0]))")
            res.update({"bp":p.url,"title":t,"links":links}); break
        open(OUT,"a").write(json.dumps(res)+"\n"); n+=1
        if n%20==0: print(time.strftime("%H:%M:%S"),n,flush=True)
        time.sleep(1.0)
    b.close()
print("DONE",flush=True)
