# OPEN-180 epic: Ramon thinks 4 of the open tickets are actually done -- please check and close what's confirmed

Ramon reviewed the current OPEN-180 open-ticket list and flagged 4 that he believes are already
done in practice, even though Jira still shows them In Progress/In Review. Asked me to check with
you rather than just re-reading the tickets myself, since you have the actual EC2/production
visibility to confirm real state, not just what's written on the ticket.

## OPEN-191 (In Progress) — "Phase 2: move the database and api-v3 to AWS together"

The highest-risk item in the epic (the only phase that risks the website). Given tonight's work
alone -- the RDS replica is live and logically replicating in real time (confirmed directly,
`pg_subscription`/`pg_stat_subscription`), api-v3 is running against it, and multiple real
production reads/writes went through it tonight (OPEN-293's backfill verification, the MI LegBot
run's bill text reads) -- this looks functionally complete. Please confirm from your side whether
there's anything still outstanding (e.g. a cutover step, DNS/traffic still pointing at the old
path, a rollback path not yet retired) before this gets marked Done, or close it if there isn't.

## OPEN-265 (In Review) — LegBot's Mac Studio bill-text read path for RDS-only-loaded jurisdictions

## OPEN-290 (In Review) — Consolidate `/trigger/scraper-session-legbot` into `/trigger/bill-artifact-generation`

## OPEN-292 (In Review) — LegBot overlap lock's flat 4h TTL doesn't cover full-session sweeps (lease renewal)

All three are already In Review, and OPEN-292 in particular has direct real-world validation
already recorded: your own note tonight (`mi-full-session-run-complete-20260916.md`) said the
Mac-side restart carrying PR #158's lease-renewal fix was deliberately held until the MI
full-session run finished, specifically *because* the old flat 4h TTL couldn't have covered a
31.4-hour run -- and that run just completed clean with no lock-related issue reported. If that
restart has since happened (or once it does), that's real evidence this one's fix works as
intended. Please check whether each of these three has a merged PR with nothing left blocking
"In Review" -> "Done", and transition the ones that are actually finished.

Not doing the transitions myself -- flagging so you can confirm against what's actually merged/
deployed rather than me guessing from ticket text alone.