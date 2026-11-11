# Tarrant County TX, Nov 3 2026 Joint General and Special Elections: parse one Find My Ballot sample ballot PDF
# (Hart layout: 2 columns, contest header boxes with English bold title + Spanish italic, one box per option, "Write-in" rows).
import pdfplumber,re,json,sys,os
PARTY={'REP','DEM','LIB','GRN','IND','NON'}
def is_box(r): return abs(r['width']-21.7)<1.2 and abs(r['height']-10.5)<1.2
def lines(pg):
    W=pg.width; ws=[w for w in pg.extract_words(x_tolerance=1,extra_attrs=['fontname','size']) if 6<=w['size']<=16]
    L=[]
    for w in sorted(ws,key=lambda w:(round(w['top'],1),w['x0'])):
        c=0 if w['x0']<W/2 else 1; f='B' if 'Bold' in w['fontname'] else 'I' if 'Italic' in w['fontname'] else 'R'
        for x in L:
            if x['c']==c and abs(x['t']-w['top'])<=2.5 and x['f']==f and w['x0']-x['x1']<15: x['w'].append(w['text']); x['x1']=w['x1']; break
        else: L.append(dict(c=c,t=w['top'],b=w['bottom'],f=f,w=[w['text']],x0=w['x0'],x1=w['x1'],sz=round(w['size'])))
    for x in L: x['text']=' '.join(x['w'])
    return L
def parse(path):
    pdf=pdfplumber.open(path); cons=[]; prec=None; nbox=0; grp=None; stray=[]
    for pi,pg in enumerate(pdf.pages):
        boxes=[r for r in pg.rects if is_box(r)]; nbox+=len(boxes)
        hdrs=[r for r in pg.rects if r['width']>200 and 15<r['height']<200]
        L=lines(pg)
        for x in L:
            m=re.match(r'^Precinct (\d{4}-\d{3})$',x['text'])
            if m: prec=m[1]
        for c in (0,1):
            cur=None; inhdr_prev=False
            for x in sorted([l for l in L if l['c']==c and l['t']>90 and l['t']<950],key=lambda l:l['t']):
                hd=any(h['top']-3<=x['t']<=h['bottom'] and h['x0']-3<=x['x0']<=h['x1'] for h in hdrs)
                bx=any(abs((b['top']+b['bottom'])/2-(x['t']+x['b'])/2)<6 and 0<x['x0']-b['x1']<30 for b in boxes)
                if hd:
                    if pi==0 and c==0 and x['sz']==11 and x['f']=='R' and x['t']<350: continue  # instructions + party legend
                    if x['f']=='R' and x['sz']>=10:  # section (entity / election) header
                        grp=(grp+' '+x['text']) if (cur is None and inhdr_prev and grp_open) else x['text']; grp_open=True; inhdr_prev=True; cur=None; continue
                    grp_open=False
                    if cur is None or cur.get('done_hdr'):
                        cur=dict(title=[],es=[],ins=[],c=[],r=[],q=[],wi=0,grp=grp,pg=pi,col=c); cons.append(cur)
                    if x['f']=='B': cur['title'].append(x['text'])
                    elif x['f']=='I': cur['es'].append(x['text'])
                    else: cur['ins'].append(x['text'])
                    inhdr_prev=True; continue
                inhdr_prev=False; grp_open=False
                if cur is None: stray.append(x['text']); continue
                cur['done_hdr']=True
                if bx and x['f']=='R':
                    w=x['w']; party=''
                    if w and w[-1] in PARTY: party=w[-1]; w=w[:-1]
                    cur['c'].append([' '.join(w),party]); continue
                if x['text']=='Write-in' and x['sz']==8: cur['wi']+=1; continue
                if x['f']=='I' and x['text']=='Escribir en': continue
                if x['f']=='R': cur['q'].append(x['text'])
                elif x['f']=='I': pass
                else: stray.append(x['text'])
    out=[]
    for k in cons:
        t=' '.join(k['title']); vf='1'
        ins=' '.join(k['ins']); m=re.search(r'Vote for (none, )?(one|two|three|four|five|six|seven)',ins,re.I)
        if m: vf=str(['one','two','three','four','five','six','seven'].index(m[2].lower())+1)
        opts=[o for o,_ in k['c']]
        isq=bool(opts) and all(re.match(r'^(FOR|AGAINST|YES|NO|For|Against|Yes|No)\b',o) for o in opts)
        if isq: out.append(dict(t='q',title=t,grp=k['grp'],pre=ins,q=' '.join(k['q']),r=opts,wi=k['wi']))
        else: out.append(dict(t='r',title=t,grp=k['grp'],vf=vf,c=k['c'],wi=k['wi'],note=k['q']))
    nopt=sum(len(c.get('c') or c.get('r'))+c['wi'] for c in out)
    return dict(file=os.path.basename(path),prec=prec,nbox=nbox,nopt=nopt,contests=out,stray=stray)
if __name__=='__main__':
    files=sys.argv[2:]; res=[]
    for f in files:
        try: res.append(parse(f))
        except Exception as e: res.append(dict(file=os.path.basename(f),error=repr(e)))
    json.dump(res,open(sys.argv[1],'w'),ensure_ascii=False)
