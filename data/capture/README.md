# Ballot capture ("our own VIP data")

Shmuel's plan (Nov 10, 2026): build KnowUS's own nationwide ballot data by saving every state's and county's official
sample ballots in the weeks before each election, while they are posted (many counties take them down afterwards).

| File | What it is |
|---|---|
| `calendar.json` | Every election date from now through Nov 2027, by state, each with the official page that states it. |
| `sources.json` | Where each state / county posts its official sample ballots: URL, format, how to fetch it, whether it walls bots. Official sources only. |
| `manifests/<date>/<ST>/<source>.json` | What was captured: every file's URL, sha256, size, first/last seen, and which release asset holds the bytes. |
| `needs-browser.json` | Sources that wall automated fetches (or whose robots.txt says no). They are not retried by the job; a browser run captures them. |
| `state.json` | Which checkpoints (T45, T30, T14, T5, T2 days before) are done for each election and state. |
| `status.json` | The last runs' summaries and the elections in the next 60 days. |
| `staged/<date>/<ST>/` | App-format ballots converted from a capture (never published from here; a person reviews and publishes). |

Raw files live in GitHub releases named `capture-<date>-<ST>` (one zip per source per checkpoint, only new or changed
files), so the repository stays small.

How it runs: `.github/workflows/ballot-capture.yml`, daily at 11:41 UTC, plus manual runs (election + state).
Scripts: `scripts/capture/capture.py` (plan / run), `scripts/capture/stage.py` (converts what has a parser),
`scripts/capture/parsers/vip5/` (a VIP 5 feed + its printed sample ballots -> the app's ballot files; the v49 North
Carolina pipeline, generalized).

Rules carried over from the ballots in the app: a ballot is "complete" only when it matches one printed official sample
ballot exactly (every contest, candidate and question present, nothing extra, the same number of races printed);
everything else is stored with ok:0 and its reason, and the app shows it labelled "may not be complete" with the official
button. No contest is ever invented; sources are official election offices only.

## Asking offices that have not posted (approved by Shmuel, Nov 10 2026)

`scripts/capture/requests_queue.py` (run by the daily job) drafts one email per office whose ballots are not captured
21 days or less before its election (and 3+ days out), into `request-queue.json`, using `request-template.json`
(sender "Samantha (KnowUS)", from shmuel.knowus@mail.tab.bot). The job never sends mail. Tab sends each drafted entry
that has an official email and records it with `scripts/capture/requests_mark.py "<key>" sent`; one follow-up 7 days
later if there is no reply (`... followup`), never more. Ballots that come back are converted with the same parsers and
rules as captured ones. Offices with no official email on file are listed as such, never guessed.
