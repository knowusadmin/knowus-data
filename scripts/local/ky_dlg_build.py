#!/usr/bin/env python3
"""KnowUS local officials, Kentucky: build data/officials-local/KY.json from the Kentucky Department for Local
Government (DLG) city directory (kydlgweb.ky.gov, a state .gov source; each city's page lists the officials the city
reports to DLG on its City Officials Update Form). Owner's source policy: official sources only, names exactly as
printed, never invented.
usage: ky_dlg_build.py <dlg_dump_dir (list.json + v/<id>.json from ky_dlg fetch)> <site data/local/KY.json> <out.json>
Optional 4th arg: data/officials-local/manual/KY.json (hand-checked places from their own official site; they replace the DLG list).
In DLG's directory Blackey, Blaine, Blandville, Bonnieville, Monterey, Poplar Hills, Raywick, South Park View and Vicco are 'Dissolved'; they stay empty.
Kept roles: Mayor, City Council, City Commission (elected), City Manager, City Administrator, City Clerk.
Contacts (owner's local-contacts rules): a person's phone is kept only if it is the city office's own line; an email
only if it is on the city's own domain (never free mail / ISP mail); otherwise the city office's main line, address and
email are shown, marked as the office's main contact (g:1). No home addresses.
Places that already carry officials from the city's own website keep them; a DLG mayor that disagrees with the city
site's mayor is not added (the city site wins), and DLG people are added only when not already listed."""
import json,re,sys,glob,os,datetime as dt
from collections import Counter
dump,sitef,out=sys.argv[1:4]
MAN=json.load(open(sys.argv[4],encoding='utf-8'))['places'] if len(sys.argv)>4 else {}
TODAY=os.environ.get('KNOWUS_DATE') or dt.date.today().isoformat()
U='https://kydlgweb.ky.gov/Cities/16_CityView.cfm?City_ID=%d'
ROLE={'Mayor':('Mayor','gen_mayor',0),'City Council':('Council Member','gen_council',1),'City Commission':('City Commissioner','gen_council',1),
      'City Manager':('City Manager',None,2),'City Administrator':('City Administrator',None,3),'City Clerk':('City Clerk',None,4)}
FREE=set('gmail.com yahoo.com hotmail.com bellsouth.net outlook.com icloud.com aol.com windstream.net att.net twc.com ymail.com live.com msn.com comcast.net charter.net sbcglobal.net me.com mac.com frontier.com frontiernet.net roadrunner.com rr.com insightbb.com earthlink.net verizon.net mchsi.com prodigy.net juno.com netzero.net cox.net zoominternet.net spectrum.net kih.net tds.net brmemc.net hughes.net'.split())
def nm(s):
    s=s.lower().replace('city of ','').replace('st.','saint').replace('st ','saint ')
    return re.sub(r'[^a-z]','',s)
ALIAS={'middlesborough':'middlesboro','lexingtonfayette':'lexington'}
def digits(p): d=re.sub(r'\D','',p or ''); return d[-10:] if len(d)>=10 else ''
def fmt(d): return '(%s) %s-%s'%(d[:3],d[3:6],d[6:]) if len(d)==10 else ''
def fixcase(s):
    s=s.strip()
    if s.isupper() and len(s)>3: return s.title()
    return s[:1].upper()+s[1:] if s[:1].islower() else s
def host(u):
    m=re.match(r'https?://([^/]+)',u or ''); return m.group(1).lower().lstrip('www.') if m else ''
def base(h): 
    p=h.split('.'); return '.'.join(p[-2:]) if len(p)>=2 else h
def okmail(e,cityname,doms):
    if not e or '@' not in e or ' ' in e: return False
    d=e.split('@')[1].lower()
    if d in FREE or base(d) in FREE: return False
    if base(d) in doms: return True
    if d.endswith('.gov') or d.endswith('.ky.us'): return True
    return nm(cityname)[:6] in nm(d)   # city's own domain, e.g. alexandriaky.org, lagrangeky.net
V={}
for f in glob.glob(os.path.join(dump,'v','*.json')):
    v=json.load(open(f)); n=v['c']['n']
    if n.startswith('Z_'): continue
    V[nm(n)]=v
