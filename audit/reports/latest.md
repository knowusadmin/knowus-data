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

## Dead source links on the running list (515)

Every link here answered 404/410 or a server error. This list includes a one-time full check of all 26,857 sources on the "Positions and record" pages (16:55 UTC); each run re-checks them and drops the ones that work again. Full list: `audit/reports/dead-links.json` (also `deadLinks` in latest.json).

- `#/p/A000055/positions` → http://www.politicususa.com/2013/10/25/house-vol-3-robert-aderholt-alabamas-4th-district.html (HTTP 404)
- `#/p/A000148/positions` → https://vote.norml.org/politicians/173832 (HTTP 500)
- `#/p/A000370/positions` → https://vote.norml.org/politicians/5935 (HTTP 500)
- `#/p/A000371/positions` → http://california.realestaterama.com/2016/06/14/aguilar-announces-federal-funds-to-combat-veteran-homelessness-in-san-bernardino-county-ID07954.html (HTTP 404)
- `#/p/A000372/positions` → https://vote.norml.org/politicians/136062 (HTTP 500)
- `#/p/A000381/positions` → https://abcnews.go.com/US/wireStory/democratic-lawmakers-visiting-el-salvador-abrego-garcias-behalf-121005188 (HTTP 404)
- `#/p/B000825/positions` → https://www.ouraynews.com/news/boebert-fires-ouray-county-crowd (HTTP 404)
- `#/p/B001230/positions` → http://www.jsonline.com/blogs/news/175431831.html (HTTP 404)
- `#/p/B001243/positions` → https://www.thedailybeast.com/articles/2013/06/09/the-fringe-factor-women-don-t-want-equal-pay-laws (HTTP 404)
- `#/p/B001260/positions` → http://www.heraldtribune.com/article/20080717/BLOG01/380139045/2364/BLOG01&title=Buchanan_votes_to_override_another_Bush_veto (HTTP 404)
- `#/p/B001260/positions` → http://www.heraldtribune.com/article/20101210/article/12101047 (HTTP 404)
- `#/p/B001260/positions` → http://www.opencongress.org/bill/111-h1839/show (HTTP 404)
- `#/p/B001267/positions` → http://www.9news.com/news/local/next/debating-the-definition-of-terrorism-after-the-las-vegas-shooting/480668441 (HTTP 404)
- `#/p/B001267/positions` → http://www.coloradoindependent.com/25564/bennet-on-the-record-supports-dream-act-for-immigration-reform (HTTP 404)
- `#/p/B001277/positions` → http://waysandmeans.house.gov/legacy/fullcomm/107cong/6-6-02/records/blumenthal.htm (HTTP 404)
- `#/p/B001277/positions` → http://www.socialfunds.com/news/article.cgi/article878.html (HTTP 404)
- `#/p/B001277/positions` → https://www.theday.com/national-politics/20210107/murphy-blumenthal-call-for-investigation-of-capitols-security-response-to-riots (HTTP 404)
- `#/p/B001278/positions` → http://www.beavertonvalleytimes.com/news/story.php?story_id=120958893605414700S (HTTP 404)
- `#/p/B001281/positions` → https://www.dispatch.com/news/20191213/rep-beatty-says-she-supports-impeachment-and-thinks-some-republicans-do-too (HTTP 404)
- `#/p/B001281/positions` → https://www.dispatch.com/news/20191217/beatty-gets-challenge-as-candidates-line-up-for-central-ohio-congressional-seats (HTTP 404)
- `#/p/B001281/positions` → https://www.dispatch.com/news/20200226/us-rep-joyce-beatty-touts-experience-in-primary-race (HTTP 404)
- `#/p/B001282/positions` → https://spectrumnews1.com/ky/louisville/pure-politics/2019/04/16/rep--andy-barr-speaks-on-green-energy-and-the-green-new-deal (HTTP 404)
- `#/p/B001282/positions` → https://www.samhsa.gov/medication-assisted-treatment/training-materials-resources/state-grant-programs (HTTP 404)
- `#/p/B001287/positions` → https://www.prochoiceamerica.org/2016/02/26/dr-ami-bera-us-house/ (HTTP 404)
- `#/p/B001288/positions` → http://www.corybooker.com/vision/keeping-america-secure (HTTP 404)
- `#/p/B001296/positions` → http://www.legis.state.pa.us/cfdocs/legis/RCC/PUBLIC/listVoteSummaryH.cfm?sYear=2009&sInd=0&cteeCde=36&theDate=03/11/2009&rNbr=88 (HTTP 404)
- `#/p/B001298/positions` → https://www.rollcall.com/news/policy/house-republicans-break-2-1-trump-withdrawal-kurd-support (HTTP 404)
- `#/p/B001299/positions` → https://indianapublicradio.org/news/2017/08/congressman-jim-banks-touches-on-health-care-defense-in-auburn-town-hall/ (HTTP 404)
- `#/p/B001302/positions` → https://www.sourcepolitics.com/11-republicans-vote-against-helping-9-11-first-responders/ (HTTP 404)
- `#/p/B001306/positions` → https://medcitynews.com/2010/02/ohio-house-proposal-would-require-random-drug-tests-for-medicaid-eligibility/comment-page-1 (HTTP 504)
- `#/p/B001318/positions` → https://vermontconservationvoters.com/legislators/becca-balint/ (HTTP 404)
- `#/p/C001035/positions` → https://oklahoman.com/article/feed/1041091/senate-approves-sen-collins-provisions-to-opioid-act (HTTP 404)
- `#/p/C001047/positions` → http://www.dailymail.com/News/statenews/201004120920 (HTTP 404)
- `#/p/C001053/positions` → http://riponadvance.com/news/legislation-would-give-home-school-families-access-to-education-tax-deduction/ (HTTP 404)
- `#/p/C001053/positions` → https://amp.oklahoman.com/amp/7410360001/amp/7410360001 (HTTP 404)
- `#/p/C001056/positions` → http://www.elpasotimes.com/texas/ci_12907117 (HTTP 404)
- `#/p/C001066/positions` → http://tbo.com/pinellas-county/in-pinellas-head-start-starts-again-20140824/ (HTTP 404)
- `#/p/C001067/positions` → https://votesmart.org/public-statement/761529/us-rep-yvette-d-clarke-marks-roe-v-wade-anniversary#.W46RN5NKgWo (HTTP 404)
- `#/p/C001068/positions` → http://www.aldf.org/article.php?id=860 (HTTP 404)
- `#/p/C001068/positions` → http://www.downtownmemphiscommission.com/article.asp?id=76 (HTTP 404)
- `#/p/C001069/positions` → https://courtney.house.gov/media-center/press-releases/courtney-statement-trump-s-de-certification-iran-nuclear-agreement (HTTP 404)
- `#/p/C001072/positions` → http://carson.house.gov/newsroom/press-releases/congressman-andr-carson-statement-on-un-security-council-resolution-on (HTTP 404)
- `#/p/C001072/positions` → http://clerk.house.gov/evs/2008/index.asp (HTTP 404)
- `#/p/C001072/positions` → http://clerk.house.gov/evs/2009/index.asp (HTTP 404)
- `#/p/C001088/positions` → https://timesng.com.ng/2026/04/us-lawmaker-says-american-families-paying-the-price-for-war-of-choice/ (HTTP 404)
- `#/p/C001098/positions` → http://morningconsult.com/2015/06/voter-views-on-usa-freedom-act-bode-well-for-graham-and-rubio-not-cruz-and-paul/ (HTTP 404)
- `#/p/C001098/positions` → http://www.dailydot.com/politics/net-neutrality-ted-cruz-fcc/ (HTTP 404)
- `#/p/C001098/positions` → http://www.thedailybeast.com/articles/2014/01/30/the-issue-bringing-ted-cruz-and-black-democrats-together.html (HTTP 404)
- `#/p/C001098/positions` → https://www.tedcruz.org/wp-content/uploads/pdf/NewdowAmicus.pdf (HTTP 404)
- `#/p/C001101/positions` → http://clerk.house.gov/committee_info/oal.aspx (HTTP 404)
- `#/p/C001101/positions` → http://www.mass.gov/legis/journal/hj031308.pdf (HTTP 404)
- `#/p/C001101/positions` → http://www.metrowestdailynews.com/news/x1602167167/Patrick-signs-animal-control-reform-bill-in-Ashland (HTTP 404)
- `#/p/C001101/positions` → http://www.prochoicemass.org/media/press/20100826.shtml (HTTP 404)
- `#/p/C001108/positions` → http://www.bgdailynews.com/news/gubernatorial-hopeful-comer-speaks-about-farm-program/article_2d38f4b7-2105-591e-9e44-9269cdcb6d90.html (HTTP 404)
- `#/p/C001108/positions` → https://votesmart.org/candidate/political-courage-test/35169/james-comer-jr/#.WkR6b1Q-dE4 (HTTP 404)
- `#/p/C001113/positions` → http://www.ktvn.com/story/36524490/senator-catherine-cortez-masto-cosponsors-bill-on-gun-control-and-releases-statement-on-las-vegas-shooting (HTTP 404)
- `#/p/C001114/positions` → https://energycommerce.house.gov/subcommittees/health-117th-congress (HTTP 404)
- `#/p/C001121/positions` → https://one-colorado.org/new/2-25-equality-act-passes-in-u-s-house-of-representatives/ (HTTP 404)
- `#/p/C001125/positions` → http://algiersdevelopment.com/profiles/senator-troy-a-carter/ (HTTP 404)
- `#/p/C001131/positions` → https://www.austinmonthly.com/AM/August-2018/Greg-Casar-Fights-to-Change-Austin/index.php?cparticle=2&siarticle=1&requiressl=true#artanc (HTTP 404)
- `#/p/C001131/positions` → https://www.thenation.com/article/activists-austin-novel-plan-tackle-affordable-housing-crisis/ (HTTP 404)
- `#/p/C001131/positions` → https://www.thenation.com/article/austin-just-brought-paid-sick-leave-to-the-south/ (HTTP 404)
- `#/p/C001131/positions` → https://www.thenation.com/article/cities-saying-no-ice-canceling-contracts-agency/ (HTTP 404)
- `#/p/D000032/positions` → https://nbc-2.com/election/2020/11/03/republican-byron-donalds-wins-district-19-congressional-seat/ (HTTP 404)
- `#/p/D000032/positions` → https://www.orlandosentinel.com/politics/os-ne-scott-rubio-biden-certification-20210107-cqf3nlqro5hodj22e2xnfvgmuy-story.html?outputType=amp (HTTP 410)
- `#/p/D000216/positions` → https://appropriations.house.gov/news/statements/chairwoman-delauro-statement-at-hearing-on-impacts-on-women-denied-abortions-because (HTTP 404)
- `#/p/D000399/positions` → http://www.alternet.org/story/140715/shame%3A_the_%27anti-war%27_democrats_who_sold_out/ (HTTP 404)
- `#/p/D000399/positions` → https://doggett.house.gov/issues/transparency-trump-administration (HTTP 404)
- `#/p/D000399/positions` → https://doggett.house.gov/media-center/press-releases/house-passes-rep-lloyd-doggett-s-bipartisan-bill-protect-48-million (HTTP 404)
- `#/p/D000399/positions` → https://doggett.house.gov/media-center/press-releases/rep-doggett-introduces-permanent-extension-american-opportunity-tax (HTTP 404)
- `#/p/D000563/positions` → https://www.durbin.senate.gov/issues/immigration-and-the-dream-act (HTTP 410)
- `#/p/D000600/positions` → https://votesmart.org/candidate/political-courage-test/24312/mario-diaz-balart/ (HTTP 404)
- `#/p/D000631/positions` → http://pahouse.com/SouthEastDelegation/InTheNews/NewsRelease/?id=80281 (HTTP 404)
- `#/p/D000631/positions` → http://www.pahouse.com/PASafe/InTheNews/NewsRelease/?id=72304 (HTTP 404)
- `#/p/D000631/positions` → https://www.speaker.gov/newsroom/11221-0 (HTTP 404)
- `#/p/D000635/positions` → https://www.opb.org/article/2025/04/21/more-democratic-lawmakers-are-visiting-el-salvador-on-abrego-garcia-s-behalf/ (HTTP 404)
- `#/p/E000294/positions` → http://tpmdc.talkingpointsmemo.com/2010/06/emmer-defends-nullification-minnesotans-should-have-a-say-in-the-laws-that-govern-them.php (HTTP 404)
- `#/p/E000294/positions` → https://emmer.house.gov/media-center/press-releases/emmer-statement-department-interior-s-final-list-critical-minerals (HTTP 404)
- `#/p/E000295/positions` → http://iowapublicradio.org/post/candidate-profile-joni-ernst (HTTP 404)
- `#/p/E000295/positions` → http://www.newtondailynews.com/2013/11/26/ernst-payton-speak-at-local-gop-meeting/a8bhvwe/ (HTTP 404)
- …and 435 more

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
