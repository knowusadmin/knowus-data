# KnowUS site audit — 2026-11-09 05:01 UTC

**5 high · 0 medium · 8 low** — 844 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/42564123453) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (5)

### Dead tap — 5

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/candidate/gov_al_doug-jones` | div.card.cpos "Economy & taxes Has called for reductions in corporate taxes rather than tax increases. po" | Looks tappable (named box "KEY POSITIONS") but tapping it does nothing (no page change, no new view) | 360/390 | `screenshots/A-360-001-deadtap.jpg` |
| `#/candidate/gov_ri_helena-foulkes` | div.card.cpos "Economy & taxes Promised to use the state's millionaire's tax to fund new housing developm" | Looks tappable (named box "KEY POSITIONS") but tapping it does nothing (no page change, no new view) | 360/390 | `screenshots/A-360-003-deadtap.jpg` |
| `#/candidate/house_wy_al_lisa-kinney` | div.card.cpos "Immigration & border Wants to investigate whether ICE officers run on a bounty system (202" | Looks tappable (named box "KEY POSITIONS") but tapping it does nothing (no page change, no new view) | 360/390 | `screenshots/A-360-004-deadtap.jpg` |
| `#/candidate/mayor_louisville-ky_craig-greenberg` | div.card.cpos "Abortion Ran on a platform that included supporting legal access to abortion (2022 campaig" | Looks tappable (named box "KEY POSITIONS") but tapping it does nothing (no page change, no new view) | 360/390 | `screenshots/A-360-005-deadtap.jpg` |
| `#/candidate/senate_ks_adam-hamilton` | div.card.cpos "Social issues Changed his position on homosexuality and supports a pluralist approach to h" | Looks tappable (named box "KEY POSITIONS") but tapping it does nothing (no page change, no new view) | 360/390 | `screenshots/A-360-002-deadtap.jpg` |

## Low (8)

### Source link unreachable — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/pr47/positions` | https://www.washingtonpost.com/politics/2025/01/23/federal-worker-mandates-resistance-trump/ | No answer within 20 s (may block automated checks) | — |  |

### Website down (app shows "Website currently down") — 7

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/KY/local/21193` | https://perrycounty.ky.gov | HTTP 502 | — |  |
| `#/s/MO/local/29029/p40916` | http://www.cityoflaurie.com/ | HTTP 526 | — |  |
| `#/s/NY/local/36055/p58354` | http://www.villageofpittsford.org | HTTP 522 | — |  |
| `#/s/PA/local/42033` | http://www.clearfieldco.org | HTTP 500 | — |  |
| `#/s/PA/local/42129/p79776` | http://www.vandergriftborough.org/ | No answer within 20 s | — |  |
| `#/s/TX/local/48075/p14668` | http://childresstexas.com | HTTP 502 | — |  |
| `#/s/WI/local/55043/p45325` | http://livingstonvillage.webs.com | No answer within 20 s | — |  |

## Dead source links on the running list (5)

Every link here answered 404/410 or a server error; each run re-checks them and drops the ones that work again. Full list: `audit/reports/dead-links.json`.

- `#/s/KY/local/21193` → https://perrycounty.ky.gov (HTTP 502, since 2026-11-08)
- `#/s/MO/local/29029/p40916` → http://www.cityoflaurie.com/ (HTTP 526, since 2026-11-09)
- `#/s/NY/local/36055/p58354` → http://www.villageofpittsford.org (HTTP 522, since 2026-11-08)
- `#/s/PA/local/42033` → http://www.clearfieldco.org (HTTP 500, since 2026-11-09)
- `#/s/TX/local/48075/p14668` → http://childresstexas.com (HTTP 502, since 2026-11-08)

## What was covered

- pages with AI text checked: 564
- taps tested: 1220
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
- local officials: 20
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
- officials data age (hours): 25
- last good hourly refresh (hours ago): 0.5
- bills index age (hours): 0
- dead links dropped (no longer in the app): 0
- outbound links known: 32730
- links the app already labels "Website currently down": 2082
- outbound links checked: 204
- dead links on the running list: 5
- outbound links OK: 168
- outbound links refused bots (401/403/429, not counted as broken): 28
- app status line: "Live data · checked 4:52 AM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
