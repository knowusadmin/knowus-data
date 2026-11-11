
import pdfplumber,re,json,sys,os
COLX=[(0,235),(235,417),(417,700)]
def col(x): return 0 if x<235 else 1 if x<417 else 2
SECT=re.compile(r'^(Federal|State|County|District|Precinct|City|School|Special|Municipal|Independent School District|Proposition|Propositions|City of .*|.* ISD|.*Emergency Services District.*|ESD.*|Town of .*|Village of .*)$')
def lines_of(pg):
    q=pg.dedupe_chars(tolerance=1.2).filter(lambda o: not (o.get('object_type')=='char' and (o.get('size',0)>25 or o.get('size',0)<7)))
    ws=q.extract_words(x_tolerance=1.5,extra_attrs=['fontname','size'])
    ov=[]
    for c in pg.curves:
        if 7.5<=c['width']<=10.5 and 4.5<=c['height']<=7.5:
            if not any(abs(c['x0']-a)<2.5 and abs(c['top']-b)<2.5 for a,b in ov): ov.append((c['x0'],c['top']))
    L=[]
    for w in sorted(ws,key=lambda w:(round(w['top']),w['x0'])):
        c=col(w['x0']); b='Bold' in w['fontname']; it='Italic' in w['fontname']
        for x in L:
            if x['c']==c and abs(x['t']-w['top'])<=2.5 and w['x0']-x['x1']<14 and x['b']==b: x['w'].append(w['text']); x['x1']=w['x1']; break
        else: L.append(dict(c=c,t=w['top'],x0=w['x0'],x1=w['x1'],b=b,it=it,w=[w['text']]))
    for x in L: x['text']=' '.join(x['w']); del x['w']
    return L,[(col(x),x,t) for x,t in ov]
def title_of(head):
    h=list(head)
    while h and (h[-1][0].startswith('(') or h[-1][0].endswith(')') and not h[-1][1]): 
        # strip the Spanish block (may span several lines starting with "(")
        i=len(h)-1
        while i>=0 and not h[i][0].startswith('('): i-=1
        if i<0: break
        h=h[:i]
        break
    t=[]
    for tx,b in reversed(h):
        if not b or SECT.match(tx): break
        t.insert(0,tx)
    return ' '.join(t)
def parse(path):
    pdf=pdfplumber.open(path); cons=[]; bad=[]; nov=0; used=0
    for pi,pg in enumerate(pdf.pages):
        L,O=lines_of(pg)
        if not O: continue
        nov+=len(O)
        for c in (0,1,2):
            Ls=sorted([l for l in L if l['c']==c],key=lambda l:l['t']); Os=sorted([(t,x) for cc,x,t in O if cc==c])
            # option lines = lines whose top is within an oval's band
            optline=set()
            opts=[]
            for t,x in Os:
                tl=[i for i,l in enumerate(Ls) if t-4<=l['t']<=t+7 and l['x0']>x+5]
                for i in tl: optline.add(i)
                opts.append((t,' '.join(Ls[i]['text'] for i in tl)))
            # walk: heading accumulates non-option lines; 'Vote for' closes heading
            cur=None; head=[]
            events=sorted([('L',l['t'],i) for i,l in enumerate(Ls) if i not in optline]+[('O',t,k) for k,(t,_) in enumerate(opts)],key=lambda e:(e[1],0 if e[0]=='L' else 1))
            for kind,t,i in events:
                if kind=='L':
                    l=Ls[i]; tx=l['text']
                    if re.match(r'^\(?Vote (for|por)',tx):
                        if tx.startswith('Vote for'):
                            cur=dict(kind='r',head=[h for h in head],title=title_of(head),vf=tx,opts=[],page=pi,col=c); cons.append(cur); head=[]
                        continue
                    if cur is not None and cur['opts'] and not cur.get('closed'):
                        cur['closed']=True
                    if cur is not None and cur['kind']=='q' and not cur['opts']:
                        cur['body'].append(tx); continue
                    head.append((tx,l['b']))
                else:
                    used+=1
                    ot=opts[i][1]
                    if cur is None or cur.get('closed'):
                        # a question: heading lines are its title+body
                        cur=dict(kind='q',head=head,body=[],opts=[],page=pi,col=c); cons.append(cur); head=[]
                    cur['opts'].append(ot)
            if head: cons.append(dict(kind='x',head=head,page=pi,col=c))
    sty=sorted({h[0] if not isinstance(h,str) else h for c in cons if c['kind']=='x' for h in c['head'] if re.fullmatch(r'[A-Z0-9][A-Z0-9-]{2,}',(h[0] if not isinstance(h,str) else h)) and not re.fullmatch(r'\d+',(h[0] if not isinstance(h,str) else h))})
    return dict(file=os.path.basename(path),ovals=nov,used=used,style=sty,contests=cons,bad=bad)
if __name__=='__main__':
    out=[parse(sys.argv[1]+'/'+f) for f in sorted(os.listdir(sys.argv[1]))]
    json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False); print('DONE',len(out))
