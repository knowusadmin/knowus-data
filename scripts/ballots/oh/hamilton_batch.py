
import json,sys,os,subprocess,gzip,re
D=sys.argv[1]; sys.path.insert(0,D); import hparse
out={}; os.makedirs(D+'/txt',exist_ok=True)
fs=sorted(f for f in os.listdir(D+'/pdf') if f.endswith('.pdf'))
for i,fn in enumerate(fs):
    f=D+'/pdf/'+fn; n=fn[:-4]
    try:
        hdr,res,left,L=hparse.parse(f)
        txt=subprocess.run(['timeout','-k','2','30','pdftotext','-layout',f,'-'],capture_output=True,text=True).stdout
        gzip.open(D+'/txt/'+n+'.txt.gz','wt').write(txt)
        chk={'vote':txt.count('(Vote for'),'writein':txt.count('Write-in'),'yes':len(re.findall(r'\b(YES|FOR THE|FOR THE TAX LEVY|FOR THE BOND ISSUE|FOR)\b\s*$',txt,re.M))}
        out[n]={'hdr':hdr,'contests':res,'left':[(l['p'],l['c'],l['t'],l['s'],l['b']) for l in left],'chk':chk}
    except Exception as e: out[n]={'error':repr(e)}
    if i%50==0: print(i,flush=True)
json.dump(out,open(D+'/parsed.json','w')); print('DONE',len(out),flush=True)
