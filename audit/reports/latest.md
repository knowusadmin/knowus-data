# KnowUS site audit — 2026-11-27 08:07 UTC

**1 high · 3 medium · 56 low** — 856 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/45962277301) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (1)

### Stale data — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/` | officials-meta.json checkedAt 2026-11-10T03:07:33.969Z | The app's "Updated" time is 413 hours old (limit 48) | — |  |

## Medium (3)

### Source link server error — 3

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/ID/local/16033/p22960` | https://duboisidaho.gov/council | HTTP 521 (twice) | — |  |
| `#/s/KS/local/20111/p01675` | https://cityofamericus.municipalimpact.com/mayor | HTTP 521 (twice) | — |  |
| `#/s/MO/local/29185/p44282` | https://lowrycitymo.gov/mayor | HTTP 521 (twice) | — |  |

## Low (56)

### Console error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` |  | requestStorageAccess: Permission denied. | 360/390 |  |

### Failed network request — 13

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/bill/US-119-HR11146` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/bill/US-119-HR11156` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/federalist/37` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/B001299` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/cab0/positions` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/cab16` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/D000616` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/E000299` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/G000386` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/G000581` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/pr47/positions` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/s/IN/local/18073` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |

### Source link unreachable — 29

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/C001112` | https://carbajal.house.gov | No answer within 20 s (may block automated checks) | — |  |
| `#/p/p585/positions` | https://www.wvlegislature.gov/senate1/president.cfm | No answer within 20 s (may block automated checks) | — |  |
| `#/s/AR/local/05059/p60020` | https://rockportar.org/mayor-and-council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/CA/local/06063` | https://www.plumascounty.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/CT/local/09001/p18430` | https://www.danbury-ct.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/FL/local/12099/p35875` | https://www.jupiter.fl.us/m/directory | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IA/local/19079/p25050` | https://ellsworthiowa.org/council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/KS/local/20141/p49425` | https://www.cityofnatoma.com/mayor | No answer within 20 s (may block automated checks) | — |  |
| `#/s/ME/local/23011/p30550` | http://www.hallowell.govoffice.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/ME/local/23031/t03133665` | http://www.hollismaine.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MN/local/27131/p17126` | http://www.cityofdundas.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NC/local/37193/p47880` | http://www.north-wilkesboro.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/ND/local/38055/p51380` | https://www.maxnd.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NE/local/31081/p18825` | https://giltnerne.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NH/local/33015/t01554580` | http://www.northhampton-nh.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NJ/local/34021/p33150` | https://www.hopewellboroughnj.gov/m/newsflash?cat=1 | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NJ/local/34039/p21000` | https://www.elizabethnj.org/215/City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NY/local/36037/p04715` | https://www.cityofbataviany.gov/163/City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NY/local/36053/t05371993` | http://www.townofsullivan.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/OH/local/39151/p12000` | http://www.cantonohio.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48113/p71156` | http://www.townofsunnyvale.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48183/p43888` | https://longviewtexas.gov/2144/Government | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48201/p07300` | https://www.bellairetx.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48201/p77956` | https://westutx.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48339/p67400` | https://www.shenandoahtx.us/ | No answer within 20 s (may block automated checks) | — |  |

…and 4 more (all in `latest.json`).

### Website down (app shows "Website currently down") — 13

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/p117/positions` | https://www.janjonesforgeorgia.com/ | HTTP 404 | — |  |
| `#/s/FL/local/12047/p35375` | https://www.jasperfl.gov/ | HTTP 404 | — |  |
| `#/s/FL/local/12061/p33600` | http://www.irshores.com | HTTP 522 | — |  |
| `#/s/ID/local/16087/p52750` | https://midvaleidaho.org/ | HTTP 404 | — |  |
| `#/s/MO/local/29009/p10144` | https://cityofbutterfield.com/council | No answer within 20 s | — |  |
| `#/s/OH/local/39093/p40544` | http://www.camdentwp.us/about-kipton-village | HTTP 404 | — |  |
| `#/s/OH/local/39107/p69540` | http://www.vil.saint-henry.oh.us | HTTP 404 | — |  |
| `#/s/PA/local/42011/t01165320` | http://www.co.berks.pa.us/Muni/robeson/Pages/ | HTTP 404 | — |  |
| `#/s/PA/local/42017/t01749120` | http://www.middletownbucks.org | HTTP 404 | — |  |
| `#/s/SC/local/45019` | http://www.charlestoncounty.org | No answer within 20 s | — |  |
| `#/s/TN/local/47043/p09880` | http://townofburnstn.net/admin.html | HTTP 404 | — |  |
| `#/s/TX/local/48485/p22984` | http://www.electratexas.org/ | HTTP 404 | — |  |
| `#/s/WY/local/56031/p32290` | https://townofglendo.com/ | HTTP 500 | — |  |

## Dead source links on the running list (14)

Every link here answered 404/410 or a server error; each run re-checks them and drops the ones that work again. Full list: `audit/reports/dead-links.json`.

- `#/p/p117/positions` → https://www.janjonesforgeorgia.com/ (HTTP 404, since 2026-11-21)
- `#/s/FL/local/12047/p35375` → https://www.jasperfl.gov/ (HTTP 404, since 2026-11-24)
- `#/s/FL/local/12061/p33600` → http://www.irshores.com (HTTP 522, since 2026-11-23)
- `#/s/ID/local/16033/p22960` → https://duboisidaho.gov/council (HTTP 521, since 2026-11-27)
- `#/s/ID/local/16087/p52750` → https://midvaleidaho.org/ (HTTP 404, since 2026-11-22)
- `#/s/KS/local/20111/p01675` → https://cityofamericus.municipalimpact.com/mayor (HTTP 521, since 2026-11-27)
- `#/s/MO/local/29185/p44282` → https://lowrycitymo.gov/mayor (HTTP 521, since 2026-11-27)
- `#/s/OH/local/39093/p40544` → http://www.camdentwp.us/about-kipton-village (HTTP 404, since 2026-11-23)
- `#/s/OH/local/39107/p69540` → http://www.vil.saint-henry.oh.us (HTTP 404, since 2026-11-21)
- `#/s/PA/local/42011/t01165320` → http://www.co.berks.pa.us/Muni/robeson/Pages/ (HTTP 404, since 2026-11-24)
- `#/s/PA/local/42017/t01749120` → http://www.middletownbucks.org (HTTP 404, since 2026-11-11)
- `#/s/TN/local/47043/p09880` → http://townofburnstn.net/admin.html (HTTP 404, since 2026-11-21)
- `#/s/TX/local/48485/p22984` → http://www.electratexas.org/ (HTTP 404, since 2026-11-16)
- `#/s/WY/local/56031/p32290` → https://townofglendo.com/ (HTTP 500, since 2026-11-27)

## What was covered

- contact-box links checked: 204
- source links checked: 5908
- pages with AI text checked: 560
- taps tested: 794
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
- state legislators (from city pages): 26
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
- officials data age (hours): 413
- last good hourly refresh (hours ago): 0.1
- bills index age (hours): 2
- dead links dropped (no longer in the app): 0
- outbound links known: 28936
- links the app already labels "Website currently down": 650
- outbound links checked: 211
- dead links on the running list: 14
- outbound links OK: 151
- outbound links refused bots (401/403/429, not counted as broken): 15
- cited sources checked: 218040
- banned citations: 0
- app status line: "Live data · checked 8:00 AM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
