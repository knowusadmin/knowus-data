#!/usr/bin/env python3
"""KnowUS contacts: merge data/contacts/* (repo) into a site build. Idempotent.
usage: apply_contacts.py <site_dir> <contacts_dir>
 - people.json   -> data.js  window.GOV_DATA.people[id].ct
 - local/<ST>.json -> data/local/<ST>.json  (keys L|U|dist|name, L|L|dist|name, C|fips|name, P|placeid|name)
 - candidates.json -> data/candidates/photos.json photos[id].ct  (campaign contacts, camp:1)
Prints counts. Only ct fields are touched."""
import json,sys,os,glob
site,cd=sys.argv[1],sys.argv[2]
n={"people":0,"leg":0,"county":0,"place":0,"cand":0,"miss":0}
pj=os.path.join(cd,"people.json")
if os.path.exists(pj):
    P=json.load(open(pj))["people"]
    fp=os.path.join(site,"data.js"); t=open(fp,encoding="utf-8").read()
    pre="window.GOV_DATA="; assert t.startswith(pre), "unexpected data.js start"
    body=t[len(pre):].rstrip(); semi=body.endswith(";"); body=body[:-1] if semi else body
    G=json.loads(body)
    for pid,ct in P.items():
        if pid in G["people"]: G["people"][pid]["ct"]=ct; n["people"]+=1
        else: n["miss"]+=1
    open(fp,"w",encoding="utf-8").write(pre+json.dumps(G,ensure_ascii=False,separators=(",",":"))+(";" if semi else "")+("\n" if t.endswith("\n") else ""))
for f in glob.glob(os.path.join(cd,"local","*.json")):
    C=json.load(open(f)); st=C["st"]; ct=C["ct"]
    lf=os.path.join(site,"data","local",st+".json")
    if not os.path.exists(lf): continue
    d=json.load(open(lf,encoding="utf-8"))
    for ch,dd in (d.get("leg") or {}).items():
        for dist,lst in dd.items():
            for o in lst:
                k="L|%s|%s|%s"%(ch,dist,o.get("n"))
                if k in ct: o["ct"]=ct[k]; n["leg"]+=1
    for c in d.get("counties",[]):
        for o in c.get("o",[]) or []:
            k="C|%s|%s"%(c.get("f"),o.get("n"))
            if k in ct: o["ct"]=ct[k]; n["county"]+=1
    for pid,p in (d.get("places") or {}).items():
        for o in p.get("o",[]) or []:
            k="P|%s|%s"%(pid,o.get("n"))
            if k in ct: o["ct"]=ct[k]; n["place"]+=1
    json.dump(d,open(lf,"w",encoding="utf-8"),ensure_ascii=False,separators=(",",":"))
cj=os.path.join(cd,"candidates.json")
if os.path.exists(cj):
    CC=json.load(open(cj))["candidates"]
    pf=os.path.join(site,"data","candidates","photos.json"); ph=json.load(open(pf,encoding="utf-8"))
    for cid,ct in CC.items():
        e=ph["photos"].setdefault(cid,{})
        e["ct"]=ct; n["cand"]+=1
    json.dump(ph,open(pf,"w",encoding="utf-8"),ensure_ascii=False,indent=0)
print(json.dumps(n))
