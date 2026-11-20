# KnowUS site audit — 2026-11-20 01:59 UTC

**2 high · 0 medium · 27 low** — 864 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/44656488839) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (2)

### Failed network request — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/H000601` | https://knowus.sites.tab.bot/img/congress/B001243.jpg | HTTP 500 | 390 |  |

### Stale data — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/` | officials-meta.json checkedAt 2026-11-10T03:07:33.969Z | The app's "Updated" time is 239 hours old (limit 48) | — |  |

## Low (27)

### Console error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` |  | requestStorageAccess: Permission denied. | 360/390 |  |

### Failed network request — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 403 | 360/390 |  |

### Source link unreachable — 22

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/AK/local/02063/p82200` | https://www.valdezak.gov/132/City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/FL/local/12011/p43125` | https://www.margatefl.com/27/GOVERNMENT | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IA/local/19181/p38280` | https://www.indianolaiowa.gov/160/City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IL/local/17043/p81048` | https://www.wheaton.il.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MI/local/26163/p49000` | https://www.livonia.gov/27/Your-Government | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MI/local/26163/t16367625` | https://www.redfordtwp.gov/m/directory | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MN/local/27009/p56896` | https://www.ci.stcloud.mn.us/81/City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MN/local/27037/p46924` | https://www.northfieldmn.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MO/local/29047/p42032` | https://libertymissouri.gov/m/directory/department?did=74 | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MO/local/29091/p80098` | http://www.willowspringsmo.com/m/directory/department?did=9 | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NJ/local/34003/p21480` | https://www.cityofenglewood.org/1170/City-Manager-Administration | No answer within 20 s (may block automated checks) | — |  |
| `#/s/OH/local/39017/p49840` | https://cityofmiddletown.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/OH/local/39035/p61686` | https://www.pepperpike.org/m/directory | No answer within 20 s (may block automated checks) | — |  |
| `#/s/OH/local/39035/t03558408` | http://www.olmstedtownship.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/OH/local/39051/t05122442` | http://www.fultoncountyoh.com | No answer within 20 s (may block automated checks) | — |  |
| `#/s/OR/local/41039/p15950` | https://www.cottagegroveor.gov/1192/Your-Government | No answer within 20 s (may block automated checks) | — |  |
| `#/s/OR/local/41067/p26200` | https://www.forestgrove-or.gov/27/Government | No answer within 20 s (may block automated checks) | — |  |
| `#/s/PA/local/42029/t02968288` | http://www.schuylkilltwp.com | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48141/p75668` | http://www.vintontx.govoffice2.com | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48193/p31952` | http://www.ci.hamilton.tx.us/m/directory/department?did=20 | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48439/p07552` | http://www.ci.benbrook.tx.us/m/newsflash/Archive/Item/771?arcId=1715 | No answer within 20 s (may block automated checks) | — |  |
| `#/s/WI/local/55033/p51025` | http://www.menomonie-wi.gov | No answer within 20 s (may block automated checks) | — |  |

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

- contact-box links checked: 218
- source links checked: 5966
- pages with AI text checked: 574
- taps tested: 826
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
- local officials: 42
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
- officials data age (hours): 239
- last good hourly refresh (hours ago): 0.3
- bills index age (hours): 0
- dead links dropped (no longer in the app): 0
- outbound links known: 28683
- links the app already labels "Website currently down": 429
- outbound links checked: 203
- dead links on the running list: 3
- outbound links OK: 158
- outbound links refused bots (401/403/429, not counted as broken): 20
- cited sources checked: 217814
- banned citations: 0
- app status line: "Live data · checked 1:50 AM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
