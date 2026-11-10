# Official 2026 general-election ballots (v46, Nov 10 2026)

Rule (owner): every address gets either a verified COMPLETE official ballot, or the heading
"Races we've confirmed for your address (may not be complete)" plus the blue "See your complete official sample ballot" button.

Connecticut (data/ballots/ct-2026-11-03.json): every town's official sample-ballot PDF from the Secretary of the State
(portal.ct.gov/sots/election-services/town-ballots/2026-november-town-election-ballots), 169 towns, 609 ballot faces.
`ctparse.py` reads each PDF's grid by word positions (cell labels 1A, 2B ...), `ctbuild.py` builds contests/questions and runs
cross-checks (statewide offices identical on every face; US House / State Senate / State House identical across each district;
every column header recognised; question text complete). A face that fails any check is stored with ok:0 and its reasons
(`why`) and the app shows it labelled with the town's PDF button. Address -> face: town (Census county subdivision) + CD + SD + HD.

Rockland County NY (data/ballots/ny-rockland-2026-11-03.json): all 307 election-district sample ballots from the Rockland
County Board of Elections' official sample-ballot site (app.enhancedvoting.com), fetched with `rockland_fetch.js` (a real browser;
the API needs the page's CSRF header). Address -> ballot: town + CD + SD + AD + village (only villages with November contests).
When several different ballots fit (Clarkstown town-council wards), only shared races show, labelled, with the official link.
