"""KnowUS source policy checker. The rule lives in data/sources-policy.json (edit that file, not this one).
from sources_policy import ok, classify  ->  ok(url, own_hosts=()) is True when the app may cite url."""
import json,os,re
from urllib.parse import urlparse
HERE=os.path.dirname(os.path.abspath(__file__))
P=json.load(open(os.environ.get('KNOWUS_SOURCES_POLICY') or next(p for p in [os.path.join(HERE,'..','data','sources-policy.json'),os.path.join(HERE,'sources-policy.json')] if os.path.exists(p))))
PATS=[re.compile(p) for p in P['official_patterns']]
_G={}
for _g,_on in P['groups_kept'].items():
    if _g.startswith('_') or not _on: continue
    for _d in P.get(_g,[]): _G.setdefault(_d,_g)
def dom(u):
    try: h=(urlparse(u).hostname or '').lower()
    except Exception: return ''
    return h[4:] if h.startswith('www.') else h
def inner(u):
    m=re.match(r'https?://web\.archive\.org/web/[^/]+/(.*)',u or '')
    if m:
        x=m.group(1); return x if x.startswith('http') else 'http://'+x
    return u
def ends(h,d): return h==d or h.endswith('.'+d)
def classify(url,own_hosts=()):
    """('allowed'|'pending'|'banned'|'none', group)"""
    if not url: return ('none','none')
    h=dom(inner(url))
    if not h: return ('none','none')
    for d,v in P['pending'].items():
        if d.startswith('_'): continue
        if ends(h,d): return ('banned' if v=='ban' else 'pending','pending:'+d)
    for d in P['news_banned']:
        if ends(h,d): return ('banned','news_banned')
    for d in P['news_allowed']:
        if ends(h,d): return ('allowed','news_allowed')
    if any(p.search(h) for p in PATS): return ('allowed','official')
    for oh in own_hosts or ():
        if oh and ends(h,oh): return ('allowed','own_site')
    hs=h.split('.')
    for i in range(len(hs)):
        g=_G.get('.'.join(hs[i:]))
        if g: return ('allowed',g)
    return ('banned','unlisted')
def ok(url,own_hosts=()):
    return classify(url,own_hosts)[0] in ('allowed','pending')
