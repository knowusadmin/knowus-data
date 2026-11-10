
import sys,json,os,time,glob
sys.path.insert(0,'/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'); from photolib import *
from concurrent.futures import ThreadPoolExecutor
S='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/final/site'; STG='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'
def log(*a): print(time.strftime('%H:%M:%S'),*a,flush=True)
for st in sys.argv[1:]:
    d=json.load(open(S+'/data/local/'+st+'.json'))
    groups={}
    for pk,e in [('c'+c['f'],c) for c in d['counties']]+list(d['places'].items()):
        offs=[o for o in e.get('o',[]) if o.get('g')!='b']
        for o in offs: groups.setdefault(o.get('u'),[]).append((pk,o,[x['n'] for x in offs]))
    def one(a):
        u,items=a; out={}
        if not u: return out
        try:
            r=requests.get(u,headers=H,timeout=10,verify=False)
            if r.status_code!=200: return out
            soup=bs4.BeautifulSoup(r.text,'lxml')
        except Exception: return out
        for pk,o,names in items:
            ct=contacts_for(soup,r.url,o['n'],names)
            if ct: out[pk+'-'+slug(o['n'])]=dict(ct,n=o['n'])
        return out
    C={}
    with ThreadPoolExecutor(2) as ex:
        for c_ in ex.map(one,groups.items()): C.update(c_)
    json.dump(C,open(STG+'/contact_local/'+st+'.json','w'),indent=0); log(st,'contacts',len(C))
log('DONE')
