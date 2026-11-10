# KnowUS site audit — 2026-11-10 01:50 UTC

**5 high · 43 medium · 6 low** — 828 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/42737761530) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (5)

### Dead tap — 2

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/candidate/gov_az_gertritrude-gonzalez` | a "Source ↗" | Link is covered by another element: p.small "Vote count: Arizona Secretary of State (official results portal on app.enhancedvoting.com)" | 360 | `screenshots/A-360-019-covered.jpg` |
| `#/candidate/gov_az_unassigned-in` | a "Source ↗" | Link is covered by another element: p.small "Vote count: Arizona Secretary of State (official results portal on app.enhancedvoting.com)" | 360 | `screenshots/A-360-020-covered.jpg` |

### Hourly refresh failing — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(GitHub Actions)` | refresh.yml | Last 6 runs did not succeed | — |  |

### Term already ended but shown as current — 2

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/H001104` | Term ends November 3, 2026 | Jon Husted (Junior U.S. Senator from Ohio): end date is in the past | 360/390 |  |
| `#/p/M001244` | Term ends November 3, 2026 | Ashley Moody (Junior U.S. Senator from Florida): end date is in the past | 360/390 |  |

## Medium (43)

### Empty box — 43

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/cab0` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-001-empty.jpg` |
| `#/p/cab1` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-002-empty.jpg` |
| `#/p/cab11` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-011-empty.jpg` |
| `#/p/cab12` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-012-empty.jpg` |
| `#/p/cab13` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-013-empty.jpg` |
| `#/p/cab15` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-014-empty.jpg` |
| `#/p/cab17` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-015-empty.jpg` |
| `#/p/cab18` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-016-empty.jpg` |
| `#/p/cab2` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-003-empty.jpg` |
| `#/p/cab21` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-017-empty.jpg` |
| `#/p/cab22` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-018-empty.jpg` |
| `#/p/cab3` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-004-empty.jpg` |
| `#/p/cab4` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-005-empty.jpg` |
| `#/p/cab5` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-006-empty.jpg` |
| `#/p/cab6` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-007-empty.jpg` |
| `#/p/cab7` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-008-empty.jpg` |
| `#/p/cab8` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-009-empty.jpg` |
| `#/p/cab9` | div.card | Visible box with nothing in it | 360/390 | `screenshots/A-360-010-empty.jpg` |
| `#/p/p121` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-003-empty.jpg` |
| `#/p/p14` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-001-empty.jpg` |
| `#/p/p146` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-004-empty.jpg` |
| `#/p/p159` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-005-empty.jpg` |
| `#/p/p171` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-006-empty.jpg` |
| `#/p/p210` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-007-empty.jpg` |
| `#/p/p233` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-008-empty.jpg` |
| `#/p/p246` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-009-empty.jpg` |
| `#/p/p259` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-010-empty.jpg` |
| `#/p/p272` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-011-empty.jpg` |
| `#/p/p286` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-012-empty.jpg` |
| `#/p/p310` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-013-empty.jpg` |
| `#/p/p332` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-014-empty.jpg` |
| `#/p/p357` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-015-empty.jpg` |
| `#/p/p394` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-016-empty.jpg` |
| `#/p/p407` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-017-empty.jpg` |
| `#/p/p432` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-018-empty.jpg` |
| `#/p/p457` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-019-empty.jpg` |
| `#/p/p482` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-020-empty.jpg` |
| `#/p/p494` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-021-empty.jpg` |
| `#/p/p533` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-022-empty.jpg` |
| `#/p/p556` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-023-empty.jpg` |
| `#/p/p568` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-024-empty.jpg` |
| `#/p/p57` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-002-empty.jpg` |
| `#/p/p607` | div.card | Visible box with nothing in it | 360/390 | `screenshots/B-360-025-empty.jpg` |

## Low (6)

### Console error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` |  | requestStorageAccess: Permission denied. | 360/390 |  |

### Failed network request — 2

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 403 | 360/390 |  |
| `#/p/W000795` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 403 | 360 |  |

### Source link unreachable — 3

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/OH/local/39055/t05532914` | https://hambdentownship.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/PA/local/42129/p47000` | http://www.manorborough.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/WI/local/55087/p72725` | http://www.seymour.govoffice.com/ | No answer within 20 s (may block automated checks) | — |  |

## What was covered

- source links checked: 10404
- pages with AI text checked: 544
- taps tested: 722
- federal people: 48
- past presidents: 6
- senators: 200
- positions pages: 32
- state pages: 18
- election views: 8
- election sheets: 16
- candidate rows: 22
- candidate profiles: 40
- in-app links spot-checked: 240
- house members: 120
- governors: 100
- local states: 14
- counties: 14
- local officials: 12
- cities: 14
- state legislators (from city pages): 26
- sign-in screen checked: 2
- constitution pages: 70
- declaration: 2
- federalist papers: 20
- learn/role pages: 16
- taps skipped (page changed state): 4
- bills: 24
- exec orders: 10
- full profiles scanned: 151
- local states scanned: 50
- local AI profiles scanned: 322
- vote totals checked: 264
- officials data age (hours): 0
- bills index age (hours): 0
- dead links dropped (no longer in the app): 9
- outbound links known: 18249
- links the app already labels "Website currently down": 1841
- outbound links checked: 200
- dead links on the running list: 0
- outbound links OK: 176
- outbound links refused bots (401/403/429, not counted as broken): 21
- cited sources checked: 55358
- banned citations: 0
- app status line: "Updated 1:34 AM · hourly check of official sources"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
