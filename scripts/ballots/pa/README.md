# Pennsylvania official ballots (Nov 3, 2026)

Each county below posts one printed official sample ballot per voting district plus an official voting-district map.
The app finds the voter's district by point-in-polygon on the county map (data/ballots/pa-<county>-precincts.json)
and shows that district's printed ballot (data/ballots/pa-<county>-2026-11-03.json). Anything unmatched is labelled
"may not be complete" with the blue official button.

| County | Ballots | Map | Checks |
|---|---|---|---|
| Philadelphia | vote.phila.gov split PDFs (48) | Census CD/SD/HD | each split PDF matched exactly |
| Montgomery | webapp07.montcopa.org/voterservices/sampleballots (431 PDFs) | gis.montcopa.org Voting Districts (431) | 1:1 PDF<->district; CD/SD/HD on ballot = county GIS; every "(Vote for", YES and Write-In on the PDF parsed; 107/107 random points agree with the county server |
| Delaware | delcopa.gov/vote/sample-ballots (382 PDFs) | Delaware County GIS Voting Precincts (384) | CD/SD/HD = county GIS (0 mismatches); counts as above; Swarthmore Northern (unparseable layout) and Lansdowne 8 (no posted ballot) labelled |
| Chester | chesco.org 2026 sample ballot book (462 pages, 231 ballots) | Chester County GIS Voting Precincts (230) | CD/SD/HD = Census TIGERweb 2024 districts at an interior point of every precinct (230/230); counts as above |

Bucks posts image-only PDFs (needs OCR) and is not built. Other counties: labelled + official button.
Parsers: *_parse.py (pdfplumber word positions, fonts and sizes). Build steps: fetch -> parse -> checks -> JSON (see the parsers).
