# RDS data-quality backfill: Ramon approved the real `--commit` run -- one jurisdiction at a time, smallest first, Congress (`us`) last

*Replies to `notes/status-check-open266-rds-backfill-mi-cookie-20260910.md`.* Approved -- go ahead
per `PLAN-rds-data-quality-backfill.md` §4's Step 2, with one explicit condition: **one
jurisdiction at a time, stop and report back after each, confirm the verification in §5 looks
right before starting the next one.** Not a blast-through-all-six run.

## Order, smallest to largest, `us` strictly last

Built from the real numbers already in the plan (§3's per-ticket table, and the Step 1 dry-run
counts) as the best available size proxy per jurisdiction -- not exact total-archive sizes for
all six, but the closest thing on record, and good enough to satisfy the actual goal (build
confidence on small runs before trusting the biggest one):

1. **`mi`** -- recompute-diff-order only (not in Step 1's scope; OPEN-217 affected ~1,519 docs
   here, the smallest figure on record for any of the six).
2. **`ut`** -- refresh-extraction **then** recompute-diff-order, in that order specifically (§3's
   own sequencing rule: recomputing diffs before re-extraction would just recompute against the
   same stale single-line text). ~1,021 bills / 3,100 docs.
3. **`fl`** -- recompute-diff-order only. ~2,712 docs (OPEN-217).
4. **`wa`** -- refresh-extraction then recompute-diff-order, same ordering rule as `ut`.
   ~3,411 bills / 5,818 docs (docs count from the fresh Step 3 dry-run: `stale_docs=6230` now
   that `poppler-utils` is actually working).
5. **`va`** -- recompute-diff-order only. Largest of the non-`us` group: ~8,963 (OPEN-217) +
   380 (OPEN-224) + 1,447 (OPEN-246) touching the same underlying document set.
6. **`us`** -- refresh-extraction then recompute-diff-order, **last, deliberately**. By far the
   largest: 37,672 bills / 73,510 stale docs per the fresh Step 3 dry-run. Only start this one
   once all five above are done and confirmed clean.

## Before starting at all (§4's preflight, from the plan -- not new asks)

- Confirm the running `openstates-core` revision genuinely includes all five fixes
  (OPEN-211/217/219/224/246), not just the one already known to matter most.
- Check for a scheduled RDS load in flight for whichever jurisdiction is about to run (same
  standing discipline as checking before scraping) -- a concurrent load makes the before/after
  counts in §5 uninterpretable.
- Confirm a recent RDS automatic nightly backup exists (already running on its own, no setup
  needed) as the rollback point, per §4.

## For each jurisdiction, in order

1. `refresh-extraction <state> --commit` first, only for `ut`/`wa`/`us` (skip for `mi`/`fl`/`va`
   -- they were never in OPEN-211's scope).
2. Immediately before `recompute-diff-order <state> --commit`: run `recompute-diff-order <state>
   --dry-run` one more time right beforehand -- its counts are the real acceptance bar (§5.1),
   not the historical Mac-side numbers, since RDS's own document set can legitimately differ.
3. `recompute-diff-order <state> --commit`.
4. Spot-check at least one `nulled` and one `corrected` document from this run's own output
   against the same document on the Mac's local Postgres (§5.2) -- not an unrelated general
   query.
5. **Stop. Report the dry-run counts, commit counts, spot-check result, and confirmed code
   revision back on `notes/ops-handoff` before starting the next jurisdiction.** Abort and flag
   rather than continue if: the pre-commit dry-run doesn't match the commit's own counts, the
   command errors, the code revision is missing a fix, or a spot-check doesn't match the Mac.

Take as long as needed between jurisdictions -- no rush, the whole point of going one at a time is
to actually look at each result before trusting the next, biggest one.
