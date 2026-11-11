
import requests,json,sys,os,time
from concurrent.futures import ThreadPoolExecutor
UA={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36'}
D=sys.argv[1]
while not os.path.exists(D+'/geo-raw.json'): time.sleep(2)
G=json.load(open(D+'/geo-raw.json')); pcts=sorted(set(f['attributes']['PRECINCT'] for f in G['features']))
print('precincts',len(pcts),flush=True)
def one(p):
    got=[]
    for s in range(0,8):
        u=f'https://votehamiltoncountyohio.gov/files/ballots/N{p}{s}.pdf'; out=f'{D}/pdf/N{p}{s}.pdf'
        if os.path.exists(out): got.append(s); continue
        for a in range(3):
            try:
                r=requests.get(u,headers=UA,timeout=60)
                if r.status_code==200 and r.content[:4]==b'%PDF': open(out,'wb').write(r.content); got.append(s)
                break
            except Exception: time.sleep(4)
        if s>=1 and s not in got and (s-1) not in got: break
    return p,got
res={}
with ThreadPoolExecutor(3) as ex:
    for i,(p,g) in enumerate(ex.map(one,pcts)):
        res[p]=g
        if i%50==0 or not g: print(i,p,g,flush=True)
json.dump(res,open(D+'/splits.json','w')); print('DONE',flush=True)
