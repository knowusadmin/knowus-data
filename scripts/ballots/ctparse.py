
import re, sys, json, subprocess, html, os
from collections import defaultdict, Counter
def words_of(pdf):
    out=subprocess.run(['timeout','-k','5','60','pdftotext','-bbox',pdf,'-'],capture_output=True,text=True).stdout
    pages=[]
    for pg in re.findall(r'<page[^>]*>(.*?)</page>',out,re.S):
        ws=[]
        for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>',pg):
            ws.append(dict(x0=float(m[1]),y0=float(m[2]),x1=float(m[3]),y1=float(m[4]),t=html.unescape(m[5])))
        pages.append(ws)
    return pages
def lines(ws,tol=2.5):
    ws=sorted(ws,key=lambda w:(w['y0'],w['x0'])); L=[]
    for w in ws:
        if L and abs(L[-1][0]['y0']-w['y0'])<tol: L[-1].append(w)
        else: L.append([w])
    res=[]
    for l in L:
        l=sorted(l,key=lambda w:w['x0']); s=l[0]['t']
        for a,b_ in zip(l,l[1:]):
            gap=b_['x0']-a['x1']; h=max(1.0,a['y1']-a['y0'])
            s+=('' if gap<0.5 else ' ')+b_['t']
        res.append(s)
    return res
LAB=re.compile(r'^(\d{1,2})([A-Z])$')
def parse_page(ws):
    labs=[w for w in ws if LAB.match(w['t'])]
    offw=[w for w in ws if w['t'] in('Office','Oficina','Cargo')]
    oy0=min([w['y0'] for w in offw]) if offw else 0
    labs=[w for w in labs if w['y0']>oy0+5]
    if not labs: return None
    cols=defaultdict(list); rows=defaultdict(list)
    for w in labs:
        m=LAB.match(w['t']); cols[int(m[1])].append(w); rows[m[2]].append(w)
    def med(a): a=sorted(a); return a[len(a)//2]
    cx={n:med([(w['x0']+w['x1'])/2 for w in v]) for n,v in cols.items()}
    ry={L:sum(w['y0'] for w in v)/len(v) for L,v in rows.items()}
    ns=sorted(cx); Ls=sorted(ry,key=lambda k:ry[k])
    sp=(cx[ns[-1]]-cx[ns[0]])/max(1,len(ns)-1) if len(ns)>1 else 60
    bounds={}
    for i,n in enumerate(ns):
        lo=(cx[ns[i-1]]+cx[n])/2 if i else cx[n]-sp/2
        hi=(cx[ns[i+1]]+cx[n])/2 if i+1<len(ns) else cx[n]+sp/2
        bounds[n]=(lo,hi)
    left=bounds[ns[0]][0]; right=bounds[ns[-1]][1]
    cols=defaultdict(list)
    for w in labs:
        xc=(w['x0']+w['x1'])/2
        for n in ns:
            if bounds[n][0]<=xc<bounds[n][1]: cols[n].append(w); break
    top=min(ry.values())
    # office header: words above first row label, below "Office"
    off=[w for w in ws if w['t'] in('Office','Oficina') ]
    oy=min([w['y0'] for w in off]) if off else top-120
    hdr={}
    for n in ns:
        lo,hi=bounds[n]
        hw=[w for w in ws if w['y0']>oy-2 and w['y1']<top-1 and lo<=(w['x0']+w['x1'])/2<hi and not re.fullmatch(r'\d{1,2}',w['t'])]
        hdr[n]=' '.join(lines(hw))
    # cells: each name word belongs to the nearest label above it in its column
    lastlab=max(w['y0'] for w in labs)
    nameW=[w for w in ws if left<=(w['x0']+w['x1'])/2<right and w['y0']>top-2 and not LAB.match(w['t']) and w['y0']<lastlab+60]
    cellw=defaultdict(list)
    for w in nameW:
        cxw=(w['x0']+w['x1'])/2
        n=[k for k in ns if bounds[k][0]<=cxw<bounds[k][1]]
        if not n: continue
        n=n[0]
        cand=[l for l in cols[n] if l['y0']<w['y0']-1 and w['y0']-l['y0']<38]
        if not cand: continue
        l=max(cand,key=lambda l:l['y0'])
        cellw[(n,l['t'],round(l['y0']))].append(w)
    # party blocks on the left
    lw=sorted([w for w in ws if w['x1']<left+3 and w['y0']>top-12],key=lambda w:w['y0'])
    blocks=[]
    for w in lw:
        if blocks and w['y0']-blocks[-1]['y1']<9: blocks[-1]['w'].append(w); blocks[-1]['y1']=max(blocks[-1]['y1'],w['y1'])
        else: blocks.append(dict(w=[w],y0=w['y0'],y1=w['y1']))
    for bl in blocks: bl['t']=' '.join(lines(bl['w']))
    cells=[]
    for (n,lt,ly),cw in cellw.items():
        yc=sum((w['y0']+w['y1'])/2 for w in cw)/len(cw)
        bl=min(blocks,key=lambda bl:abs((bl['y0']+bl['y1'])/2-yc)) if blocks else None
        cells.append(dict(col=n,label=lt,y=yc,text=' '.join(lines(cw)),party=bl['t'] if bl else '',pdist=abs((bl['y0']+bl['y1'])/2-yc) if bl else 999))
    cells.sort(key=lambda c:(c['y'],c['col']))
    res=dict(cells=cells,blocks=[(bl['t'],round(bl['y0']),round(bl['y1'])) for bl in blocks])
    lastc=cx[ns[-1]]
    starts=[w for w in ws if (w['t'].lstrip('"\u201c').startswith('Shall') or re.fullmatch(r'\d{1,2}\.',w['t']) or w['t'].startswith('Vote') and False) and w['x0']>lastc+10]
    qx=min([w['x0'] for w in starts]+[right])
    qw=[w for w in ws if w['x0']>=qx-3 and w['y0']>oy-30]
    return dict(cols=ns,hdr=hdr,qlines=lines(qw),right=right,**res)
if __name__=='__main__':
    out={}
    for pdf in sys.argv[2:]:
        town=os.path.basename(pdf)[:-4]; pages=words_of(pdf); txt=subprocess.run(['pdftotext','-layout',pdf,'-'],capture_output=True,text=True).stdout.split('\f')
        out[town]=[]
        for i,ws in enumerate(pages):
            p=parse_page(ws)
            hd='\n'.join((txt[i] if i<len(txt) else '').split('\n')[:14])
            g=lambda pat: (re.search(pat,hd) or [None,None])[1]
            meta=dict(cd=g(r'Congressional District[^\d]{0,40}?(\d+)'),sd=g(r'Senatorial District[^\d]{0,40}?(\d+)'),ad=g(r'Assembly District[^\d]{0,40}?(\d+)'),
                      vd=g(r'Voting District(?:/Distrito Electoral)?[ \t]+([^\n]+?)[ \t]*(?:\n|$)'),page=i+1)
            out[town].append(dict(meta=meta,grid=p))
    json.dump(out,open(sys.argv[1],'w'),indent=0)
