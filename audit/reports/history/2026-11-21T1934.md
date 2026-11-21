# KnowUS site audit — 2026-11-21 19:34 UTC

**1 high · 0 medium · 54 low** — 860 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/44941021802) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (1)

### Stale data — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/` | officials-meta.json checkedAt 2026-11-10T03:07:33.969Z | The app's "Updated" time is 280 hours old (limit 48) | — |  |

## Low (54)

### Console error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` |  | requestStorageAccess: Permission denied. | 360/390 |  |

### Failed network request — 16

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/bill/US-119-S4538` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/bills/eo/14429` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/federalist/14` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/federalist/7` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/cab0/positions` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/cab16` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/E000295` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/G000386` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/H001067` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/M001218` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/pr47/positions` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/S001230` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/W000187` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/s/OH/local/39035/p78932/leg/U/21/0` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/s/SC/local/45035` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |

### Source link unreachable — 32

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/CA/local/06073/p22804` | http://www.escondido.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/CA/local/06081/p31708` | https://www.halfmoonbay.gov/882/Government | No answer within 20 s (may block automated checks) | — |  |
| `#/s/CO/local/08029/p12635` | http://www.cedaredgecolorado.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/FL/local/12005/p09725` | http://www.cityofcallaway.com | No answer within 20 s (may block automated checks) | — |  |
| `#/s/FL/local/12031/p35050` | https://www.jacksonvillebeach.org/298/Mayor-City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/FL/local/12086/p54275` | https://www.palmettobay-fl.gov/376/Mayor-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/FL/local/12099/p71525` | https://www.tequesta.org/1155/How-to-Become-a-Council-Member | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IA/local/19121/p86520` | https://winterset.gov/286/Mayor-and-City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IA/local/19181/p38280` | https://www.indianolaiowa.gov/160/City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/KS/local/20091/p17850` | https://www.desotoks.us/150/Administration-City-Hall | No answer within 20 s (may block automated checks) | — |  |
| `#/s/KS/local/20119/p45325` | https://www.cityofmeade.org/1204/City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MA/local/25027/t02771620` | http://www.uxbridge-ma.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MD/local/24001/p21325` | https://www.cumberlandmd.gov/320/Mayor-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/ME/local/23019/t01955565` | http://www.orono.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/ME/local/23031/t03137270` | http://www.kittery.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MI/local/26065/p47180` | https://www.cityofleslie.org/m/directory | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MN/local/27053/p30140` | https://www.hopkinsmn.com/27/Your-Government | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MO/local/29117/p13690` | http://www.chillicothecity.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NC/local/37183/p32260` | http://www.hollyspringsnc.us | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NJ/local/34011/t01144580` | https://mauricerivertwp.org/27/Municipal-Offices | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NJ/local/34013/t01346380` | https://www.twp.millburn.nj.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NJ/local/34027/t02747670` | https://www.montvillenj.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NJ/local/34029/p04180` | https://www.beachwoodusa.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NY/local/36063/t06382370` | http://www.wilsonnewyork.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NY/local/36103/p56660` | https://www.patchoguevillage.gov/ | No answer within 20 s (may block automated checks) | — |  |

…and 7 more (all in `latest.json`).

### Website down (app shows "Website currently down") — 5

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/p117/positions` | https://www.janjonesforgeorgia.com/ | HTTP 404 | — |  |
| `#/s/OH/local/39107/p69540` | http://www.vil.saint-henry.oh.us | HTTP 404 | — |  |
| `#/s/PA/local/42017/t01749120` | http://www.middletownbucks.org | HTTP 404 | — |  |
| `#/s/TN/local/47043/p09880` | http://townofburnstn.net/admin.html | HTTP 404 | — |  |
| `#/s/TX/local/48485/p22984` | http://www.electratexas.org/ | HTTP 404 | — |  |

## Dead source links on the running list (5)

Every link here answered 404/410 or a server error; each run re-checks them and drops the ones that work again. Full list: `audit/reports/dead-links.json`.

- `#/p/p117/positions` → https://www.janjonesforgeorgia.com/ (HTTP 404, since 2026-11-21)
- `#/s/OH/local/39107/p69540` → http://www.vil.saint-henry.oh.us (HTTP 404, since 2026-11-21)
- `#/s/PA/local/42017/t01749120` → http://www.middletownbucks.org (HTTP 404, since 2026-11-11)
- `#/s/TN/local/47043/p09880` → http://townofburnstn.net/admin.html (HTTP 404, since 2026-11-21)
- `#/s/TX/local/48485/p22984` → http://www.electratexas.org/ (HTTP 404, since 2026-11-16)

## What was covered

- contact-box links checked: 196
- source links checked: 5834
- pages with AI text checked: 566
- taps tested: 810
- federal people: 48
- past presidents: 6
- senators: 200
- positions pages: 32
- state pages: 18
- election views: 8
- election sheets: 16
- candidate rows: 22
- candidate profiles: 42
- in-app links spot-checked: 240
- house members: 120
- governors: 100
- local states: 14
- counties: 14
- local officials: 34
- cities: 14
- state legislators (from city pages): 28
- sign-in screen checked: 2
- constitution pages: 70
- declaration: 2
- federalist papers: 20
- learn/role pages: 16
- bills: 24
- exec orders: 10
- full profiles scanned: 151
- local states scanned: 50
- local AI profiles scanned: 322
- vote totals checked: 328
- officials data age (hours): 280
- last good hourly refresh (hours ago): 0.2
- bills index age (hours): 0
- dead links dropped (no longer in the app): 0
- outbound links known: 28562
- links the app already labels "Website currently down": 485
- outbound links checked: 205
- dead links on the running list: 5
- outbound links OK: 146
- outbound links refused bots (401/403/429, not counted as broken): 22
- cited sources checked: 217814
- banned citations: 0
- app status line: "Live data · checked 7:27 PM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
