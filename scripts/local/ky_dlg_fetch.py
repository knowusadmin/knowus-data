
import requests,re,json,time,sys,os
from concurrent.futures import ThreadPoolExecutor
OUT=sys.argv[1]
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'}
S=requests.Session();S.headers.update(UA)
B='https://kydlgweb.ky.gov/Cities/'
S.get(B+'16_CityHome.cfm',timeout=40)
def cl(gt):
    y=S.post(B+'16_CityList.cfm',data={'City_Name':'','County':'','AreaDevDist':'','Gov_Type':gt,'Appalachia':'','Delta_Region':'','button':'SEARCH'},headers={'Referer':B+'16_CityHome.cfm'},timeout=120)
    out=[]
    for rw in re.findall(r'<tr[^>]*>(.*?)</tr>',y.text,re.S):
        cells=[re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',c)).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>',rw,re.S)]
        idm=re.search(r'City_ID=(\d+)',rw)
        if idm: out.append({'id':int(idm.group(1)),'n':cells[0],'county':cells[1],'pop':cells[2],'gt':gt})
    print('list',gt,y.status_code,len(out),flush=True)
    return out
L=[]
for gt in ['City Manager','Commission','Mayor/Council','Urban County']:
    for k in range(3):
        try: L+=cl(gt);break
        except Exception as e: print('ERR list',gt,e,flush=True);time.sleep(5)
json.dump(L,open(OUT+'/list.json','w'))
def tx(s): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s)).replace('&amp;','&').replace('&nbsp;',' ').strip()
def one(c):
    fn=OUT+'/v/%d.json'%c['id']
    if os.path.exists(fn): return
    for k in range(3):
        try:
            z=S.get(B+'16_CityView.cfm?City_ID=%d'%c['id'],timeout=60)
            if z.status_code!=200: raise Exception('status %d'%z.status_code)
            h=z.text
            hdr={}
            for lab,val in re.findall(r'<td[^>]*>\s*(?:<[^>]+>\s*)*([A-Za-z.\- ]+):\s*(?:<[^>]+>\s*)*</td>\s*<td[^>]*>(.*?)</td>',h,re.S):
                hdr[lab.strip()]=tx(val)
            # first officials table (with EMAIL)
            i=h.find('FIRST NAME')
            j=h.find('FIRST NAME',i+10)
            seg=h[i:j if j>0 else len(h)]
            offs=[]
            for rw in re.findall(r'<tr[^>]*>(.*?)</tr>',seg,re.S):
                cells=[tx(x) for x in re.findall(r'<td[^>]*>(.*?)</td>',rw,re.S)]
                cells=[x for x in cells]
                if len(cells)>=3 and cells[0]!='FIRST NAME':
                    offs.append(cells)
            web=re.findall(r'href="(https?://[^"]+)"',h)
            json.dump({'c':c,'hdr':hdr,'offs':offs,'links':web,'raw_len':len(h)},open(fn,'w'))
            return
        except Exception as e:
            print('ERR',c['id'],e,flush=True);time.sleep(4)
os.makedirs(OUT+'/v',exist_ok=True)
with ThreadPoolExecutor(2) as ex: list(ex.map(one,L))
print('DONE',len(L),flush=True)
