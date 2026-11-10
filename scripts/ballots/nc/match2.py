
import json,os,re,gzip,collections,unicodedata,glob
NC=os.path.dirname(os.path.abspath(__file__))
S1=json.load(open(f'{NC}/stage1.json')); C=S1['contests']
def nz(s): return re.sub(r'[^A-Z0-9]','',unicodedata.normalize('NFKD',s or '').upper())
keys=[k for k,s in json.load(open(f'{NC}/sb_keys.json')) if k.endswith('.pdf')]
bycounty=collections.defaultdict(list)
for k in keys: bycounty[nz(k.split('/')[-1].split('-')[0])].append(k)
def toks(cid):
    c=C[cid]
    if c['k']=='c': return [nz(n) for n,_ in c['c'] if len(nz(n))>=5]
    return [nz(c['q'])[:60]] if c.get('q') else []
def otoks(cid):
    c=C[cid]
    if c['k']=='c': return [nz(n) for n,_ in c['c'] if len(nz(n))>=5]
    return [nz(c['q'])[:30]] if c.get('q') else []
def streams(lay):
    # per page, per column: the normalized text stream of that column, in reading order
    out=[]
    for pi,pg in enumerate(lay.split('\f')):
        lines=pg.split('\n'); W=max([len(l) for l in lines]+[1])
        cols={}
        for li,l in enumerate(lines):
            for mm in re.finditer(r'\S+(?: {1,2}\S+)*',l):
                b=min(2,int(mm.start()/(W/3.0)))
                cols.setdefault(b,[]).append(nz(mm.group(0)))
        for b in sorted(cols): out.append(((pi,b),''.join(cols[b])))
    return out
def pos_of(st,t):
    for key,s in st:
        i=s.find(t)
        if i>=0: return (key[0],key[1],i)
    return None
styles=collections.defaultdict(dict)
for s in S1['splits']:
    styles[s['county']].setdefault(tuple(s['full']),[]).append(s['id'])
out={};stats=collections.Counter();issues=[];corder=collections.defaultdict(collections.Counter)
for co,st in sorted(styles.items()):
    allc=sorted({c for f in st for c in f})
    T={c:toks(c) for c in allc}
    pdfs=bycounty.get(nz(co),[])
    texts={};lays={}
    for k in pdfs:
        p=f"{NC}/sbtxt/{k.split('/')[-1][:-4]}.txt.gz"
        if os.path.exists(p):
            raw,lay=gzip.open(p,'rt').read().split('\f=====LAYOUT=====\f')
            texts[k]=nz(raw); lays[k]=streams(lay)
    if len(texts)<len(pdfs): issues.append((co,'missing pdf text',len(pdfs)-len(texts)))
    res={}
    for f in st:
        res[f]={'pdfs':[],'order':None}
    for k,tx in texts.items():
        pres={c for c in allc if T[c] and all(t in tx for t in T[c])}
        cands=[]
        for f in st:
            fs=set(f)
            need=[c for c in f if T[c]]
            if not all(c in pres for c in need): continue
            own=set(t for c in f for t in T[c])
            extra=[c for c in pres-fs if any(t not in own for t in T[c])]
            if extra: continue
            cands.append(f)
        if len(cands)==1:
            f=cands[0]; res[f]['pdfs'].append(k)
            pos={}
            for c in f:
                if T[c]:
                    ps=[pos_of(lays[k],t) for t in otoks(c)]
                    ps=[x for x in ps if x]
                    if ps: pos[c]=min(ps)
            for c in f:
                cc=C[c]
                if cc['k']=='c' and len(cc['c'])>1:
                    pp=[(pos_of(lays[k],nz(n)),n) for n,_ in cc['c']]
                    if all(x[0] for x in pp): corder[c][tuple(n for _,n in sorted(pp))]+=1
            miss=[c for c in f if T[c] and c not in pos]
            if any(C[c]['k']!='m' for c in miss): res[f].setdefault('orders',[]); continue
            order=sorted(pos,key=lambda c:pos[c])+sorted(miss,key=lambda c:(C[c]['seq'],C[c]['t']))
            res[f].setdefault('orders',[]).append(tuple(order))
        else:
            stats['pdf '+('unmatched' if not cands else 'ambiguous')]+=1; issues.append((co,k.split('/')[-1],'pdf matched %d styles'%len(cands)))
    ost=[]
    for f,r in res.items():
        os_=r.get('orders') or []
        order=list(collections.Counter(os_).most_common(1)[0][0]) if os_ else None
        nok=[c for c in f if not T[c]]
        if order is not None:
            for c in nok:  # write-in-only: insert before the contest with the longest shared title prefix (else at the end of its section)
                w=C[c]['t'].split(); best=None;bl=0
                for i,o in enumerate(order):
                    ow=C[o]['t'].split(); l=0
                    while l<min(len(w),len(ow)) and w[l]==ow[l]: l+=1
                    if l>bl: bl,best=l,i
                if best is None: order=order+[c]
                else:
                    j=best
                    while j+1<len(order) and len(os.path.commonprefix([C[order[j+1]]['t'].split(),w]))>=bl: j+=1
                    order=order[:j+1]+[c]+order[j+1:]
        ok=bool(r['pdfs']) and order is not None and len(order)==len(f)
        why='' if ok else ('no official sample ballot PDF matched' if not r['pdfs'] else 'printed order could not be read' if order is None else 'order incomplete')
        stats['style ok' if ok else 'style not ok']+=1
        if not ok: issues.append((co,'style',why,len(f)))
        ost.append({'full':list(f),'order':order if order else sorted(f,key=lambda c:(C[c]['seq'] if C[c]['seq'] is not None else 98)),'pdfs':r['pdfs'],'ok':ok,'why':why,'splits':st[f]})
    out[co]=ost
json.dump(out,open(f'{NC}/stage2.json','w'))
co_={c:list(v.most_common(1)[0][0]) for c,v in corder.items()}
mixed=sum(1 for v in corder.values() if len(v)>1)
json.dump(co_,open(f'{NC}/corder.json','w'))
print('candidate order read for',len(co_),'contests; differing between PDFs:',mixed,flush=True)
print(dict(stats),flush=True)
for i in issues[:60]: print(i)
print('issues',len(issues))
