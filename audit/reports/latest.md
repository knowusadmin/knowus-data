# KnowUS site audit — 2026-11-08 16:00 UTC

**5 high · 9 medium · 10 low** — 730 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/42497048144) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (5)

### Banned label in AI text — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/S001196/positions` | Elise M. Stefanik — "conspiracy" (via) | https://en.wikipedia.org/wiki/Elise_Stefanik#2020_election_fraud_conspiracy_theories | — |  |

### Dead tap — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/bill/US-119-HR7954` | button.linkbtn "Show all 15" | Looks tappable (button) but could not be reached by a tap (covered or off-screen) | 360/390 | `screenshots/C-360-001-deadtap.jpg` |

### Failed network request — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/IA/local/19153/p57675/o/0` | https://knowus.sites.tab.bot/data/local-ai/IA.json?v=1 | HTTP 404 | 360/390 |  |

### Term already ended but shown as current — 2

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/H001104` | Term ends November 3, 2026 | Jon Husted (Junior U.S. Senator from Ohio): end date is in the past | 360/390 |  |
| `#/p/M001244` | Term ends November 3, 2026 | Ashley Moody (Junior U.S. Senator from Florida): end date is in the past | 360/390 |  |

## Medium (9)

### Broken source link — 4

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/MN/local/27025/t02521194` | http://www.fishlaketownship.org | HTTP 404 | — |  |
| `#/s/NY/local/36089/t08912342` | http://www.cantonnewyork.us/portal.html | HTTP 404 | — |  |
| `#/s/SD/local/46051` | http://www.grantcountysd.com/gcdc | HTTP 404 | — |  |
| `#/s/VA/local/51063/p28544` | https://floydcova.org | HTTP 404 | — |  |

### Loaded label in non-AI text — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/cab9` | "conspiracy" |  his initials RFK Jr., is an American politician, environmental lawyer, author, conspiracy theorist, and anti-vaccine activist serving as the 26th United States | 360/390 |  |

### Local tab empty — 2

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/OH/local/39035` |  | County shows no cities or towns | 360/390 |  |
| `#/s/TN/local/47147` |  | County shows no cities or towns | 360/390 |  |

### Missing content — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/bills/eo` |  | Exec Orders tab shows no orders | 360/390 |  |

### Page never finished loading — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/` |  | Still showing "Loading…" or changing after 8 s | 390 |  |

## Low (10)

### Source link unreachable — 10

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/E000295/positions` | https://www.washingtonpost.com/news/morning-mix/wp/2016/07/22/the-story-of-sarah-root-who-trump-said-was-sacrificed-on-the-altar-of-open-bor | No answer within 20 s (may block automated checks) | — |  |
| `#/s/AR/local/05143/p57170` | http://www.prairiegrovearkansas.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/CA/local/06041/p16462` | http://www.ci.corte-madera.ca.us/index.html | No answer within 20 s (may block automated checks) | — |  |
| `#/s/CO/local/08067/p05265` | http://www.bayfield.govoffice.com | No answer within 20 s (may block automated checks) | — |  |
| `#/s/GA/local/13031/p73256` | http://www.sboro.net/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IN/local/18073/p63756` | http://remingtonindiana.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/OH/local/39023/p54334` | http://www.newcarlisleohio.net | No answer within 20 s (may block automated checks) | — |  |
| `#/s/PA/local/42129/p31200` | http://www.city.greensburg.pa.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48143/p70208` | http://www.ci.stephenville.tx.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TX/local/48453/p13552` | http://www.cedarparktx.us/ | No answer within 20 s (may block automated checks) | — |  |

## What was covered

- pages with AI text checked: 120
- taps tested: 1040
- federal people: 48
- past presidents: 6
- senators: 200
- state pages: 9
- election views: 8
- election sheets: 16
- in-app links spot-checked: 240
- house members: 120
- governors: 100
- local states: 12
- counties: 12
- local officials: 20
- cities: 8
- sign-in screen checked: 2
- constitution pages: 35
- declaration: 2
- federalist papers: 20
- learn/role pages: 8
- bills: 24
- AI profiles scanned: 1224
- full profiles scanned: 151
- local states scanned: 50
- local AI profiles scanned: 322
- vote totals checked: 191
- officials data age (hours): 12
- last good hourly refresh (hours ago): 0.9
- bills index age (hours): 1
- outbound links known: 32473
- outbound links checked: 200
- outbound links OK: 162
- outbound links refused bots (401/403/429, not counted as broken): 21
- app status line: "Live data · checked 3:53 PM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
