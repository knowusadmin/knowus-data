
import json,sys,time,requests
BX=sys.argv[1]; GC='https://maps.bexar.org/arcgis/rest/services/Locators/BeCoMultiRole/GeocodeServer/findAddressCandidates'
s=requests.Session(); s.headers['User-Agent']='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130'
out=[]
for j in json.load(open(BX+'/verify_jobs.json')):
    c=None
    for i in range(4):
        try: c=s.get(GC,params={'SingleLine':j['a'],'outSR':4326,'f':'json','maxLocations':1},timeout=60).json().get('candidates',[]); break
        except Exception as e: time.sleep(4*(i+1))
    j['c']=c[0] if c else None; out.append(j); time.sleep(0.15)
    if len(out)%200==0: print(len(out),flush=True); json.dump(out,open(BX+'/verify_geo.part.json','w'))
json.dump(out,open(BX+'/verify_geo.json','w')); print('DONE',flush=True)
