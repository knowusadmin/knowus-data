
# Michigan MVIC PublicBallot (Nov 3 2026 State General) ballot HTML -> contests. Used by mi_parse_all.py and mi_build.py.
import re
from bs4 import BeautifulSoup, NavigableString, Tag
def clean(s): return re.sub(r'\s+',' ',s.replace('\xa0',' ')).strip()
def ptext(nodes):
    """Paragraph texts of free HTML nodes (proposal body)."""
    paras=[];cur=[]
    def flush():
        t=clean(''.join(cur))
        if t: paras.append(t)
        cur.clear()
    def walk(n):
        if isinstance(n,NavigableString):
            cur.append(str(n));return
        if not isinstance(n,Tag): return
        if n.name=='br': flush();return
        blk=n.name in ('p','div','li','ul','ol','table','tr','h1','h2','h3','h4')
        if blk: flush()
        for ch in n.children: walk(ch)
        if blk: flush()
    for n in nodes: walk(n)
    flush();return paras
def parse(html):
    sp=BeautifulSoup(html,'lxml')
    hdr=[clean(x) for x in sp.select_one('div.text-center').get_text('\n').split('\n') if clean(x)]
    out=[];sec=div=None
    gen=sp.select_one('#generalElectionOffices')
    cur=None
    if gen:
        for el in gen.find_all('div'):
            cl=el.get('class') or []
            if 'section' in cl: sec=clean(el.get_text(' '))
            elif 'division' in cl: div=clean(el.get_text(' '))
            elif 'office' in cl:
                cur=dict(t='r',sec=sec,div=div,title=clean(el.get_text(' ')),lines=[],vf=None,c=[]);out.append(cur)
            elif 'term' in cl:
                t=clean(el.get_text(' ')); m=re.match(r'^Vote for not more than (-?\d+)$',t)
                if m: cur['vf']=m[1]
                else: cur['lines'].append(t)
            elif 'candidate' in cl:
                nm=[];des=[]
                for ch in el.children:
                    if isinstance(ch,Tag) and 'formerName' in (ch.get('class') or []): des.append(clean(ch.get_text(' ')))
                    elif isinstance(ch,Tag) and ch.name=='br': nm.append('\n')
                    else: nm.append(ch.get_text(' ') if isinstance(ch,Tag) else str(ch))
                names=[clean(x) for x in ''.join(nm).split('\n') if clean(x)]
                pty=el.find_next_sibling('div',class_='party'); pty=clean(pty.get_text(' ')) if pty else ''
                cur['c'].append([' and '.join(names),pty,' '.join(des)])
    ps=sp.select_one('#proposals')
    if ps:
        kids=list(ps.children);cur=None;body=[]
        def close():
            if cur is not None: cur['body']=ptext(body)
        for n in kids:
            if isinstance(n,Tag) and n.name=='div' and 'row' in (n.get('class') or []) and n.find('div',class_=['section','division','proposalTitle']):
                d=n.find('div',class_=['section','division','proposalTitle']);cl=d.get('class')
                if 'section' in cl: sec=clean(d.get_text(' '));continue
                if 'division' in cl: close();cur=None;body=[];div=clean(d.get_text(' '));continue
                close();body=[]
                tl=[clean(x) for x in d.get_text('\n').split('\n') if clean(x)]
                cur=dict(t='q',sec=sec,div=div,title=tl[0],sub=tl[1:]);out.append(cur)
            else:
                if cur is not None: body.append(n)
        close()
    n_cand=len(sp.select('div.candidate')); n_prop=len(sp.select('div.proposalTitle')); n_off=len(sp.select('div.office'))
    chk=dict(cand=n_cand==sum(len(c['c']) for c in out if c['t']=='r'),prop=n_prop==sum(1 for c in out if c['t']=='q'),off=n_off==sum(1 for c in out if c['t']=='r'),
             vf=all(c['vf'] for c in out if c['t']=='r'),nonempty=all(c['c'] for c in out if c['t']=='r'),body=all(c['body'] for c in out if c['t']=='q'))
    return dict(hdr=hdr,contests=out,n_cand=n_cand,n_prop=n_prop,chk=chk)
