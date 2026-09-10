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

**This is a permanent dead end, not a "not yet retried" -- unlike the `is_error=False` rows
below.** OPEN-263's own skip-check fix is deliberately narrower than "retry anything not fully
archived": it only reclassifies a row as retryable when `is_error=False` and `archive_location`
is unset (a successful extraction whose upload failed). A row with `is_error=True` still matches
the skip-check's other branch and is skipped on every future run, by design -- retrying every
extraction failure automatically on each archive run would repeat the exact live-traffic cost
OPEN-33/OPEN-229's own reprocess-in-place mechanism exists to avoid (reprocessing from an
already-downloaded local file, not re-fetching). So these 35 rows do not self-heal the way the
`is_error=False` rows do; recovering them requires one of the two real options below, not just
waiting for the next scheduled run. Whoever scopes the eventual fix has two: a bespoke one-off
script in OPEN-33's style (35 rows total across three jurisdictions is small), or building
OPEN-229 first and using it generally. Not deciding that here -- this write-up is the input for
that decision, not the decision itself, consistent with how the original stuck-rows breakdown was
handled.

## Still open: MA's ~75 excess `is_error=False` rows

`notes/stuck-rows-correlation-breakdown-20260910.md` found MA has 149 rows with `is_error=False`
and `archive_location IS NULL`, against a 2026-09-09 `rev21` batch `archived` count of only 74 --
roughly double, meaning about 75 of them predate yesterday's incident and have some other,
unconfirmed cause.

What's ruled in from history: a prior investigation found MA had zero archiving log lines at all
in prod's `logs/scraper.log` before 2026-08-10 (`project-archive-scheduler-al-ma-us-weekly`).
Taking that log record as complete and `BillVersionDocument` creation as tied to that archiving
path (both reasonable but unverified assumptions, not independently re-confirmed here) would place
every MA row within the roughly one-month, weekly-cadence window between then and the 2026-09-09
incident. One plausible explanation -- not yet confirmed -- is that MA's weekly runs each hit a handful of the
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

## Acceptance criteria status (all four, for traceability)

| # | Criterion | Status |
|---|---|---|
| 1 | Determine MA's ~75 excess `is_error=False` rows' actual cause | Open -- hypothesis written up above, blocked on production data |
| 2 | Confirm whether `is_error=True` rows are covered by an existing mechanism | **Confirmed: not covered by any current automatic or reusable mechanism** (see above) |
| 3 | Determine VA's 4 rows' actual cause | Open -- hypothesis written up above, blocked on production data |
| 4 | Decide, with real evidence, whether any of this is worth a backfill, scoped separately from OPEN-263 | Blocked -- depends on 1 and 3 resolving first; not decided here |

## Disposition

Not filing a backfill or code change here. The recovery story differs by row type, which is the
one correction this write-up makes over its own first draft: OPEN-263's fix makes the
`is_error=False`/null-`archive_location` rows (MA's ~75 excess, VA's 4) retryable on their
jurisdiction's next real archive run, the same mechanism that recovers the ~624-row incident set --
but it deliberately does **not** touch the 35 `is_error=True` rows (ma/mi/wa), which stay stuck
until a separate action is taken (see above). This ticket's remaining scope is diagnostic and
decision-making: confirm MA's and VA's actual causes, then decide (criterion 4) whether any of
this -- including the `is_error=True` rows, which need action regardless of cause -- is worth a
deliberate one-off script now versus waiting on OPEN-229.

**Verification plan for the next write-up:** once the requested production data comes back,
confirm or reject the VA hypothesis by checking whether the 4 rows fall within the specific
23,516 rows OPEN-33's backfill touched, and confirm or reject the MA hypothesis by checking
whether its excess rows cluster into distinct groups consistent with separate weekly runs (rather
than one batch). Separately, after OPEN-263's fix has been live through at least one real archive
run per jurisdiction (ma/mi/wa/va), re-count each jurisdiction's `is_error=False`/null-
`archive_location` rows -- a drop to (near) zero for that subset would confirm the retry mechanism
recovered them as expected; the `is_error=True` counts are expected to stay unchanged, since
nothing in OPEN-263 touches them.
