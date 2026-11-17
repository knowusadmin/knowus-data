# KnowUS site audit — 2026-11-17 08:02 UTC

**1 high · 0 medium · 35 low** — 848 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/44042412526) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (1)

### Stale data — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/` | officials-meta.json checkedAt 2026-11-10T03:07:33.969Z | The app's "Updated" time is 173 hours old (limit 48) | — |  |

## Low (35)

### Console error — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` |  | requestStorageAccess: Permission denied. | 360/390 |  |

### Failed network request — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `(start)` | https://content-firebaseappcheck.googleapis.com/v1/projects/knowus-6b767/apps/1:250914929257:web:51f258f30e98de6bff40f8:exchangeRecaptchaEnt | HTTP 403 | 360/390 |  |

### Source link unreachable — 30

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/AL/local/01069` | http://www.houstoncounty.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/AR/local/05055/p53390` | https://www.paragouldcityar.gov/222/City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/CA/local/06037/p03666` | https://www.baldwinpark.com/268/City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/CA/local/06059/p25380` | https://www.fountainvalley.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/CO/local/08123/p19080` | https://daconoco.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/DE/local/10005/p41830` | http://www.ci.lewes.de.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/FL/local/12069/p43425` | http://www.cityofmascotte.com | No answer within 20 s (may block automated checks) | — |  |
| `#/s/FL/local/12085/p35925` | https://townofjupiterisland.com/178/Commissioners | No answer within 20 s (may block automated checks) | — |  |
| `#/s/FL/local/12131/p16800` | http://www.defuniaksprings.net | No answer within 20 s (may block automated checks) | — |  |
| `#/s/GA/local/13077/p55020` | https://www.newnanga.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IA/local/19013/p11755` | http://www.ci.cedar-falls.ia.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IA/local/19067/p12765` | https://www.cityofcharlescity.org/103/City-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IL/local/17043/p37907` | http://www.itasca.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IL/local/17043/p77993` | http://www.invillapark.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MA/local/25021/p78972` | http://www.weymouth.ma.us/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MA/local/25021/t02160785` | http://www.townofsharon.net/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MI/local/26103/t10351920` | https://www.marquettetownship.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NC/local/37183/p32260` | http://www.hollyspringsnc.us | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NH/local/33013/t01300660` | http://www.allenstownnh.gov | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NJ/local/34003/p20020` | https://www.edgewaternj.org/370/Your-Council-Members | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NJ/local/34035/p43620` | https://www.manvillenj.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/OH/local/39035/p09274` | https://www.brooklynhts.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/OH/local/39055/p13554` | http://www.chardon.cc/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/PA/local/42029/p19752` | https://www.downingtown.org/244/Mayor-Borough-Council | No answer within 20 s (may block automated checks) | — |  |
| `#/s/SC/local/45083/p68290` | http://www.cityofspartanburg.org | No answer within 20 s (may block automated checks) | — |  |

…and 5 more (all in `latest.json`).

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

- contact-box links checked: 232
- source links checked: 5744
- pages with AI text checked: 558
- taps tested: 794
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
- local officials: 28
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
- officials data age (hours): 173
- last good hourly refresh (hours ago): 0.1
- bills index age (hours): 0
- dead links dropped (no longer in the app): 0
- outbound links known: 28875
- links the app already labels "Website currently down": 696
- outbound links checked: 203
- dead links on the running list: 3
- outbound links OK: 157
- outbound links refused bots (401/403/429, not counted as broken): 13
- cited sources checked: 217814
- banned citations: 0
- app status line: "Live data · checked 7:55 AM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
