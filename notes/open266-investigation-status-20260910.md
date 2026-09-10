# OPEN-266 investigation status: MA and VA root causes confirmed with real production data

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

## Confirmed: MA's excess is 100 rows (not ~75), and it's one homogeneous pattern -- not scattered failures

The original ~75 estimate (149 total minus yesterday's 74 `archived` count) was a rough
subtraction, not a row-level match, and turned out to undercount: the prod agent pulled the exact
bill UUIDs yesterday's `rev21` run touched (embedded in its own `S3 upload failed for bills/raw/
ma/.../{identifier}--{uuid}/...` log lines, via `_archive_path()`'s naming convention) and
filtered MA's 149 `is_error=False`/null-`archive_location` rows against that precise set --
**100 rows genuinely don't match any bill yesterday's run touched** (full data:
`notes/open266-data-pulled-20260910.md` on `notes/ops-handoff`).

This kills the "accumulated small failures across several weekly runs" hypothesis this write-up
originally floated -- the actual data doesn't look like that at all. All 100 rows are strikingly
homogeneous: same legislative session (`194th`) for all of them, same `version_note` for all of
them (`"Bill Text"`), same URL shape for all of them
(`https://malegislature.gov/Bills/194/{HD|SD}NNNN.pdf`), blank `version_date` for all of them. One
consistent pattern across 100 different bills reads far more like a single systemic gap specific
to MA's `"Bill Text"` document type (a filed bill's own text, distinct from
`Chapter_Law_Text_Enacted` and other version types MA already archives successfully) than like
independent, scattered upload failures. **Not yet confirmed whether this is a total gap** (no
`"Bill Text"` MA document has ever successfully archived) **or partial** -- the prod agent
flagged this as an easy follow-up pull (count of MA `"Bill Text"` rows with a real
`archive_location`) that hasn't been done yet.

**Practical consequence, worth watching for after OPEN-263's fix runs against MA (task-definition
revision 22, requested via `notes/open263-rev22-deployed-please-run-20260910.md`):** since these
rows are `is_error=False`, OPEN-263's skip-check fix makes them retryable on the next run, same as
any other stuck-but-successfully-extracted row. If the underlying cause was transient (e.g. a
past S3 permission gap, now resolved), the retry should succeed and `archive_location` should get
populated for all 100. If it's a live, still-present bug specific to `"Bill Text"` documents (for
example, something in `_s3_object_key()`/`_upload_and_verify()` that mishandles this URL shape or
media type specifically), the retry will fail again in the same way and regenerate new
null-`archive_location` rows for the same 100 bills, indefinitely. **That distinction can only be
answered by checking MA's row counts again after a real post-rev-22 archive run** -- if the count
of null-`archive_location`, `"Bill Text"`-type MA rows doesn't drop close to zero, that is itself
strong evidence of a live bug worth its own ticket, not just historical debris.

## Confirmed: VA's 4 rows exactly match the OPEN-33 hypothesis

The prod agent pulled the specific 4 rows (`notes/open266-data-pulled-20260910.md`): `SB 759`
(Finance and Appropriations Substitute, Chaptered, and Enrolled versions) and `HB 1320`
(Appropriations Substitute), all 2026 session, all `is_error=False` with `archive_location` still
null. This is exactly the shape the hypothesis predicted -- OPEN-33's backfill (2026-08-06) fixed
`is_error`/`raw_text` for 23,516 VA rows via a direct in-place DB update that never touched
`archive_location` at all. A document whose *original* scrape-time S3 upload also failed,
independent of the separate extraction bug OPEN-15 fixed, would look exactly like this: extraction
now succeeds (post-backfill), but the row was never actually uploaded, ever. Confirmed with two
real, named bills, not just "plausible" -- a small, already-understood straggler from OPEN-33, not
a new or ongoing bug. Same as MA's homogeneous set, these are `is_error=False` and therefore
retryable via OPEN-263's fix on VA's next real archive run.

## Acceptance criteria status (all four, for traceability)

| # | Criterion | Status |
|---|---|---|
| 1 | Determine MA's excess `is_error=False` rows' actual cause | **Confirmed: 100 rows (not ~75), one homogeneous `"Bill Text"`-type pattern, session 194th** -- total-vs-partial gap not yet distinguished (see above) |
| 2 | Confirm whether `is_error=True` rows are covered by an existing mechanism | **Confirmed: not covered by any current automatic or reusable mechanism** (see above) |
| 3 | Determine VA's 4 rows' actual cause | **Confirmed: exactly matches the OPEN-33 hypothesis** (see above) |
| 4 | Decide, with real evidence, whether any of this is worth a backfill, scoped separately from OPEN-263 | Decided below |

## Disposition

**VA's 4 rows and MA's 100 `is_error=False` rows:** no separate backfill script. Both are
retryable via OPEN-263's own fix on their jurisdiction's next real archive run, the same
mechanism recovering the ~624-row incident set -- no code change needed here, just the archive
run itself (already requested for ma/mi/wa/va via task-definition revision 22). The one
follow-up this ticket still owes: after that run, re-check MA's `"Bill Text"`-type null-
`archive_location` count. If it drops near zero, these were historical debris and OPEN-266 closes
clean. If a meaningful number remain (regenerated by the retry, not the original 100), that's
evidence of a live, still-present bug specific to MA's `"Bill Text"` document type -- worth its
own new ticket at that point, not a guess made now.

**The 35 `is_error=True` rows (ma: 30, mi: 4, wa: 1):** unaffected by any of the above --
confirmed above (criterion 2) to have no existing retry path at all, self-heal or otherwise.
Recovering them is a real, separate decision: a bespoke one-off script in OPEN-33's own style (35
rows across 3 jurisdictions is small), or building OPEN-229 first and using it. Not deciding
that here -- flagging it as the one piece of this ticket that requires an actual choice, not just
observation, whenever someone picks it up.
