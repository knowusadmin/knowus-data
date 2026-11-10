
import json,os,re,io,zipfile,collections,glob
import pandas as pd
NC=os.path.dirname(os.path.abspath(__file__))
VZ=zipfile.ZipFile(f'{NC}/raw/vipFeed-37-2026-11-03.zip')
SS=pd.read_csv(io.BytesIO(VZ.read('data/street_segment.txt')),dtype=str,encoding='utf-8-sig',keep_default_na=False,usecols=['address_direction','odd_even_both','precinct_id','start_house_number','end_house_number','street_direction','street_name','street_suffix','zip']).apply(lambda s:s.str.strip())
S1=json.load(open(f'{NC}/stage1.json')); S2=json.load(open(f'{NC}/stage2.json'))
sp_c={s['id']:s['county'] for s in S1['splits']}
sty={}
for co,sts in S2.items():
    for i,s in enumerate(sts):
        for p in s['splits']: sty[p]=(i,s['ok'])
files={}
res=collections.Counter()
for r in SS.itertuples(index=False):
    co=sp_c[r.precinct_id]; slug=re.sub(r'[^a-z]+','-',co.lower()).strip('-')
    D=files.get(slug) or json.load(open(f'{NC}/out/{slug}.json')); files[slug]=D
    lo,hi=int(r.start_house_number or 0),int(r.end_house_number or 0); h=(lo+hi)//2
    if r.odd_even_both=='odd' and h%2==0: h+=1
    if r.odd_even_both=='even' and h%2==1: h+=1
    if h>hi: h=lo
    k=' '.join((r.street_direction+' '+r.street_name+' '+r.street_suffix+' '+r.address_direction).split())
    v=D['st'][k][r.zip]
    if isinstance(v[0],int): sps=[v[2]] if v[0]<=h<=v[1] else []
    else: sps=[q[3] for q in v if q[0]<=h<=q[1] and (not q[2] or (h%2==1 if q[2]==1 else h%2==0))]
    ss={D['sp'][j][0] for j in sps}
    exp,ok=sty[r.precinct_id]
    if len(ss)==1:
        s=next(iter(ss))
        if s!=exp: res['WRONG']+=1
        elif D['s'][s]['ok']: res['complete']+=1
        else: res['labelled (style unverified)']+=1
    else: res['labelled (overlapping ranges)']+=1
print(dict(res),flush=True)
