# GO: OPEN-390, answers your stop `8e93940`: reject only the NC changelogs whose comparison changed in the 11-16 clean-up, then fill every missing one. Nothing is deleted. 2026-11-17 (Mac side)

**Ramon, 2026-11-17** (OPEN-390 comment 21274): "yeah, we can simply reject the bad ones on production so that the next legbot run writes over them. no need to delete any data".

**Why your 923 rows exist:**
* They were written by the NC full-session LegBot run of 10-19 to 10-21, for the 474 bills that had a comparison then. My "about 0" came from a stale 10-18 count; my mistake.
* Since then, your 11-16 text clean-up (OPEN-584, struck words; status `729baa3`, step 4A: `diffs_corrected=633`) changed some of those comparisons. So some of the 923 describe the old text, and those are the ones to reject.

**The model server is free:**
* Ramon stopped the Mac's organization-logo catch-up at 17:16 local (22:16 UTC). The Mac log's last logo item is 22:15:49 UTC; since 22:16 it logs `organization_logo_catch_up: disabled`. The posts you saw up to 22:25 were from its last minutes.
* The Mac side's LA/NE dev sample (SYNC-175) finished at 23:00 UTC; nothing of it is running.
* At 23:11 UTC: no LegBot bill task on CAMS in the last 10 minutes, and no open production LegBot run.

## What I need from you
1. **Find the bad ones (read only):**
   * for each of the 923 NC `bill_changelog` rows, take the comparison it was written from (the `diff_from_previous_version` of the row's `bill_version` document, compared against `compare_version`);
   * compare that comparison in your **11-16 export** (step 4A, 6,207 rows, md5 `572f4b66dbcea3b201ed80092cef07f0`, taken before the refresh) with the same document's comparison in RDS **today**;
   * **the rows to reject are those whose comparison differs**, at most 633.

   Report the count, by session and version note, plus 3 example bills. If the export can't be matched to a row (an id mismatch, a document missing), list those and treat them as not changed.
2. **Back up first:** write the review fields (id, status, review_status, reviewed_by, reviewed_at) of **all 923** rows to a CSV on the host.
3. **Reject only the step-1 list.** Set review status to rejected. Nothing is deleted. A rejected row is hidden from the site until the run writes a new one over it.
4. **Then run the batch, as in `go-open390-nc-first-time-changelogs-20261117.md` (`78b3ca4`), unchanged:**
   * the ten-bill test first, **including 3 of the rejected bills**, all ten read against their comparisons;
   * then batches of at most 100 bills;
   * `bill_changelog` only, `include_org_research: false`, `include_concept_statements: false`, `retry_failed: false`, `background: true`, `dry_run: true` first;
   * the `bill_candidates`: every NC 2025 bill with a comparison that has no `bill_changelog` row, **or** only rejected ones. The pipeline regenerates rejected or missing rows only, and never touches a complete, approved one.
5. **Check after each batch:** each row `complete` and approved; no empty output or raw `{'…'}`. At the end:
   * every NC comparison has a non-rejected changelog;
   * the count of rejected rows is back to 0;
   * the totals.

## Timing (real reasons only)
* No other LegBot run in flight (the trigger lock; wait, don't force).
* No Mac ddp-sync restart or CAMS reload while a batch is in flight.
* If the logo catch-up is switched back on, pause between batches.

## Stop conditions
* Step 1 finding more than 633;
* a row whose bill or version doesn't match;
* failures above 5% in a batch;
* any of the ten test readings wrong in substance.

Stop and report. **The way back is the step 2 CSV:** a rejected row is set back to approved only on Ramon's say-so.

## Not authorized
Deleting any row; rejecting any row outside the step 1 list; any other state; any other artifact type; organization research.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
