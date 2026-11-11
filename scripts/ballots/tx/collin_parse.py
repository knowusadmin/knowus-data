
# Collin County TX Nov 3 2026: parse one ballot-style PDF (3 columns; bold titles, BoldItalic Spanish, "Vote for", ovals left of options)
import pdfplumber,re,json,sys,os
PARTY={'Rep':'Republican','Dem':'Democratic','Lib':'Libertarian','Grn':'Green','Ind':'Independent'}
def colof(x,W): return 0 if x<W*0.3627 else 1 if x<W*0.6435 else 2
def lines(pg):
    ws=pg.extract_words(x_tolerance=1,keep_blank_chars=False,extra_attrs=['fontname','size'])
    W=pg.width; L=[]
    for w in sorted(ws,key=lambda w:(round(w['top'],0),w['x0'])):
        c=colof(w['x0'],W); f=w['fontname']; b='Bold' in f; it='Italic' in f
        for x in L:
            if x['c']==c and abs(x['t']-w['top'])<=2 and 0<=w['x0']-x['x1']<9 and x['b']==b and x['it']==it:
                x['w'].append(w['text']); x['x1']=w['x1']; break
        else: L.append(dict(c=c,t=w['top'],x0=w['x0'],x1=w['x1'],b=b,it=it,sz=w['size'],w=[w['text']]))
    for x in L: x['text']=' '.join(x['w'])
    return L
def parse(path):
    pdf=pdfplumber.open(path); cons=[]; ovals=0; hdr=None; stray=[]; sect=''
    for pi,pg in enumerate(pdf.pages):
        W=pg.width; L=lines(pg)
        OV=[]
        for cv in pg.curves:
            if 7.5<=cv['width']<=9.5 and 4.5<=cv['height']<=6.5 and not any(abs(cv['x0']-a)<2 and abs(cv['top']-b)<2 for a,b in OV): OV.append((cv['x0'],cv['top']))
        # instruction ovals (inside the instruction paragraph) are inline in text; drop ovals with text immediately left of them
        realOV=[]
        for ox,oy in OV:
            c=colof(ox,W)
            left=[l for l in L if l['c']==c and abs(l['t']-oy)<6 and l['x1']<ox+1 and l['x1']>ox-60]
            if left and pi==0 and oy<200: continue
            realOV.append((ox,oy))
        ovals+=len(realOV)
        for c in (0,1,2):
            Ls=sorted([l for l in L if l['c']==c and l['t']>30],key=lambda l:(l['t'],l['x0']))
            Os=sorted([(oy,ox) for ox,oy in realOV if colof(ox,W)==c])
            optidx=set(); evs=[]
            for oy,ox in Os:
                tl=[i for i,l in enumerate(Ls) if oy-4<=l['t']<=oy+4 and l['x0']>ox+4 and not l['it']]
                optidx.update(tl); evs.append(('O',oy,' '.join(Ls[i]['text'] for i in sorted(tl,key=lambda i:Ls[i]['x0']))))
            for i,l in enumerate(Ls):
                if i not in optidx: evs.append(('L',l['t'],i))
            evs.sort(key=lambda e:(e[1],0 if e[0]=='L' else 1))
            cur=None; title=[]; body=[]
            for k,(kind,t,v) in enumerate(evs):
                if kind=='L':
                    l=Ls[v]; tx=l['text']
                    if pi==0 and t<205 and not cur: 
                        m=re.search(r'\b(\d{1,4})\b',tx)
                        continue
                    if l['it']:
                        continue
                    if re.match(r'^Vote for',tx):
                        cur=dict(kind='r',sect=sect,title=' '.join(title),vf=tx,c=[],wi=0,page=pi,col=c); cons.append(cur); title=[]; body=[]; continue
                    if l['b']:
                        nxt=[e for e in evs[k+1:k+3] if e[0]=='L']
                        if nxt and Ls[nxt[0][2]]['it'] and not Ls[nxt[0][2]]['b'] and re.match(r'^\(',Ls[nxt[0][2]]['text']) and not title:
                            sect=tx; cur=None; continue
                        if cur is not None: cur=None
                        title.append(tx); body=[]; continue
                    # regular text
                    if title and not cur: body.append(tx); continue
                    if cur is not None and cur['kind']=='q':
                        if cur['opts']:
                            ent=cur['title']; et=cur.get('etype','')
                            cur=dict(kind='q',sect=sect,title=ent,etype=et,body=[],opts=[],page=pi,col=c); cons.append(cur)
                        cur['body'].append(tx); continue
                    if re.match(r'^(Legend|Republican Party|Democratic Party|Libertarian Party|Green Party|Independent)',tx) or tx in ('Rep','Dem','Lib','Grn','Ind') or re.match(r'^(Vote Both Sides|Continue|Page)',tx): continue
                    stray.append(tx)
                else:
                    tx=v
                    if cur is None or (cur['kind']=='r' and title):
                        if title:
                            cur=dict(kind='q',sect=sect,title=' '.join(title),body=body,opts=[],page=pi,col=c); cons.append(cur); title=[]; body=[]
                        else:
                            stray.append('OVAL? '+tx); continue
                    if cur['kind']=='q': cur['opts'].append(tx); continue
                    if re.match(r'^Write-?\s?in',tx,re.I) or tx=='': cur['wi']+=1; continue
                    m=re.match(r'^(.*?)\s+(Rep|Dem|Lib|Grn|Ind)$',tx)
                    cur['c'].append([m[1],PARTY[m[2]]] if m else [tx,''])
    nopt=sum(len(c['c'])+c['wi'] if c['kind']=='r' else len(c['opts']) for c in cons)
    return dict(file=os.path.basename(path),nopt=nopt,ovals=ovals,contests=cons,stray=stray[:30])
if __name__=='__main__':
    D=sys.argv[1]; out=[]
    for i,f in enumerate(sorted(os.listdir(D))):
        try: out.append(parse(D+'/'+f))
        except Exception as e: out.append(dict(file=f,error=repr(e)))
        if i%10==0: print(i,flush=True)
    json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False); print('DONE',len(out),flush=True)
