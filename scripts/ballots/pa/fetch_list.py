
import requests,json,os,sys,time
from concurrent.futures import ThreadPoolExecutor
UA={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36'}
D=sys.argv[1]; lst=json.load(open(D+'/list.json'))
def one(x):
    n,u=x; out=D+'/pdf/'+n+'.pdf'
    if os.path.exists(out) and os.path.getsize(out)>5000: return 'have'
    for a in range(3):
        try:
            c=requests.get(u,headers=UA,timeout=60).content
            if c[:4]==b'%PDF': open(out,'wb').write(c); return 'ok'
        except Exception: time.sleep(5)
    return 'fail '+n
with ThreadPoolExecutor(3) as ex:
    for i,r in enumerate(ex.map(one,lst)):
        if r not in('ok','have') or i%50==0: print(i,r,flush=True)
print('DONE',flush=True)
