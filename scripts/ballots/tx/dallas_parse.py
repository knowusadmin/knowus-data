# Dallas County TX, Nov 3 2026 General & Joint Election: parse the county's 216 official ballot-style PDFs
# (Clarity Connect SampleBallots/2026/261103GeneralJoint/<n>.pdf). Trilingual EN/ES/VI, 3 columns, one oval per option.
# English race titles Calibri Bold 11, "Vote for" Bold 10; props: section header Bold 9, title Bold 8, body Regular 8.
# The "Uncontested Races" candidate list is an embedded image (OCR'd separately, by image hash).
import pdfplumber,re,json,sys,os,collections,hashlib
PARTIES={'Rep': 'Republican', 'Dem': 'Democratic', 'Lib': 'Libertarian', 'Grn': 'Green', 'Ind': 'Independent', 'REP': 'Republican', 'DEM': 'Democratic', 'LIB': 'Libertarian', 'GRN': 'Green'}
FOOT=re.compile('^(Vote Both Sides|Vote ambos lados|Bỏ phiếu cả hai bên|Phiếu \\d+ trong \\d+|Boleta \\d+ de \\d+|Ballot \\d+ of \\d+)')
def colof(x): return 0 if x<230 else (1 if x<411 else 2)
def lines(pg):
    ws=pg.extract_words(x_tolerance=1.5,extra_attrs=['fontname','size'])
    ws=[w for w in ws if 'Helvetica' not in w['fontname']]
    ws=sorted(ws,key=lambda w:(round(w['top']),w['x0']))
    L=[]
    for w in ws:
        st=w['fontname'].split('+')[-1]; st=('A' if 'Arial' in st else '')+('B' if 'Bold' in st else 'I' if 'Italic' in st else 'R')+str(round(w['size']))
        if L and abs(L[-1]['top']-w['top'])<2.5 and 0<=w['x0']-L[-1]['x1']<12 and L[-1]['st']==st and colof(L[-1]['x0'])==colof(w['x0']):
            L[-1]['text']+=' '+w['text']; L[-1]['x1']=w['x1']
        else: L.append(dict(x0=w['x0'],x1=w['x1'],top=w['top'],st=st,text=w['text']))
    ov=[c for c in pg.curves if 7.5<c['width']<9.5 and 4.5<c['height']<6.5]
    return L,ov
def parse_dallas(path):
    pdf=pdfplumber.open(path); seq=[]; nov=0; style=None; uimgs=[]
    for pi,pg in enumerate(pdf.pages):
        L,ov=lines(pg); nov+=len(ov)
        body=[]
        for l in L:
            if l['top']>1185 and l['st']=='R10' and re.fullmatch(r'\d+',l['text']) and l['x0']<200:
                style=style or l['text']; continue
            if FOOT.match(l['text']) or l['st'].startswith('A') or l['st'] in ('R6',): continue
            if pi==0 and l['top']<120: continue
            if l['text']=='ELECTION JUDGE INITIALS' or re.fullmatch(r'\d+ \d+|\d+',l['text']) and l['st'] in('R10','R8','R6'): continue
            body.append(l)
        for im in pg.images:
            uimgs.append(dict(page=pi,bbox=(im['x0'],im['top'],im['x1'],im['bottom']),sha=__import__('hashlib').sha1(im['stream'].get_data()).hexdigest()))
        for c in (0,1,2):
            cl=sorted([l for l in body if colof(l['x0'])==c],key=lambda l:(l['top'],l['x0']))
            co=sorted([o for o in ov if colof(o['x0'])==c],key=lambda o:o['top'])
            ev=[]; used=set()
            for o in co:
                cand=[(i,l) for i,l in enumerate(cl) if abs(l['top']-(o['top']-2))<5 and 5<l['x0']-o['x1']<30 and i not in used]
                if cand:
                    i,l=min(cand,key=lambda il:il[1]['x0']); used.add(i)
                    party=''
                    for j,r in enumerate(cl):
                        if j!=i and abs(r['top']-l['top'])<2.5 and r['x0']>l['x1'] and r['text'] in PARTIES: party=PARTIES[r['text']]; used.add(j)
                    ev.append(dict(top=o['top']-2,kind='opt',text=l['text'],party=party))
                else:
                    lab=[i for i,l in enumerate(cl) if 'Write-in' in l['text'] and 0<l['top']-o['top']<30]
                    if not lab: raise Exception('unlabelled oval p%d %d,%d'%(pi,o['x0'],o['top']))
                    ev.append(dict(top=o['top'],kind='wi')); used.update(lab)
            for i,l in enumerate(cl):
                if i in used: continue
                ev.append(dict(top=l['top'],kind=l['st'],text=l['text'],x0=l['x0']))
            seq+=sorted(ev,key=lambda e:e['top'])
    return seq,nov,style,uimgs
