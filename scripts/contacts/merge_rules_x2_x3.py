# KnowUS contacts: merge rules used for House contact forms (x2) and campaign sites (x3).
# Reference copy of the merge logic run on 2026-11-11; inputs are extract.py outputs.
import json,re,collections
from urllib.parse import urlparse
FREEMAIL='@(gmail|yahoo|hotmail|outlook|aol|icloud|me|msn|live|comcast|att|protonmail|proton|ymail|mail|gmx)\\.'
FREEMAIL=re.compile(FREEMAIL,re.I)
SOC={'x': '(^|\\.)(x|twitter)\\.com$', 'fb': '(^|\\.)facebook\\.com$', 'ig': '(^|\\.)instagram\\.com$', 'yt': '(^|\\.)youtube\\.com$'}
def host(u):
    try: return urlparse(u).netloc.lower()
    except Exception: return ''

def regdom(h):
    h=h.lower().split(':')[0]; p_=h.split('.')
    if len(p_)>=3 and p_[-1]=='us' and p_[-2] in ('co','ci','state','k12'): return '.'.join(p_[-4:]) if len(p_)>=4 else h
    return '.'.join(p_[-2:])

# merge_x2: add only the f (contact form) field to Congress members' office contact.
# merge_x3: campaign email (campaign domain or candidate-name domain, no free mail), phone, contact-page form, missing social; no addresses.
