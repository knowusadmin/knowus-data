
import html,json,os,subprocess,requests,time,concurrent.futures as cf,gzip,shutil
NC=os.path.dirname(os.path.abspath(__file__))
keys=[[html.unescape(k),s] for k,s in json.load(open(f'{NC}/sb_keys.json'))]
B="https://s3.amazonaws.com/dl.ncsbe.gov/"
def free_gb():
    s=shutil.disk_usage('/home/user'); return s.free/1e9
def one(k):
    name=k.split('/')[-1][:-4]
    out=f'{NC}/sbtxt/{name}.txt.gz'
    if os.path.exists(out): return 'skip'
    tmp=f'{NC}/tmp/{name}.pdf'
    for a in range(3):
        try:
            r=requests.get(B+k.replace(' ','%20').replace("'",'%27').replace('&','%26'),timeout=30)
            if r.status_code==200 and r.content[:4]==b'%PDF':
                open(tmp,'wb').write(r.content); break
        except Exception as e: pass
        time.sleep(2)
    else: return 'fail'
    try:
        t1=subprocess.run(['timeout','-k','5','60','pdftotext',tmp,'-'],capture_output=True,text=True,timeout=70).stdout
        t2=subprocess.run(['timeout','-k','5','60','pdftotext','-layout',tmp,'-'],capture_output=True,text=True,timeout=70).stdout
    finally:
        os.remove(tmp)
    with gzip.open(out,'wt') as f: f.write(t1+'\n\f=====LAYOUT=====\f\n'+t2)
    return 'ok'
done=0;st={}
with cf.ThreadPoolExecutor(3) as ex:
    for i,res in enumerate(ex.map(one,[k for k,s in keys if k.endswith('.pdf')])):
        st[res]=st.get(res,0)+1
        if i%50==0:
            print(i,st,round(free_gb(),2),flush=True)
            if free_gb()<1.6: print('LOW DISK, stopping',flush=True); os._exit(2)
print('DONE',st,flush=True)
