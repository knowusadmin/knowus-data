#!/usr/bin/env python3
"""KnowUS: apply data/officials-local/<ST>.json (filled local officials) to a site build's data/local/<ST>.json.
usage: apply_local_officials.py <site_dir> <officials_local_dir>
Each stored place carries its full official list ("o"); it replaces the place's list only when the place id and name
match the site file. Idempotent. Run BEFORE scripts/contacts/apply_contacts.py (postbuild.sh does)."""
import json,sys,os,glob
site,src=sys.argv[1],sys.argv[2]
tot={}
for f in sorted(glob.glob(os.path.join(src,'*.json'))):
    D=json.load(open(f,encoding='utf-8')); st=D['st']
    lf=os.path.join(site,'data','local',st+'.json')
    if not os.path.exists(lf): tot[st]='no site file'; continue
    d=json.load(open(lf,encoding='utf-8')); n=0; skip=0
    for pid,p in D.get('places',{}).items():
        sp=d.get('places',{}).get(pid)
        if not sp or sp.get('n')!=p.get('n'): skip+=1; continue
        sp['o']=p['o']; n+=1
        if p.get('w') and not sp.get('w'): sp['w']=p['w']
    if D.get('src',{}).get('name'): d.setdefault('src',{})['officials_state']=D['src']['name']
    json.dump(d,open(lf,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    tot[st]={'places':n,'skipped':skip}
print(json.dumps(tot))
