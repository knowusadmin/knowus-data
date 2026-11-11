
import pdfplumber,re,sys,json,collections
COLX=300
def lines_of(path):
    global OVP
    OVP={}
    pdf=pdfplumber.open(path); out=[]; ovals=0; hdr=[]; LASTMODE=['H']
    for pg in pdf.pages:
        OVP[pg.page_number]=sum(1 for r in pg.rects if 21<=r['width']<=25 and 12<=r['height']<=16); ovals+=OVP[pg.page_number]
        ws=[w for w in pg.extract_words(extra_attrs=['size','fontname']) if 7<w['size']<20 and 'Times' not in w['fontname']]
        hrs0=sorted([(r['top'],'F' if r['width']>500 else 'H') for r in pg.rects if (r['width']>500 or 255<r['width']<290) and r['height']>20],key=lambda x:x[0])
        def modef(y):
            m=LASTMODE[0]
            for t,k in hrs0:
                if t<=y+1: m=k
            return m
        rows=[]
        for w in sorted(ws,key=lambda w:(round(w['top']),w['x0'])):
            if rows and abs(w['top']-rows[-1]['top'])<=2.5: rows[-1]['w'].append(w)
            else: rows.append({'top':w['top'],'w':[w]})
        segs=[]
        for r in rows:
            r['w'].sort(key=lambda w:w['x0']); cur=[r['w'][0]]
            for w in r['w'][1:]:
                if (cur[-1]['x0']<COLX<=w['x0'] and modef(w['top'])=='H'): segs.append(cur); cur=[w]
                else: cur.append(w)
            segs.append(cur)
        mid=pg.width/2
        hrs=sorted([(r['top'],'F' if r['width']>500 else 'H') for r in pg.rects if (r['width']>500 or 255<r['width']<290) and r['height']>20],key=lambda x:x[0])
        def mode(y):
            m=LASTMODE[0]
            for t,k in hrs:
                if t<=y+1: m=k
            return m
        L=[]
        for sg in segs:
            t=' '.join(w['text'] for w in sg); s=max(w['size'] for w in sg); b=all('Bold' in w['fontname'] for w in sg)
            c=0 if (sg[0]['x0']<COLX or mode(sg[0]['top'])=='F') else 1
            L.append(dict(p=pg.page_number,c=c,top=round(sg[0]['top'],1),x=round(sg[0]['x0']),x1=round(sg[-1]['x1']),t=t,s=round(s,1),b=b))
        if hrs: LASTMODE[0]=hrs[-1][1]
        if pg.page_number==1: hdr=[l['t'] for l in L if l['s']>=13.5]
        L=[l for l in L if not (l['s']>=13.5 and l['s']<16)]
        out+=sorted(L,key=lambda l:(l['c'],l['top']))
    return out,ovals,hdr
def parse(path):
    L,ovals,hdr=lines_of(path)
    # base x per (page,col): min x of bold 12 'For ' or 'Issue' lines
    res=[];cur=None;st=None;left=[];started=False;OP=[]
    bases={}
    for l in L:
        if (l['b'] and (l['t'].startswith('For ') and l['s']>=11.5)) or (l['b'] and l['s']>=17 and l['t'].startswith('Issue')):
            k=(l['p'],l['c']); bases[k]=min(bases.get(k,999),l['x'])
    ft=min([l['top'] for l in L if l['p']==1 and l['b'] and l['t'].startswith('For ') and l['s']>=11.5] or [0])
    L=[l for l in L if not (l['p']==1 and l['top']<ft-2)]
    gb={c:min([v for k,v in bases.items() if k[1]==c] or [999]) for c in (0,1)}
    for l in L:
        t,s,b=l['t'],l['s'],l['b']; base=bases.get((l['p'],l['c']),gb[l['c']]); ind=l['x']-base
        if b and s>=17 and re.match(r'^Issue \d+',t):
            cur={'kind':'q','num':t,'title':[],'sub':[],'text':[],'resp':[],'cands':[],'wi':0,'vf':''}; res.append(cur); st='qt'; started=True; continue
        if cur and cur['kind']=='q' and st=='qt' and b and s>=11.5 and ind<8 and t.startswith('For '): cur['title'].append(t); continue
        if b and s>=11.5 and t.startswith('For ') and ind<8 and not (cur and cur['kind']=='q' and st in('resp',) and False):
            if cur and cur['kind']=='q' and st=='resp' and ind>=8: pass
            else:
                cur={'kind':'race','title':[t[4:]],'vf':'','cands':[],'wi':0,'note':[]}; res.append(cur); st='rt'; started=True; continue
        if not started: continue
        if cur['kind']=='race':
            if st=='rt' and b and ind<8:
                if t.startswith('(Vote for'): cur['vf']=t; st='vf'; continue
                if s>=11.5 or (t.startswith('(') and s>=9.5): cur['title'].append(t); continue
                if s<9.5: cur['note'].append(t); continue
            if st=='rt' and b and s<9.5: cur['note'].append(t); continue
            if st in('rt','vf','cand','party') and b and s>=11.5 and ind>=8:
                OP.append(l['p'])
                if t=='Write-in': cur['wi']+=1; st='cand'; continue
                cur['cands'].append([t,'']); st='cand'; continue
            if st=='cand' and not b and 9.5<=s<11.5 and ind>=8 and cur['cands'] and not cur['cands'][-1][1]:
                cur['cands'][-1][1]=t; st='party'; continue
            if st=='vf' and b and t.startswith('(') : cur['vf']+=' '+t; continue
            left.append(l); continue
        else:
            if st=='qt' and b and s>=11.5 and ind<8: cur['title'].append(t); continue
            if st in('qt','sub') and b and 9.5<=s<11.5 and ind<8: cur['sub'].append(t); st='sub'; continue
            if st in('qt','sub','text') and not b and 9.5<=s<11.5 and ind<8: cur['text'].append(t); st='text'; continue
            if st=='text' and b and 9.5<=s<11.5 and ind<8: cur['text'].append(t); continue
            if st in('text','sub','resp') and b and s>=11.5 and ind>=8: cur['resp'].append(t); OP.append(l['p']); st='resp'; continue
            if st=='text' and not b and 9.5<=s<11.5: cur['text'].append(t); continue
            left.append(l); continue
    for r in res:
        r['title']=' '.join(r['title'])
        if r['kind']=='q': r['sub']=' '.join(r['sub']); r['text']=' '.join(r['text'])
    nov=sum(len(r['cands'])+r['wi'] for r in res if r['kind']=='race')+sum(len(r['resp']) for r in res if r['kind']=='q')
    opp=dict(collections.Counter(OP))
    return {'ovp':OVP,'opp':opp,'hdr':hdr,'contests':res,'left':[(l['p'],l['c'],l['x'],l['t'][:60],l['s'],l['b']) for l in left],'ovals':ovals,'nov':nov}
if __name__=='__main__':
    d=parse(sys.argv[1])
    for r in d['contests']: print(r['kind'],'|',r.get('num',''),r['title'],'|',r['vf'],r['cands'],r['wi'],'|',(r.get('sub') or '')[:60],'|',(r.get('text') or '')[:80],r.get('resp'))
    print('LEFT',d['left']); print('ovals',d['ovals'],'parsed',d['nov'],d['hdr'])
