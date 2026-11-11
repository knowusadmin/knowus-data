#!/usr/bin/env python3
"""Record what Tab did with a request-queue entry (the job itself never sends mail).
  requests_mark.py "<key>" sent|followup|replied|received|bounced [note]
Keys are the entries' keys in data/capture/request-queue.json ("<date>|<ST>|<county>")."""
import datetime as dt, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAP = os.environ.get('CAPTURE_DIR') or os.path.join(ROOT, 'data', 'capture')
qp = os.path.join(CAP, 'request-queue.json'); q = json.load(open(qp))
key, what = sys.argv[1], sys.argv[2]; note = ' '.join(sys.argv[3:])
it = q['items'][key]; now = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
if what == 'sent':
    if it.get('sent'): sys.exit('already sent once; only one follow-up is allowed (use followup)')
    it['sent'] = now; it['status'] = 'sent'; it['followUpDue'] = (dt.date.today() + dt.timedelta(days=7)).isoformat()
elif what == 'followup':
    if not it.get('sent') or it.get('followUpSent'): sys.exit('no follow-up allowed (not sent yet, or already followed up)')
    it['followUpSent'] = now; it['status'] = 'followed up'
elif what in ('replied', 'received', 'bounced'):
    it[what if what != 'received' else 'replied'] = now; it['status'] = what
it.setdefault('log', []).append([now, what, note])
json.dump(q, open(qp, 'w'), indent=1, ensure_ascii=False, sort_keys=True)
print(key, it['status'])
