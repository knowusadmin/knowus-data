
import pdfplumber,re,json,sys
OVX=[34,215,397]
def col(x): return 0 if x<210 else 1 if x<392 else 2
VF=re.compile(r'^\(Vote for (One|Two|Three|Four|Five|\d+)\)')
ES=re.compile(r'^(Senador|Representante|Gobernador|Procurador|Director|Comisionad|Secretari|Corte|Juez|Jueza|Alcalde|Supervisor de|Miembro|Distrito|Grupo|N\.º|Artículo|Pregunta|Fondo|Exención|Aumento|Tribunal|Consejo|Comisi|Ciudad|Sección|Junta|Agua|Asiento|Escaño|Puesto|Distrito de|Referéndum|Elección|Impuesto|Aprobación|Enmienda|Muebles|Agrícolas|Exenci|Límite|Bonos|Bono|Propuesta|Programa)')
def lines_of(pg):
    ws=pg.extract_words(x_tolerance=1.2,extra_attrs=['fontname','size'])
    top=pg.crop((0,0,612,140)).extract_text() or ''
    m=re.search(r'Official General Election Ballot\s*\n(.+)',top); lab=m.group(1).strip() if m else None
    start=any(w['text'].startswith('Instructions') for w in ws)
    TOP=235 if start else 30
    O=[(col(r['x0']),r['top']) for r in pg.rects if 21<=r['width']<=25 and 12<=r['height']<=16 and r['top']>TOP-5]
    L=[]
    for w in ws:
        if w['top']<TOP or w['top']>1160 or 'Helvetica' in w['fontname'] or 'Code39' in w['fontname']: continue
        c=col(w['x0']); b='Bold' in w['fontname']
        for x in L:
            if x['c']==c and abs(x['t']-w['top'])<=2 and x['b']==b and w['x0']-x['x1']<12: x['w'].append(w['text']); x['x1']=w['x1']; break
        else: L.append(dict(c=c,t=w['top'],x=w['x0']-OVX[c],x1=w['x1'],b=b,w=[w['text']]))
    for x in L: x['text']=' '.join(x['w']); del x['w']
    # drop continuation of instructions at top of first page cols (non-bold before first bold in col on start page)
    return lab,start,L,O
def parse_ballot(pages):
    cons=[]; nov=0; used=0; bad=[]
    for (L,O) in pages:
        nov+=len(O)
        for c in (0,1,2):
            Ls=sorted([l for l in L if l['c']==c],key=lambda l:l['t']); Os=sorted([o[1] for o in O if o[0]==c])
            # heads: a bold line at x~7 whose previous line is not bold-at-7 (start of a bold run)
            heads=[]; prevb=False
            for i,l in enumerate(Ls):
                hb=l['b'] and abs(l['x']-7)<=3
                if hb and not prevb: heads.append(i)
                prevb=hb
            # bold runs inside measures (Spanish title after English body) are continuations: a head is a new contest only if
            # the previous contest already had ovals before it
            starts=[]
            for i in heads:
                if not starts: starts.append(i); continue
                t0=Ls[starts[-1]]['t']; t1=Ls[i]['t']
                if any(t0<o<t1 for o in Os): starts.append(i)
            if Os and (not starts or Os[0]<Ls[starts[0]]['t']):
                bad.append(f'c{c}: oval before first head')
            for si,i in enumerate(starts):
                end=Ls[starts[si+1]]['t']-1 if si+1<len(starts) else 1e9
                blk=[l for l in Ls if Ls[i]['t']<=l['t']<end]
                bo=[o for o in Os if Ls[i]['t']<o<end]; used+=len(bo)
                bold=[]
                for l in blk:
                    if l['b'] and abs(l['x']-7)<=3: bold.append(l['text'])
                    else: break
                en=[];
                for t in bold:
                    if ES.match(t) or re.search(r'[áéíóúñ¿º]',t): break
                    en.append(t)
                vf=[l['text'] for l in blk if VF.match(l['text'])]
                body=[l['text'] for l in blk if not l['b'] and l['x']<15 and not VF.match(l['text'])]
                opts=[]
                for k,o in enumerate(bo):
                    nx=bo[k+1] if k+1<len(bo) else end
                    tl=[l for l in blk if o-4<=l['t']<nx-4 and l['x']>=18]
                    opts.append([[round(l['x']),l['text']] for l in tl])
                cons.append(dict(title=en,bold=bold,vf=vf[0] if vf else '',body=body,opts=opts))
    if nov!=used: bad.append(f'{nov} ovals, {used} assigned')
    out=[]
    for k in cons:
        if not k['opts']: bad.append('contest without ovals: '+' / '.join(k['bold'])); continue
        if k['vf']:
            cands=[]; wi=0
            for o in k['opts']:
                if not o: bad.append('empty option in '+' '.join(k['title'])); continue
                if o[0][1].startswith('Write-in'): wi+=1; continue
                name=[t for x,t in o if not re.fullmatch(r'[A-Z]{3}',t) and x<150]
                party=[t for x,t in o if re.fullmatch(r'[A-Z]{3}',t)]
                if len(name)>2 or len(party)>1: bad.append('odd option '+str(o))
                cands.append([' and '.join(name),party[0] if party else ''])
            m=VF.match(k['vf']).group(1)
            out.append(dict(t='r',title=' '.join(k['title']),vf=m,c=cands,wi=wi))
        else:
            r=[o[0][1] if o else '' for o in k['opts']]
            out.append(dict(t='q',title=' '.join(k['title']),bold=k['bold'],body=k['body'],r=r))
    return out,bad,nov
def run(path,a,b,outp):
    pdf=pdfplumber.open(path); N=len(pdf.pages); res=[]; cur=None
    for i in range(a,N):
        pg=pdf.pages[i]; lab,start,L,O=lines_of(pg)
        if start and i>=b: break
        if start:
            if cur: res.append(cur)
            cur=dict(label=lab,pages=[i],items=[(L,O)])
        else:
            if cur is None: continue
            cur['pages'].append(i); cur['items'].append((L,O))
            if lab and lab!=cur['label']: cur.setdefault('lab2',[]).append(lab)
        pg.close()
        if i%50==0: print(i,len(res),flush=True)
    if cur: res.append(cur)
    out=[]
    for r in res:
        C,bad,nov=parse_ballot(r['items'])
        if r.get('lab2'): bad.append('label change '+str(r['lab2']))
        out.append(dict(label=r['label'],pages=r['pages'],ovals=nov,bad=bad,contests=C))
    json.dump(out,open(outp,'w')); print('DONE',len(out),sum(1 for x in out if x['bad']),flush=True)
if __name__=='__main__': run(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4])
