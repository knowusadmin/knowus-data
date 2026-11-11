
import pdfplumber,re,json,sys,os
OVX=[37,219,400]
def col(x): return 0 if x<212 else 1 if x<395 else 2
VF=re.compile(r'^\(Vote for (?:up to )?(One|Two|Three|Four|Five|\d+)\)')
ESW=re.compile(r'^(¿|Deber|Renovaci|Para |Propuesta|Esta enmienda|Enmienda|Enmiendas|Referendo|Junta|Comisionad|Senador|Representante|Gobernador|Fiscal|Director|Juez|Tribunal|Distrito|Grupo|N\.º|Artículo|Corte|Alcalde|Supervisor de|Miembro|Concejal|Ciudad|Pregunta|Asiento|Puesto|Distrito)')
def clean(pg):
    return pg.dedupe_chars(tolerance=1.2).filter(lambda o: not (o.get('object_type')=='char' and o.get('size',0)>25))
def lines_of(pg):
    q=clean(pg)
    ws=q.extract_words(x_tolerance=1.5,extra_attrs=['fontname','size'])
    lab=None
    for w in pg.extract_words(extra_attrs=['size']):
        if 30<w['size']<40 and re.fullmatch(r'\d{3,5}[A-Z]?',w['text']): lab=w['text']
    TOP=18
    ins=[w for w in ws if w['text']=='Instrucciones:']
    if ins:
        TOP=max(w['bottom'] for w in ws if ins[0]['top']-2<w['top']<ins[0]['top']+45)+3
    ov=[]
    for c in pg.curves:
        if 8<=c['width']<=10.5 and 5<=c['height']<=7.5 and TOP-5<c['top']<1150:
            if not any(abs(c['x0']-a)<2.5 and abs(c['top']-b)<2.5 for a,b in ov): ov.append((c['x0'],c['top']))
    O=[(col(x),t) for x,t in ov]
    L=[]
    for w in ws:
        if w['top']<TOP or w['top']>1150: continue
        c=col(w['x0']); b='Bold' in w['fontname']
        for x in L:
            if x['c']==c and abs(x['t']-w['top'])<=2 and x['b']==b and w['x0']-x['x1']<12: x['w'].append(w['text']); x['x1']=w['x1']; break
        else: L.append(dict(c=c,t=w['top'],x=w['x0']-OVX[c],x1=w['x1'],b=b,w=[w['text']]))
    for x in L: x['text']=' '.join(x['w']); del x['w']
    start=bool(ins)
    return lab,start,L,O
