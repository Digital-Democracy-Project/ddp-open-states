# OPEN-266 investigation status: one of four acceptance criteria confirmed, two blocked on production data

OPEN-266 was split out of OPEN-263's investigation (see `notes/stuck-rows-correlation-breakdown-20260910.md`
and `notes/backfill-scope-decided-split-filed-20260910.md`) to cover the ~123
`BillVersionDocument` rows with null `archive_location` that predate the 2026-09-09 S3-permission
incident. This write-up records what's confirmed so far and what's still open, rather than
guessing at the remainder to close the ticket out prematurely.

## Confirmed: the `is_error=True` rows (ma: 30, mi: 4, wa: 1) are not covered by any existing mechanism

OPEN-266's acceptance criteria ask whether these 35 rows are already handled by OPEN-33's
reprocess-in-place mechanism, or OPEN-229's generalized `reextract` command. Checked both
directly:

- **OPEN-33** (done, 2026-08-06) was a one-off, VA-specific backfill script -- it reprocessed
  already-downloaded files on disk for VA only, via a direct in-place DB update, no live
  re-scrape, no S3 involved at all. It was never built as a reusable per-jurisdiction tool.
- **OPEN-229** ("generalize OPEN-33's reprocess-in-place mechanism into a real `reextract`
  command") is still status **To Do** in Jira, unstarted. Its own description confirms: "no
  `reextract` command exists; OPEN-33's own backfill was a one-off VA-specific mechanism, never
  generalized into a reusable per-state command."

So these 35 rows are genuinely stuck today, the same way the OPEN-263 rows were before that
fix -- just for a different underlying reason (a real extraction failure that happened *before*
the S3 upload step, rather than a blocked upload after a successful extraction). Whoever scopes
the eventual fix has two real options: a bespoke one-off script in OPEN-33's style (35 rows total
across three jurisdictions is small), or building OPEN-229 first and using it generally. Not
deciding that here -- this write-up is the input for that decision, not the decision itself,
consistent with how the original stuck-rows breakdown was handled.

## Still open: MA's ~75 excess `is_error=False` rows

`notes/stuck-rows-correlation-breakdown-20260910.md` found MA has 149 rows with `is_error=False`
and `archive_location IS NULL`, against a 2026-09-09 `rev21` batch `archived` count of only 74 --
roughly double, meaning about 75 of them predate yesterday's incident and have some other,
unconfirmed cause.

What's ruled in from history: MA had zero archiving activity at all before 2026-08-10
(`project-archive-scheduler-al-ma-us-weekly` -- "AL, MA, US had zero archiving log lines ever in
prod's `logs/scraper.log` before this"), so every MA `BillVersionDocument` row was created within
the roughly one-month, weekly-cadence window between then and the 2026-09-09 incident. One
plausible explanation -- not yet confirmed -- is that MA's weekly runs each hit a handful of the
same class of S3-upload failure OPEN-263 just fixed at 100%-failure scale, accumulating a smaller
number across several earlier runs rather than one big batch. This can't be confirmed or ruled
out without row-level data (which specific bills/versions/URLs, and whether they cluster into
distinct batches) that this dev checkout cannot query directly -- see "Blocked on" below.

## Still open: VA's 4 rows

VA had `fetched=0` in both of 2026-09-09's runs (only 2 real 404 `fetch_errors`, never reached
the persist/upload step), so these 4 predate the incident entirely and are unexplained by it.

Working hypothesis, not yet confirmed: OPEN-33's backfill (2026-08-06) fixed `is_error`/`raw_text`
for 23,516 VA rows via a direct in-place DB update with no S3 involved at all. If those rows
already had a real `archive_location` set from their *original* scrape-time upload -- independent
of the later-discovered extraction bug OPEN-15 fixed, since `is_error` and `archive_location` are
tracking two different pipeline stages -- then only documents whose *original* upload also failed,
on top of the separate extraction bug, would still show null today. That would make these 4 a
small, unrelated straggler rather than a new bug. Requesting the specific 4 rows would confirm or
kill this directly.

## Blocked on: production row-level data

This dev checkout has no direct RDS or production-Postgres-mirror access at the row level needed
here -- the local AWS IAM user (`ddp-scraper`) lacks `secretsmanager:GetSecretValue` on the RDS
master credential (that permission is scoped to the ECS task role, not this local user), and the
Mac's own local Postgres instance reachable from this environment is a separate, unrelated
database. A data request (bill/version/URL identifiers for MA's excess rows and VA's 4, or at
minimum a legislative_session distribution for MA) has been filed on `notes/ops-handoff` for the
prod agent to pull: `notes/open266-data-request-20260910.md`.

## Disposition

Not filing a backfill or code change here -- OPEN-263's own fix already makes all of these rows
retryable on their jurisdiction's next real archive run (ma/mi/wa/va), the same mechanism that
recovers the ~624-row incident set. This ticket's remaining scope is purely diagnostic: writing
down the actual cause for MA's excess and VA's 4 before deciding whether any of it warrants a
deliberate one-off action versus letting the next scheduled run recover it naturally. Will follow
up with a second write-up once the requested data comes back.
