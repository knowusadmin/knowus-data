# Fort Bend County TX: check every printed ballot style's districts against the county's official precinct layer
# (Voter Precincts 2025: US House, State Senate, State House, SBOE, Commissioner precinct). Expect 0 mismatches.
# python3 fortbend_verify.py data/ballots/tx-fortbend-2026-11-03.json
import json,re,sys,requests
U="https://gisportal.fortbendcountytx.gov/arcgis/rest/services/InteractiveMap/Elections_Public/MapServer/1/query"
d=json.load(open(sys.argv[1]))
A={f['attributes']['PRECINCTID']:f['attributes'] for f in requests.get(U,params=dict(where='1=1',outFields='*',returnGeometry='false',f='json'),timeout=60).json()['features']}
bad=0
for k,s in d['s'].items():
    if not s['ok']: print('labelled, no single printed style:',k); continue
    a=A[s['p']]; got={}
    for i in s['o']:
        c=d['c'][i]; m=re.search(r'(\d+)',c.get('d','') or '') or re.search(r'District (\d+)$',c['title'])
        for key,pre in (('cd','United States Representative'),('sd','State Senator'),('hd','State Representative'),('sboe','Member, State Board'),('comm','County Commissioner')):
            if c['title'].startswith(pre) and m: got[key]=m[1]
    n=lambda v:str(int(float(v)))
    want={'cd':n(a['FED_CONGRE']),'hd':n(a['STATE_REP_']),'sboe':n(a['STATE_BOAR'])}
    if 'sd' in got: want['sd']=n(a['STATE_SENA'])
    if str(a['COMM_PRECI']) in ('2','4'): want['comm']=str(a['COMM_PRECI'])
    if got!=want: bad+=1; print('MISMATCH',k,got,want)
print('mismatches',bad,'of',sum(1 for s in d['s'].values() if s['ok']))
