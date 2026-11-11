
import pdfplumber,re,json,sys
def page_lines(pg):
    ws=[w for w in pg.extract_words(extra_attrs=['size','fontname']) if w['size']<20]
    hdr=' '.join(w['text'] for w in sorted([w for w in ws if w['top']<45],key=lambda w:w['x0'])) if pg.page_number%2==1 else ''
    foot=' '.join(w['text'] for w in sorted([w for w in ws if w['top']>930 and w['top']<965],key=lambda w:w['x0']))
    ws=[w for w in ws if (255 if pg.page_number%2==1 else 20)<=w['top']<948 and not (w['x0']>420 and 855<w['top']<885 and w['text'] in('Chester','County','Board','of','Elections'))]
    cols={}
    for w in ws:
        c=0 if w['x0']<(212 if pg.page_number%2==0 else 232) else (1 if w['x0']<396 else 2)
        cols.setdefault(c,[]).append(w)
    out=[]
    for c in sorted(cols):
        ws2=sorted(cols[c],key=lambda w:(round(w['top']),w['x0'])); ls=[]
        for w in ws2:
            if ls and abs(w['top']-ls[-1]['top'])<=2.5: ls[-1]['w'].append(w)
            else: ls.append({'top':w['top'],'w':[w]})
        for l in ls:
            l['w'].sort(key=lambda w:w['x0']); t=' '.join(w['text'] for w in l['w'])
            out.append(dict(c=c,top=round(l['top']),t=t,s=round(max(w['size'] for w in l['w']),1),b=all('Bold' in w['fontname'] for w in l['w'])))
    return hdr,foot,out
def parse_lines(L):
    res=[];cur=None;st=None;left=[]
    for l in L:
        t,s,b=l['t'],l['s'],l['b']
        if b and s>=14: continue
        if st=='qtext' and b and 9.5<=s<10.5 and isinstance(cur['title'],list) and t in cur['title']: continue
        if b and s>=10.5 and st not in('vf','cand'):
            if cur is None or st!='head': cur={'title':[],'district':'','vf':'','inst':[],'cands':[],'wi':0,'text':[],'resp':[]}; res.append(cur); st='head'
            cur['title'].append(t); continue
        if b and s>=10.5 and st in('vf','cand'):
            if st=='cand' and cur['wi']>0:
                cur={'title':[t],'district':'','vf':'','inst':[],'cands':[],'wi':0,'text':[],'resp':[]}; res.append(cur); st='head'; continue
            cur['cands'].append({'name':t,'desc':''}); st='cand'; continue
        if b and 9.5<=s<10.5 and not re.match(r'^Vote for',t) and not re.search(r'District$',t) and (cur is None or st in('cand','resp') or (st=='qhead')):
            if st!='qhead': cur={'title':[],'district':'','vf':'','inst':[],'cands':[],'wi':0,'text':[],'resp':[]}; res.append(cur); st='qhead'
            cur['title'].append(t); continue
        if st=='qhead' and not b and s>=10.5: cur['text'].append(t); st='qtext'; continue
        if cur is None: left.append(l); continue
        if b and 9.5<=s<10.5 and re.match(r'^Vote for',t) and st in('head','inst'): cur['vf']=t; st='vf'; continue
        if b and 9.5<=s<10.5 and re.search(r'District$',t) and st=='head': cur['district']=t; continue
        if not b and 8.5<=s<9.5 and st in('head','inst') and not cur['text']: cur['inst'].append(t); st='inst'; continue
        if not b and 8.5<=s<9.5 and st=='cand' and cur['cands']: c=cur['cands'][-1]; c['desc']=(c['desc']+' '+t).strip(); continue
        if not b and s<8.5 and t in('Write-in','Write-In'): cur['wi']+=1; st='cand'; continue
        if not b and s>=9.5 and st in('head','qtext') and t not in('YES','NO','Yes','No'): cur['text'].append(t); st='qtext'; continue
        if t in('Yes','No','YES','NO') and st in('qtext','resp','inst','head'): cur['resp'].append(t); st='resp'; continue
        left.append(l)
    for r in res:
        r['title']=' '.join(r['title']); r['text']=' '.join(r['text']); r['kind']='q' if r['resp'] else 'race'
    return res,left
if __name__=='__main__':
    pdf=pdfplumber.open(sys.argv[1]); out=[]
    a,b=int(sys.argv[2]),int(sys.argv[3])
    for i in range(a,b):
        hdr,foot,L=page_lines(pdf.pages[i])
        out.append({'page':i+1,'hdr':hdr,'foot':foot,'L':L})
    json.dump(out,open(sys.argv[4],'w'))
