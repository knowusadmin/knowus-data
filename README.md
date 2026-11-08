# knowus-data

Hourly, free data refresh for the KnowUS app (knowus.sites.tab.bot). A GitHub Actions job
(`.github/workflows/refresh.yml`, every hour at :23 UTC, plus a manual "Run workflow" button) fetches public
sources, and commits the JSON below only when something actually changed. No AI is used anywhere in the job.

The app loads these files from
`https://raw.githubusercontent.com/knowusadmin/knowus-data/main/data/...` and keeps its built-in copy as the fallback.

## Files

| File | What it is | Source |
|---|---|---|
| `data/officials.json` | Same shape as the app's `window.GOV_DATA` (data.js): `asOf`, `congressAsOf`, `states`, `fed`, `people` | the app's own `live.js` merge, run in Node |
| `data/officials-overlay.json` | The overlay `live.js` caches on phones (`localStorage['wio-live-v1:'+asOf]`) | same run |
| `data/officials-meta.json` | When it was checked, which sources answered, what changed, counts per group | same run |
| `data/mayors-current.json` | Current mayor of each city in the app's `data/mayors.json` | Wikipedia city infobox, cross-checked with Wikidata |
| `data/bills/index.json`, `data/bills/XX.json` | Bill lists, same shape as the app's `data/bills/` | GovInfo (federal, keyless), Open States (states) |
| `data/bills/detail/*` | Bill pages; official summaries are added as soon as they are published | GovInfo BILLSTATUS, Open States export |

Officials sources: U.S. Congress from unitedstates/congress-legislators; governors, lieutenant governors, attorneys
general, secretaries of state, Cabinet and VP from Wikipedia's current-officeholder tables; Wikidata as backup and for a
new President; Wikipedia page summaries for photos/descriptions of anyone new. A replacement is taken only once the
source shows the new person's start date has arrived.

## Safety guards
* If an officials source fails, or a group (senators, representatives, governors, Cabinet, ...) shrinks by more than 10%
  against the last committed file, the previous files are kept and the run is marked failed.
* Same for mayors (fewer cities resolved than before).
* Files whose only change is a timestamp are not committed, so the repo grows only with real changes.

## Secrets (Settings -> Secrets and variables -> Actions)
* `OPENSTATES_KEY`: Open States API key (state bills). Without it, state bills are skipped.
* `CONGRESS_KEY` (optional): api.data.gov key for the Congress.gov API. Without it, federal bills come from GovInfo bulk data (no key).

## Base copies
`base/data.js`, `base/live.js` and `base/mayors.json` are the app's current files, re-read from the live site on every run
(so the refresh always uses the app's latest code and baked data); the copies here are the fallback if the site is unreachable.
