
import json,sys,os,subprocess,gzip,re
D=sys.argv[1]; sys.path.insert(0,D); import dparse
out={}; lst=json.load(open(D+'/list.json')); os.makedirs(D+'/txt',exist_ok=True)
for i,(n,u) in enumerate(lst):
    f=D+'/pdf/'+n+'.pdf'
    try:
        res,left,L=dparse.parse(f)
        txt=subprocess.run(['timeout','-k','2','30','pdftotext','-layout',f,'-'],capture_output=True,text=True).stdout
        gzip.open(D+'/txt/'+n+'.txt.gz','wt').write(txt)
        hdr=re.search(r'2026 General Election\s+(.+?)\s*$',txt,re.M)
        chk={'vote':txt.count('(Vote'),'yes':len(re.findall(r'^\s*Yes\s*$',txt,re.M))+len(re.findall(r'\s{3}Yes\s*$',txt,re.M)),'writein':txt.count('Write-in'),'nums':len(re.findall(r'\(\d{2,3}\)',txt)),'hdr':hdr.group(1).strip() if hdr else None,'pages':txt.count('\f')}
        out[n]={'url':u,'contests':res,'left':[(l['p'],l['c'],l['t']) for l in left],'chk':chk}
    except Exception as e: out[n]={'url':u,'error':repr(e)}
    if i%50==0: print(i,flush=True)
json.dump(out,open(D+'/parsed.json','w')); print('DONE',len(out),flush=True)
