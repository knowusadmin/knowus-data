# Florida county official ballots (Nov 3, 2026)

## Palm Beach County (v53)
- Ballots: Palm Beach County Supervisor of Elections, "2026 General Election Sample Ballots" (votepalmbeach.gov/DocumentCenter/View/2735): one printed 2-page ballot per precinct, 817 ballots (812 geographic precincts + 5 non-geographic 9901.x/9902 ballots, which are not used). The site needs a real browser (browser_download.mjs).
- Map: the Supervisor of Elections' "Precincts_2026" layer (services1.arcgis.com/ZWOoUZbtaYePLlPw PRECINCTS/FeatureServer/0, used in its Voting Precinct and District Map), 813 polygons. 812 match the ballots 1:1, plus 1 "NP" area.
- Parse: palmbeach_parse.py. Check on every ballot: every printed oval is an option of a contest (45,196 ovals, 0 left over); 0 ballots flagged.
- Contests: 31 races + 12 questions (6 judicial retentions, Amendments 1-3, County Parks / Library District / School District questions). Every race matches the Supervisor's "All Contests" sample ballot (candidates, order, write-in lines).
- Districts: the Congress, State Senate, State House and School Board numbers printed on each precinct's ballot equal the Supervisor's own district layers at an interior point of the precinct: CD 812/812, HD 812/812, SD 622/622 (where on the ballot), School Board 129/129. 0 mismatches.
