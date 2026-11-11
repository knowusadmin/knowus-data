
import requests,json,sys
fs='https://services.arcgis.com/JyZag7oO4NteHGiq/arcgis/rest/services/Open_Data_Feature_Collection/FeatureServer/41/query'
j=requests.get(fs,params={'where':'1=1','outFields':'OBJECTID,PRECINCT,PRC_NAME','outSR':'4326','geometryPrecision':'6','maxAllowableOffset':'0.00003','f':'json'},timeout=120).json()
json.dump(j,open(sys.argv[1]+'/geo-raw.json','w')); print(len(j['features']),j.get('exceededTransferLimit'),flush=True)
