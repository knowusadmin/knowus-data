
import json,os,re,html,subprocess,requests,unicodedata
PH=os.path.dirname(os.path.abspath(__file__)); OUT=os.environ.get('PH_OUT',PH)
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36'}
SRC='https://vote.phila.gov/voting/candidates-for-office/'
h=requests.get(SRC,timeout=30,headers=UA).content.decode('utf-8')
def nz(s): return re.sub(r'[^A-Z0-9]','',unicodedata.normalize('NFKD',s or '').upper())
contests=[]; cur=None
for m in re.finditer(r'<h3>(.*?)</h3>|<li>(.*?)</li>',h,re.S):
    if m.group(1):
        t=html.unescape(re.sub(r'<[^>]+>','',m.group(1))).strip()
        mm=re.match(r'^(.*?) – (.*?) – (Vote for .*)$',t)
        if mm: cur={'office':mm.group(1),'dist':mm.group(2),'vf':mm.group(3),'c':[]}; contests.append(cur)
        else: cur=None
    elif cur is not None and m.group(2):
        t=html.unescape(re.sub(r'<[^>]+>','',m.group(2))).strip()
        mm=re.match(r'^(.*?)\s*\(([^)]+)\)\s*\[(\d+)\]$',t)
        if mm: cur['c'].append([mm.group(1).strip(),mm.group(2).title(),mm.group(3)])
        else: print('UNPARSED',t)
# questions (official ballot questions PDF)
qp=f'{PH}/q.pdf'
open(qp,'wb').write(requests.get('https://vote.phila.gov/media/2026G_Ballot_Questions.pdf',timeout=30,headers=UA).content)
qt=subprocess.run(['timeout','-k','5','30','pdftotext','-layout',qp,'-'],capture_output=True,text=True,timeout=40).stdout
qs=[]
for m in re.finditer(r'Question #(\d+).*?Ballot Question:\s*(.*?)\n\s*Statement:',qt,re.S):
    qs.append({'n':int(m.group(1)),'q':re.sub(r'\s+',' ',m.group(2)).strip()})
splits=re.findall(r'href="([^"]*SampleBallot/2026_General/[^"]+\.pdf)"[^>]*>\s*([^<]*?)\s*<',h)
def dnum(s): m=re.match(r'(\d+)',s); return m.group(1) if m else None
out={'v':1,'county':'Philadelphia','read':__import__('datetime').date.today().isoformat(),'source':'Philadelphia County Board of Elections (City Commissioners)','sourceUrl':SRC,
     'questionsUrl':'https://vote.phila.gov/media/2026G_Ballot_Questions.pdf','lookup':'https://vote.phila.gov/voting/voting-at-the-polls/sample-ballots/','c':[],'q':qs,'s':{}}
for c in contests:
    kind='gov' if c['office'].startswith('Governor') else 'cd' if 'Congress' in c['office'] else 'sd' if c['office'].startswith('Senator') else 'hd' if 'General Assembly' in c['office'] else 'other'
    out['c'].append({'t':c['office']+('' if c['dist']=='Statewide' else ', '+c['dist']),'k':kind,'d':dnum(c['dist']),'vf':re.sub(r'^Vote for ','',c['vf']),'c':[[n,p] for n,p,_ in c['c']]})
issues=[]
for url,name in splits:
    cd,sd,hd=name.split('-')
    want=[i for i,c in enumerate(out['c']) if c['k']=='gov' or (c['k']=='cd' and c['d']==cd) or (c['k']=='sd' and c['d']==sd) or (c['k']=='hd' and c['d']==hd)]
    p=f'{PH}/tmp.pdf'; open(p,'wb').write(requests.get(url,timeout=30,headers=UA).content)
    raw=subprocess.run(['timeout','-k','5','30','pdftotext',p,'-'],capture_output=True,text=True,timeout=40).stdout; os.remove(p)
    tx=nz(raw)
    miss=[(out['c'][i]['t'],n) for i in want for n,_ in out['c'][i]['c'] if all(nz(x) not in tx for x in n.split(' AND '))]
    extra=[(c['t'],n) for i,c in enumerate(out['c']) if i not in want for n,_ in c['c'] if nz(n.split(' AND ')[0]) in tx and not any(nz(n.split(' AND ')[0]) in nz(m) for j in want for m,_ in out['c'][j]['c'])]
    qok=all(('QUESTION%d'%q['n']) in tx for q in qs) and ('QUESTION%d'%(len(qs)+1)) not in tx
    hdr=('%sTHDISTRICT'%hd in tx or '%sNDDISTRICT'%hd in tx or '%sSTDISTRICT'%hd in tx or '%sRDDISTRICT'%hd in tx)
    ok=not miss and not extra and qok and hdr and len([c for c in want if out['c'][c]['k']=='gov'])==1
    if not ok: issues.append((name,miss[:3],extra[:3],qok,hdr))
    out['s'][name]={'o':want,'pdf':url,'ok':1 if ok else 0}
json.dump(out,open(f'{OUT}/pa-philadelphia-2026-11-03.json','w'),separators=(',',':'),ensure_ascii=False)
print('contests',len(out['c']),'questions',len(qs),'splits',len(out['s']),'ok',sum(v['ok'] for v in out['s'].values()),flush=True)
for i in issues: print(i)
