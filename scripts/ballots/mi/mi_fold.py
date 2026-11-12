
# Fold the Michigan ballots into a KnowUS site build (worker 448daed7's hand-off). Idempotent.
#   python3 mi_fold.py OUTDIR SITE_DIR
# Copies OUTDIR/mi-*-2026-11-03.json + mi-*-precincts.json into SITE/data/ballots/ and patches SITE/ballot.js:
#  1. one PAC entry per Michigan county (st:'MI', loaded per county like the TX/PA/OH/FL counties)
#  2. paBallot: the full-ballot link says "(PDF)" only when the link is a PDF (Michigan's is the state's ballot page)
#  3. paBallot: a labelled part with its own reason (S.why) says that reason instead of "couldn't be matched"
#  4. paBallot: "All <county> sample ballots" also drops ", Michigan"
import sys,os,re,json,glob,shutil
O,S=sys.argv[1],sys.argv[2]
B=S+'/ballot.js'; js=open(B,encoding='utf-8').read(); orig=js
files=sorted(glob.glob(O+'/mi-*-2026-11-03.json'))
ent=[]
for f in files:
    sl=re.match(r'mi-(.+)-2026-11-03\.json',os.path.basename(f))[1]
    d=json.load(open(f)); cn=d['county'].replace(' County, Michigan','')
    rx=re.escape(cn.lower()).replace('st\\.\\ ','(?:st\\.? ?|saint )').replace('\\ ',' ').replace('\\-','-')
    ent.append("mi%s:{st:'MI',f:'mi-%s-2026-11-03.json',g:'mi-%s-precincts.json',re:/^%s(?: county)?$/i,d:null,geo:null,pick:{}}"%(sl,sl,sl,rx))
    for g in (f,f.replace('-2026-11-03.json','-precincts.json')): shutil.copyfile(g,S+'/data/ballots/'+os.path.basename(g))
if 'mialcona:{' not in js:
    i=js.index('var PAC={'); j=js.index('}};',i)
    js=js[:j+1]+',\n  /* Michigan (MVIC per-precinct ballots, v-next) */\n  '+',\n  '.join(ent)+'};'+js[j+3:]
a="fullLink:{label:'Official sample ballot (PDF)',url:S.pdf,sub:D.office+' \\u2014 '+key}"
if a in js: js=js.replace(a,"fullLink:{label:/\\.pdf(\\?|$)/i.test(S.pdf)?'Official sample ballot (PDF)':'Official sample ballot',url:S.pdf,sub:D.office+' \\u2014 '+key}")
b="coverage:'Your address couldn\\u2019t be matched to one of the county\\u2019s voting districts'"
if b in js and 'raw.why' not in js: js=js.replace(b,"coverage:(raw&&raw.why)?'Your precinct ('+key+') has '+raw.why+', so only the races confirmed for your address are shown. Your official sample ballot has the rest.':'Your address couldn\\u2019t be matched to one of the county\\u2019s voting districts'")
c="D.county.replace(/, (Pennsylvania|Ohio|Florida)$/,'')"
if c in js: js=js.replace(c,"D.county.replace(/, (Pennsylvania|Ohio|Florida|Michigan)$/,'')")
assert js.count('mialcona:{')==1 and 'raw.why' in js and 'Florida|Michigan' in js and ":'Official sample ballot'," in js
if js!=orig: open(B,'w',encoding='utf-8').write(js)
print('ok',len(files),'counties; ballot.js',len(orig),'->',len(js))
