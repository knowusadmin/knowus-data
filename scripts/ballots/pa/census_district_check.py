
import requests,json,sys
from concurrent.futures import ThreadPoolExecutor
pts=json.load(open(sys.argv[1]+'/pts.json'))
U='https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/identify'
def q(p):
    k,xy=p
    if not xy: return [k,None]
    for a in range(3):
        try:
            j=requests.get(U,params={'geometry':f'{xy[0]},{xy[1]}','geometryType':'esriGeometryPoint','sr':'4326','layers':'all','tolerance':'0','mapExtent':f'{xy[0]-0.01},{xy[1]-0.01},{xy[0]+0.01},{xy[1]+0.01}','imageDisplay':'400,400,96','returnGeometry':'false','f':'json'},timeout=40).json()
            return [k,[(r['layerName'],r['attributes'].get('BASENAME') or r['attributes'].get('NAME')) for r in j.get('results',[])]]
        except Exception as e: err=repr(e)
    return [k,'ERR '+err]
with ThreadPoolExecutor(3) as ex: out=list(ex.map(q,pts))
json.dump(out,open(sys.argv[1]+'/tiger.json','w')); print('DONE',len(out))
