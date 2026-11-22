# KnowUS site audit — 2026-11-22 19:37 UTC

**2 high · 0 medium · 23 low** — 860 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/45061069063) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (2)

### Dead tap — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/candidate/senate_ak_write-in` | a "Source ↗" | Link is covered by another element: p.small "Vote count: State of Alaska, Division of Elections, Unofficial results — first-choice tota" | 390 | `screenshots/A-390-001-covered.jpg` |

### Stale data — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/` | officials-meta.json checkedAt 2026-11-10T03:07:33.969Z | The app's "Updated" time is 304 hours old (limit 48) | — |  |

## Low (23)

### Console error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` |  | requestStorageAccess: Permission denied. | 360/390 |  |

### Failed network request — 16

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/federalist/28` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/federalist/36` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/federalist/61` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/cab0/positions` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/cab16` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/E000297` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/F000468` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/G000386` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/L000562` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/L000571` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/M001215` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/Y000064` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/s/GA/local/13001` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/s/GA/local/13001/p06016/o/3` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |

### Website down (app shows "Website currently down") — 6

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/p117/positions` | https://www.janjonesforgeorgia.com/ | HTTP 404 | — |  |
| `#/s/ID/local/16087/p52750` | https://midvaleidaho.org/ | HTTP 404 | — |  |
| `#/s/OH/local/39107/p69540` | http://www.vil.saint-henry.oh.us | HTTP 404 | — |  |
| `#/s/PA/local/42017/t01749120` | http://www.middletownbucks.org | HTTP 404 | — |  |
| `#/s/TN/local/47043/p09880` | http://townofburnstn.net/admin.html | HTTP 404 | — |  |
| `#/s/TX/local/48485/p22984` | http://www.electratexas.org/ | HTTP 404 | — |  |

## Dead source links on the running list (6)

Every link here answered 404/410 or a server error; each run re-checks them and drops the ones that work again. Full list: `audit/reports/dead-links.json`.

- `#/p/p117/positions` → https://www.janjonesforgeorgia.com/ (HTTP 404, since 2026-11-21)
- `#/s/ID/local/16087/p52750` → https://midvaleidaho.org/ (HTTP 404, since 2026-11-22)
- `#/s/OH/local/39107/p69540` → http://www.vil.saint-henry.oh.us (HTTP 404, since 2026-11-21)
- `#/s/PA/local/42017/t01749120` → http://www.middletownbucks.org (HTTP 404, since 2026-11-11)
- `#/s/TN/local/47043/p09880` → http://townofburnstn.net/admin.html (HTTP 404, since 2026-11-21)
- `#/s/TX/local/48485/p22984` → http://www.electratexas.org/ (HTTP 404, since 2026-11-16)

## What was covered

- contact-box links checked: 254
- source links checked: 5958
- pages with AI text checked: 570
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
- local officials: 40
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
- officials data age (hours): 304
- last good hourly refresh (hours ago): 0.2
- bills index age (hours): 6
- dead links dropped (no longer in the app): 0
- outbound links known: 28606
- links the app already labels "Website currently down": 480
- outbound links checked: 205
- dead links on the running list: 6
- outbound links OK: 178
- outbound links refused bots (401/403/429, not counted as broken): 21
- cited sources checked: 217814
- banned citations: 0
- app status line: "Live data · checked 7:30 PM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
