
import sys,json,os;sys.path.insert(0,'/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46');from photolib import *
M=json.load(open('/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/photos46/manual.json')); out={}
for k,v in M.items():
    st,key=k.split('|'); os.makedirs(STG+'/img/'+st,exist_ok=True)
    if os.path.exists(STG+'/img/'+st+'/'+key+'.webp') and v.get('done'): continue
    p,info=make_photo(v['img'],key,referer=v['src'],need_face=not v.get('noface'),max_faces=v.get('maxf',1),out=STG+'/img/'+st)
    print(k,p and 'OK',info)
