
# Bexar County TX, Nov 3 2026 General Election: parse one official individual sample ballot PDF (maps.bexar.org Ballots table ->
# home.bexar.org/electionsresources/ballots/Sample_N.pdf). 3 columns; English Bold titles / Regular names; Spanish Italic dropped;
# one oval (curve ~9x6) per option; party code (REP/DEM/LIB/GRN/IND) right-aligned on the option line.
import pdfplumber,re,json,sys,os
PARTY={'REP':'Republican','DEM':'Democratic','LIB':'Libertarian','GRN':'Green','IND':'Independent'}
VF={'one':'1','two':'2','three':'3','four':'4','five':'5'}
def sty(fn):
    f=fn.split('+')[-1]
    return 'BI' if 'BoldItalic' in f else ('B' if 'Bold' in f else ('I' if 'Italic' in f else 'R'))
def colx(x): return 0 if x<228 else (1 if x<410 else 2)
def page_items(pg):
    ws=pg.extract_words(x_tolerance=1.5,extra_attrs=['fontname','size'])
    ws=sorted(ws,key=lambda w:(colx(w['x0']),round(w['top']),w['x0']))
    L=[]
    for w in ws:
        s=sty(w['fontname']); c=colx(w['x0'])
        if L and L[-1]['c']==c and abs(L[-1]['top']-w['top'])<2.5 and L[-1]['s']==s and 0<=w['x0']-L[-1]['x1']<10:
            L[-1]['text']+=' '+w['text']; L[-1]['x1']=w['x1']
        else: L.append(dict(c=c,x0=w['x0'],x1=w['x1'],top=w['top'],s=s,text=w['text']))
    ov=[dict(c=colx(o['x0']),x0=o['x0'],top=o['top']) for o in pg.curves if 7<=o['width']<=10.5 and 4.5<=o['height']<=7.5]
    return L,ov
