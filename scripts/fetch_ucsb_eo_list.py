#!/usr/bin/env python3
"""Save the American Presidency Project's "Executive Orders" category listing (newest first, 60 per page) as JSON pages,
for scripts/fetch_eo_history_text.py. Usage: python3 scripts/fetch_ucsb_eo_list.py <out_dir>
Rebuild order for data/eo/hist: this script -> fetch_eo_history_text.py <out_dir> <text_cache> ->
build_eo_history.py data/eo/hist --text-cache <text_cache> -> ai_summaries_eo_history.py --text-cache <text_cache>."""
import requests,json,os,sys,time,re
from bs4 import BeautifulSoup
OUT=sys.argv[1]; os.makedirs(OUT,exist_ok=True)
UA={'User-Agent':'Mozilla/5.0 (KnowUS research; contact shmuel.knowus@mail.tab.bot)'}
B='https://www.presidency.ucsb.edu/documents/app-categories/written-presidential-orders/presidential/executive-orders?items_per_page=60&page='
p=0; empty=0
while p<400:
    fp=f'{OUT}/p{p:03d}.json'
    if os.path.exists(fp): p+=1; continue
    for t in range(4):
        try:
            r=requests.get(B+str(p),headers=UA,timeout=40)
            if r.status_code==200: break
        except Exception as e: print('err',p,e,flush=True)
        time.sleep(5+5*t)
    else:
        print('fail',p,flush=True); p+=1; continue
    s=BeautifulSoup(r.text,'lxml'); out=[]
    for row in s.select('.views-row'):
        a=row.select_one('.field-title a'); d=row.select_one('.date-display-single'); pr=row.select_one('.col-sm-4 a')
        if not a: continue
        out.append({'title':a.get_text(' ',strip=True),'url':a['href'],'date':(d.get('content') or '')[:10] if d else '','pres':pr.get_text(strip=True) if pr else '','presurl':pr['href'] if pr else ''})
    json.dump(out,open(fp,'w'))
    print('page',p,len(out),flush=True)
    if not out:
        empty+=1
        if empty>=2: break
    p+=1; time.sleep(0.5)
print('DONE',flush=True)
