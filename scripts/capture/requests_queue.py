#!/usr/bin/env python3
"""Sample-ballot request queue (Shmuel, Nov 10 2026). OFF by default and never sends anything itself.

For every election 21 days out or closer (and at least 3 days away), each registered office whose ballots have not been
captured yet gets one entry in data/capture/request-queue.json: office, its official email (as printed on its own .gov
contact page, with that page's URL), election, county, and the drafted email from data/capture/request-template.json.
A follow-up is drafted 7 days after a send that got no reply. Sending is done by Tab (mail from
shmuel.knowus@mail.tab.bot) only while requests-config.json says "enabled": true; Tab then records "sent" / "replied"
on the entry. Ballots that come back by email are converted with the same parsers and verification rules.
"""
import datetime as dt, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAP = os.environ.get('CAPTURE_DIR') or os.path.join(ROOT, 'data', 'capture')
def load(p, d):
    try: return json.load(open(p))
    except FileNotFoundError: return d
def captured(el, st, sid):
    m = load(os.path.join(CAP, 'manifests', el, st, sid + '.json'), {})
    return any(r.get('ok') for r in m.get('runs', []))
def slug(s):
    import re; return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')[:60] or 'x'
def fmt_date(d): return d.strftime('%B %-d, %Y')
def main():
    today = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else (dt.datetime.utcnow() - dt.timedelta(hours=5)).date()
    cfg = load(os.path.join(CAP, 'requests-config.json'), {'enabled': False})
    tpl = load(os.path.join(CAP, 'request-template.json'), {})
    cal = load(os.path.join(CAP, 'calendar.json'), {}); src = load(os.path.join(CAP, 'sources.json'), {})
    qp = os.path.join(CAP, 'request-queue.json'); q = load(qp, {'items': {}})
    q['enabled'] = bool(cfg.get('enabled')); q['note'] = 'Drafts only. Nothing here is sent by the job; Tab sends when enabled and records the outcome.'
    seen = set()
    for st, s in sorted((cal.get('states') or {}).items()):
        reg = (src.get('states') or {}).get(st) or {}
        for e in s.get('elections') or []:
            try: d = dt.date.fromisoformat(e['date'])
            except Exception: continue
            left = (d - today).days
            if left > 21 or left < 3: continue
            names = [x.get('county') or x.get('town') for x in reg.get('counties') or []]
            statewide = (e.get('scope') or '').startswith('statewide') or (e.get('whoVotes') or '').strip().lower() == 'all'
            txt = ' '.join(str(e.get(k) or '') for k in ('name', 'covers', 'whoVotes', 'notes')).lower()
            named = {c for c in names if c and re.search(r'\b' + re.escape(c.lower()) + r'\b', txt)}
            if not statewide and not named: continue      # a local election whose offices we cannot tell: never email blind
            for ent in (reg.get('counties') or []):
                county = ent.get('county') or ent.get('town'); sid = slug(county + '-' + (ent.get('what') or ent.get('format') or 'src'))
                if not statewide and county not in named: continue
                key = f'{d.isoformat()}|{st}|{slug(county)}'
                if key in seen: continue
                seen.add(key)
                if captured(d.isoformat(), st, sid) or key in q['items'] and q['items'][key].get('status') in ('replied', 'received'):
                    if key in q['items'] and q['items'][key].get('status') == 'drafted': q['items'][key]['status'] = 'not needed (captured)'
                    continue
                off = ent.get('office') or {}
                it = q['items'].get(key) or {'state': st, 'county': county, 'election': d.isoformat(), 'electionName': e.get('name'),
                                             'office': off.get('name'), 'email': off.get('email'), 'emailSource': off.get('emailSource'),
                                             'status': 'drafted' if off.get('email') else 'no official email on file', 'drafted': today.isoformat(),
                                             'sent': None, 'followUpDue': None, 'followUpSent': None, 'replied': None}
                vals = {'[Election date]': fmt_date(d), '[date]': fmt_date(d), '[County]': county + ('' if ' ' in county or st in ('CT', 'MA', 'ME', 'NH', 'RI', 'VT') else ' County')}
                subj, body = tpl.get('subject', ''), tpl.get('body', '')
                for k, v in vals.items(): subj = subj.replace(k, v); body = body.replace(k, v)
                it['subject'], it['body'] = subj, body
                if it.get('sent') and not it.get('replied') and not it.get('followUpSent'):
                    it['followUpDue'] = (dt.date.fromisoformat(it['sent'][:10]) + dt.timedelta(days=7)).isoformat()
                    it['followUpBody'] = tpl.get('followUp', body)
                q['items'][key] = it
    for k in list(q['items']):    # drafts that no longer apply (out of scope, election passed) go; anything sent stays
        if k not in seen and q['items'][k].get('status') in ('drafted', 'no official email on file', 'not needed (captured)'): del q['items'][k]
    q['built'] = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    json.dump(q, open(qp, 'w'), indent=1, ensure_ascii=False, sort_keys=True)
    open_ = [k for k, v in q['items'].items() if v['status'] == 'drafted']
    print(f'request queue: {len(q["items"])} entries, {len(open_)} drafted, enabled={q["enabled"]}')
if __name__ == '__main__':
    main()
