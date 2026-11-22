# KnowUS site audit — 2026-11-22 01:56 UTC

**1 high · 0 medium · 23 low** — 854 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/44973226301) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (1)

### Stale data — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/` | officials-meta.json checkedAt 2026-11-10T03:07:33.969Z | The app's "Updated" time is 287 hours old (limit 48) | — |  |

## Low (23)

### Console error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` |  | requestStorageAccess: Permission denied. | 360/390 |  |

### Failed network request — 14

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/bills/eo/14426` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/federalist/11` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/federalist/16` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/federalist/41` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/B001299` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/C001069` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/cab16` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/G000386` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/pr47/positions` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/T000468` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/W000806` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/s/OR/local/41003` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/s/OR/local/41003/p49600` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |

### Source link unreachable — 3

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/IA/local/19119/p43410` | https://www.cityoflarchwood.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NC/local/37083/p38680` | http://www.townoflittleton-nc.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NJ/local/34029/p39900` | http://www.leisurevillagenj.com | No answer within 20 s (may block automated checks) | — |  |

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

- contact-box links checked: 240
- source links checked: 5934
- pages with AI text checked: 566
- taps tested: 808
- federal people: 48
- past presidents: 6
- senators: 200
- positions pages: 32
- state pages: 18
- election views: 8
- election sheets: 16
- candidate rows: 20
- candidate profiles: 40
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
- officials data age (hours): 287
- last good hourly refresh (hours ago): 0.3
- bills index age (hours): 0
- dead links dropped (no longer in the app): 0
- outbound links known: 28665
- links the app already labels "Website currently down": 562
- outbound links checked: 205
- dead links on the running list: 5
- outbound links OK: 174
- outbound links refused bots (401/403/429, not counted as broken): 23
- cited sources checked: 217814
- banned citations: 0
- app status line: "Live data · checked 1:49 AM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
