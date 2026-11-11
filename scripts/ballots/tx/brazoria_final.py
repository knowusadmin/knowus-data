
import json,sys
D=sys.argv[1]; R=sys.argv[2]
B=json.load(open(D+'/bz-build.json'))
COM=None
for v in B['S'].values():
    v.pop('common',None) if v['ok'] else None
common=sorted(set.intersection(*[set(v['o']) for v in B['S'].values() if v['ok']]))
out=dict(read='2026-11-11',county='Brazoria County, Texas',
 source='Brazoria County Clerk, Elections Division — official sample ballot for every precinct (Nov 3, 2026 General & Joint Election, “Sample Ballots (Boletas de Muestra)”, 89 precinct ballots), placed by the county’s 2026 voter precinct map and, where a precinct has more than one printed ballot, the county’s city limits (City of Freeport) and school district (Sweeny ISD) boundaries',
 sourceUrl='https://www.brazoriacountyclerktx.gov/departments/elections/sample-ballots',
 lookup='https://www.brazoriacountyclerktx.gov/departments/elections/sample-ballots',
 office='Brazoria County Clerk, Elections Division',c=B['C'],s=B['S'],common=common)
json.dump(out,open(R+'/data/ballots/tx-brazoria-2026-11-03.json','w'),ensure_ascii=False,separators=(',',':'))
geo=dict(v=1,source=['Brazoria County, Texas — Voter Precincts 2026 from the Brazoria County GIS (maps.brazoriacountytx.gov, Political Boundaries), split where a precinct has more than one printed ballot by the county’s City Limits (City of Freeport) and School Districts (Sweeny ISD) layers','https://maps.brazoriacountytx.gov/arcgis/rest/services/general/Political_Boundaries/MapServer/11','2026-11-11'],
 scale=100000.0,note='Each polygon is a precinct, or the part of a precinct that gets one of its printed ballots. Precinct 84 (a sliver with no county address points) has no printed ballot posted; it shows the races on every ballot in the county and the official sample ballot link. Smallest first.',p=B['geo'])
json.dump(geo,open(R+'/data/ballots/tx-brazoria-precincts.json','w'),ensure_ascii=False,separators=(',',':'))
print('ok',len(out['s']),len(out['c']),len(geo['p']),len(common))
