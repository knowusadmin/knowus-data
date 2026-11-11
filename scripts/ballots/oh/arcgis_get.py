
import requests,json,sys
u=sys.argv[1]; out=sys.argv[2]
feats=[];off=0
while True:
    j=requests.get(u+'/query',params={'where':'1=1','outFields':'*','outSR':'4326','geometryPrecision':'6','maxAllowableOffset':'0.00003','f':'json','resultOffset':off,'resultRecordCount':1000},timeout=120).json()
    feats+=j['features']; print(len(feats),flush=True)
    if not j.get('exceededTransferLimit'): break
    off+=len(j['features'])
json.dump({'features':feats},open(out,'w')); print('DONE',flush=True)
