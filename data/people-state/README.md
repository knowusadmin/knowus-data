# State legislators who sponsor bills (KUS-SPONSORS 3, Nov 12 2026)
Built by scripts/sponsors/state_sponsors.py from Open States' monthly public PostgreSQL dump (data.openstates.org/postgres/monthly/, streamed by HTTP range; same reader as scripts/fetch_state_bulk_details.py).
- ../bills/state-sponsors/<ST>.json: bills{<app bill id>: {s: primary sponsor, f: the person the list card names, p: {name: id} when several primaries, c: {cosponsor name: id}}}, people{id: {n,p,ch,d}}. ids = Open States person UUIDs (ocd-person/<uuid>), from each sponsorship row's person_id: never matched by name.
- <ST>.json: people{uuid: {n, p (party), cur, ch (U/L), d (district), t (title), e (email), img, off (offices: address/voice/fax), links, src, terms, sp (bills sponsored), cs (cosponsored)}}.
- Photos, links and sources kept only when scripts/sources_policy.py classifies them official (government sites; no party/caucus, campaign or news hosts).
- Membership start dates are record dates, not first-elected dates: the app does not show them.
- Rebuild monthly after the new dump (1st of the month): python3 scripts/sponsors/state_sponsors.py . . ; the hourly list fetch also writes sponsorPid on new bills.
- ../people-state-votes/<ST>/<uuid>.json (KUS-SPONSORS 4): {src, m:[motion texts], v:[[bill id, date, motion index, option, result]]}: each legislator's roll-call votes on KnowUS bills, from opencivicdata_personvote rows that carry the person's Open States ID (voter_id). Built by scripts/sponsors/state_votes.py; votes recorded by name only are not used.