site=json.load(open(sitef,encoding='utf-8'))
res={'st':'KY','built':TODAY,'src':{'name':'Kentucky Department for Local Government, city directory (kydlgweb.ky.gov)','note':'Officials as each city reports them to the state on its City Officials Update Form; names exactly as printed.'},'places':{}}
stats={'cities':0,'matched':0,'filled_new':0,'added_to_existing':0,'officials':0,'no_dlg':[],'dlg_empty':[],'conflicts':[]}
for pid,p in site['places'].items():
    if p.get('t')=='CDP': continue
    stats['cities']+=1
    k=nm(p['n']);k=ALIAS.get(k,k); v=V.get(k)
    if not v: stats['no_dlg'].append(p['n']); continue
    stats['matched']+=1
    h=v['hdr']; off=digits(h.get('Phone')); cid=v['c']['id']
    cmail=h.get('e-Mail','').strip()
    doms={base(host(p.get('w','')))} - {''}
    if okmail(cmail,p['n'],doms): doms.add(base(cmail.split('@')[1].lower()))
    else: cmail=''
    addr=', '.join(x for x in [h.get('Address','').strip(), (h.get('City','').strip()+', KY '+h.get('Zip','').strip()).strip(', ')] if x)
    people={}
    used=Counter(o[4].strip().lower() for o in v['offs'] if len(o)>4 and o[4].strip())
    for o in v['offs']:
        first,last,title,ph,em=(o+['']*5)[:5]
        if title not in ROLE: continue
        name=re.sub(r'\s+',' ',(fixcase(first)+' '+fixcase(last))).strip()
        if not first.strip() or not last.strip() or re.search(r'vacan|tbd|n/a|none|unknown',name,re.I): continue
        r,rk,order=ROLE[title]
        if name in people:
            q=people[name]
            if r not in q['_rs']: q['_rs'].append((order,r))
            q['order']=min(q['order'],order); q['rk']=q['rk'] or rk
            if order==0: q['rk']='gen_mayor'
            continue
        ct={}
        pd=digits(ph)
        ct['p']=[fmt(off)] if off else []
        g=1
        if okmail(em,p['n'],doms): ct['e']=em.strip(); g = 1 if (em.strip().lower()==cmail.lower() or used[em.strip().lower()]>1) else 0
        elif cmail: ct['e']=cmail
        if not ct['p']: ct.pop('p')
        if addr: ct['a']=addr
        if p.get('w'): ct['w']=p['w']
        ct['src']=U%cid
        if g: ct['g']=1
        people[name]={'_rs':[(order,r)],'n':name,'r':r,'rk':rk,'src':'dlg','u':U%cid,'d':TODAY,'ct':ct,'order':order}
    L=sorted(people.values(),key=lambda x:(x['order'],x['n'].split()[-1]))
    for x in L:
        x.pop('order'); x['r']=' / '.join(r for _,r in sorted(set(x.pop('_rs'))))
    if not L: stats['dlg_empty'].append(p['n']); continue
    ex=[o for o in (p.get('o') or []) if o.get('src') not in ('dlg','dced','state')]  # ignore our own earlier fill (site file may already carry it)
    if ex:
        exm=[o for o in ex if o.get('rk')=='gen_mayor']
        exnames={nm(o['n']) for o in ex}
        def same(a,b): 
            a,b=a.split(),b.split(); return nm(a[-1])==nm(b[-1]) and nm(a[0])[:1]==nm(b[0])[:1]
        add=[]
        for x in L:
            if any(same(x['n'],o['n']) for o in ex): continue
            if exm and x['r'].startswith('Mayor'):
                stats['conflicts'].append({'place':p['n'],'site_mayor':exm[0]['n'],'site_url':exm[0].get('u'),'dlg_mayor':x['n'],'dlg_url':x['u']}); continue
            add.append(x)
        if not add: continue
        res['places'][pid]={'n':p['n'],'o':ex+add}; stats['added_to_existing']+=1; stats['officials']+=len(add)
    else:
        res['places'][pid]={'n':p['n'],'o':L}; stats['filled_new']+=1; stats['officials']+=len(L)
for pid,mp in MAN.items():
    if pid in site['places'] and site['places'][pid]['n']==mp['n']:
        res['places'][pid]=mp; stats['manual']=stats.get('manual',0)+1; stats['officials']+=len(mp['o'])
        if mp['n'] in stats['no_dlg']: stats['no_dlg'].remove(mp['n'])
DISS={'Blackey','Blaine','Blandville','Bonnieville','Monterey','Poplar Hills','Raywick','South Park View','Vicco'}
stats['dissolved_per_dlg']=sorted(x for x in stats['no_dlg'] if x in DISS)
stats['not_in_dlg']=sorted(x for x in stats['no_dlg'] if x not in DISS)

# compact: drop a contact block's website when it repeats the place's own site, and drop blocks with nothing to show
for pid,p in res['places'].items():
    w=p.get('w') or site['places'].get(pid,{}).get('w')
    for o in p['o']:
        ct=o.get('ct')
        if not ct: continue
        if o.get('src') in ('dced','dlg') and w and ct.get('w')==w: ct.pop('w')
        if not any(k in ct for k in ('p','e','f','a','w','s')): o.pop('ct')
res['stats']=stats
json.dump(res,open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(json.dumps({k:(v if not isinstance(v,list) else (len(v),v[:20])) for k,v in stats.items()}))
