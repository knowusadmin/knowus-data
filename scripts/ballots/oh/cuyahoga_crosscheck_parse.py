
import pdfplumber,re,json,sys
def items(pg):
    ws=pg.extract_words(extra_attrs=['fontname','size'])
    ov=[c for c in pg.curves if 12<=c['x1']-c['x0']<=14 and 7.5<=c['bottom']-c['top']<=9.6]
    o2=[]
    for c in sorted(ov,key=lambda c:(c['x0'],c['top'])):
        if not any(abs(c['x0']-a)<=4 and abs(c['top']-b)<=3 for a,b in o2): o2.append((c['x0'],c['top']))
    lines=[]
    for w in ws:
        if not (95<w['top']<1135): continue
        b='Bold' in w['fontname']
        col=0 if w['x0']<200 else 1 if w['x0']<390 else 2
        for L in lines:
            if L['col']==col and L['b']==b and abs(L['top']-w['top'])<=2 and abs(L['size']-w['size'])<0.6 and w['x0']-L['x1']<25:
                L['w'].append(w); L['x1']=w['x1']; break
        else: lines.append(dict(col=col,b=b,top=w['top'],x=w['x0'],x1=w['x1'],size=round(w['size'],1),w=[w]))
    for L in lines: L['text']=' '.join(x['text'] for x in sorted(L['w'],key=lambda x:x['x0'])); del L['w']
    O=[dict(col=0 if x<200 else 1 if x<390 else 2,top=t,x=x) for x,t in o2]
    foot=' '.join(w['text'] for w in ws if w['top']>1185)
    return lines,O,foot

COLX={0:28,1:222,2:398}
def fix(s): return re.sub(r'(\d-)\s+(\d)',r'\1\2',re.sub(r'\s+',' ',s)).strip()
def blocks_of(ind):
    B=[]
    for l in ind:
        if B:
            last=B[-1][-1]
            if l['top']-last['top']<=15 and not (l['size']>=11 and last['size']<11):
                B[-1].append(l); continue
        B.append([l])
    return B
def parse_ballot(pitems):
    contests=[]; bad=[]; nov=0; used=0
    for pi,(lines,O,foot) in enumerate(pitems):
        nov+=len(O)
        for col in (0,1,2):
            Ls=sorted([l for l in lines if l['col']==col and l['top']>115],key=lambda l:l['top'])
            Os=sorted([o for o in O if o['col']==col],key=lambda o:o['top'])
            cx=(sorted(o['x'] for o in Os)[len(Os)//2]+2) if Os else COLX[col]
            heads=[]
            for l in Ls:
                if not l['b'] or l['size']<11.5 or abs(l['x']-cx)>6: continue
                if l['text'].startswith('For '): heads.append(('r',l))
                elif re.match(r'^(Issue \d+|\d{1,3})$',l['text']): heads.append(('q',l))
            if Os and (not heads or Os[0]['top']<heads[0][1]['top']): bad.append(f'p{pi} c{col}: oval before any header')
            for hi,(kind,h) in enumerate(heads):
                end=heads[hi+1][1]['top'] if hi+1<len(heads) else 1e9
                blk=[l for l in Ls if h['top']<=l['top']<end]
                bo=[o for o in Os if h['top']<o['top']<end-2]
                used+=len(bo)
                ind=[l for l in blk if l['b'] and l['x']>cx+10]
                if kind=='r':
                    first=ind[0]['top'] if ind else 1e9
                    hdr=[l for l in blk if l['b'] and l['x']<=cx+8 and l['top']<first]
                    title=fix(' '.join(l['text'] for l in hdr if l['size']>=11.5 and not l['text'].startswith('(Vote')))
                    vfl=[l['text'] for l in hdr if l['text'].startswith('(Vote for not more than')]
                    vf=re.search(r'than (\d+)',vfl[0]).group(1) if vfl else ''
                    notes=[fix(l['text']) for l in hdr if l['size']<11.5 and not l['text'].startswith('(Vote')]
                else:
                    num=re.sub(r'^Issue ','',h['text']); tl=[]
                    for l in blk[1:]:
                        if not l['b'] or l['size']<11: break
                        tl.append(l['text'])
                    title=fix(' '.join(tl))
                bl=blocks_of(ind)
                if len(bl)!=len(bo): bad.append(f'p{pi} c{col} {title[:40]}: {len(bl)} options, {len(bo)} ovals'); continue
                opts=[]
                for b,o in zip(bl,bo):
                    if abs(b[0]['top']-o['top'])>16: bad.append(f'p{pi} c{col} {title[:40]}: option {b[0]["text"]} far from oval')
                    nm=fix(' '.join(l['text'] for l in b if l['size']>=10.5)); pt=fix(' '.join(l['text'] for l in b if l['size']<10.5))
                    if kind=='r':
                        if not nm and pt.startswith('Write-in'): opts.append(['__WI__','']); continue
                        if not nm: bad.append(f'{title[:30]}: empty name'); 
                        opts.append([nm,pt.rstrip('/ ').strip()])
                    else: opts.append((nm or pt).rstrip('/ ').strip())
                if kind=='r': contests.append(dict(t='r',title=title,vf=vf,notes=notes,opts=opts,page=pi,col=col))
                else: contests.append(dict(t='q',num=num,title=title,opts=opts,page=pi,col=col))
    if used!=nov: bad.append(f'{nov} ovals on the ballot, {used} assigned')
    return contests,bad,nov,used
def split_ballots(pdf):
    cur=None; out=[]
    for i,pg in enumerate(pdf.pages):
        ws=pg.extract_words()
        foot=' '.join(w['text'] for w in ws if w['top']>1185)
        m=re.search(r'\[([A-Z0-9]+)\]',foot)
        code=m.group(1) if m else None
        head=' '.join(w['text'] for w in ws if 100<w['top']<115 and w['x0']<300)
        if code is None: out.append(('?',head,[i])); cur=None; continue
        if cur and cur[0]==code: cur[2].append(i)
        else: cur=(code,head,[i]); out.append(cur)
    return out

def run(pdfpath,out):
    pdf=pdfplumber.open(pdfpath); res=[]; cur=None
    def flush():
        if cur:
            c,bad,nov,used=parse_ballot(cur['items'])
            res.append(dict(code=cur['code'],head=cur['head'],pages=cur['pages'],contests=c,bad=bad,ovals=nov))
    for i,pg in enumerate(pdf.pages):
        it=items(pg); foot=it[2]
        m=re.search(r'\[([A-Z0-9]+)\]',foot); code=m.group(1) if m else '?'+str(i)
        head=' '.join(l['text'] for l in it[0] if l['b'] and 100<l['top']<115 and l['col']==0)
        if cur and cur['code']==code: cur['items'].append(it); cur['pages'].append(i)
        else:
            flush(); cur=dict(code=code,head=head,pages=[i],items=[it])
        pg.close()
        if i%50==0: print(pdfpath[-12:],i,len(res),flush=True)
    flush()
    json.dump(res,open(out,'w')); print('DONE',len(res),sum(1 for r in res if r['bad']),flush=True)
if __name__=='__main__':
    for a in sys.argv[1:]:
        run(a, a.replace('.pdf','.parsed.json'))
