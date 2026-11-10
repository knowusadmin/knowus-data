
import sys,json,os;sys.path.insert(0,'/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46');from photolib import *
from concurrent.futures import ThreadPoolExecutor
inp,outj=sys.argv[1],sys.argv[2]
rows=[json.loads(l) for l in open(inp)]
res=json.load(open(outj)) if os.path.exists(outj) else {}
PH=re.compile(r'SubmitPhoto|BP-Initials|Silhouette|placeholder|Default|NoImage|no_image|BallotpediaLogo',re.I)
def one(b):
    k=b['key']
    if k in res and res[k].get('f'): return k,res[k]
    if not b.get('img'): return k,{'n':b['n'],'miss':'no ballotpedia page with photo matching name+office','tried':b.get('tried')}
    if PH.search(b['img']): return k,{'n':b['n'],'miss':'ballotpedia has no photo (placeholder)','u':b.get('url')}
    parts=k.split('|'); st=parts[0] if parts[0]!='P' else 'P'; key=parts[-1]
    d=STG+'/img/'+st; os.makedirs(d,exist_ok=True)
    p,info=make_photo(b['img'],key,referer=b.get('url'),out=d)
    if not p: return k,{'n':b['n'],'miss':'ballotpedia photo rejected: '+str(info),'u':b.get('url'),'img':b['img']}
    return k,{'n':b['n'],'f':key+'.webp','src':b['url'],'img':b['img'],'ib':b.get('ib','')[:120],'kb':round(info/1024,1)}
with ThreadPoolExecutor(2) as ex:
    for k,v in ex.map(one,rows): res[k]=v
json.dump(res,open(outj,'w'),indent=0)
print(len(res),'ok',sum(1 for v in res.values() if v.get('f')))
