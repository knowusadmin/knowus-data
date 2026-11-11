
import pdfplumber,re,json,sys
OVX=[52,233,415]
def colof(x):
    return 0 if x<OVX[1]-3 else 1 if x<OVX[2]-3 else 2
def items(pg):
    ws=pg.extract_words(x_tolerance=1.2,extra_attrs=['fontname','size'])
    TOPCUT=190 if any(w['text'].startswith('Instructions') for w in ws if w['top']<190) else 25
    O=[dict(col=colof(r['x0']),top=r['top'],x=r['x0']) for r in pg.rects if 21<=r['width']<=25 and 12<=r['height']<=16]
    lines=[]
    for w in ws:
        if w['top']<TOPCUT or w['top']>1215: continue
        if 'Code39' in w['fontname']: continue
        col=colof(w['x0']); b='Bold' in w['fontname']
        for L in lines:
            if L['col']==col and abs(L['top']-w['top'])<=2 and L['b']==b and w['x0']-L['x1']<12:
                L['w'].append(w); L['x1']=w['x1']; break
        else: lines.append(dict(col=col,top=w['top'],x=w['x0'],x1=w['x1'],b=b,size=round(w['size'],1),w=[w]))
    for L in lines: L['text']=' '.join(x['text'] for x in sorted(L['w'],key=lambda x:x['x0'])); del L['w']
    txt=' '.join(w['text'] for w in ws if w['top']<190)
    m=re.search(r'PCT\.\s*(\S+)',txt)
    return lines,O,(m.group(1) if m else None)
VF=re.compile(r'^\(Vote for (One|Two|Three|Four|Five|Six|Seven|\d+)\)$')
def parse(items_list):
    res=[]; bad=[]; nov=0; used=0
    for pi,(lines,O,_) in enumerate(items_list):
        nov+=len(O)
        for col in (0,1,2):
            Ls=sorted([l for l in lines if l['col']==col],key=lambda l:l['top']); Os=sorted([o for o in O if o['col']==col],key=lambda o:o['top'])
            ox=OVX[col]
            # option text lines start at ox+20..ox+30 ; header lines at ox+4..ox+9
            heads=[i for i,l in enumerate(Ls) if l['b'] and abs(l['x']-(ox+6))<=4 and (i==0 or not (Ls[i-1]['b'] and abs(Ls[i-1]['x']-(ox+6))<=4 and l['top']-Ls[i-1]['top']<12))]
            # merge: header = consecutive bold lines; a header that directly follows a "(Vote for" line or is Spanish is part of same contest: we treat English header as one immediately followed (after its bold lines) by "(Vote for" or by text lines
            starts=[]
            for i in heads:
                prev=[l for l in Ls[:i] if l['top']<Ls[i]['top']]
                # Spanish header: previous non-empty line is "(Vote for ...)" -> continuation
                if prev and VF.match(prev[-1]['text']): continue
                starts.append(i)
            if Os and (not starts or Os[0]['top']<Ls[starts[0]]['top']): bad.append(f'p{pi} c{col}: oval before header')
            for si,i in enumerate(starts):
                end=Ls[starts[si+1]]['top'] if si+1<len(starts) else 1e9
                blk=[l for l in Ls if Ls[i]['top']<=l['top']<end]
                bo=[o for o in Os if Ls[i]['top']<o['top']<end]; used+=len(bo)
                title=[]; 
                for l in blk:
                    if l['b'] and abs(l['x']-(ox+6))<=4: title.append(l['text'])
                    else: break
                vfl=[l['text'] for l in blk if VF.match(l['text'])]
                opts=[]
                for k,o in enumerate(bo):
                    nxt=bo[k+1]['top'] if k+1<len(bo) else end
                    tl=[l for l in blk if o['top']-2<=l['top']<min(nxt-2,o['top']+40) and l['x']>=ox+20 and not l['b'] or (o['top']-2<=l['top']<min(nxt-2,o['top']+40) and l['x']>=ox+20 and l['b'])]
                    tl=[l for l in tl if l['x']>=ox+20]
                    opts.append([ (l['x']-ox,l['text']) for l in tl])
                res.append(dict(page=pi,col=col,title=title,vf=vfl[0] if vfl else '',opts=opts,body=[l['text'] for l in blk if l['x']<ox+20 and not l['b'] and not VF.match(l['text']) and not l['text'].startswith('(Vote por')][:60]))
    if nov!=used: bad.append(f'{nov} ovals, {used} assigned')
    return res,bad,nov

