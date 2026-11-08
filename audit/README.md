# KnowUS site audit

`.github/workflows/site-audit.yml` opens the live app (https://knowus.sites.tab.bot/) every 6 hours, and on demand
(Actions → "KnowUS site audit" → Run workflow), in Chromium at 390 px and 360 px phone widths, and reports anything broken.
It costs nothing (GitHub-hosted runners on this public repo) and never signs in or writes to Firebase; the sign-in screen
is only loaded, and the audit hides it on its own copy of the page to read the screens behind it.

What it checks
- JavaScript errors, failed requests for the app's own files and data
- sideways scroll on every page it visits
- dead taps: every link, button, row, box with ›, "About the role" / "Positions and record" box and local official row
  must be reachable by a finger and must open something or change the view (taps that could sign in, save, track or
  email are never pressed)
- pages: President, VP, Cabinet, 3 past presidents, all 100 senators, 60 random House members, all 50 governors,
  state Executive/Legislative/Judicial pages, the Election tab, Local (Ohio → Cuyahoga → University Heights plus 5 random
  states: county → city → 3 officials), every Constitution page, the Declaration, 10 random Federalist papers, Learn pages,
  Bills + 10 random bills, Exec Orders once that tab exists; then up to 40 in-app links it saw but did not visit
- data: "undefined", "null", "NaN", "[object Object]" on screen, empty boxes, broken images, duplicates in one list,
  an end-of-term date in the past, the "Updated" time older than 48 h, the hourly refresh failing, non-integer vote totals
- wording: banned labels in AI-written text (racist, extremist, far-right, far-left, authoritarian, controversial,
  divisive, baseless, debunked, conspiracy, false claims); official titles of orders and bills are exempt
- 200 random outbound source links (HEAD, then GET): 404/410 and 5xx are flagged

Reading the results
- `audit/reports/latest.md` — the newest report, grouped by severity; `audit/reports/latest.json` — the same as data
  (counts by severity, each issue with route, element, problem, widths and screenshot name)
- `audit/reports/history/` — one report per run (last 120); `audit/reports/history.csv` — counts per run
- screenshots: the run's "site-audit-screenshots" artifact (Actions → the run → Artifacts)
- any high-severity problem opens or updates ONE issue titled "Site audit: N problems found"; a clean run closes it

Run locally: `cd audit && npm i playwright && npx playwright install chromium`, then
`node audit/crawl.mjs --shard A --width 390 --out out/A-390` (shards A, B, C; `--shard T` with `AUDIT_ROUTES="#/p/pr47"`
checks just those routes), `node audit/data.mjs --out out/data`, `node audit/report.mjs out`.
