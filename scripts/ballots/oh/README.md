# Ohio county official ballots (Nov 3, 2026)

## Hamilton County (v51)
- Ballots: Hamilton County Board of Elections, one printed sample ballot PDF per precinct split: votehamiltoncountyohio.gov/files/ballots/N<precinct><split>.pdf (618 PDFs, 563 precincts; 52 precincts have 2-3 splits).
- Map: Hamilton County CAGIS open data, Voting Precincts (Open_Data_Feature_Collection FeatureServer/41), 563 precincts.
- Parse: hamilton_hparse.py (pdfplumber words, fonts, sizes, 3 columns). Checks on every PDF: parsed races = "(Vote for" lines, write-ins = "Write-in" lines, questions = NO/AGAINST lines, nothing left over (618/618 pass).
- Districts: CD/SD/HD on every single-ballot precinct's ballot = Census TIGERweb (120th CD, 2026 SLD) at an interior point (0 mismatches; SD 8 is not up in 2026).
- Splits: the contests that differ between a precinct's splits are only school-district levies/income taxes or CD/HD races, so the app picks the split by the voter's Census unified school district and CD/HD; otherwise it shows the races common to all splits, labelled, with the official button.
- Built into data/ballots/oh-hamilton-2026-11-03.json (contest registry, ballot rotation kept) and oh-hamilton-precincts.json.

## Lucas County (v51)
- Ballots: Ohio's shared county sample-ballot site (lookup.boe.ohio.gov/vtrapp/lucas, the Lucas County Board of Elections' own ballot list): 315 precinct-split PDFs for 280 precincts (tgsi_list.mjs / tgsi_download.mjs, a real browser because the site has a bot check).
- Map: Lucas County GIS "Lucas County Wards and Precincts" Precinct Layer (2026), 280 precincts, names matched 1:1 to the ballot list.
- Parse: tgsi_parse.py. Check on every PDF: printed ovals per page = parsed candidates + write-ins + responses per page; nothing left over except the Board's signature lines (315/315 pass).
- Districts: CD/SD/HD on every ballot = the county map's ushouse/ohsenate/ohhouse (0 mismatches).
- Splits: 8 split precincts have identical ballots; 17 split by school district / HD; 4 (Harding 1, Spencer 1, Oregon 1, Richfield 1) differ by library/city/village questions and stay labelled with the official button.

## Montgomery County (v52)
- Ballots: Ohio's shared county sample-ballot site (lookup.boe.ohio.gov/vtrapp/montgomery), the Montgomery County Board of Elections' list: 468 precinct-split PDFs (tgsi_list.mjs / tgsi_download.mjs). PDF hashes kept, PDFs deleted after parsing.
- Map: Montgomery County GIS (gis.mcohio.org) voting precinct layer, 495 features with the Board's precinct, split, CD/SD/HD and school codes.
- Result: 347 single-ballot precincts complete, 39 split ballots picked by school district / district, 15 split precincts that differ by local questions stay labelled with the official button.

## Cuyahoga County cross-check (v52)
- Cuyahoga has been live since v37 (data/ballots/oh-cuyahoga-*.json, 915 precinct ballots from the Board's 12 sample-ballot books + the Board's "Voting Precincts 2026" map layer).
- cuyahoga_crosscheck_parse.py is an independent parser (ovals = options on every page). Nov 11 run: 758 of 915 ballots read cleanly, and all 758 are identical to the live data (contests, candidates in printed order, write-in lines, vote-for, issue numbers). The other 157 have a 3-line issue-option layout this parser does not read. There were 0 disagreements.
