# OPEN-266 investigation status: MA's and VA's row-level patterns characterized with real data -- true causes still open

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

## Characterized with real data: MA's excess is 100 rows (not ~75), one homogeneous pattern -- true cause still open

Two different things below, kept deliberately separate: what the data confirms about the shape
of these rows (solid), and why they ended up this way (still a hypothesis, not proven).

**Confirmed by the data:** the original ~75 estimate (149 total minus yesterday's 74 `archived`
count) was a rough subtraction, not a row-level match, and turned out to undercount: the prod
agent pulled the exact bill UUIDs yesterday's `rev21` run touched (embedded in its own `S3 upload
failed for bills/raw/ma/.../{identifier}--{uuid}/...` log lines, via `_archive_path()`'s naming
convention) and filtered MA's 149 `is_error=False`/null-`archive_location` rows against that
precise set -- **100 rows genuinely don't match any bill yesterday's run touched.** The source
note (`notes/open266-data-pulled-20260910.md` on `notes/ops-handoff`) states the session,
`version_note`, and URL-shape properties below hold for all 100 rows, not just the 10-row sample
it prints for illustration -- worth stating plainly here since a documentation write-up
shouldn't quietly launder a 10-row sample into a 100-row claim: same legislative session
(`194th`) for all of them, same `version_note` for all of them (`"Bill Text"`), same URL shape for
all of them (`https://malegislature.gov/Bills/194/{HD|SD}NNNN.pdf`), blank `version_date` for all
of them.

**Not confirmed -- a reading of that pattern, not a proven mechanism:** this makes the
"accumulated small failures across several weekly runs" hypothesis this write-up originally
floated look considerably less likely (100 identical-shape rows don't resemble several
independent incidents the way a truly scattered failure pattern would), but uniform document
characteristics don't by themselves prove *when* these failures happened or rule out repeated
failures against the same document type across multiple runs -- it's evidence against the
original hypothesis, not a disproof of every alternative. One consistent pattern across 100
different bills is suggestive of a single systemic gap specific to
MA's `"Bill Text"` document type (a filed bill's own text, distinct from
`Chapter_Law_Text_Enacted` and other version types MA already archives successfully). But
*why* that gap exists -- and whether it's a total gap (no `"Bill Text"` MA document has ever
successfully archived) or partial -- is genuinely still open. The prod agent flagged the
total-vs-partial count (MA `"Bill Text"` rows with a real `archive_location`, for comparison) as
an easy follow-up pull that hasn't been done yet. Acceptance criterion 1 should be read as
"characterized, cause still open," not "solved."

**Practical consequence:** since these rows are `is_error=False`, OPEN-263's skip-check fix makes
them retryable on MA's next real archive run (task-definition revision 22, requested via
`notes/open263-rev22-deployed-please-run-20260910.md`). Whether that retry actually succeeds (a
transient historical cause) or fails again in the same way (a live, still-present bug specific to
`"Bill Text"` documents -- e.g. something in `_s3_object_key()`/`_upload_and_verify()` mishandling
this URL shape or media type) is exactly what the verification plan in the Disposition section
below is built to answer precisely, rather than guessed at here.

## VA's 4 rows match the OPEN-33 hypothesis's predicted shape exactly -- historical cause not independently traced

The prod agent pulled the specific 4 rows (`notes/open266-data-pulled-20260910.md`): `SB 759`
(Finance and Appropriations Substitute, Chaptered, and Enrolled versions) and `HB 1320`
(Appropriations Substitute), all 2026 session, all `is_error=False` with `archive_location` still
null. This is exactly the observable shape the hypothesis predicted -- OPEN-33's backfill
(2026-08-06) fixed `is_error`/`raw_text` for 23,516 VA rows via a direct in-place DB update that
never touched `archive_location` at all, so a document whose *original* scrape-time S3 upload also
failed, independent of the separate extraction bug OPEN-15 fixed, would look exactly like this:
extraction now succeeds (post-backfill), but the row was never actually uploaded, ever. Worth being
precise about what's actually established here versus what isn't: these 4 rows' current field
values match the hypothesis's prediction exactly, and that match is real evidence for it -- but
it wasn't independently checked against OPEN-33's specific 23,516-row backfill population (e.g. by
row ID), so this is the hypothesis matching observed reality, not a direct before/after trace of
these exact 4 rows through OPEN-33's own update, and not a ruling-out of every other possible
explanation for the same field values. Treat criterion 3 as "strongly supported, not independently
traced" rather than fully closed. Same as MA's set, these are `is_error=False` and therefore
retryable via OPEN-263's fix on VA's next real archive run.

## Acceptance criteria status (all four, for traceability)

| # | Criterion | Status |
|---|---|---|
| 1 | Determine MA's excess `is_error=False` rows' actual cause | **Characterized with real data** (100 rows, not ~75; one homogeneous `"Bill Text"`-type pattern confirmed across all 100) -- **true root cause still open**, pending the total-vs-partial pull and the post-retry check below |
| 2 | Confirm whether `is_error=True` rows are covered by an existing mechanism | **Confirmed: not covered by any current automatic or reusable mechanism** (see above) |
| 3 | Determine VA's 4 rows' actual cause | **Strongly supported, not independently traced**: observed shape matches the OPEN-33 hypothesis's prediction exactly, but not row-traced against OPEN-33's specific backfill population -- actual historical cause remains technically open (see above) |
| 4 | Decide, with real evidence, whether any of this is worth a backfill, scoped separately from OPEN-263 | **Partially decided**: no backfill for MA's 100 or VA's 4 (see disposition). **Not decided** for the 35 `is_error=True` rows -- that choice is still open |

