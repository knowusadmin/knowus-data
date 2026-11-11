
import pdfplumber,re,json,sys
def lines_of(path):
    pdf=pdfplumber.open(path); out=[]
    for pg in pdf.pages:
        p=pg.page_number
        ws=[w for w in pg.extract_words(extra_attrs=['size','fontname']) if w['size']<20 and w['top']>=118 and w['top']<760]
        cols={}
        for w in ws:
            c=0 if w['x0']<240 else (1 if w['x0']<393 else 2)
            cols.setdefault(c,[]).append(w)
        for c in sorted(cols):
            ws2=sorted(cols[c],key=lambda w:(round(w['top']),w['x0'])); ls=[]
            for w in ws2:
                if ls and abs(w['top']-ls[-1]['top'])<=2.5: ls[-1]['w'].append(w)
                else: ls.append({'top':w['top'],'w':[w]})
            for l in ls:
                l['w'].sort(key=lambda w:w['x0']); t=' '.join(w['text'] for w in l['w'])
                s_=max(w['size'] for w in l['w']); b_=all('Bold' in w['fontname'] for w in l['w'])
                if s_<2 or (not b_ and s_>=11.5): continue
                if re.search(r'intentionally left blank|^This page$|^intentionally|Esta p.gina se deja|^Vote Both Sides|^Continue voting on next page|Ballot / Vote en ambos|^Vote en ambos|^en blanco$|intencionalmente|Continue voting|Contin.e vot|^de la boleta$',t): continue
                if re.match(r'^Page \d+ of \d+$',t): continue
                out.append(dict(p=p,c=c,top=round(l['top']),t=t,s=round(max(w['size'] for w in l['w']),1),b=all('Bold' in w['fontname'] for w in l['w'])))
    return out
def parse(path):
    L=lines_of(path); res=[]; cur=None; st=None; left=[]
    for l in L:
        t,s,b=l['t'],l['s'],l['b']
        if not b and st=='head' and s<9.8: continue
        if not b and st=='vf' and t.startswith('(Vote por'): continue
        if t.startswith('Write-in') and not b and st in('vf','cand'): cur['wi']+=1; st='cand'; continue
        if b and s>=9.8:
            if cur is None or st not in('head',):
                cur={'title':[],'vf':'','cands':[],'wi':0,'text':[],'resp':[],'pos':(l['p'],l['c'])}; res.append(cur); st='head'
            cur['title'].append(t); continue
        if cur is None: left.append(l); continue
        if b and 8.5<=s<9.8 and t.startswith('(Vote') and st=='head': cur['vf']=t; st='vf'; continue
        if b and 8.5<=s<9.8 and st=='vf' and not cur['cands'] and not re.match(r'^\(\d+\)',t) and not t.endswith(')')==False: pass
        m=re.match(r'^\((\d+)\)\s*(.+)$',t)
        if b and 8.5<=s<9.8 and m and st in('vf','cand'):
            cur['cands'].append({'no':m.group(1),'name':[m.group(2)],'party':''}); st='cand'; continue
        if b and 8.5<=s<9.8 and st=='cand' and cur['cands'] and not cur['cands'][-1]['party']:
            cur['cands'][-1]['name'].append(t); continue
        if not b and 8.5<=s<9.8 and st=='cand' and cur['cands'] and t not in('Yes','No'):
            c=cur['cands'][-1]; c['party']=(c['party']+' '+t).strip(); continue
        if not b and s<8.5 and t=='Write-in' and st in('vf','cand'): cur['wi']+=1; st='cand'; continue
        if not b and 9.8<=s and st in('head','qtext'): cur['text'].append(t); st='qtext'; continue
        if st in('qtext','resp') and s<9.5 and t.split()[0] not in('Yes','No'): continue
        if not b and t.split()[0] in('Yes','No') and len(t.split())<=2 and st in('qtext','resp'): cur['resp'].append(t.split()[0]); st='resp'; continue
        if not b and t in('Yes','No') and st in('qtext','resp'): cur['resp'].append(t); st='resp'; continue
        left.append(l)
    for r in res:
        tl=r['title']; pre=[]
        while tl and re.match(r'^(To the|Pennsylvania:|voters of)',tl[-1]) or (tl and r['text'] and tl[-1].endswith(':')):
            pre.insert(0,tl.pop())
        # preamble may span lines: pull back lines from the first "To the"
        k=next((i for i,x in enumerate(r['title']) if x.startswith('To the')),None)
        if k is not None: pre=r['title'][k:]+pre; r['title']=r['title'][:k]
        r['pre']=' '.join(pre); r['title']=' '.join(r['title']); r['text']=' '.join(r['text'])
        m=re.search(r'\s*(\d+(?:st|nd|rd|th) (?:Congressional |Senatorial |Legislative )?District)$',r['title'])
        r['district']=m.group(1) if m else ''
        if m: r['title']=r['title'][:m.start()].strip()
        r['kind']='q' if r['resp'] else 'race'
    return res,left,L
if __name__=='__main__':
    res,left,L=parse(sys.argv[1]); print(json.dumps(res,indent=1)); print('LEFT',[(l['p'],l['c'],l['t'],l['s'],l['b']) for l in left])
