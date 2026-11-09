# KnowUS site audit — 2026-11-09 19:45 UTC

**1 high · 1 medium · 21 low** — 846 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/42684831437) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (1)

### Hourly refresh failing — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(GitHub Actions)` | refresh.yml | Last successful run was 7 hours ago | — |  |

## Medium (1)

### Source link server error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/MO/local/29225/p66800` | http://www.seymourmissouri.org | HTTP 500 (twice) | — |  |

## Low (21)

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
| `#/s/CT/local/09001/t00163480` | http://www.townofreddingct.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MN/local/27079/p43738` | http://www.montgomery.govoffice.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48065/p54960` | http://www.panhandletx.govoffice2.com | No answer within 20 s (may block automated checks) | — |  |

### Website down (app shows "Website currently down") — 16

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/p405/positions` | https://www.newsobserver.com/news/state/north-carolina/article247593105.html | No answer within 20 s | — |  |
| `#/s/AL/local/01117/p33256` | http://www.townofharpersville.com/ | HTTP 521 | — |  |
| `#/s/AZ/local/04011/p14380` | http://cliftonaz.gov | No answer within 20 s | — |  |
| `#/s/FL/local/12113/p48050` | http://www.floridasplayground.com/navarre-beach/ | No answer within 20 s | — |  |
| `#/s/ID/local/16001/p44290` | http://www.cityofkuna.com | No answer within 20 s | — |  |
| `#/s/IN/local/18093/p04114` | https://www.bedford.in.us/ | No answer within 20 s | — |  |
| `#/s/KS/local/20007` | http://BarberCounty.net | HTTP 522 | — |  |
| `#/s/KY/local/21193` | https://perrycounty.ky.gov | HTTP 502 | — |  |
| `#/s/MA/local/25017/t01731085` | http://www.hopkinton.org/ | No answer within 20 s | — |  |
| `#/s/MO/local/29029/p40916` | http://www.cityoflaurie.com/ | HTTP 526 | — |  |
| `#/s/MO/local/29071/p77416` | http://www.ci.washington.mo.us/ | No answer within 20 s | — |  |
| `#/s/NC/local/37137/p42480` | http://mesictownof.com/ | No answer within 20 s | — |  |
| `#/s/NE/local/31139/p39100` | http://www.piercenebraska.com/ | HTTP 404 | — |  |
| `#/s/NY/local/36055/p58354` | http://www.villageofpittsford.org | HTTP 522 | — |  |
| `#/s/PA/local/42033` | http://www.clearfieldco.org | HTTP 500 | — |  |
| `#/s/TX/local/48075/p14668` | http://childresstexas.com | HTTP 502 | — |  |

## Dead source links on the running list (9)

Every link here answered 404/410 or a server error; each run re-checks them and drops the ones that work again. Full list: `audit/reports/dead-links.json`.

- `#/s/AL/local/01117/p33256` → http://www.townofharpersville.com/ (HTTP 521, since 2026-11-09)
- `#/s/KS/local/20007` → http://BarberCounty.net (HTTP 522, since 2026-11-09)
- `#/s/KY/local/21193` → https://perrycounty.ky.gov (HTTP 502, since 2026-11-08)
- `#/s/MO/local/29029/p40916` → http://www.cityoflaurie.com/ (HTTP 526, since 2026-11-09)
- `#/s/MO/local/29225/p66800` → http://www.seymourmissouri.org (HTTP 500, since 2026-11-09)
- `#/s/NE/local/31139/p39100` → http://www.piercenebraska.com/ (HTTP 404, since 2026-11-09)
- `#/s/NY/local/36055/p58354` → http://www.villageofpittsford.org (HTTP 522, since 2026-11-08)
- `#/s/PA/local/42033` → http://www.clearfieldco.org (HTTP 500, since 2026-11-09)
- `#/s/TX/local/48075/p14668` → http://childresstexas.com (HTTP 502, since 2026-11-08)

## What was covered

- pages with AI text checked: 564
- taps tested: 1218
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
- local officials: 26
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
- officials data age (hours): 39
- last good hourly refresh (hours ago): 7.3
- bills index age (hours): 0
- dead links dropped (no longer in the app): 0
- outbound links known: 32934
- links the app already labels "Website currently down": 1776
- outbound links checked: 209
- dead links on the running list: 9
- outbound links OK: 174
- outbound links refused bots (401/403/429, not counted as broken): 15
- app status line: "Checking for updates…"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