def parse_ballot(pages):
    cons=[]; nov=0; used=0; bad=[]
    for (L,O) in pages:
        nov+=len(O)
        for c in (0,1,2):
            Ls=sorted([l for l in L if l['c']==c],key=lambda l:l['t']); Os=sorted([o[1] for o in O if o[0]==c])
            heads=[]; prevb=False
            for i,l in enumerate(Ls):
                hb=l['b'] and -3<=l['x']<=4
                if hb and not prevb: heads.append(i)
                prevb=hb
            starts=[]
            for i in heads:
                if not starts: starts.append(i); continue
                if any(Ls[starts[-1]]['t']<o<Ls[i]['t'] for o in Os): starts.append(i)
            if Os and (not starts or Os[0]<Ls[starts[0]]['t']): bad.append(f'c{c}: oval before first head')
            for si,i in enumerate(starts):
                end=Ls[starts[si+1]]['t']-1 if si+1<len(starts) else 1e9
                blk=[l for l in Ls if Ls[i]['t']<=l['t']<end]
                bo=[o for o in Os if Ls[i]['t']<o<end]; used+=len(bo)
                bold=[]
                for l in blk:
                    if l['b'] and -3<=l['x']<=4: bold.append(l['text'])
                    else: break
                vf=[l['text'] for l in blk if VF.match(l['text'])]
                # option lines: text at x>=14 in [o-6, next_o-6)
                opts=[]
                for k,o in enumerate(bo):
                    nx=bo[k+1] if k+1<len(bo) else end
                    tl=[l for l in blk if o-7<=l['t']<min(nx-7,o+40) and l['x']>=12]
                    opts.append([[round(l['x']),l['text'],l['t']] for l in tl])
                if vf:
                    cons.append(dict(kind='r',bold=bold,vf=vf[0],opts=opts))
                else:
                    # split into questions: groups of ovals separated by body text
                    body=[l for l in blk if l['x']<12 and l['t']>Ls[i]['t'] and l['text'] not in bold]
                    groups=[]; cur=None
                    for k,o in enumerate(bo):
                        if cur and not any(cur['last']<l['t']<o-7 and l['x']<12 for l in blk): cur['o'].append(k); cur['last']=o
                        else:
                            cur=dict(o=[k],first=o,last=o); groups.append(cur)
                    prev=Ls[i]['t']
                    for g in groups:
                        gb=[l for l in blk if prev<=l['t']<g['first']-7 and l['x']<12]
                        cons.append(dict(kind='q',bold=bold,lines=[(l['text'],l['b']) for l in gb],opts=[opts[k] for k in g['o']]))
                        prev=g['last']+1
    if nov!=used: bad.append(f'{nov} ovals, {used} assigned')
    out=[]
    for k in cons:
        if not k['opts']: bad.append('no ovals: '+' / '.join(k['bold'])); continue
        en=[]
        for t in k['bold']:
            if ESW.match(t) or re.search(r'[áéíóúñ¿º]',t): break
            en.append(t)
        if k['kind']=='r':
            cands=[]; wi=0
            for o in k['opts']:
                if not o: bad.append('empty option '+' '.join(en)); continue
                if o[0][1].startswith('Write-in'): wi+=1; continue
                name=[t for x,t,_ in o if not re.fullmatch(r'[A-Z]{3}',t) and x<130]
                party=[t for x,t,_ in o if re.fullmatch(r'[A-Z]{3}',t)]
                m=[re.match(r'^(.*\S)\s+([A-Z]{3})$',n) for n in name]
                if m and m[0]: name[0]=m[0].group(1); party=[m[0].group(2)]+party
                if len(name)>2 or len(set(party))>1: bad.append('odd option '+str(o))
                cands.append([' and '.join(name),party[0] if party else ''])
            out.append(dict(t='r',title=' '.join(en),bold=k['bold'],vf=VF.match(k['vf']).group(1),vfl=k['vf'],c=cands,wi=wi,rf=[[t for x,t,_ in o] for o in k['opts']]))
        else:
            r=[o[0][1] if o else '' for o in k['opts']]; rf=[[t for x,t,_ in o] for o in k['opts']]
            out.append(dict(t='q',title=' '.join(en),bold=k['bold'],lines=k['lines'],r=r,rf=rf))
    return out,bad,nov
def run(path,outp):
    pdf=pdfplumber.open(path); items=[]; lab=None; labs=set()
    for i,pg in enumerate(pdf.pages):
        l,st,L,O=lines_of(pg)
        if l: labs.add(l)
        items.append((L,O)); pg.close()
    C,bad,nov=parse_ballot(items)
    if len(labs)!=1: bad.append('labels '+str(labs))
    return dict(file=os.path.basename(path),label=sorted(labs)[0] if labs else None,ovals=nov,bad=bad,contests=C)
if __name__=='__main__':
    D=sys.argv[1]; fs=sorted(os.listdir(D))[int(sys.argv[2]):int(sys.argv[3])]; out=[]
    for i,f in enumerate(fs):
        try: out.append(run(D+'/'+f,None))
        except Exception as e: out.append(dict(file=f,bad=['crash '+str(e)[:200]],contests=[]))
        if i%10==0: print(i,flush=True)
    json.dump(out,open(sys.argv[4],'w')); print('DONE',len(out),sum(1 for x in out if x['bad']),flush=True)
