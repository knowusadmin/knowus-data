# KnowUS site audit — 2026-11-10 19:38 UTC

**23 high · 0 medium · 5 low** — 836 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/42886071429) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (23)

### Banned source cited — 12

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `data/officials.json` | a29.asmdc.org | 1 citation(s) of a29.asmdc.org, which data/sources-policy.json does not allow | — |  |
| `data/officials.json` | a69.asmdc.org | 1 citation(s) of a69.asmdc.org, which data/sources-policy.json does not allow | — |  |
| `data/officials.json` | indianasenatedemocrats.org | 1 citation(s) of indianasenatedemocrats.org, which data/sources-policy.json does not allow | — |  |
| `data/officials.json` | indianahousedemocrats.org | 1 citation(s) of indianahousedemocrats.org, which data/sources-policy.json does not allow | — |  |
| `data/officials.json` | housedems.com | 1 citation(s) of housedems.com, which data/sources-policy.json does not allow | — |  |
| `data/officials.json` | pacourts.us | 1 citation(s) of pacourts.us, which data/sources-policy.json does not allow | — |  |
| `data/officials.json, data/officials.json` | x.com | 243 citation(s) of x.com, which data/sources-policy.json does not allow | — |  |
| `data/officials.json, data/officials.json` | facebook.com | 224 citation(s) of facebook.com, which data/sources-policy.json does not allow | — |  |
| `data/officials.json, data/officials.json` | instagram.com | 207 citation(s) of instagram.com, which data/sources-policy.json does not allow | — |  |
| `data/officials.json, data/officials.json` | youtube.com | 117 citation(s) of youtube.com, which data/sources-policy.json does not allow | — |  |
| `data/officials.json, data/officials.json` | housedems.ct.gov | 2 citation(s) of housedems.ct.gov, which data/sources-policy.json does not allow | — |  |
| `data/officials.json, data/officials.json` | senatedems.com | 2 citation(s) of senatedems.com, which data/sources-policy.json does not allow | — |  |

### Banned source shown — 8

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/candidate/house_mt_2_michael-eisenhauer` | https://eisenhauerforcongress.com/eisenhauer-launches-campaign-as-an-independent-candidate-to-represent-montanas-second-congressional-distri | Link to a source the source policy does not allow (data/sources-policy.json) | 360/390 |  |
| `#/candidate/mayor_anaheim-ca_alfredo-rodriguez` | https://rodriguezforanaheim.com/ | Link to a source the source policy does not allow (data/sources-policy.json) | 360/390 |  |
| `#/candidate/senate_al_everett-wess` | https://wessforsenate.com/ | Link to a source the source policy does not allow (data/sources-policy.json) | 360/390 |  |
| `#/s/CO/local/08093/p34630/leg/L/13/0` | https://x.com/McCluskieforCO | Link to a source the source policy does not allow (data/sources-policy.json) | 360/390 |  |
| `#/s/CO/local/08093/p34630/leg/L/13/0` | https://www.facebook.com/McCluskieforCO | Link to a source the source policy does not allow (data/sources-policy.json) | 360/390 |  |
| `#/s/CO/local/08093/p34630/leg/L/13/0` | https://www.instagram.com/mccluskieforco | Link to a source the source policy does not allow (data/sources-policy.json) | 360/390 |  |
| `#/s/CO/local/08093/p34630/leg/U/4/0` | https://www.instagram.com/mark.baisley | Link to a source the source policy does not allow (data/sources-policy.json) | 360/390 |  |
| `#/s/NY/local/36063/p51055/leg/L/145/0` | https://x.com/VoteJudgeAngelo | Link to a source the source policy does not allow (data/sources-policy.json) | 360/390 |  |

### Dead tap — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/candidate/gov_az_unassigned-in` | a "Source ↗" | Link is covered by another element: p.small "Vote count: Arizona Secretary of State (official results portal on app.enhancedvoting.com)" | 360 | `screenshots/A-360-001-covered.jpg` |

### Term already ended but shown as current — 2

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/H001104` | Term ends November 3, 2026 | Jon Husted (Junior U.S. Senator from Ohio): end date is in the past | 360/390 |  |
| `#/p/M001244` | Term ends November 3, 2026 | Ashley Moody (Junior U.S. Senator from Florida): end date is in the past | 360/390 |  |

## Low (5)

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
| `#/s/AL/local/01057/p25840` | https://fayetteal.org/administration/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NY/local/36075/p57661` | https://www.villageofphoenix-ny.gov/districtpage.cfm?pageid=3447 | No answer within 20 s (may block automated checks) | — |  |
| `#/s/VT/local/50027/t02732425` | http://www.hartland.govoffice.com/ | No answer within 20 s (may block automated checks) | — |  |

## What was covered

- source links checked: 5804
- pages with AI text checked: 548
- taps tested: 754
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
- local officials: 16
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
- full profiles scanned: 151
- local states scanned: 50
- local AI profiles scanned: 322
- vote totals checked: 328
- officials data age (hours): 16
- last good hourly refresh (hours ago): 0.2
- bills index age (hours): 0
- dead links dropped (no longer in the app): 0
- outbound links known: 17585
- links the app already labels "Website currently down": 2133
- outbound links checked: 200
- dead links on the running list: 0
- outbound links OK: 186
- outbound links refused bots (401/403/429, not counted as broken): 11
- cited sources checked: 63807
- banned citations: 801
- app status line: "Live data · checked 7:31 PM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
