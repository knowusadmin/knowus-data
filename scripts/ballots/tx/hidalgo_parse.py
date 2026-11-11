
# Hidalgo County TX, Nov 3 2026: parse one official ballot-style sample PDF (4 columns; English title bold, Spanish italic in parens;
# one printed box per option; candidates regular text with party at the end; "Write-in Escribir en" boxes).
import pdfplumber,re,json,sys,os
PARTY={'REP','DEM','LIB','GRN','IND'}
def parse(path):
    pdf=pdfplumber.open(path); cons=[]; nbox=0; hdr=None; cur=None; carry=[]
    for pi,pg in enumerate(pdf.pages):
        ws=[w for w in pg.extract_words(x_tolerance=1.5,extra_attrs=['fontname','size']) if 9<=w['size']<=11.6 and 'Helvetica' not in w['fontname']]
        allw=pg.extract_words(x_tolerance=1.5,extra_attrs=['fontname','size'])
        for w in allw:
            pass
        txt=pg.extract_text() or ''
        m=re.search(r'BALLOT STYLE #(\d+)',txt); hdr=hdr or (m and int(m[1]))
        bx=sorted([r for r in pg.rects if 18<=r['width']<=21 and 7<=r['height']<=9],key=lambda r:(round(r['x0']),r['top']))
        nbox+=len(bx)
        colx=sorted(set(round(r['x0']) for r in bx))
        # merge close column x
        cx=[]
        for x in colx:
            if not cx or x-cx[-1]>40: cx.append(x)
        if pi==0 and cx and cx[0]>100: pass
        def col(x0):
            i=0
            for j,c in enumerate(cx):
                if x0>=c-12: i=j
            return i
        # lines per column
        L=[]
        for w in sorted(ws,key=lambda w:(round(w['top']),w['x0'])):
            if w['top']<150: continue
            c=col(w['x0']); b='Bold' in w['fontname']; it='Italic' in w['fontname']
            for l in L:
                if l['c']==c and abs(l['t']-w['top'])<=2.5 and l['b']==b and l['it']==it and w['x0']-l['x1']<15:
                    l['w'].append(w['text']); l['x1']=w['x1']; break
            else: L.append(dict(c=c,t=w['top'],x0=w['x0'],x1=w['x1'],b=b,it=it,w=[w['text']]))
        for l in L: l['text']=' '.join(l['w'])
        for c in range(len(cx)):
            Ls=sorted([l for l in L if l['c']==c],key=lambda l:l['t'])
            B=[r for r in bx if col(r['x0'])==c]
            # event list: title lines, boxes, regular lines
            ev=[('L',l['t'],l) for l in Ls]+[('B',r['top']-1.5,r) for r in B]
            ev.sort(key=lambda e:(e[1],0 if e[0]=='B' else 1))
            title=carry; carry=[]; opt=None; body=[]
            for kind,t,o in ev:
                if kind=='B':
                    if title:
                        cur=dict(title=' '.join(title),opts=[],vf=None,page=pi,col=c,body=body); cons.append(cur); title=[]; body=[]
                    if cur is None: cur=dict(title='?',opts=[],vf=None,page=pi,col=c); cons.append(cur)
                    near=' '.join(w['text'] for w in allw if abs(w['top']-o['top'])<5 and o['x1']<w['x0']<o['x1']+60)
                    opt=dict(t=o['top'],x=o['x1'],w=[],wi=bool(re.match(r'^Write',near))); cur['opts'].append(opt); continue
                tx=o['text']
                if o['b'] and not o['it']:
                    if opt is not None or not title: title=[]
                    title.append(tx); opt=None; continue
                if o['it']: continue
                if re.match(r'^Vote for',tx,re.I):
                    if title: cur=dict(title=' '.join(title),opts=[],vf=tx,page=pi,col=c); cons.append(cur); title=[]
                    continue
                if re.match(r'^\(?Vote por',tx,re.I): continue
                if opt is not None and o['x0']>opt['x']-2 and o['t']-opt['t']<40: opt['w'].append(tx); continue
                if title and title[0].upper().startswith('PROPOSITION'): body.append(tx); continue
                if title: title.append(tx); continue
            carry=title
    out=[]
    for c in cons:
        os_=[]; wi=0
        for o in c['opts']:
            s=re.sub(r'(\w)- (\w)',r'\1-\2',' '.join(o['w']).strip())
            if o.get('wi') or re.match(r'^Write-in',s): wi+=1; continue
            os_.append(s)
        t=re.sub(r'(\w)- (\w)',r'\1-\2',c['title']); v=c['vf']
        m=re.search(r'\s*-?\s*\(?(Vote for [^)]*\)?)\)?\s*$',t)
        if m: v=v or m[1]; t=t[:m.start()].strip()
        out.append(dict(body=' '.join(c.get('body') or []),title=t,vf=v,opts=os_,wi=wi))
    nopt=sum(len(c['opts'])+c['wi'] for c in out)
    return dict(file=os.path.basename(path),bs=hdr,nbox=nbox,nopt=nopt,contests=out)
if __name__=='__main__':
    D=sys.argv[1]; res=[]
    for f in sorted(os.listdir(D)):
        try: res.append(parse(D+'/'+f))
        except Exception as e: res.append(dict(file=f,error=repr(e)))
        print(f,flush=True)
    json.dump(res,open(sys.argv[2],'w'),ensure_ascii=False,indent=0); print('DONE',flush=True)
