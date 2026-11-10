
import sys,json,csv,io,os,time,glob,traceback
sys.path.insert(0,'/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'); from photolib import *
from concurrent.futures import ThreadPoolExecutor
S='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/final/site'; OUT='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'+'/leg'; os.makedirs(OUT,exist_ok=True)
def log(*a): print(time.strftime('%H:%M:%S'),*a,flush=True)
order=['OH']+[os.path.basename(f)[:2] for f in sorted(glob.glob(S+'/data/local/*.json')) if not f.endswith('OH.json')]
def do_state(st):
    outf=OUT+'/'+st+'.json'
    if os.path.exists(outf): return
    d=json.load(open(S+'/data/local/'+st+'.json')); leg=d.get('leg') or {}
    try:
        r=requests.get('https://data.openstates.org/people/current/%s.csv'%st.lower(),headers=H,timeout=30); rows=list(csv.DictReader(io.StringIO(r.text)))
    except Exception as e: log(st,'csv fail',e); rows=[]
    os_by={}
    for row in rows:
        ch={'upper':'U','lower':'L','legislature':'U'}.get(row['current_chamber'],'?')
        os_by.setdefault((ch,row['current_district'].strip()),[]).append(row)
    res={}; os.makedirs('/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'+'/img/'+st,exist_ok=True)
    jobs=[]
    for ch,dd in leg.items():
        for dist,L in dd.items():
            for m in L:
                cand=os_by.get((ch,dist)) or os_by.get((ch,dist.lstrip('0'))) or []
                f,l=nameparts(m['n']); hit=None
                for row in cand:
                    rf,rl=nameparts(row['name'])
                    if rl==l or (l and l in norm(row['name']).split()) or (norm(row.get('family_name','')).split()[-1:]==[l]): hit=row; break
                key=ch+dist+'-'+slug(m['n'])
                if not hit or not hit.get('image'): res[key]={'n':m['n'],'miss':'no openstates match' if not hit else 'no image in openstates'}; continue
                jobs.append((key,m,hit))
    def one(a):
        key,m,hit=a; u=hit['image']
        if BAN.search(u): return key,{'n':m['n'],'miss':'image on banned host'}
        p,info=make_photo(u,key,out='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'+'/img/'+st)
        if not p: return key,{'n':m['n'],'miss':info,'img':u}
        return key,{'n':m['n'],'f':key+'.webp','src':m.get('u') or u,'img':u,'kb':round(info/1024,1)}
    with ThreadPoolExecutor(2) as ex:
        for key,v in ex.map(one,jobs): res[key]=v
    json.dump(res,open(outf,'w'),indent=0)
    ok=sum(1 for v in res.values() if 'f' in v); log(st,'members',len(res),'photos',ok)
for st in order:
    try: do_state(st)
    except Exception: log(st,'ERR',traceback.format_exc()[-400:])
log('DONE')
