#!/usr/bin/env python3
"""KnowUS: Jon Husted (H001104) term end, issue #3 (Nov 11 2026). Idempotent; edits data.js in place.
usage: timeout -k 5 30 python3 husted_patch.py W/final/site/data.js
Sources: Ohio Secretary of State results file (liveresults.ohiosos.gov VSSC1622 file, already in the app's election data:
Brown 2,301,042, Husted 2,077,748, unofficial count, certification pending) and Ohio Revised Code 3521.02
(codes.ohio.gov/ohio-revised-code/section-3521.02: "The appointee shall hold office until the fifteenth day of December
succeeding the next regular state election")."""
import sys
p = sys.argv[1]; t = open(p, encoding='utf-8').read()
OLD_TE = '"te":"November 3, 2026","prior":"Lieutenant Governor of Ohio","phone":"202-224-3353"'
NEW_TE = '"te":"December 15, 2026","prior":"Lieutenant Governor of Ohio","phone":"202-224-3353"'
OLD_NOTE = '"note":"Lost the Nov 3, 2026 special election to Sherrod Brown (D), per AP results; official certification pending. Under Ohio law (R.C. 3521.02) this appointment runs until Dec 15, 2026; Brown, the senator-elect, takes office when sworn in and serves the rest of the term, through Jan 3, 2029."'
NEW_NOTE = '"note":"Lost the Nov 3, 2026 special election to Sherrod Brown (D), per the Ohio Secretary of State\'s results; official certification pending. Under Ohio law (R.C. 3521.02) this appointment runs until Dec 15, 2026. Brown, the senator-elect, takes office when sworn in and serves the rest of the term, through Jan 3, 2029."'
n = 0
for old, new in ((OLD_TE, NEW_TE), (OLD_NOTE, NEW_NOTE)):
    c = t.count(old)
    if c == 1: t = t.replace(old, new); n += 1
    elif c == 0 and t.count(new) == 1: print('already applied:', new[:40])
    else: sys.exit('unexpected match count %d for %s' % (c, old[:50]))
open(p, 'w', encoding='utf-8').write(t); print('changed', n, 'of 2')
