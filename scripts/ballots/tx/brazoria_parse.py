
# Brazoria County TX, Nov 3 2026 General & Joint Election: parse one official precinct sample-ballot PDF
# (3 columns; English title Bold, Spanish Italic; one outlined box per option; party code in Regular after the name; Calibri watermark dropped).
import pdfplumber,re,json,sys,os,collections
PARTY={'REP','DEM','LIB','GRN','IND','NP'}
def fn(o): return o['fontname'].split('+')[-1]
def plines(pg):
    pc=pg.filter(lambda o: o.get('object_type')!='char' or (o['size']>=1 and 'Calibri' not in o['fontname']))
    ws=sorted(pc.extract_words(x_tolerance=1.5,extra_attrs=['fontname','size']),key=lambda w:(round(w['top']),w['x0']))
    L=[]
    for w in ws:
        st=fn(w).split(',')[-1]
        if L and abs(L[-1]['top']-w['top'])<2.5 and 0<=w['x0']-L[-1]['x1']<8 and L[-1]['st']==st:
            L[-1]['text']+=' '+w['text']; L[-1]['x1']=w['x1']
        else: L.append(dict(x0=w['x0'],x1=w['x1'],top=w['top'],st=st,text=w['text']))
    boxes=[r for r in pg.rects if 20.5<=r['width']<=23.5 and 9<=r['height']<=12 and r.get('stroke')]
    return L,boxes
def col(x): return 0 if x<200 else (1 if x<390 else 2)
def parse(path):
    pdf=pdfplumber.open(path); seq=[]; nbox=0; hdr=None
    for pg in pdf.pages:
        L,B=plines(pg); nbox+=len(B)
        for l in L:
            if hdr is None:
                m=re.match(r'^Precinct (\S+)$',l['text'])
                if m: hdr=m[1]
        L=[l for l in L if l['top']>105 and not l['text'].startswith('Read Both Sides')]
        for c in (0,1,2):
            cl=sorted([l for l in L if col(l['x0'])==c],key=lambda l:l['top'])
            # attach party (Regular, same line, right of a Bold) to option lines
            used=set()
            for i,l in enumerate(cl):
                if not (l['st']=='Bold' or (l['st']=='Regular' and l['text']=='Write-in')): continue
                bx=[b for b in B if abs(b['top']-l['top'])<4 and 0<l['x0']-b['x1']<12]
                if bx:
                    party=''
                    cand=[(j,r) for j,r in enumerate(cl) if j!=i and j not in used and r['st']=='Regular' and r['text'] in PARTY and ((abs(r['top']-l['top'])<2.5 and r['x0']>l['x1']) or (2.5<=r['top']-l['top']<17 and r['x0']>=l['x0']-2))]
                    if cand: j,r=min(cand,key=lambda jr:abs(jr[1]['top']-l['top'])); party=r['text']; used.add(j)
                    l['opt']=True; l['party']=party
            att=[b for b in B if col(b['x0'])==c]
            hit=set()
            for l in cl:
                if l.get('opt'):
                    for k,b in enumerate(att):
                        if abs(b['top']-l['top'])<4 and 0<l['x0']-b['x1']<12: hit.add(k)
            extra=[]
            for k,b in enumerate(att):
                if k in hit: continue
                lab=[l for l in cl if l['text']=='Write-in' and 0<l['top']-b['top']<30]
                if not lab: raise Exception('unlabelled box at %d,%d'%(b['x0'],b['top']))
                extra.append(dict(opt=True,text='Write-in',top=b['top'],st='Bold',party=''))
            items=[l for i,l in enumerate(cl) if i not in used and l['st']!='Italic' and not (l['text']=='Write-in' and not l.get('opt'))]+extra
            seq+=sorted(items,key=lambda l:l['top'])
    cons=[]; title=[]; body=[]; header=None; cur=None; last=None
    for l in seq:
        if l.get('opt'):
            if title:
                cur=dict(header=header,title=' '.join(title),body=' '.join(body),opts=[],wi=0); cons.append(cur); title=[]; body=[]
            if cur is None: raise Exception('option before title: '+l['text'])
            t=l['text']
            if t.startswith('Write-in'): cur['wi']+=1
            else: cur['opts'].append([t,l['party']])
            last='opt'; continue
        if l['st']=='Bold':
            if title and last=='title' and l['top']-ltop<16: title.append(l['text']); ltop=l['top']; continue
            if title:  # a bold block followed by another bold block: it was a section header
                header=' '.join(title) if '=' not in ' '.join(title) else None
            title=[l['text']]; body=[]; ltop=l['top']; last='title'; cur=None; continue
        if l['st']=='Regular':
            if title: body.append(l['text']); last='body'
            elif cur is not None and re.match(r'^Vote for',l['text']): cur.setdefault('vf',l['text'])
            continue
    nopt=sum(len(c['opts'])+c['wi'] for c in cons)
    return dict(file=os.path.basename(path),prec=hdr,nbox=nbox,nopt=nopt,contests=cons)
if __name__=='__main__':
    D=sys.argv[1]; res=[]
    for f in sorted(os.listdir(D)):
        try: res.append(parse(D+'/'+f))
        except Exception as e: res.append(dict(file=f,error=repr(e)))
        print(f,flush=True)
    json.dump(res,open(sys.argv[2],'w'),ensure_ascii=False,indent=0); print('DONE',flush=True)
