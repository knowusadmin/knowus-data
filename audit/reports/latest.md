# KnowUS site audit — 2026-11-24 19:47 UTC

**1 high · 0 medium · 29 low** — 862 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/45472445077) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (1)

### Stale data — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/` | officials-meta.json checkedAt 2026-11-10T03:07:33.969Z | The app's "Updated" time is 353 hours old (limit 48) | — |  |

## Low (29)

### Console error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` |  | requestStorageAccess: Permission denied. | 360/390 |  |

### Failed network request — 16

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/bill/US-119-HR8352` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/federalist/37` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/federalist/62` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/federalist/65` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/B000825` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/B001230` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/cab15` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/cab16` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/D000622` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/F000466` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/G000386` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/M000871` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/pr47/positions` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/s/OH/local/39035/p78932/leg/U/21/0` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/s/PA/local` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |

### Source link unreachable — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/VA/local/51069/p51512` | https://www.middletownva.gov/middletown-officials/ | No answer within 20 s (may block automated checks) | — |  |

### Website down (app shows "Website currently down") — 11

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/p117/positions` | https://www.janjonesforgeorgia.com/ | HTTP 404 | — |  |
| `#/s/FL/local/12047/p35375` | https://www.jasperfl.gov/ | HTTP 404 | — |  |
| `#/s/FL/local/12061/p33600` | http://www.irshores.com | HTTP 522 | — |  |
| `#/s/ID/local/16087/p52750` | https://midvaleidaho.org/ | HTTP 404 | — |  |
| `#/s/NY/local/36103/p02044` | https://www.amityville.gov/m/newsflash/home/detail/323 | HTTP 404 | — |  |
| `#/s/OH/local/39093/p40544` | http://www.camdentwp.us/about-kipton-village | HTTP 404 | — |  |
| `#/s/OH/local/39107/p69540` | http://www.vil.saint-henry.oh.us | HTTP 404 | — |  |
| `#/s/PA/local/42011/t01165320` | http://www.co.berks.pa.us/Muni/robeson/Pages/ | HTTP 404 | — |  |
| `#/s/PA/local/42017/t01749120` | http://www.middletownbucks.org | HTTP 404 | — |  |
| `#/s/TN/local/47043/p09880` | http://townofburnstn.net/admin.html | HTTP 404 | — |  |
| `#/s/TX/local/48485/p22984` | http://www.electratexas.org/ | HTTP 404 | — |  |

## Dead source links on the running list (11)

Every link here answered 404/410 or a server error; each run re-checks them and drops the ones that work again. Full list: `audit/reports/dead-links.json`.

- `#/p/p117/positions` → https://www.janjonesforgeorgia.com/ (HTTP 404, since 2026-11-21)
- `#/s/FL/local/12047/p35375` → https://www.jasperfl.gov/ (HTTP 404, since 2026-11-24)
- `#/s/FL/local/12061/p33600` → http://www.irshores.com (HTTP 522, since 2026-11-23)
- `#/s/ID/local/16087/p52750` → https://midvaleidaho.org/ (HTTP 404, since 2026-11-22)
- `#/s/NY/local/36103/p02044` → https://www.amityville.gov/m/newsflash/home/detail/323 (HTTP 404, since 2026-11-24)
- `#/s/OH/local/39093/p40544` → http://www.camdentwp.us/about-kipton-village (HTTP 404, since 2026-11-23)
- `#/s/OH/local/39107/p69540` → http://www.vil.saint-henry.oh.us (HTTP 404, since 2026-11-21)
- `#/s/PA/local/42011/t01165320` → http://www.co.berks.pa.us/Muni/robeson/Pages/ (HTTP 404, since 2026-11-24)
- `#/s/PA/local/42017/t01749120` → http://www.middletownbucks.org (HTTP 404, since 2026-11-11)
- `#/s/TN/local/47043/p09880` → http://townofburnstn.net/admin.html (HTTP 404, since 2026-11-21)
- `#/s/TX/local/48485/p22984` → http://www.electratexas.org/ (HTTP 404, since 2026-11-16)

## What was covered

- contact-box links checked: 236
- source links checked: 5842
- pages with AI text checked: 566
- taps tested: 818
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
- officials data age (hours): 353
- bills index age (hours): 0
- dead links dropped (no longer in the app): 0
- outbound links known: 28670
- links the app already labels "Website currently down": 674
- outbound links checked: 211
- dead links on the running list: 11
- outbound links OK: 185
- outbound links refused bots (401/403/429, not counted as broken): 14
- cited sources checked: 217814
- banned citations: 0
- app status line: "Live data · checked 7:39 PM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
