# KnowUS site audit — 2026-11-28 08:00 UTC

**1 high · 0 medium · 29 low** — 864 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/46123163852) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (1)

### Stale data — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/` | officials-meta.json checkedAt 2026-11-10T03:07:33.969Z | The app's "Updated" time is 437 hours old (limit 48) | — |  |

## Low (29)

### Console error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` |  | requestStorageAccess: Permission denied. | 360/390 |  |

### Failed network request — 10

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/bills/eo/14406` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/federalist/29` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/C001101` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/cab0/positions` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 390 |  |
| `#/p/cab16` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/G000386` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/p/pr47/positions` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360 |  |
| `#/p/S001218` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |
| `#/s/NJ/local/34009/p80210/o/0` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 429 | 360/390 |  |

### Source link unreachable — 5

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/ME/local/23005/p60545` | https://www.portlandmaine.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MT/local/30085/p29500` | https://townoffroid.com/mayor | No answer within 20 s (may block automated checks) | — |  |
| `#/s/ND/local/38047` | https://logancountynd.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48129/p15112` | https://cityofclarendontx.com/council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48379/p22276` | https://cityofeasttawakoni.com/council | No answer within 20 s (may block automated checks) | — |  |

### Website down (app shows "Website currently down") — 13

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/p117/positions` | https://www.janjonesforgeorgia.com/ | HTTP 404 | — |  |
| `#/s/FL/local/12047/p35375` | https://www.jasperfl.gov/ | HTTP 404 | — |  |
| `#/s/FL/local/12061/p33600` | http://www.irshores.com | HTTP 522 | — |  |
| `#/s/ID/local/16087/p52750` | https://midvaleidaho.org/ | HTTP 404 | — |  |
| `#/s/NJ/local/34003/p72420` | https://www.tenaflynj.gov/m/newsflash/home/detail/791 | HTTP 404 | — |  |
| `#/s/NY/local/36119/t11930367` | https://www.greenburghny.com/AlertCenter.aspx?AID=PUBLIC-NOTICE-Meeting-DateTime-changes-f-489 | HTTP 404 | — |  |
| `#/s/OH/local/39093/p40544` | http://www.camdentwp.us/about-kipton-village | HTTP 404 | — |  |
| `#/s/OH/local/39107/p69540` | http://www.vil.saint-henry.oh.us | HTTP 404 | — |  |
| `#/s/PA/local/42011/t01165320` | http://www.co.berks.pa.us/Muni/robeson/Pages/ | HTTP 404 | — |  |
| `#/s/PA/local/42017/t01749120` | http://www.middletownbucks.org | HTTP 404 | — |  |
| `#/s/TN/local/47043/p09880` | http://townofburnstn.net/admin.html | HTTP 404 | — |  |
| `#/s/TX/local/48485/p22984` | http://www.electratexas.org/ | HTTP 404 | — |  |
| `#/s/WY/local/56031/p32290` | https://townofglendo.com/ | HTTP 500 | — |  |

## Dead source links on the running list (13)

Every link here answered 404/410 or a server error; each run re-checks them and drops the ones that work again. Full list: `audit/reports/dead-links.json`.

- `#/p/p117/positions` → https://www.janjonesforgeorgia.com/ (HTTP 404, since 2026-11-21)
- `#/s/FL/local/12047/p35375` → https://www.jasperfl.gov/ (HTTP 404, since 2026-11-24)
- `#/s/FL/local/12061/p33600` → http://www.irshores.com (HTTP 522, since 2026-11-23)
- `#/s/ID/local/16087/p52750` → https://midvaleidaho.org/ (HTTP 404, since 2026-11-22)
- `#/s/NJ/local/34003/p72420` → https://www.tenaflynj.gov/m/newsflash/home/detail/791 (HTTP 404, since 2026-11-27)
- `#/s/NY/local/36119/t11930367` → https://www.greenburghny.com/AlertCenter.aspx?AID=PUBLIC-NOTICE-Meeting-DateTime-changes-f-489 (HTTP 404, since 2026-11-27)
- `#/s/OH/local/39093/p40544` → http://www.camdentwp.us/about-kipton-village (HTTP 404, since 2026-11-23)
- `#/s/OH/local/39107/p69540` → http://www.vil.saint-henry.oh.us (HTTP 404, since 2026-11-21)
- `#/s/PA/local/42011/t01165320` → http://www.co.berks.pa.us/Muni/robeson/Pages/ (HTTP 404, since 2026-11-24)
- `#/s/PA/local/42017/t01749120` → http://www.middletownbucks.org (HTTP 404, since 2026-11-11)
- `#/s/TN/local/47043/p09880` → http://townofburnstn.net/admin.html (HTTP 404, since 2026-11-21)
- `#/s/TX/local/48485/p22984` → http://www.electratexas.org/ (HTTP 404, since 2026-11-16)
- `#/s/WY/local/56031/p32290` → https://townofglendo.com/ (HTTP 500, since 2026-11-27)

## What was covered

- contact-box links checked: 270
- source links checked: 5912
- pages with AI text checked: 568
- taps tested: 820
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
- local officials: 36
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
- officials data age (hours): 437
- last good hourly refresh (hours ago): 0.2
- bills index age (hours): 0
- dead links dropped (no longer in the app): 0
- outbound links known: 28776
- links the app already labels "Website currently down": 709
- outbound links checked: 213
- dead links on the running list: 13
- outbound links OK: 168
- outbound links refused bots (401/403/429, not counted as broken): 27
- cited sources checked: 218293
- banned citations: 0
- app status line: "Live data · checked 7:52 AM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
