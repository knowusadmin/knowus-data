
import pdfplumber,re,json,sys,os
B=lambda w:'Bold' in w['fontname']
def lines_of(path):
    pdf=pdfplumber.open(path); out=[]
    for pg in pdf.pages:
        ws=[w for w in pg.extract_words(extra_attrs=['size','fontname']) if w['size']<20]
        p=pg.page_number
        def keep(w):
            if p==1 and w['top']<288: return False
            if w['top']>=655: return False
            return True
        ws=[w for w in ws if keep(w)]
        cols={}
        for w in ws:
            c=0 if w['x0']<215 else (1 if w['x0']<392 else 2)
            cols.setdefault(c,[]).append(w)
        for c in sorted(cols):
            ws2=sorted(cols[c],key=lambda w:(round(w['top']),w['x0']))
            ls=[]
            for w in ws2:
                if ls and abs(w['top']-ls[-1]['top'])<=2.5: ls[-1]['w'].append(w)
                else: ls.append({'top':w['top'],'w':[w]})
            for l in ls:
                l['w'].sort(key=lambda w:w['x0'])
                t=' '.join(w['text'] for w in l['w'])
                if t.startswith('CONTINUE VOTING') or t.startswith('REVERSE SIDE') or t in('VOTE BOTH SIDES',): continue
                out.append(dict(p=p,c=c,top=round(l['top']),t=t,s=round(max(w['size'] for w in l['w']),1),b=all(B(w) for w in l['w'])))
    return out
def parse(path):
    L=lines_of(path); res=[]; cur=None; st=None; left=[]
    def new(kind):
        nonlocal cur
        cur={'kind':kind,'title':[],'vf':'','cands':[],'wi':0,'text':[],'note':[],'resp':[],'p':None}; res.append(cur)
    for l in L:
        t,s,b=l['t'],l['s'],l['b']
        if b and s>=10.5:
            if cur is None or st!='head': new('race'); st='head'; cur['p']=(l['p'],l['c'])
            cur['title'].append(t); continue
        if cur is None: left.append(l); continue
        if b and s>=9.5 and st=='head' and t in('Ballot Question','Ballot Questions'):
            cur['kind']='q'; cur['sub']=t; st='qtext'; continue
        if st in('head','vf') and not b and t.startswith('(') or (st=='vf' and not b and s>=9.5 and not cur['cands'] and not t.isupper()):
            cur['vf']=(cur['vf']+' '+t).strip(); st='vf'; continue
        if b and s>=9.5 and st in('vf','note'): cur['note'].append(t); st='note'; continue
        if st=='qtext' and not b and s>=9.2 and t not in('YES','NO'): cur['text'].append(t); continue
        if st in('qtext','resp') and t in('YES','NO'): cur['resp'].append(t); st='resp'; continue
        if t=='Write-In' and st in('vf','note','cand'): cur['wi']+=1; st='cand'; continue
        if not b and 8.5<=s<9.3 and st in('vf','note','cand') and re.match(r"^[A-Z0-9][A-Za-z0-9 .,'\"()\-]*$",t) and t.upper()==t:
            cur['cands'].append({'name':t,'party':'','roles':[]}); st='cand'; continue
        if s<8 and st=='cand' and cur['cands']:
            c=cur['cands'][-1]
            if t in('Governor','Lieutenant Governor'): c['roles'].append(t)
            else: c['party']=(c['party']+' '+t).strip()
            continue
        left.append(l)
    return res,left,L
def finish(res):
    out=[]; i=0
    while i<len(res):
        r=res[i]; out.append(r); i+=1
    for r in out:
        r['title']=' '.join(r['title'])
        r['text']=' '.join(r['text'])
        m=re.search(r'\s*(\d+(?:st|nd|rd|th) District)$',r['title'])
        r['district']=m.group(1) if m else ''
        if m: r['title']=r['title'][:m.start()].strip()
    return out
if __name__=='__main__':
    for f in sys.argv[1:]:
        res,left,L=parse(f); res=finish(res)
        print(json.dumps(res,indent=1)); print('LEFT',[(l['p'],l['c'],l['top'],l['t'],l['s'],l['b']) for l in left])
