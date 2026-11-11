
import requests,json,time
U="https://maps.brazoriacountytx.gov/arcgis/rest/services/general/Address_Points/MapServer/0/query"; out=[]; off=0
while True:
    for i in range(5):
        try: r=requests.get(U,params={"where":"1=1","outFields":"OBJECTID","returnGeometry":"true","outSR":4326,"f":"json","resultOffset":off,"resultRecordCount":2000,"orderByFields":"OBJECTID"},timeout=90).json(); break
        except Exception as e: r={}; time.sleep(4)
    fs=r.get("features",[])
    out+=[[round(f["geometry"]["x"],6),round(f["geometry"]["y"],6)] for f in fs if f.get("geometry") and isinstance(f["geometry"].get("x"),(int,float))]
    print(off,len(fs),flush=True)
    if len(fs)<2000: break
    off+=len(fs)
json.dump(out,open("/home/user/tab/tasks/93914f9e-9935-4bae-8cd6-b6d9b1159c1d/work/helpers/nation47/tx/brazoria/addrpts.json","w")); print("DONE",len(out),flush=True)
