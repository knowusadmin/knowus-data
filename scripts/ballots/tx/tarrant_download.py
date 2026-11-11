
import select
def _sl(t): select.select([],[],[],t)
import json,sys,os,time,requests
from concurrent.futures import ThreadPoolExecutor
D=sys.argv[1]
while not os.path.exists(D+'/lookup.json'): _sl(10)
LK=json.load(open(D+'/lookup.json'))
fs=sorted({p for x in LK for r in x['res'] for p in r if '/English-Spanish/' in p})
s=requests.Session(); s.headers['User-Agent']='Mozilla/5.0 (KnowUS civic data; ballots)'
def get(p):
    fn=D+'/pdf/'+p.split('/')[-1]
    if os.path.exists(fn) and os.path.getsize(fn)>1000: return 1
    for i in range(6):
        try:
            r=s.get('https://gisit.tarrantcounty.com'+p,timeout=120)
            if r.status_code==200 and r.content[:4]==b'%PDF': open(fn,'wb').write(r.content); return 1
        except Exception: pass
        _sl(3+3*i)
    return 0
with ThreadPoolExecutor(4) as ex: ok=sum(ex.map(get,fs))
print('DL',ok,len(fs),flush=True)
