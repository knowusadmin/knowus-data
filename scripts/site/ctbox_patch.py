import sys
p=sys.argv[1]; a=open(p,encoding='utf-8').read()
OLD="(c.camp?'Campaign contact, from the candidate\\u2019s own public pages.':'Public office contact only, as published by the office.')"
NEW="(c.camp?'Campaign contact, from the candidate\\u2019s own public pages or Ballotpedia.':c.g?'Main contact for the office, as published by the office (not a direct personal line).':'Public office contact only, as published by the office.')"
if a.count(NEW)==1: print('ctbox already applied')
elif a.count(OLD)==1: open(p,'w',encoding='utf-8').write(a.replace(OLD,NEW)); print('ctbox applied')
else: sys.exit('ctbox: unexpected match')
