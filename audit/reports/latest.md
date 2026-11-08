# KnowUS site audit — 2026-11-08 16:41 UTC

**3 high · 97 medium · 13 low** — 806 page visits at 390 px and 360 px phone widths · [this run](https://github.com/knowusadmin/knowus-data/actions/runs/42500429126) (screenshots are in the run's artifacts)

Severity: **high** = a user hits a broken thing (dead tap, error, wrong/stale fact, banned wording, sideways scroll). **medium** = looks wrong or a source link is broken. **low** = worth a look (third-party hiccups, console noise).

## High (3)

### Page not found — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/NH/local/33011/p45140/leg/L/Hillsborough 15/1` | New Hampshire Executive Legislative Judicial Local  Legislator not found. Back | Route shows the "doesn't exist / not found" message | 360/390 | `screenshots/B-360-001-notfound.jpg` |

### Term already ended but shown as current — 2

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/H001104` | Term ends November 3, 2026 | Jon Husted (Junior U.S. Senator from Ohio): end date is in the past | 360/390 |  |
| `#/p/M001244` | Term ends November 3, 2026 | Ashley Moody (Junior U.S. Senator from Florida): end date is in the past | 360/390 |  |

## Medium (97)

### Broken source link — 90

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/B001277/positions` | https://www.theday.com/national-politics/20210107/murphy-blumenthal-call-for-investigation-of-capitols-security-response-to-riots | HTTP 404 | — |  |
| `#/p/B001277/positions` | http://www.socialfunds.com/news/article.cgi/article878.html | HTTP 404 | — |  |
| `#/p/B001302/positions` | https://www.sourcepolitics.com/11-republicans-vote-against-helping-9-11-first-responders/ | HTTP 404 | — |  |
| `#/p/C001047/positions` | http://www.dailymail.com/News/statenews/201004120920 | HTTP 404 | — |  |
| `#/p/C001066/positions` | http://tbo.com/pinellas-county/in-pinellas-head-start-starts-again-20140824/ | HTTP 404 | — |  |
| `#/p/C001108/positions` | https://votesmart.org/candidate/political-courage-test/35169/james-comer-jr/#.WkR6b1Q-dE4 | HTTP 404 | — |  |
| `#/p/C001108/positions` | http://www.bgdailynews.com/news/gubernatorial-hopeful-comer-speaks-about-farm-program/article_2d38f4b7-2105-591e-9e44-9269cdcb6d90.html | HTTP 404 | — |  |
| `#/p/C001113/positions` | http://www.ktvn.com/story/36524490/senator-catherine-cortez-masto-cosponsors-bill-on-gun-control-and-releases-statement-on-las-vegas-shootin | HTTP 404 | — |  |
| `#/p/C001125/positions` | http://algiersdevelopment.com/profiles/senator-troy-a-carter/ | HTTP 404 | — |  |
| `#/p/D000600/positions` | https://votesmart.org/candidate/political-courage-test/24312/mario-diaz-balart/ | HTTP 404 | — |  |
| `#/p/G000555/positions` | http://www.nydailynews.com/ny_local/2009/02/03/2009-02-03_in_effort_to_soften_antiimmigration_rep_.html | HTTP 404 | — |  |
| `#/p/G000555/positions` | http://gillibrand.senate.gov/issues/issue/?id=57cd61b3-dc1b-4613-b528-40a874429dc9 | HTTP 404 | — |  |
| `#/p/G000555/positions` | http://schumer.senate.gov/new_website/record.cfm?id=311344 | HTTP 404 | — |  |
| `#/p/G000565/positions` | http://www.opencongress.org/bill/112-h140/show | HTTP 404 | — |  |
| `#/p/G000565/positions` | http://www.fox10phoenix.com/news/arizona-news/27036260-story | HTTP 410 | — |  |
| `#/p/G000607/positions` | https://votesmart.org/candidate/biography/114778/james-gallagher | HTTP 404 | — |  |
| `#/p/K000400/positions` | https://a54.asmdc.org/press-releases/20191002-governor-newsom-signs-assembly-bills-241-and-242-address-implicit-bias | HTTP 404 | — |  |
| `#/p/K000400/positions` | https://a54.asmdc.org/news/20190212-assemblymember-sydney-kamlager-dove-co-authors-legislation-restore-right-vote-people | HTTP 404 | — |  |
| `#/p/K000400/positions` | https://a54.asmdc.org/press-releases/20180930-governor-jerry-brown-signs-ab-987 | HTTP 404 | — |  |
| `#/p/K000400/positions` | https://a54.asmdc.org/press-releases/20190627-assemblymember-sydney-kamlager-dove-d-los-angeles-seeks-end-discrimination | HTTP 404 | — |  |
| `#/p/L000570/positions` | https://www.abqjournal.com/1313755/lujaacutens-plan-requires-netzero-carbon-emissions-by-2050.html | HTTP 404 | — |  |
| `#/p/L000570/positions` | http://votesmart.org/public-statement/747238/stop-the-war-on-coal-act-of-2012#.UKx0AYfAdsY | HTTP 404 | — |  |
| `#/p/L000570/positions` | https://votesmart.org/public-statement/464728/lujan-we-must-demand-a-public-option#.WFbcAIXaLV0 | HTTP 404 | — |  |
| `#/p/L000570/positions` | https://votesmart.org/public-statement/458401/rep-lujan-urges-administration-to-reject-troop-increase-in-afghanistan#.WFbpfIXaLV0 | HTTP 404 | — |  |
| `#/p/M000133/positions` | https://humaneaction.org/2025-scorecard-preview | HTTP 404 | — |  |
| `#/p/M001160/positions` | http://www.votesmart.org/public-statement/642709/dem-leaders-to-stearns-stop-pointless-political-attack-on-planned-parenthood | HTTP 404 | — |  |
| `#/p/M001160/positions` | http://nl.newsbank.com/nl-search/we/Archives?p_product=MWSB&p_theme=mwsb&p_action=search&p_maxdocs=200&p_topdoc=1&p_text_direct-0=10624A326F | HTTP 404 | — |  |
| `#/p/M001210/positions` | https://www.ncmedsoc.org/heroin-and-opioid-prescription-and-enforcement-hope-bill/ | HTTP 404 | — |  |
| `#/p/O000177/positions` | https://www.senate.mo.gov/20info/BTS_Web/Bill.aspx?SessionType=R&BillID=26838029 | HTTP 404 | — |  |
| `#/p/O000177/positions` | http://prospect.org/article/missouris-greitens-guts-public-sector-unions-on-his-way-out-door | HTTP 404 | — |  |
| `#/p/O000177/positions` | http://www.senate.mo.gov/mem02/ | HTTP 404 | — |  |
| `#/p/O000177/positions` | http://stlouisreview.com/article/2017-07-27/pro-life-groups-laud | HTTP 404 | — |  |
| `#/p/P000603/positions` | http://www.courierpress.com/news/2011/mar/30/kentucky-senator-paul-berates-obama-cavalierly-tak/ | HTTP 404 | — |  |
| `#/p/P000603/positions` | http://www.adn.com/2010/02/25/1156737/kentuckys-gop-senate-candidate.html | HTTP 404 | — |  |
| `#/p/P000603/positions` | http://www.amconmag.com/article/2009/aug/01/00035/ | HTTP 404 | — |  |
| `#/p/p111/positions` | https://votesmart.org/candidate/biography/142732/brad-raffensperger#.W1EuoqtjPIU | HTTP 404 | — |  |
| `#/p/p15/positions` | https://www.alaskastar.com/2018-10-26/candidate-qa-house-district-13-nancy-dahlstrom-vs-danyelle-kimp | HTTP 404 | — |  |
| `#/p/p175/positions` | https://abcnews.go.com/US/wireStory/iowa-lt-gov-adam-gregg-resigns-pursue-career-113361726 | HTTP 404 | — |  |
| `#/p/p183/positions` | https://governor.iowa.gov/2018/08/gov-reynolds-selects-susan-christensen-as-supreme-court-justice | HTTP 404 | — |  |
| `#/p/p184/positions` | https://www.kscourts.org/KSCourts/media/KsCourts/High%20Interest%20Cases/Kelly%20v%20LCC/122765Opinion.pdf | HTTP 404 | — |  |
| `#/p/p186/positions` | https://www.chicagotribune.com/news/watchdog/chi-111603tossed-sidebar-story-story.html | HTTP 404 | — |  |
| `#/p/p325/positions` | https://governor.nebraska.gov/press/gov-ricketts-signs-legislation-expand-broadband-internet-access-nebraska | HTTP 404 | — |  |
| `#/p/p332/positions` | https://gov.nv.gov/Newsroom/ExecOrders/2023/Executive_Order_2023-10/ | HTTP 404 | — |  |
| `#/p/p332/positions` | https://www.ajc.com/news/national/who-clark-county-nevada-sheriff-joseph-lombardo/UWHyaRENdiXlivzZhLomrM/ | HTTP 404 | — |  |
| `#/p/p34/positions` | http://americansforprosperity.org/noclimatetax//wp-content/uploads/2009/10/griffin.pdf | HTTP 404 | — |  |
| `#/p/p369/positions` | http://njlaw.rutgers.edu/collections/courts/appellate/m-208-13a.html | HTTP 404 | — |  |
| `#/p/p369/positions` | http://njlaw.rutgers.edu/collections/courts/supreme/a-8-08.opn.html | HTTP 404 | — |  |
| `#/p/p369/positions` | http://njlaw.rutgers.edu/collections/courts/appellate/a-35-15.opn.html | HTTP 404 | — |  |
| `#/p/p369/positions` | http://www.judiciary.state.nj.us/supreme/rabner.htm | HTTP 404 | — |  |
| `#/p/p388/positions` | https://buffalonews.com/2019/01/22/long-stalled-abortion-bill-passes-new-york-legislature/ | HTTP 404 | — |  |
| `#/p/p388/positions` | http://www.wgrz.com/news/politics/elections/robert-ortt-elected-to-state-senate-62nd-district/272860623 | HTTP 404 | — |  |
| `#/p/p388/positions` | http://buffalogeothermalheating.com/nys-senator-patrick-gallivan-senator-robert-ortt-and-assemblyman-sean-ryan-gather-at-local-business-to-s | HTTP 404 | — |  |
| `#/p/p388/positions` | http://niagarafallsreporter.com/Stories/2015/MAR10/Ortt.html | HTTP 404 | — |  |
| `#/p/p446/positions` | https://www.oregonlegislature.gov/rayfield | HTTP 404 | — |  |
| `#/p/p488/positions` | https://www.theitem.com/stories/sc-lawmakers-stall-abortion-bills-through-walkout,379182 | HTTP 404 | — |  |
| `#/p/p488/positions` | https://www.theitem.com/stories/current-south-carolina-state-flag-will-keep-flying-for-now,365616 | HTTP 404 | — |  |
| `#/p/p488/positions` | https://www.theitem.com/stories/sc-nears-transgender-sports-ban-after-senate-vote,382048 | HTTP 404 | — |  |
| `#/p/p549/positions` | http://labor.vermont.gov/learn-more-about-vermonts-new-earned-sick-time-law/ | HTTP 404 | — |  |
| `#/p/p57/positions` | https://abcnews.go.com/blogs/politics/2011/02/president-obama-instructs-justice-department-to-stop-defending-defense-of-marriage-act-calls-c | HTTP 404 | — |  |
| `#/p/p582/positions` | http://www.legis.state.wv.us/House/lawmaker.cfm?member=Delegate%20Smith,%20R. | HTTP 404 | — |  |

…and 30 more (all in `latest.json`).

### Failed network request — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/NH/local/33011/p45140/o/0` | https://knowus.sites.tab.bot/data/local-ai/NH.json | HTTP 404 | 360/390 |  |

### Loaded label in non-AI text — 1

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/cab9` | "conspiracy" |  his initials RFK Jr., is an American politician, environmental lawyer, author, conspiracy theorist, and anti-vaccine activist serving as the 26th United States | 360/390 |  |

### Source link server error — 5

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/p/J000309/positions` | http://www.substancenews.net/articles.php?page=649 | HTTP 500 (twice) | — |  |
| `#/p/V000130/positions` | http://sd40.senate.ca.gov/biography | HTTP 503 (twice) | — |  |
| `#/s/CA/local/06027/p28021` | http://www.furnacecreekresort.com/ | HTTP 522 (twice) | — |  |
| `#/s/NJ/local/34013/p19390` | http://www.eastorange-nj.org/ | HTTP 522 (twice) | — |  |
| `#/s/TX/local/48075/p14668` | http://childresstexas.com | HTTP 502 (twice) | — |  |

## Low (13)

### Source link unreachable — 13

| Route | Element | Problem | Width | Screenshot |
|---|---|---|---|---|
| `#/s/CA/local/06097/p53266` | http://www.occidental.org/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/GA/local/13031/p73256` | http://www.sboro.net/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/GA/local/13045/p82720` | http://www.whitesburgcity.com | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IL/local/17047/p31165` | http://cityofgrayville.com/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/IN/local/18021/p13276` | http://www.claycity.net/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/ME/local/23005/p60545` | https://www.portlandmaine.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/MO/local/29189/p38972` | http://www.cityofkinloch.org:80/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NC/local/37047/p66520` | http://www.taborcitync.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/ND/local/38095` | http://townercountynd.com | No answer within 20 s (may block automated checks) | — |  |
| `#/s/NH/local/33011/t01127140` | http://www.francestown-nh.gov/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/SD/local/46099` | http://www.minnehahacounty.org | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TN/local/47021/p02180` | http://www.ashlandcity.net/ | No answer within 20 s (may block automated checks) | — |  |
| `#/s/TN/local/47063/p80360` | http://www.whitepinetn.com/ | No answer within 20 s (may block automated checks) | — |  |

## Dead source links on the running list (95)

Every link here answered 404/410 or a server error; each run re-checks them and drops the ones that work again. Full list: `audit/reports/dead-links.json`.

- `#/p/B001277/positions` → https://www.theday.com/national-politics/20210107/murphy-blumenthal-call-for-investigation-of-capitols-security-response-to-riots (HTTP 404, since 2026-11-08)
- `#/p/B001277/positions` → http://www.socialfunds.com/news/article.cgi/article878.html (HTTP 404, since 2026-11-08)
- `#/p/B001302/positions` → https://www.sourcepolitics.com/11-republicans-vote-against-helping-9-11-first-responders/ (HTTP 404, since 2026-11-08)
- `#/p/C001047/positions` → http://www.dailymail.com/News/statenews/201004120920 (HTTP 404, since 2026-11-08)
- `#/p/C001066/positions` → http://tbo.com/pinellas-county/in-pinellas-head-start-starts-again-20140824/ (HTTP 404, since 2026-11-08)
- `#/p/C001108/positions` → https://votesmart.org/candidate/political-courage-test/35169/james-comer-jr/#.WkR6b1Q-dE4 (HTTP 404, since 2026-11-08)
- `#/p/C001108/positions` → http://www.bgdailynews.com/news/gubernatorial-hopeful-comer-speaks-about-farm-program/article_2d38f4b7-2105-591e-9e44-9269cdcb6d90.html (HTTP 404, since 2026-11-08)
- `#/p/C001113/positions` → http://www.ktvn.com/story/36524490/senator-catherine-cortez-masto-cosponsors-bill-on-gun-control-and-releases-statement-on-las-vegas-shooting (HTTP 404, since 2026-11-08)
- `#/p/C001125/positions` → http://algiersdevelopment.com/profiles/senator-troy-a-carter/ (HTTP 404, since 2026-11-08)
- `#/p/D000600/positions` → https://votesmart.org/candidate/political-courage-test/24312/mario-diaz-balart/ (HTTP 404, since 2026-11-08)
- `#/p/G000555/positions` → http://www.nydailynews.com/ny_local/2009/02/03/2009-02-03_in_effort_to_soften_antiimmigration_rep_.html (HTTP 404, since 2026-11-08)
- `#/p/G000555/positions` → http://gillibrand.senate.gov/issues/issue/?id=57cd61b3-dc1b-4613-b528-40a874429dc9 (HTTP 404, since 2026-11-08)
- `#/p/G000555/positions` → http://schumer.senate.gov/new_website/record.cfm?id=311344 (HTTP 404, since 2026-11-08)
- `#/p/G000565/positions` → http://www.opencongress.org/bill/112-h140/show (HTTP 404, since 2026-11-08)
- `#/p/G000565/positions` → http://www.fox10phoenix.com/news/arizona-news/27036260-story (HTTP 410, since 2026-11-08)
- `#/p/G000607/positions` → https://votesmart.org/candidate/biography/114778/james-gallagher (HTTP 404, since 2026-11-08)
- `#/p/J000309/positions` → http://www.substancenews.net/articles.php?page=649 (HTTP 500, since 2026-11-08)
- `#/p/K000400/positions` → https://a54.asmdc.org/press-releases/20191002-governor-newsom-signs-assembly-bills-241-and-242-address-implicit-bias (HTTP 404, since 2026-11-08)
- `#/p/K000400/positions` → https://a54.asmdc.org/news/20190212-assemblymember-sydney-kamlager-dove-co-authors-legislation-restore-right-vote-people (HTTP 404, since 2026-11-08)
- `#/p/K000400/positions` → https://a54.asmdc.org/press-releases/20180930-governor-jerry-brown-signs-ab-987 (HTTP 404, since 2026-11-08)
- `#/p/K000400/positions` → https://a54.asmdc.org/press-releases/20190627-assemblymember-sydney-kamlager-dove-d-los-angeles-seeks-end-discrimination (HTTP 404, since 2026-11-08)
- `#/p/L000570/positions` → https://www.abqjournal.com/1313755/lujaacutens-plan-requires-netzero-carbon-emissions-by-2050.html (HTTP 404, since 2026-11-08)
- `#/p/L000570/positions` → http://votesmart.org/public-statement/747238/stop-the-war-on-coal-act-of-2012#.UKx0AYfAdsY (HTTP 404, since 2026-11-08)
- `#/p/L000570/positions` → https://votesmart.org/public-statement/464728/lujan-we-must-demand-a-public-option#.WFbcAIXaLV0 (HTTP 404, since 2026-11-08)
- `#/p/L000570/positions` → https://votesmart.org/public-statement/458401/rep-lujan-urges-administration-to-reject-troop-increase-in-afghanistan#.WFbpfIXaLV0 (HTTP 404, since 2026-11-08)
- `#/p/M000133/positions` → https://humaneaction.org/2025-scorecard-preview (HTTP 404, since 2026-11-08)
- `#/p/M001160/positions` → http://www.votesmart.org/public-statement/642709/dem-leaders-to-stearns-stop-pointless-political-attack-on-planned-parenthood (HTTP 404, since 2026-11-08)
- `#/p/M001160/positions` → http://nl.newsbank.com/nl-search/we/Archives?p_product=MWSB&p_theme=mwsb&p_action=search&p_maxdocs=200&p_topdoc=1&p_text_direct-0=10624A326F1A1F83&p_field_direct-0=document_id&p_perpage=10&p_sort=YMD_date:D&s_trackval=GooglePM (HTTP 404, since 2026-11-08)
- `#/p/M001210/positions` → https://www.ncmedsoc.org/heroin-and-opioid-prescription-and-enforcement-hope-bill/ (HTTP 404, since 2026-11-08)
- `#/p/O000177/positions` → https://www.senate.mo.gov/20info/BTS_Web/Bill.aspx?SessionType=R&BillID=26838029 (HTTP 404, since 2026-11-08)
- `#/p/O000177/positions` → http://prospect.org/article/missouris-greitens-guts-public-sector-unions-on-his-way-out-door (HTTP 404, since 2026-11-08)
- `#/p/O000177/positions` → http://www.senate.mo.gov/mem02/ (HTTP 404, since 2026-11-08)
- `#/p/O000177/positions` → http://stlouisreview.com/article/2017-07-27/pro-life-groups-laud (HTTP 404, since 2026-11-08)
- `#/p/P000603/positions` → http://www.courierpress.com/news/2011/mar/30/kentucky-senator-paul-berates-obama-cavalierly-tak/ (HTTP 404, since 2026-11-08)
- `#/p/P000603/positions` → http://www.adn.com/2010/02/25/1156737/kentuckys-gop-senate-candidate.html (HTTP 404, since 2026-11-08)
- `#/p/P000603/positions` → http://www.amconmag.com/article/2009/aug/01/00035/ (HTTP 404, since 2026-11-08)
- `#/p/p111/positions` → https://votesmart.org/candidate/biography/142732/brad-raffensperger#.W1EuoqtjPIU (HTTP 404, since 2026-11-08)
- `#/p/p15/positions` → https://www.alaskastar.com/2018-10-26/candidate-qa-house-district-13-nancy-dahlstrom-vs-danyelle-kimp (HTTP 404, since 2026-11-08)
- `#/p/p175/positions` → https://abcnews.go.com/US/wireStory/iowa-lt-gov-adam-gregg-resigns-pursue-career-113361726 (HTTP 404, since 2026-11-08)
- `#/p/p183/positions` → https://governor.iowa.gov/2018/08/gov-reynolds-selects-susan-christensen-as-supreme-court-justice (HTTP 404, since 2026-11-08)
- `#/p/p184/positions` → https://www.kscourts.org/KSCourts/media/KsCourts/High%20Interest%20Cases/Kelly%20v%20LCC/122765Opinion.pdf (HTTP 404, since 2026-11-08)
- `#/p/p186/positions` → https://www.chicagotribune.com/news/watchdog/chi-111603tossed-sidebar-story-story.html (HTTP 404, since 2026-11-08)
- `#/p/p325/positions` → https://governor.nebraska.gov/press/gov-ricketts-signs-legislation-expand-broadband-internet-access-nebraska (HTTP 404, since 2026-11-08)
- `#/p/p332/positions` → https://gov.nv.gov/Newsroom/ExecOrders/2023/Executive_Order_2023-10/ (HTTP 404, since 2026-11-08)
- `#/p/p332/positions` → https://www.ajc.com/news/national/who-clark-county-nevada-sheriff-joseph-lombardo/UWHyaRENdiXlivzZhLomrM/ (HTTP 404, since 2026-11-08)
- `#/p/p34/positions` → http://americansforprosperity.org/noclimatetax//wp-content/uploads/2009/10/griffin.pdf (HTTP 404, since 2026-11-08)
- `#/p/p369/positions` → http://njlaw.rutgers.edu/collections/courts/appellate/m-208-13a.html (HTTP 404, since 2026-11-08)
- `#/p/p369/positions` → http://njlaw.rutgers.edu/collections/courts/supreme/a-8-08.opn.html (HTTP 404, since 2026-11-08)
- `#/p/p369/positions` → http://njlaw.rutgers.edu/collections/courts/appellate/a-35-15.opn.html (HTTP 404, since 2026-11-08)
- `#/p/p369/positions` → http://www.judiciary.state.nj.us/supreme/rabner.htm (HTTP 404, since 2026-11-08)
- `#/p/p388/positions` → https://buffalonews.com/2019/01/22/long-stalled-abortion-bill-passes-new-york-legislature/ (HTTP 404, since 2026-11-08)
- `#/p/p388/positions` → http://www.wgrz.com/news/politics/elections/robert-ortt-elected-to-state-senate-62nd-district/272860623 (HTTP 404, since 2026-11-08)
- `#/p/p388/positions` → http://buffalogeothermalheating.com/nys-senator-patrick-gallivan-senator-robert-ortt-and-assemblyman-sean-ryan-gather-at-local-business-to-support-renewable-energy/ (HTTP 404, since 2026-11-08)
- `#/p/p388/positions` → http://niagarafallsreporter.com/Stories/2015/MAR10/Ortt.html (HTTP 404, since 2026-11-08)
- `#/p/p446/positions` → https://www.oregonlegislature.gov/rayfield (HTTP 404, since 2026-11-08)
- `#/p/p488/positions` → https://www.theitem.com/stories/sc-lawmakers-stall-abortion-bills-through-walkout,379182 (HTTP 404, since 2026-11-08)
- `#/p/p488/positions` → https://www.theitem.com/stories/current-south-carolina-state-flag-will-keep-flying-for-now,365616 (HTTP 404, since 2026-11-08)
- `#/p/p488/positions` → https://www.theitem.com/stories/sc-nears-transgender-sports-ban-after-senate-vote,382048 (HTTP 404, since 2026-11-08)
- `#/p/p549/positions` → http://labor.vermont.gov/learn-more-about-vermonts-new-earned-sick-time-law/ (HTTP 404, since 2026-11-08)
- `#/p/p57/positions` → https://abcnews.go.com/blogs/politics/2011/02/president-obama-instructs-justice-department-to-stop-defending-defense-of-marriage-act-calls-clinton/ (HTTP 404, since 2026-11-08)
- `#/p/p582/positions` → http://www.legis.state.wv.us/House/lawmaker.cfm?member=Delegate%20Smith,%20R. (HTTP 404, since 2026-11-08)
- `#/p/p75/positions` → https://www.publicnewsservice.org/index.php?/content/article/25893-1 (HTTP 404, since 2026-11-08)
- `#/p/pr47/positions` → http://www.infoworld.com/article/2986220/net-neutrality/where-the-candidates-stand-on-net-neutrality.html (HTTP 404, since 2026-11-08)
- `#/p/pr47/positions` → https://www.politifact.com/truth-o-meter/promises/trumpometer/subjects/medicare/ (HTTP 404, since 2026-11-08)
- `#/p/pr47/positions` → http://www.politifact.com/truth-o-meter/statements/2016/mar/10/donald-trump/common-core-education-through-washington-dc-trump-/ (HTTP 404, since 2026-11-08)
- `#/p/S000033/positions` → http://www.politicususa.com/2015/01/21/bernie-sanders-files-constitutional-amendment-overturn-citizens-united.html (HTTP 404, since 2026-11-08)
- `#/p/S001150/positions` → http://www.scpr.org/blogs/news/2012/12/07/11459/congressman-schiff-says-he-will-reintroduce-helico/ (HTTP 404, since 2026-11-08)
- `#/p/S001211/positions` → https://www.azcentral.com/arizonarepublic/opinions/articles/20111125greg-stanton-into-the-mind.html (HTTP 404, since 2026-11-08)
- `#/p/S001211/positions` → https://www.azcentral.com/community/phoenix/articles/20110721greg-stanton-money-phoenix-mayor.html (HTTP 404, since 2026-11-08)
- `#/p/S001218/positions` → https://www.abqjournal.com/1499329/qampa-house-district-28-candidate-melanie-ann-stansbury-2.html (HTTP 404, since 2026-11-08)
- `#/p/T000478/positions` → https://wskg.org/news/representative-tenney-on-trump-insurrection-certifying-presidential-election/ (HTTP 404, since 2026-11-08)
- `#/p/T000478/positions` → http://www.oneidadispatch.com/article/OD/20170329/FEATURES/170329885 (HTTP 404, since 2026-11-08)
- `#/p/V000130/positions` → http://sd40.senate.ca.gov/biography (HTTP 503, since 2026-11-08)
- `#/p/W000437/positions` → https://www.supertalk.fm/senator-roger-wicker-says-time-to-put-a-hold-on-syrian-refugee-influx/ (HTTP 404, since 2026-11-08)
- `#/p/W000437/positions` → https://www.wicker.senate.gov/public/index.cfm/press-releases?ID=0532A3E1-B8D2-4C75-80A2-C04A11DB05A5 (HTTP 404, since 2026-11-08)
- `#/p/W000437/positions` → https://www.wicker.senate.gov/public/index.cfm/press-releases?ID=6a3ecd77-5afb-47be-b4e5-6afae6fd8f1e (HTTP 404, since 2026-11-08)
- `#/p/W000797/positions` → http://www.savethemanatee.org/newsprwassermanschultz.htm (HTTP 404, since 2026-11-08)
- `#/p/W000804/positions` → http://votesmart.org/public-statement/773315/wittman-introduces-renewable-energy-legislation#.U5tyTfldW8A (HTTP 404, since 2026-11-08)
- `#/p/W000804/positions` → http://www.floridasportsman.com/2012/04/02/senate-bill-pushes-for-wetlands-conservation-act-reauthorization/ (HTTP 404, since 2026-11-08)
- `#/s/CA/local/06027/p28021` → http://www.furnacecreekresort.com/ (HTTP 522, since 2026-11-08)
- …and 15 more

## What was covered

- pages with AI text checked: 548
- taps tested: 1198
- federal people: 48
- past presidents: 6
- senators: 200
- positions pages: 32
- state pages: 18
- election views: 8
- election sheets: 16
- in-app links spot-checked: 240
- house members: 120
- governors: 100
- local states: 14
- counties: 14
- local officials: 18
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
- AI profiles scanned: 1224
- full profiles scanned: 151
- local states scanned: 50
- local AI profiles scanned: 322
- vote totals checked: 191
- officials data age (hours): 12
- last good hourly refresh (hours ago): 0.6
- bills index age (hours): 1
- outbound links known: 32668
- outbound links checked: 307
- dead links on the running list: 95
- outbound links OK: 167
- outbound links refused bots (401/403/429, not counted as broken): 21
- app status line: "Live data · checked 4:33 PM"

_Live site: https://knowus.sites.tab.bot/ · generated by `.github/workflows/site-audit.yml`_
