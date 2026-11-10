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

# --- Democratic sources (owner's rule, Nov 9 2026 8:58 PM) ---
_D=P.get('democratic_sources') or {}
_DTOK=re.compile(_D.get('name_token_pattern') or r'$^')
_DSOC=re.compile(r'https?://(?:www\.|mobile\.|m\.)?(twitter\.com|x\.com|facebook\.com|instagram\.com|youtube\.com)/(?:@)?([A-Za-z0-9_.\-]+)')
_SOCK={'twitter.com':'twitter','x.com':'twitter','facebook.com':'facebook','instagram.com':'instagram','youtube.com':'youtube'}
def dem_source(url):
    """None, or (kind, set of owner ids) when url is a Democratic source."""
    if not _D or _D.get('rule')!='ban' or not url: return None
    u=inner(url); m=_DSOC.match(u or '')
    if m:
        b=(_D.get('social_accounts') or {}).get(_SOCK[m.group(1)]+':'+m.group(2).lower())
        if b: return ('social',{b})
    h=dom(u)
    if not h: return None
    ms=_D.get('member_sites') or {}
    if h in ms: return ('member',set(ms[h]))
    for grp in ('officeholder_sites','campaign_sites'):
        for d,o in (_D.get(grp) or {}).items():
            if ends(h,d): return (grp,set(o))
    _co=set()
    for _d,_o in (_D.get('caucus_hosted_own_pages') or {}).items():
        if ends(h,_d): _co=set(_o)
    for d in _D.get('party_org_sites') or []:
        if ends(h,d): return ('party_org',_co)
    for t in re.split(r'[.\-]',h):
        if t not in ('tandem',) and _DTOK.match(t): return ('party_org',_co)
    return None

# --- social accounts: only the page person's own account (owner's rule, Nov 10 2026) ---
_SA=P.get('social_accounts') or {}
_SAH=set(_SA.get('hosts') or [])
_SARE=re.compile(r'https?://(?:www\.|mobile\.|m\.)?([a-z.]+)/(?:@|profile/|in/|user/|c/)?([A-Za-z0-9_.\-]+)',re.I)
def social_owner(url):
    """None when url is not a social post; else the set of owner ids of its account (empty = not anyone's own)."""
    m=_SARE.match(inner(url) or '')
    if not m: return None
    h=m.group(1).lower(); h=h[4:] if h.startswith('www.') else h
    if h not in _SAH: return None
    k={'twitter.com':'twitter','x.com':'twitter','mobile.twitter.com':'twitter'}.get(h,h.split('.')[0])
    return set((_SA.get('own') or {}).get(k+':'+m.group(2).lower(),[]))
# --- narrow exceptions (v44, owner Nov 10 2026 12:34 AM ET: AP "Sure but only in the elections tab" for House calls) ---
# A host in sources-policy.json narrow_exceptions stays banned everywhere except the one use named by only_for;
# the caller states that use as context (e.g. context='house_call' for an Elections-tab House race call's callSrc).
_NX={k:v for k,v in (P.get('narrow_exceptions') or {}).items() if not k.startswith('_') and isinstance(v,dict)}
def classify(url,own_hosts=(),page_person=None,context=None):
    """('allowed'|'pending'|'banned'|'none', group)"""
    if not url: return ('none','none')
    h=dom(inner(url))
    if not h: return ('none','none')
    if context:
        for _d,_x in _NX.items():
            if ends(h,_d) and _x.get('only_for')==context: return ('allowed','exception:'+context)
    _ds=dem_source(url)
    if _ds:
        _pp=set(page_person) if isinstance(page_person,(list,tuple,set)) else ({page_person} if page_person else set())
        if _D.get('allow_own_site_for_dems') and ((_ds[1] & _pp) or any(oh and ends(h,oh) for oh in own_hosts or ())): return ('allowed','own_site')
        return ('banned','democratic_sources')
    _so=social_owner(url)
    if _so is not None:
        _pp=set(page_person) if isinstance(page_person,(list,tuple,set)) else ({page_person} if page_person else set())
        _m=re.match(r'https?://[^/]+/(?:@|profile/|in/|user/|c/)?([A-Za-z0-9_.\-]+)',inner(url) or '')
        _hd=(_m.group(1).lower() if _m else '')
        if (_so & _pp) or any(oh and ':' in oh and oh.split(':',1)[1].lower()==_hd for oh in own_hosts or ()): return ('allowed','own_social')
        return ('banned','social_not_own')
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
def ok(url,own_hosts=(),page_person=None,context=None):
    return classify(url,own_hosts,page_person,context)[0] in ('allowed','pending')
