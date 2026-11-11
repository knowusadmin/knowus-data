# Smith County TX: check every sub-precinct's printed ballot style against the county's 2026 voting-districts layer.
# python3 smith_verify.py data/ballots/tx-smith-2026-11-03.json  -> prints mismatches (expect 0)
import json,re,sys,requests
U="https://services3.arcgis.com/dPuMck04cWB2fx4h/arcgis/rest/services/GenericDistrictsFall_2026_1110_WFL1/FeatureServer/3/query"
d=json.load(open(sys.argv[1]))
A={f['attributes']['PrecSub']:f['attributes'] for f in requests.get(U,params=dict(where='1=1',outFields='*',returnGeometry='false',f='json',resultRecordCount=2000),timeout=60).json()['features']}
def idx(title,dist=None):
    return [i for i,c in enumerate(d['c']) if c['title']==title and (dist is None or c['d']==dist)]
REP={'5':idx('State Representative','District 5')[0],'6':idx('State Representative','District 6')[0]}
COM={'2':idx('County Commissioner','Precinct No. 2')[0],'4':idx('County Commissioner','Precinct No. 4')[0]}
JP={n:idx('Justice of the Peace','Precinct No. %s'%n)[0] for n in '12345'}
ESD={}
for i,c in enumerate(d['c']):
    m=re.match(r'Smith County Emergency Services District No\. (\d) Commissioner',c['title'])
    if m: ESD[(m[1],c['d'].split()[-1])]=i
ARP=[i for i,c in enumerate(d['c']) if c['title'].startswith('City of Arp')][0]
bad=0
for k,s in d['s'].items():
    if not s['ok']: print('no ballot printed:',k); continue
    o=set(s['o']); f=A[k]; want=set(d['common'])
    want.add(REP[f['STREP'].strip()[-1]])
    cp=f['COMM'].strip()[-1]
    if cp in COM: want.add(COM[cp])
    want.add(JP[f['JP'].strip()[-1]])
    m=re.match(r'ESD (\d) - Fire District ?(\d)',(f['EDSM'] or '').strip())
    if m and (m[1],m[2]) in ESD: want.add(ESD[(m[1],m[2])])
    if (f['CITY'] or '').strip()=='Arp': want.add(ARP)
    if o!=want: bad+=1; print('MISMATCH',k,sorted(o^want))
print('mismatches',bad,'of',len(d['s']))
