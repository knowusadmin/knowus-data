
import pdfplumber,re,json,sys
STARTS=[47,222,394]
def lines_of(path):
    pdf=pdfplumber.open(path); out=[]; hdr=None
    for pg in pdf.pages:
        p=pg.page_number
        allw=[w for w in pg.extract_words(extra_attrs=['size','fontname']) if w['size']<20]
        if p==1:
            h=' '.join(w['text'] for w in sorted([w for w in allw if 45<w['top']<70 and w['x0']>380],key=lambda w:w['x0'])); hdr=h
        ws=[w for w in allw if 92<=w['top']<955 and not (p==1 and w['x0']<215)]
        cols={}
        for w in ws:
            c=0 if w['x0']<218 else (1 if w['x0']<390 else 2)
            cols.setdefault(c,[]).append(w)
        for c in sorted(cols):
            ws2=sorted(cols[c],key=lambda w:(round(w['top']),w['x0'])); ls=[]
            for w in ws2:
                if ls and abs(w['top']-ls[-1]['top'])<=3: ls[-1]['w'].append(w)
                else: ls.append({'top':w['top'],'w':[w]})
            for l in ls:
                l['w'].sort(key=lambda w:w['x0']); t=' '.join(w['text'] for w in l['w'])
                out.append(dict(p=p,c=c,top=round(l['top'],1),x=round(l['w'][0]['x0']-STARTS[c]),t=t,s=round(max(w['size'] for w in l['w']),1),b=all('Bold' in w['fontname'] for w in l['w'])))
    return hdr,out
def parse(path):
    hdr,L=lines_of(path); res=[]; cur=None; st=None; left=[]; last=None
    for l in L:
        t,s,b,x=l['t'],l['s'],l['b'],l['x']
        if re.search(r'END OF BALLOT|intentionally left blank|^This page$|^This$',t): continue
        if re.match(r'^END( \(\d+/\d+/\d+\))?$',t) or re.match(r'^\(\d+/\d+/\d+\)$',t): st='end'; continue
        ind = x>=20
        if b and s>=11.5 and not ind:
            if cur is None or st not in('head',):
                cur={'title':[],'vf':'','cands':[],'wi':0,'sub':[],'text':[],'resp':[],'pos':(l['p'],l['c'])}; res.append(cur); st='head'
            cur['title'].append(t); continue
        if cur is None: left.append(l); continue
        if b and 9.5<=s<11.5 and t.startswith('(Vote for') and st=='head': cur['vf']=t; st='vf'; continue
        if st=='vf' and b and 9.5<=s<11.5 and not cur['cands'] and t.endswith(')') and not ind: cur['vf']+=' '+t; continue
        if b and s>=11.5 and ind and st in('vf','cand'):
            same = cur['cands'] and last is not None and last['p']==l['p'] and last['c']==l['c'] and l['top']-last['top']<19 and not cur['cands'][-1]['party']
            if same: cur['cands'][-1]['name'].append(t)
            else: cur['cands'].append({'name':[t],'party':''})
            st='cand'; last=l; continue
        if not b and 9.5<=s<11.5 and st=='cand' and cur['cands'] and ind:
            c=cur['cands'][-1]; c['party']=(c['party']+' '+t).strip(); last=l; continue
        if not b and s<9 and t.startswith('Write-in'): cur['wi']+=1; st='cand'; last=None; continue
        if st in('head','sub','qtext') and not ind and 9.5<=s<11.5:
            if b and st in('head','sub'): cur['sub'].append(t); st='sub'; continue
            cur['text'].append(t); st='qtext'; continue
        if b and s>=11.5 and ind and st in('qtext','sub','resp'):
            if st=='resp' and last is not None and last['c']==l['c'] and l['top']-last['top']<19: cur['resp'][-1]+=' '+t
            else: cur['resp'].append(t)
            st='resp'; last=l; continue
        left.append(l)
    for r in res:
        k=max([i for i,x in enumerate(r['title']) if x.startswith('For ')] or [0])
        r['inst']=' '.join(r['title'][:k]); r['title']=r['title'][k:]
        r['title']=' '.join(r['title']); r['text']=' '.join(r['text']); r['sub']=' '.join(r['sub']); r['kind']='q' if r['resp'] else 'race'
        for c in r['cands']: c['name']=' '.join(c['name'])
    return hdr,res,left,L
if __name__=='__main__':
    hdr,res,left,L=parse(sys.argv[1]); print(hdr)
    for r in res: print(r['kind'],'|',r['title'],'|',r['vf'],[(c['name'],c['party']) for c in r['cands']],r['wi'],'|',r['sub'][:80],'|',r['text'][:80],r['resp'])
    print('LEFT',[(l['p'],l['c'],l['x'],l['t'],l['s'],l['b']) for l in left])
