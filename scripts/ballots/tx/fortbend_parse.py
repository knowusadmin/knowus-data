
# Fort Bend County TX 2026 General: parse one ballot-style PDF (3 columns, English bold title, "Vote for", Spanish italic, candidates bold + party)
import pdfplumber,re,json,sys,os
PARTY={'REP','DEM','LIB','GRE','IND','NON'}
def lines(pg):
    ws=pg.extract_words(x_tolerance=1,extra_attrs=['fontname','size'])
    ws=[w for w in ws if 5.5<=w['size']<=16]
    W=pg.width; c1,c2=W*0.36,W*0.64
    L=[]
    for w in sorted(ws,key=lambda w:(round(w['top']),w['x0'])):
        c=0 if w['x0']<c1 else 1 if w['x0']<c2 else 2
        b='Bold' in w['fontname']; it='Italic' in w['fontname']
        for x in L:
            if x['c']==c and abs(x['t']-w['top'])<=2.5 and w['x0']-x['x1']<12 and x['b']==b and x['it']==it:
                x['w'].append(w['text']); x['x1']=w['x1']; break
        else: L.append(dict(c=c,t=w['top'],x0=w['x0'],x1=w['x1'],b=b,it=it,w=[w['text']],sz=w['size']))
    for x in L: x['text']=' '.join(x['w'])
    return L
def parse(path):
    pdf=pdfplumber.open(path); hdr=None; cons=[]; ovals=0; stray=[]
    for pi,pg in enumerate(pdf.pages):
        ovals+=sum(1 for c in pg.curves if 7<=c['width']<=11 and 5<=c['height']<=7.5 and not (pi==0 and c['x0']<235 and c['top']<372))
        L=lines(pg)
        OV=[(c['x0'],c['top']) for c in pg.curves if 7<=c['width']<=11 and 5<=c['height']<=7.5]
        def has_oval(l): return any(abs(oy-l['t'])<7 and -2<l['x0']-ox<40 for ox,oy in OV)
        for x in L:
            m=re.search(r'Precinct Precinto (\d+) BS (\d+)',x['text'])
            if m: hdr=(m[1],m[2])
        for c in (0,1,2):
            Ls=sorted([l for l in L if l['c']==c],key=lambda l:l['t'])
            if not Ls: continue
            colx=min(l['x0'] for l in Ls if l['b'] and not l['it']) if any(l['b'] and not l['it'] for l in Ls) else 0
            cur=None; title=[]; state='title'
            for l in Ls:
                t=l['text']
                m=re.match(r'(?:Precinct )?(\d{4}) BS (\d+)$',t)
                if m: hdr=(m[1],m[2]); continue
                if re.match(r'^(Precinct|Precinto|Instruction Text:|Nota de Instrucci|GENERAL ELECTION|Vote Both Sides|Vote Ambos Lados|Early Voting Clerk)',t) or t.startswith('•') or (l['c']==0 and 110<l['t']<372 and l['x0']<235 and pi==0): continue
                if re.search(r'Precinct Precinto|OFFICIAL BALLOT|BOLETA OFICIAL|Fort Bend County|November 3, 2026|General Election|Elección General|Condado de|de Noviembre',t) and l['t']<120: continue
                if l['it'] and not re.match(r'Vote por',t):
                    if cur is not None and cur['kind']=='q' and state=='body': cur['es'].append(t)
                    continue
                if re.match(r'Vote por',t): state='cands' if cur and cur['kind']=='r' else state; continue
                if re.match(r'Vote for',t):
                    cur=dict(kind='r',title=' '.join(title),tl=list(title),vf=t,c=[],wi=0,page=pi,col=c); cons.append(cur); title=[]; state='es'; continue
                if re.match(r'PROPOSITION|PROPOSICI',t) and l['b']:
                    cur=dict(kind='q',title=t,body=[],es=[],opts=[],page=pi,col=c); cons.append(cur); title=[]; state='body'; continue
                if cur is not None and cur['kind']=='q' and state=='body':
                    if t in ('FOR','AGAINST','A FAVOR','EN CONTRA') or re.match(r'^(FOR|AGAINST|YES|NO)\b',t) and len(t)<14:
                        cur['opts'].append(t); continue
                    if cur['opts'] and l['b']: state='title'; cur=None
                    else: cur['body'].append(t); continue
                if cur is not None and cur['kind']=='r' and state in ('es','cands'):
                    if t in PARTY:
                        if cur['c'] and abs(cur['c'][-1][2]-l['t'])<4 and not cur['c'][-1][1]: cur['c'][-1][1]=t
                        else: stray.append('party?'+t)
                        continue
                    if re.match(r'Write-in|Voto [Ee]scrito',t): cur['wi']+=1; continue
                    if l['b'] and l['x0']>colx+12 and cur['c'] and not has_oval(l) and l['t']-cur['c'][-1][2]<14:
                        cur['c'][-1][0]+=' '+t; cur['c'][-1][2]=l['t']; continue
                    if l['b'] and l['x0']>colx+12:
                        state='cands'; m=re.match(r'^(.*?)\s+(REP|DEM|LIB|GRE|IND)$',t)
                        cur['c'].append([m[1],m[2],l['t']] if m else [t,'',l['t']]); continue
                    if l['b'] and l['x0']<=colx+12: state='title'; cur=None
                if l['b'] and not l['it']:
                    title.append(t)
                else: stray.append(t)
    # attach parties printed on their own line: handled in post (party words at right on the same line are merged above)
    grp=None
    for c in cons:
        if c['kind']!='r': continue
        c['c']=[x[:2] for x in c['c']]
        tl=c.pop('tl',[c['title']])
        sub=re.compile(r'^(TRUSTEE|DIRECTOR|COUNCIL ?MEMBER|COUNCILMEMBER|PLACE|POSITION|DISTRICT NO|AT[- ]LARGE)',re.I)
        if len(tl)>1 and sub.match(tl[-1]): grp=' '.join(tl[:-1]); c['title']=grp+' — '+tl[-1]; c['grp']=grp
        elif len(tl)==1 and sub.match(tl[0]) and grp: c['title']=grp+' — '+tl[0]; c['grp']=grp
        else: grp=None
    nopt=sum(len(c['c'])+c['wi'] if c['kind']=='r' else len(c['opts']) for c in cons)
    return dict(file=os.path.basename(path),hdr=hdr,nopt=nopt,ovals=ovals,contests=cons,stray=stray[:40])
if __name__=='__main__':
    D=sys.argv[1]; out=[]
    for i,f in enumerate(sorted(os.listdir(D))):
        try: out.append(parse(D+'/'+f))
        except Exception as e: out.append(dict(file=f,error=repr(e)))
        if i%25==0: print(i,flush=True)
    json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False); print('DONE',len(out),flush=True)
