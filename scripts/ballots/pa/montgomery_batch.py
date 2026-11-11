
import json,sys,os,subprocess,gzip,re
sys.path.insert(0,sys.argv[1]); import dparse
MB=sys.argv[1]; out={}
lst=json.load(open(MB+'/list.json'))
os.makedirs(MB+'/txt',exist_ok=True)
for i,(m,p) in enumerate(lst):
    name=p.split('/')[-1][:-4]; f=MB+'/pdf/'+name+'.pdf'
    try:
        res,left,L=dparse.parse(f); res=dparse.finish(res)
        txt=subprocess.run(['timeout','-k','2','30','pdftotext','-layout',f,'-'],capture_output=True,text=True).stdout
        gzip.open(MB+'/txt/'+name+'.txt.gz','wt').write(txt)
        chk={'vote_for':txt.count('(Vote for'),'yes':len(re.findall(r'^\s*YES\b',txt,re.M)),'writein':txt.count('Write-In'),
             'hdr':re.search(r'^(.*?) - (\d{6})\s+Montgomery County Board',txt,re.M).groups() if re.search(r'^(.*?) - (\d{6})\s+Montgomery County Board',txt,re.M) else None,
             'ballot_id':(re.search(r'Ballot ID: (\d+)',txt) or [None,None])[1]}
        out[name]={'muni':m,'url':'https://webapp07.montcopa.org/voterservices/sampleballots/'+p.replace(' ','%20'),'contests':res,'left':[(l['p'],l['c'],l['t']) for l in left],'chk':chk}
    except Exception as e:
        out[name]={'muni':m,'error':repr(e)}
    if i%50==0: print(i,flush=True)
json.dump(out,open(MB+'/parsed.json','w'))
print('DONE',len(out),flush=True)