def parse(path):
    pdf=pdfplumber.open(path); seq=[]; nov=0; prec=bs=None
    for pi,pg in enumerate(pdf.pages):
        L,OV=page_items(pg); nov+=len(OV)
        for l in L:
            m=re.search(r'Precinct: (\S+) Ballot Style: BS (\d+)',l['text'])
            if m: prec,bs=m[1],m[2]
        hasHdr=any(re.match(r'^(Official Ballot|Sample Ballot)',l['text']) and l['top']<90 for l in L)
        lim=185 if pi==0 else (120 if hasHdr else 45)
        L=[l for l in L if l['top']>lim and l['s'] in ('B','R') and ' = ' not in l['text'] and not re.match(r'^(Legend of Party.*|Vote Both Sides|Page \d+ of \d+|BS \d+|\d{3,4}|MC)$',l['text'])]
        for c in (0,1,2):
            cl=sorted([l for l in L if l['c']==c],key=lambda l:l['top']); ov=sorted([o for o in OV if o['c']==c],key=lambda o:o['top'])
            items=[]; used=set()
            for o in ov:
                al=[i for i,l in enumerate(cl) if abs(l['top']-o['top'])<4.5 and 0<l['x0']-o['x0']<30 and i not in used]
                if al:
                    i=al[0]; used.add(i); l=cl[i]
                    pt=[j for j,r in enumerate(cl) if j not in used and r['s']=='R' and r['text'] in PARTY and abs(r['top']-l['top'])<3 and r['x0']>l['x1']]
                    party=''
                    if pt: used.add(pt[0]); party=PARTY[cl[pt[0]]['text']]
                    items.append(dict(k='opt',top=o['top'],text=l['text'],party=party))
                else:
                    wl=[i for i,l in enumerate(cl) if i not in used and l['text'].startswith('Write-in') and 0<l['top']-o['top']<25]
                    if not wl: raise Exception('unlabelled oval p%d c%d %d'%(pi,c,o['top']))
                    used.add(wl[0]); items.append(dict(k='wi',top=o['top']))
            for i,l in enumerate(cl):
                if i in used: continue
                if l['text'].startswith('Write-in'): continue
                items.append(dict(k=l['s'],top=l['top'],text=l['text']))
            seq+=sorted(items,key=lambda x:x['top'])
    s2=[]
    for it in seq:
        if it['k']=='B' and s2 and s2[-1]['k']=='B' and s2[-1]['text'].startswith('Vote for') and re.match(r'^or \w+$',it['text']): s2[-1]=dict(s2[-1],text=s2[-1]['text']+' '+it['text']); continue
        s2.append(it)
    seq=s2
    if os.environ.get('DBG'): return seq
    # contests
    cons=[]; blocks=[]; body=[]; cur=None; last_top=None; last=None; newblk=False; group=None
    for it in seq:
        k=it['k']
        if k=='B' and re.match(r'^Vote for ',it['text']):
            m=re.match(r'^Vote for none or (\w+)$',it['text']) or re.match(r'^Vote for none,(?: \w+,?)* or (\w+)$',it['text'])
            if not m or not blocks: raise Exception('vote-for '+it['text'])
            title=blocks[-1]
            for h in blocks[:-1]:
                group=None if re.match(r'^[A-Z ]+$',h) and len(h.split())<=3 else h
            cur=dict(t='r',title=title,grp=group,vf=VF[m[1]],c=[],wi=0); cons.append(cur); blocks=[]; body=[]; last='vf'; newblk=False; continue
        if k in ('opt','wi'):
            if cur is None or newblk:
                if not blocks: raise Exception('option with no title '+str(it))
                ti=[i for i,b in enumerate(blocks) if re.search(r'PROPOSITION|AMENDMENT',b,re.I)]
                if not ti: raise Exception('prop title? '+repr(blocks))
                t=ti[-1]; rest=blocks[t+1:]; pre=[b for b in rest if re.match(r'^THIS IS A',b)]; sub=[b for b in rest if not re.match(r'^THIS IS A',b)]
                for h in blocks[:t]:
                    group=None if re.match(r'^[A-Z ]+$',h) and len(h.split())<=3 else h
                cur=dict(t='q',title=blocks[t],grp=group,pre=' '.join(pre),sub=' '.join(sub),q=' '.join(body),r=[],wi=0); cons.append(cur); blocks=[]; body=[]; newblk=False
            if k=='wi': cur['wi']+=1
            elif cur['t']=='r':
                nm,pa=it['text'],it['party']
                m=re.match(r'^(.*\S)\s+(REP|DEM|LIB|GRN|IND)$',nm)
                if m and not pa: nm=m[1]; pa=PARTY[m[2]]
                cur['c'].append([nm,pa])
            else: cur['r'].append(it['text'])
            last='opt'; continue
        if k=='B':
            if last=='block' and 0<it['top']-last_top<13: blocks[-1]+=' '+it['text']
            else:
                if last!='block' and last!='body': blocks=[] if last=='opt' else blocks
                if last=='opt': body=[]
                blocks.append(it['text'])
            newblk=True; last_top=it['top']; last='block'; continue
        if k=='R':
            if blocks: body.append(it['text']); last='body'
            continue
    nopt=sum(len(c['c'] if c['t']=='r' else c['r'])+c['wi'] for c in cons)
    return dict(file=os.path.basename(path),prec=prec,bs=bs,nov=nov,nopt=nopt,contests=cons)
if __name__=='__main__':
    D=sys.argv[1]; res=[]
    fs=sorted(os.listdir(D),key=lambda f:int(re.sub(r'\D','',f) or 0))
    if len(sys.argv)>4: fs=fs[int(sys.argv[3])::int(sys.argv[4])]
    for f in fs:
        try: res.append(parse(D+'/'+f))
        except Exception as e: res.append(dict(file=f,error=repr(e)))
    json.dump(res,open(sys.argv[2],'w'),ensure_ascii=False,indent=0); print('DONE',len(res),flush=True)
