
import requests,re,os,subprocess,gzip,json,sys,time
from concurrent.futures import ThreadPoolExecutor
UA={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36'}
MB=sys.argv[1]; base='https://webapp07.montcopa.org/voterservices/sampleballots/'
r=requests.get(base,headers=UA,timeout=30)
munis=re.findall(r'<option value="([^"]+)"',r.text)
allp=[]
for m in munis:
    for a in range(3):
        try:
            t=requests.post(base+'Listsampleballots.asp',data={'Municipalities':m},headers=UA,timeout=30).text;break
        except Exception as e: time.sleep(3)
    ps=re.findall(r'HREF="\./(Sample Ballots/[^"]+\.pdf)"',t)
    allp+= [(m,p) for p in ps]
    print(m,len(ps),flush=True)
json.dump(allp,open(MB+'/list.json','w'))
print('TOTAL',len(allp),flush=True)
os.makedirs(MB+'/txt',exist_ok=True); os.makedirs(MB+'/pdf',exist_ok=True)
def one(mp):
    m,p=mp; name=p.split('/')[-1][:-4]
    out=MB+'/pdf/'+name+'.pdf'
    if os.path.exists(out) and os.path.getsize(out)>10000: return 'have'
    for a in range(3):
        try:
            c=requests.get(base+p.replace(' ','%20'),headers=UA,timeout=60).content
            if c[:4]==b'%PDF': open(out,'wb').write(c); return 'ok'
        except Exception as e: time.sleep(5)
    return 'fail '+name
with ThreadPoolExecutor(3) as ex:
    for i,res in enumerate(ex.map(one,allp)):
        if res!='ok' or i%25==0: print(i,res,flush=True)
print('DONE',flush=True)
