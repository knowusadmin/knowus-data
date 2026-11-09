# KnowUS site audit — 2026-11-09 14:00 UTC

**0 high · 0 medium · 20 low** — 850 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/42629095565) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## Low (20)

### Console error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` |  | requestStorageAccess: Permission denied. | 360/390 |  |

### Failed network request — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 403 | 360/390 |  |

### Source link unreachable — 3

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/S001194/positions` | https://www.washingtonpost.com/politics/2022/08/18/the-three-climateers-represent-new-type-climate-hawk-capitol-hill/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NC/local/37073` | http://www.gatescounty.govoffice2.com | No answer within 20 s (may block automated checks) | — |  |
| `#/s/PA/local/42029/p03656` | http://avondaleboro.net | No answer within 20 s (may block automated checks) | — |  |

### Website down (app shows "Website currently down") — 15

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/AL/local/01117/p33256` | http://www.townofharpersville.com/ | HTTP 521 | — |  |
| `#/s/FL/local/12115/p49675` | http://www.cityofnorthport.com | No answer within 20 s | — |  |
| `#/s/GA/local/13019/p63728` | http://www.raycityga.com/ | No answer within 20 s | — |  |
| `#/s/GA/local/13159/p52416` | http://www.monticelloga.org/ | No answer within 20 s | — |  |
| `#/s/IL/local/17027/p12164` | http://www.city.centralia.il.us/ | No answer within 20 s | — |  |
| `#/s/KS/local/20007` | http://BarberCounty.net | HTTP 522 | — |  |
| `#/s/KY/local/21193` | https://perrycounty.ky.gov | HTTP 502 | — |  |
| `#/s/MO/local/29029/p40916` | http://www.cityoflaurie.com/ | HTTP 526 | — |  |
| `#/s/NC/local/37137/p42480` | http://mesictownof.com/ | HTTP 503 | — |  |
| `#/s/NE/local/31139/p39100` | http://www.piercenebraska.com/ | HTTP 404 | — |  |
| `#/s/NY/local/36055/p58354` | http://www.villageofpittsford.org | HTTP 522 | — |  |
| `#/s/NY/local/36111` | http://www.co.ulster.ny.us | No answer within 20 s | — |  |
| `#/s/PA/local/42033` | http://www.clearfieldco.org | HTTP 500 | — |  |
| `#/s/TX/local/48075/p14668` | http://childresstexas.com | HTTP 502 | — |  |
| `#/s/WI/local/55089/p51150` | http://www.ci.mequon.wi.us | No answer within 20 s | — |  |

## Dead source links on the running list (9)

Every link here answered 404/410 or a server error; each run re-checks them and drops the ones that work again. Full list: `audit/reports/dead-links.json`.

- `#/s/AL/local/01117/p33256` → http://www.townofharpersville.com/ (HTTP 521, since 2026-11-09)
- `#/s/KS/local/20007` → http://BarberCounty.net (HTTP 522, since 2026-11-09)
- `#/s/KY/local/21193` → https://perrycounty.ky.gov (HTTP 502, since 2026-11-08)
- `#/s/MO/local/29029/p40916` → http://www.cityoflaurie.com/ (HTTP 526, since 2026-11-09)
- `#/s/NC/local/37137/p42480` → http://mesictownof.com/ (HTTP 503, since 2026-11-09)
- `#/s/NE/local/31139/p39100` → http://www.piercenebraska.com/ (HTTP 404, since 2026-11-09)
- `#/s/NY/local/36055/p58354` → http://www.villageofpittsford.org (HTTP 522, since 2026-11-08)
- `#/s/PA/local/42033` → http://www.clearfieldco.org (HTTP 500, since 2026-11-09)
- `#/s/TX/local/48075/p14668` → http://childresstexas.com (HTTP 502, since 2026-11-08)

## What was covered

- pages with AI text checked: 560
- taps tested: 1210
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
- local officials: 22
- cities: 14
- state legislators (from city pages): 28
- sign-in screen checked: 2
- constitution pages: 70
- declaration: 2
- federalist papers: 20
- learn/role pages: 16
- taps skipped (page changed state): 4
- bills: 24
- exec orders: 10
- AI profiles scanned: 1224
- full profiles scanned: 151
- local states scanned: 50
- local AI profiles scanned: 322
- vote totals checked: 191
- officials data age (hours): 33
- last good hourly refresh (hours ago): 1.6
- bills index age (hours): 2
- dead links dropped (no longer in the app): 0
- outbound links known: 33016
- links the app already labels "Website currently down": 2117
- outbound links checked: 207
- dead links on the running list: 9
- outbound links OK: 168
- outbound links refused bots (401/403/429, not counted as broken): 20
- app status line: "Checking for updates…"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
