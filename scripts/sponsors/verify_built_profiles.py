
import json,glob,os,re,sys,time,requests,concurrent.futures as cf
import xml.etree.ElementTree as ET
S=sys.argv[1]; PF=S+'repo/data/people-former/'
T={"house-bill":"hr","senate-bill":"s","house-joint-resolution":"hjres","senate-joint-resolution":"sjres","house-resolution":"hres","senate-resolution":"sres","house-concurrent-resolution":"hconres","senate-concurrent-resolution":"sconres"}
UP={"hr":"HR","s":"S","hjres":"HJRES","sjres":"SJRES","hres":"HRES","sres":"SRES","hconres":"HCONRES","sconres":"SCONRES"}
H={"User-Agent":"KnowUS data (knowus.tab.bot)"}
def get(u,p):
    if os.path.exists(p) and os.path.getsize(p)>300: return open(p,'rb').read()
    for k in range(4):
        try:
            r=requests.get(u,headers=H,timeout=30)
            if r.status_code==200: open(p,'wb').write(r.content); return r.content
            if r.status_code==404: return None
        except Exception: pass
        time.sleep(2+3*k)
    return None
def norm(s): return re.sub(r'\s+',' ',s).strip().lower()
items=[]
people={}
for f in sorted(glob.glob(PF+'profiles-full/*.json')):
    d=json.load(open(f)); people[d['id']]=d
    for iss in d.get('issues',[]):
        for it in iss['items']: items.append((d['id'],it))
    for it in d.get('record',[]): items.append((d['id'],it))
extra=json.load(open(S+'repo/data/people-extra.json'))
def chk(x):
    pid,it=x; src=it['src']; k=it['k']
    try:
        if k=='vote':
            m=re.search(r'clerk\.house\.gov/Votes/(\d{4})(\d+)$',src)
            if m:
                y,n=m.group(1),int(m.group(2))
                raw=get("https://clerk.house.gov/evs/%s/roll%03d.xml"%(y,n), S+'rc/h%s_%d.xml'%(y,n))
                if not raw: return pid,it,'NOXML'
                r=ET.fromstring(raw); v=None
                for rv in r.iter('recorded-vote'):
                    if rv.find('legislator').get('name-id')==pid: v=rv.find('vote').text
                yea=sum(int(e.text) for e in r.find('.//totals-by-vote').iter('yea-total')) if r.find('.//totals-by-vote') is not None else None
                nay=sum(int(e.text) for e in r.find('.//totals-by-vote').iter('nay-total')) if r.find('.//totals-by-vote') is not None else None
                legis=r.findtext('.//legis-num') or ''
                res=r.findtext('.//vote-result') or ''
            else:
                m=re.search(r'vote_(\d+)_(\d)_(\d+)\.htm',src)
                c,s_,n=m.groups()
                raw=get(src.replace('.htm','.xml'), S+'rc/s_vote_%s_%s_%s.xml'%(c,s_,n))
                if not raw: return pid,it,'NOXML'
                r=ET.fromstring(raw); v=None
                st=extra['people'][pid]['r'].split(' from ')[-1] if pid in extra.get('people',{}) else ''
                last=people[pid]['n'].split()[-1]
                for mm in r.iter('member'):
                    if mm.findtext('last_name')==last and mm.findtext('state')=={'South Carolina':'SC'}.get(st,mm.findtext('state')): v=mm.findtext('vote_cast')
                yea=int(r.findtext('.//count/yeas')); nay=int(r.findtext('.//count/nays'))
                legis=(r.findtext('.//document/document_type') or '')+' '+(r.findtext('.//document/document_number') or '')
                res=r.findtext('vote_result') or ''
            q=it.get('q','')
            cast=q.split(':')[-1].strip()
            errs=[]
            if v is None: errs.append('member not in roll')
            elif norm(v)!=norm(cast): errs.append('cast %s vs xml %s'%(cast,v))
            mt=re.search(r'(\d+)[–-](\d+)',it['t'])
            if mt and yea is not None and (int(mt.group(1)),int(mt.group(2)))!=(yea,nay): errs.append('totals %s vs %d-%d'%(mt.group(0),yea,nay))
            if 'voted for' in it['t'].lower() and v and norm(v) not in('yea','aye'): errs.append('t says for but '+v)
            if re.search(r'voted (no|against)',it['t'].lower()) and v and norm(v) not in('nay','no'): errs.append('t says no but '+v)
            if re.search(r'\bPassed\b',it['t']) and res and not re.search(r'pass|agreed',res,re.I): errs.append('result '+res)
            if re.search(r'\bFailed\b',it['t']) and res and re.search(r'pass|agreed',res,re.I) and 'not' not in res.lower(): errs.append('result '+res)
            numq=re.sub(r'\W','',q.split('·')[0]).upper(); numx=re.sub(r'\W','',legis).upper()
            if numq and numx and numq!=numx: errs.append('bill %s vs %s'%(numq,numx))
            return pid,it,('OK' if not errs else 'BAD '+'; '.join(errs))
        else:
            m=re.search(r'/bill/(\d+)th-congress/([a-z-]+)/(\d+)',src)
            c,ty,n=m.group(1),T[m.group(2)],m.group(3)
            raw=get("https://www.govinfo.gov/bulkdata/BILLSTATUS/%s/%s/BILLSTATUS-%s%s%s.xml"%(c,ty,c,ty,n), S+'bs/US-%s-%s%s.xml'%(c,UP[ty],n))
            if not raw: return pid,it,'NOXML'
            r=ET.fromstring(raw); b=r.find('bill')
            sp=[e.findtext('bioguideId') for e in b.find('sponsors').findall('item')]
            errs=[]
            if pid not in sp: errs.append('sponsor %s'%sp)
            titles=' | '.join(t.text or '' for t in b.iter('title'))
            mt=re.search(r'Sponsored (?:the )?(.*?) \((?:[HS]\.|H\.R|S\.)',it['t'])
            if mt and norm(mt.group(1)) not in norm(titles): errs.append('title "%s" not in %s'%(mt.group(1),titles[:200]))
            if 'introducedDate' in raw.decode('utf8','ignore'):
                idt=b.findtext('introducedDate')
                if 'Introduced' in it.get('q','') and idt not in it['q']: errs.append('introduced %s'%idt)
            if k=='law':
                laws=[(l.findtext('type'),l.findtext('number')) for l in b.findall('laws/item')]
                ml=re.search(r'Public Law (\d+-\d+)',it['t'])
                if ml and not any(x[1]==ml.group(1) for x in laws): errs.append('law %s vs %s'%(ml.group(1),laws))
            return pid,it,('OK' if not errs else 'BAD '+'; '.join(errs))
    except Exception as e:
        return pid,it,'ERR %r'%e
out=[]
with cf.ThreadPoolExecutor(3) as ex:
    for pid,it,st in ex.map(chk,items):
        out.append({'id':pid,'src':it['src'],'t':it['t'],'st':st}); print(pid,st,it['src'],flush=True)
json.dump(out,open(S+'verify_profiles.json','w'),indent=0)
# bios2 quotes vs bioguide text
bad=0
for f in glob.glob(PF+'bios2/*.json'):
    d=json.load(open(f)); pid=os.path.basename(f)[:-5]
    txt=norm(open(S+'bgtxt/%s.txt'%pid).read())
    for kk,v in d.get('src',{}).items():
        if norm(v['quote']) not in txt: bad+=1; print('BIOQ BAD',pid,kk,v['quote'],flush=True)
print('BIOQ bad',bad); print('DONE',flush=True)