def build(seq):
    cons=[]; cur=None; title=[]; vf=None; header=None; mode=None; ptitle=None; pbody=[]; state=None
    for e in seq:
        k=e['kind']
        if k in('opt','wi'):
            if state in('title','vf','trans'):
                cur=dict(t='r',title=' '.join(title),vf=vf,header=header,opts=[],wi=0); cons.append(cur); state='opts'
            elif state in('ptitle','pbody','ptrans'):
                cur=dict(t='q',title=ptitle,body=' '.join(pbody),header=header,opts=[],wi=0); cons.append(cur); state='opts'
            elif state=='utext':
                cur=dict(t='u',title='Uncontested Races',header=header,opts=[],wi=0); cons.append(cur); state='opts'
            if cur is None or state!='opts': raise Exception('opt with no contest '+str(e))
            if k=='wi': cur['wi']+=1
            else: cur['opts'].append([e['text'],e['party']])
            continue
        t=e['text']
        if k=='B11':
            if state=='title': title.append(t)
            else: title=[t]; vf=None; state='title'
            continue
        if k=='B10' and re.match(r'^Vote for',t):
            vf=t; state='vf'; continue
        if k=='B9':
            header=t; state='header'
            if t.startswith('Uncontested'): state='utext'
            continue
        if state=='utext': continue
        if k=='B8':
            if state in('header','opts'): ptitle=t; pbody=[]; state='ptitle'; ptop=e['top']
            elif state=='ptitle' and e['top']-ptop<12: ptitle+=' '+t; ptop=e['top']
            elif state=='ptitle' and False: pass
            else: state='ptrans'
            continue
        if k=='R8' and state in('ptitle','pbody'): pbody.append(t); state='pbody'; continue
        if state in('title','vf'): state='trans' if state=='vf' else state
        # other lines ignored (translations)
    return cons

if __name__=='__main__':
    PD=sys.argv[1]; OUT=sys.argv[2]; IMG=sys.argv[3]; os.makedirs(IMG,exist_ok=True); res=[]; seen=set()
    for f in sorted(os.listdir(PD),key=lambda f:int(f.split('.')[0])):
        try:
            seq,nov,style,ui=parse_dallas(PD+'/'+f); cons=build(seq)
            nopt=sum(len(c['opts'])+c['wi'] for c in cons)
            big=[u for u in ui if u['bbox'][3]-u['bbox'][1]>150]
            pdf=pdfplumber.open(PD+'/'+f)
            for u in big:
                if u['sha'] in seen: continue
                seen.add(u['sha']); pdf.pages[u['page']].crop(u['bbox']).to_image(resolution=400).save(IMG+'/'+u['sha']+'.png')
            res.append(dict(file=f,style=style,nov=nov,nopt=nopt,imgs=[u['sha'] for u in big],contests=cons))
        except Exception as e: res.append(dict(file=f,error=repr(e)))
        print(f,flush=True)
    json.dump(res,open(OUT,'w'),ensure_ascii=False); print('DONE',flush=True)
