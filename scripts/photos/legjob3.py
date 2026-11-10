
import sys,json,csv,io,os,time,glob,traceback
sys.path.insert(0,'/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'); from photolib import *
from concurrent.futures import ThreadPoolExecutor
S='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/final/site'; STG='/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46'; os.makedirs(STG+'/os',exist_ok=True); os.makedirs(STG+'/contact_leg',exist_ok=True)
def log(*a): print(time.strftime('%H:%M:%S'),*a,flush=True)
def dnorm(s): return re.sub(r'(senatorial|representative|assembly|legislative|house|senate)?\s*district|^district\s*','',norm(s)).strip().lstrip('0')
for f in [x for x in sorted(glob.glob(S+'/data/local/*.json')) if os.path.basename(x)[:2] in (sys.argv[1:] or [os.path.basename(x)[:2]])]:
    st=os.path.basename(f)[:2]
    try:
        cf=STG+'/os/'+st+'.csv'
        if not os.path.exists(cf):
            r=fetch('https://data.openstates.org/people/current/%s.csv'%st.lower(),H,30)
            open(cf,'w').write(r.text if r.status_code==200 else '')
        rows=list(csv.DictReader(open(cf)))
        d=json.load(open(f)); leg=d.get('leg') or {}
        prev=json.load(open(STG+'/leg/'+st+'.json')) if os.path.exists(STG+'/leg/'+st+'.json') else {}
        res={}; contact={}; jobs=[]
        for ch,dd in leg.items():
            for dist,L in dd.items():
                for m in L:
                    key=ch+dist+'-'+slug(m['n']); f_,l_=nameparts(m['n'])
                    chs={'U':('upper','legislature'),'L':('lower',)}[ch] if ch in 'UL' else ('upper','lower','legislature')
                    pool=[x for x in rows if x['current_chamber'] in chs]
                    hit=[x for x in pool if dnorm(x['current_district'])==dnorm(dist) and nameparts(x['name'])[1]==l_]
                    if not hit: hit=[x for x in pool if nameparts(x['name'])==(f_,l_)]
                    if not hit: hit=[x for x in pool if nameparts(x['name'])[1]==l_ and norm(x.get('given_name',''))[:3]==f_[:3]]
                    if len(hit)!=1:
                        res[key]=prev.get(key) if prev.get(key,{}).get('f') else {'n':m['n'],'miss':'no unique openstates match (%d)'%len(hit)}; continue
                    h=hit[0]
                    contact[key]={k:h.get(k,'') for k in ['email','capitol_address','capitol_voice','district_address','district_voice','twitter','facebook','instagram','youtube','links']}
                    contact[key]['n']=m['n']
                    if prev.get(key,{}).get('f') and os.path.exists(STG+'/img/'+st+'/'+prev[key]['f']): res[key]=prev[key]; continue
                    if not h.get('image'): res[key]={'n':m['n'],'miss':'no image in openstates'}; continue
                    jobs.append((key,m,h))
        def one(a):
            key,m,h=a; u=h['image']
            if BAN.search(u): return key,{'n':m['n'],'miss':'image on banned host'}
            p,info=make_photo(u,key,out=STG+'/img/'+st)
            if not p: return key,{'n':m['n'],'miss':info,'img':u}
            return key,{'n':m['n'],'f':key+'.webp','src':m.get('u') or u,'img':u,'kb':round(info/1024,1)}
        os.makedirs(STG+'/img/'+st,exist_ok=True)
        with ThreadPoolExecutor(2) as ex:
            for key,v in ex.map(one,jobs): res[key]=v
        json.dump(res,open(STG+'/leg/'+st+'.json','w'),indent=0); json.dump(contact,open(STG+'/contact_leg/'+st+'.json','w'),indent=0)
        log(st,'members',len(res),'photos',sum(1 for v in res.values() if 'f' in v),'contact',len(contact))
    except Exception: log(st,'ERR',traceback.format_exc()[-400:])
log('DONE')