## Disposition

**VA's 4 rows and MA's 100 `is_error=False` rows:** no separate backfill script. Both are
retryable via OPEN-263's own fix on their jurisdiction's next real archive run, the same
mechanism recovering the ~624-row incident set -- no code change needed here, just the archive
run itself (already requested for ma/mi/wa/va via task-definition revision 22).

**Verification plan, and an honest limit on what DB state alone can show:** an aggregate
before/after count can't distinguish "recovered," "not yet attempted," and "failed again," and
OPEN-263's own delete-then-recreate mechanic means a retried row gets a new row id, so row-id
comparison doesn't work either -- the natural key, `(bill, version_note, version_date,
source_url)`, is what stays stable and is the right thing to compare. But the natural key alone
still isn't enough: a row whose retry was **never attempted this run** (e.g. the run didn't reach
that bill at all) and a row whose retry **was attempted and failed again** look identical from the
database afterward -- both leave a still-`is_error=False`/null row under the exact same key,
completely unchanged, because OPEN-263's fix only deletes-and-recreates the row on a **successful**
create; every early-exit failure path (fetch error, blocked, persist error) leaves the
pre-existing row exactly as it was, with no visible change at all -- only a successful retry
actually replaces it (with a new row id, but a real `archive_location`).

1. Before drawing any conclusion, confirm task-definition revision 22 actually ran to completion
   against `ma` (and `va`).
2. Capture the natural key for all 100 MA rows and all 4 VA rows *before* that run (already have
   VA's; MA's are in `notes/open266-data-pulled-20260910.md`).
3. After the run, look up each of those exact natural keys again. A real `archive_location` now
   set is unambiguous: recovered. A row still `is_error=False`/null under the same key is
   ambiguous by DB state alone -- resolving it needs either (a) the run's own console/log output
   checked for these specific URLs (a `fetch_errors`/`blocked`/`persist_errors` line naming one of
   them is direct evidence of an attempt that failed again; no line at all is evidence, not proof,
   that it wasn't reached), or (b) confirming the run actually reached these specific *documents*,
   not just these bills. Checked directly against the current code for exactly this: every
   exception type the per-link loop can raise either `continue`s to the next link (a fetch
   exception, `WafBlockDetected`, a persist `OSError`) or falls through to the `create()` attempt
   regardless (an extraction exception, which sets `is_error=True` but does not `continue`) --
   except `ScrapeError`, which is deliberately re-raised and propagates all the way out of
   `archive_bill_versions()`, aborting the entire run, not just the current bill. There is no third
   path that silently exits one bill's link loop early while the run carries on to the next bill.
   Checked the outer per-bill loop (`archive()`) directly too, since a per-bill catch-and-continue
   there would be exactly the kind of gap that could break this argument: its only `except` clause
   is `except ScrapeError as e: ... sys.exit(1)` -- it re-raises nothing, catches nothing else, and
   exits the whole process rather than moving on to the next bill. So the only two outcomes for any
   bill this run reaches are "every one of its links got a recorded outcome" or "the process
   crashed/exited non-zero," never a silent partial skip. That means a run that's confirmed to
   have completed normally (not crashed, exit code 0, full summary line printed) could not have hit
   a mid-run abort anywhere in it -- so a target bill appearing anywhere in that run's processing
   had every one of its links, including its `"Bill Text"` link, walked to one of those recorded
   outcomes. Cross-check MA's total distinct bills processed this run against its known full bill
   count (and confirm no `n`-count limit was active) to rule out a partial/limited run in the first
   place.
4. Distinguish two different claims here. A single confirmed-failed-again document (via 3a or 3b)
   is real evidence of a live failure for that one document -- weak and possibly transient on its
   own, but not nothing. Reserve "evidence of a systemic live bug" (the pattern this ticket is
   actually trying to characterize) for a result where most or all of MA's 100 keys come back
   confirmed-attempted-and-still-null; a handful failing while most recover is still worth noting
   as a genuine, if isolated, failure, just not evidence of the systemic gap hypothesized above.
   The same check applies to VA's 4, even though a systemic pattern there is far less likely given
   the population is only 4 rows.

**The 35 `is_error=True` rows (ma: 30, mi: 4, wa: 1):** unaffected by any of the above --
confirmed above (criterion 2) to have no existing retry path at all, self-heal or otherwise.
Recovering them is a real, separate, still-undecided choice: a bespoke one-off script in OPEN-33's
own style (35 rows across 3 jurisdictions is small), or building OPEN-229 first and using it. Not
deciding that here -- flagging it as the one piece of this ticket that requires an actual choice,
not just observation, whenever someone picks it up. OPEN-266 should not be closed on the strength
of MA/VA's disposition alone while this piece remains open.