def parse2(items_list):
    """sequence of contests: races (title,vf,cands) and measures (context text, options)"""
    seq=[]; bad=[]; nov=0; used=0
    for pi,(lines,O,_) in enumerate(items_list):
        nov+=len(O)
        for col in (0,1,2):
            ox=OVX[col]
            Ls=sorted([l for l in lines if l['col']==col],key=lambda l:l['top']); Os=sorted([o for o in O if o['col']==col],key=lambda o:o['top'])
            ev=sorted([('L',l['top'],l) for l in Ls]+[('O',o['top']-1.5,o) for o in Os],key=lambda e:e[1])
            ctx=[]; i=0
            while i<len(ev):
                k,t,x=ev[i]
                if k=='L':
                    ctx.append(x); i+=1; continue
                # an oval run: consecutive ovals with their option lines
                run=[]
                while i<len(ev):
                    k,t,x=ev[i]
                    if k=='O': run.append([x,[]]); i+=1; continue
                    if run and x['x']>=ox+20 and x['top']-run[-1][0]['top']<40: run[-1][1].append(x); i+=1; continue
                    break
                used+=len(run)
                opts=[[ (l['x']-ox,l['text'],l['b']) for l in r[1]] for r in run]
                # header: bold lines at ox+6 in ctx
                hdr=[l for l in ctx if l['b'] and abs(l['x']-(ox+6))<=4]
                vf=[l['text'] for l in ctx if VF.match(l['text'])]
                seq.append(dict(page=pi,col=col,ctx=[(l['text'],l['b'],round(l['x']-ox)) for l in ctx],vf=vf,opts=opts))
                ctx=[]
            if ctx: seq.append(dict(page=pi,col=col,ctx=[(l['text'],l['b'],round(l['x']-ox)) for l in ctx],vf=[],opts=[]))
    if nov!=used: bad.append(f'{nov} ovals, {used} assigned')
    return seq,bad,nov

JUNK=re.compile(r'^(PCT\.|Vote Both|Sides of Page|la Página|Side / Lado|Vote en Ambos)')
ES=set('de la el los las del que para por una en se al su sus con como o y un es lo ser sobre más ciudad condado distrito enmienda pregunta artículo sección municipio'.split())
EN=set('the of to and for in be shall a an by this is on as with or that from city county district amendment question article section'.split())
def lang(t):
    w=re.findall(r"[a-záéíóúñü]+",t.lower()); e=sum(x in EN for x in w); s=sum(x in ES for x in w)
    if re.search(r'[ñ¿áéíóú]',t.lower()): s+=2
    return 'es' if s>e else 'en' if e>s else '?'
def contests(seq):
    out=[]; carry=[]
    for s in seq:
        ctx=[c for c in s['ctx'] if not JUNK.match(c[0])]
        if not s['opts']:
            carry+=ctx; continue
        ctx=carry+ctx; carry=[]
        opts=[[t for _,t,_ in o] for o in s['opts']]
        if s['vf']:
            t_=[]; 
            for c in ctx:
                if c[0].startswith('(Vote for'): break
                if c[1]: t_.append(c[0])
            vf=VF.match(s['vf'][0]).group(1)
            cands=[]; wi=0
            for o,raw in zip(opts,s['opts']):
                if o and o[0].startswith('Write-in'): wi+=1; continue
                # name at x~23, party token at end of first line or separate line at x>=120 (3-letter code)
                first=o[0]; party=''
                m=re.match(r'^(.*\S)\s+([A-Z]{3})$',first)
                if m: first,party=m.group(1),m.group(2)
                rest=[]
                for t in o[1:]:
                    if re.fullmatch(r'[A-Z]{3}',t): party=t
                    else: rest.append(t)
                cands.append([' and '.join([first]+rest) if rest else first, party])
            out.append(dict(t='r',title=' '.join(t_),vf=vf,c=cands,wi=wi))
        else:
            en=[c[0] for c in ctx if lang(c[0])!='es']
            out.append(dict(t='q',ctx=[c[0] for c in ctx],en=en,r=[o[0] for o in opts]))
    return out

def run(path,a,b,out):
    pdf=pdfplumber.open(path); N=len(pdf.pages); res=[]; cur=None
    def isstart(pg): return any(w['text'].startswith('Instructions') for w in pg.extract_words() if w['top']<190)
    i=a
    while i<N and not isstart(pdf.pages[i]): i+=1
    while i<N:
        pg=pdf.pages[i]; st=isstart(pg)
        if st and i>=b: break
        it=items(pg)
        if st:
            if cur: res.append(cur)
            cur=dict(pct=it[2],pages=[i],items=[it])
        else: cur['pages'].append(i); cur['items'].append(it)
        pg.close(); i+=1
        if i%100==0: print(i,len(res),flush=True)
    if cur: res.append(cur)
    outl=[]
    for r in res:
        seq,bad,nov=parse2(r['items']); C=contests(seq)
        pcts=set(x[2] for x in r['items'] if x[2])
        if len(pcts)!=1: bad.append('pct labels '+str(pcts))
        outl.append(dict(pct=r['pct'],pages=r['pages'],bad=bad,ovals=nov,contests=C))
    json.dump(outl,open(out,'w')); print('DONE',len(outl),sum(1 for r in outl if r['bad']),flush=True)
if __name__=='__main__':
    run(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4])
