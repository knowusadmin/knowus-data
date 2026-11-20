# KnowUS site audit — 2026-11-20 08:01 UTC

**1 high · 0 medium · 42 low** — 850 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/44698287636) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (1)

### Stale data — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/` | officials-meta.json checkedAt 2026-11-10T03:07:33.969Z | The app's "Updated" time is 245 hours old (limit 48) | — |  |

## Low (42)

### Console error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` |  | requestStorageAccess: Permission denied. | 360/390 |  |

### Failed network request — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 403 | 360/390 |  |

### Source link unreachable — 37

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/CA/local/06019/p67056` | http://www.ci.sanger.ca.us | No answer within 20 s (may block automated checks) | — |  |
| `#/s/CA/local/06037/p48914` | http://www.montereypark.ca.gov/m/calendar/event/detail/13292 | No answer within 20 s (may block automated checks) | — |  |
| `#/s/FL/local/12103/p62425` | https://www.cityofsafetyharbor.com/37/City-Commission | No answer within 20 s (may block automated checks) | — |  |
| `#/s/GA/local/13069/p23872` | http://www.cityofdouglas.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/ID/local/16001/p44290` | https://www.kunacity.id.gov/m/directory/department?did=6 | No answer within 20 s (may block automated checks) | — |  |
| `#/s/ID/local/16059` | http://www.lemhicountyidaho.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IL/local/17161/p49867` | http://www.moline.il.us | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IL/local/17163/p22255` | http://www.cesl.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/KS/local/20015/p20075` | https://www.eldoks.gov/529/City-Commission | No answer within 20 s (may block automated checks) | — |  |
| `#/s/KS/local/20015/p20075` | https://www.eldoks.gov/379/Meet-the-Commission | No answer within 20 s (may block automated checks) | — |  |
| `#/s/KS/local/20091/p60825` | http://www.roelandpark.net | No answer within 20 s (may block automated checks) | — |  |
| `#/s/KY/local/21101` | https://hendersonky.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MA/local/25017/p37000` | https://www.lowellma.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MA/local/25017/t01756130` | https://www.readingma.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MA/local/25027/t02726430` | http://www.grafton-ma.gov/m/directory/department?did=31 | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MD/local/24031/p62850` | https://www.poolesvillemd.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MD/local/24033/p70850` | https://seatpleasantmd.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MO/local/29143/p52076` | http://www.new-madrid.mo.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MO/local/29183` | http://www.sccmo.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MT/local/30057` | http://www.madison.mt.gov | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NC/local/37101/p12860` | http://www.townofclaytonnc.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NE/local/31177/p05350` | https://www.blairne.gov/m/directory/department?did=4 | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NH/local/33001/t00167300` | http://www.sanborntonnh.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NH/local/33011/t01137140` | https://hollisnh.gov/1586/Town-Office-Hours-and-Phone-Directory | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NJ/local/34025/t02500070` | https://www.aberdeennj.org/27/Government | No answer within 20 s (may block automated checks) | — |  |

…and 12 more (all in `latest.json`).

### Website down (app shows "Website currently down") — 3

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/PA/local/42011/t01165320` | http://www.co.berks.pa.us/Muni/robeson/Pages/ | HTTP 404 | — |  |
| `#/s/PA/local/42017/t01749120` | http://www.middletownbucks.org | HTTP 404 | — |  |
| `#/s/TX/local/48485/p22984` | http://www.electratexas.org/ | HTTP 404 | — |  |

## Dead source links on the running list (3)

Every link here answered 404/410 or a server error; each run re-checks them and drops the ones that work again. Full list: `audit/reports/dead-links.json`.

- `#/s/PA/local/42011/t01165320` → http://www.co.berks.pa.us/Muni/robeson/Pages/ (HTTP 404, since 2026-11-11)
- `#/s/PA/local/42017/t01749120` → http://www.middletownbucks.org (HTTP 404, since 2026-11-11)
- `#/s/TX/local/48485/p22984` → http://www.electratexas.org/ (HTTP 404, since 2026-11-16)

## What was covered

- contact-box links checked: 192
- source links checked: 5804
- pages with AI text checked: 562
- taps tested: 800
- federal people: 48
- past presidents: 6
- senators: 200
- positions pages: 32
- state pages: 18
- election views: 8
- election sheets: 16
- candidate rows: 22
- candidate profiles: 44
- in-app links spot-checked: 240
- house members: 120
- governors: 100
- local states: 14
- counties: 14
- local officials: 30
- cities: 14
- state legislators (from city pages): 28
- sign-in screen checked: 2
- constitution pages: 70
- declaration: 2
- federalist papers: 20
- learn/role pages: 16
- bills: 24
- exec orders: 10
- full profiles scanned: 150
- local states scanned: 50
- local AI profiles scanned: 322
- vote totals checked: 328
- officials data age (hours): 245
- last good hourly refresh (hours ago): 1.4
- bills index age (hours): 2
- dead links dropped (no longer in the app): 0
- outbound links known: 28671
- links the app already labels "Website currently down": 406
- outbound links checked: 203
- dead links on the running list: 3
- outbound links OK: 146
- outbound links refused bots (401/403/429, not counted as broken): 17
- cited sources checked: 217814
- banned citations: 0
- app status line: "Live data · checked 7:54 AM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
