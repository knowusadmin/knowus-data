# North Carolina full official ballots (v49)

All sources are the NC State Board of Elections (https://dl.ncsbe.gov):
- data/vipFeed/vipFeed-37-<date>.zip: precinct splits, contests, candidates, official street address ranges
- ENRS/<date>/results_pct_<date>.zip: canvassed precinct results (each precinct's contest set must match the feed)
- data/SampleBallots/<date>/*.pdf: every printed official sample ballot (each ballot style must match one: all candidates and referenda present, none extra; contest and candidate order as printed)
- Elections/<year>/Candidate Filing/referendums_<date>.pdf: referendum text with punctuation

Run in a folder with raw/ holding the four downloads above:
1. fetch_pdfs.py (needs sb_keys.json: the S3 listing of data/SampleBallots/<date>/) -> sbtxt/*.txt.gz (PDFs deleted after reading)
2. build1.py -> stage1.json   3. match2.py -> stage2.json + corder.json   4. NC_OUT=<dir> build3.py -> <county>.json + index.json
coverage.py checks every official street range against the built files.
For a new election change the date in the file names. Contests the feed omits (write-in-only offices) are added from the canvass.
