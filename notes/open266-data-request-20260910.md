# OPEN-266 investigation -- requesting production DB data I can't pull from the dev checkout

Picking up the ~123-row remainder from `notes/stuck-rows-correlation-breakdown-20260910.md`
now that OPEN-263 itself is fixed and in review. One finding closed out already without needing
DB access; two still need real row-level data only the prod side can pull.

## Closed already: the is_error=True rows (ma: 30, mi: 4, wa: 1) have no existing retry mechanism

Checked OPEN-229 directly (Jira): status is still "To Do", not started. Its own description
confirms "no `reextract` command exists; OPEN-33's own backfill was a one-off VA-specific
mechanism, never generalized into a reusable per-state command." So these 35 rows are not
silently covered by anything -- they're genuinely stuck the same way the OPEN-263 rows were,
just for a different reason (a real extraction failure, not a blocked upload). Nothing to fix in
code for this ticket's purposes; the actual acceptance criterion here is answered: no, not
covered, and fixing it for real means either a bespoke one-off script (OPEN-33's style, 35 rows is
small enough) or building OPEN-229 first. Recording this as a decision point for whoever picks up
OPEN-266's disposition, not deciding it myself.

## Still needed: MA's ~75 excess `is_error=False`/null-`archive_location` rows

Can't tell from ticket/git history alone whether these came from several small S3-upload
failures across MA's weekly archiver runs since it went live 2026-08-10 (each run's own smaller
version of what OPEN-263 just fixed at 100%-failure scale), or from something else entirely. If
you can pull it: for MA's rows matching `is_error=False AND archive_location IS NULL AND raw_text
!= ''`, beyond the ~74 that already match yesterday's `rev21` batch -- a sample of the REMAINING
ones' `version_note`/`version_date`/`source_url`/`bill_id` (or just their `bill.legislative_
session_id` distribution) would tell us whether they cluster into distinct historical batches
(several previous weekly runs, each contributing a handful) or one single earlier event.

## Still needed: VA's 4 rows

Working hypothesis, not confirmed: OPEN-33's backfill (2026-08-06) fixed `is_error`/`raw_text`
for 23,516 VA rows via a direct in-place DB update -- **no S3 involved at all** per that
investigation's own write-up. If those rows already had a real `archive_location` from their
*original* scrape-time upload (independent of the later-discovered extraction bug OPEN-15 fixed),
then only documents whose *original* S3 upload ALSO failed, on top of the extraction bug, would
still be null today -- a small, unrelated straggler, not a new bug. If you can pull VA's specific
4 rows (`version_note`, `version_date`, `source_url`), that would confirm or kill this directly.

## What this doesn't need

Not asking for a backfill decision or any write -- OPEN-263's own fix already makes all of these
retryable on the next real archive run for their jurisdiction (ma/mi/wa/va), same as the ~624-row
incident set. This is purely about writing down the actual cause on OPEN-266 before deciding
whether any of it is worth a deliberate one-off action versus just letting the next scheduled run
pick it up naturally.
