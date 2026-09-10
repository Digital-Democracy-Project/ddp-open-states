# Backfill scope decided -- split into OPEN-263 (incident recovery) and OPEN-266 (older, separate)

*Replies to `notes/stuck-rows-correlation-breakdown-20260910.md`.* Ramon reviewed the breakdown
and decided scope. Recorded on both tickets, summarizing here for the thread:

## OPEN-263 (this incident) -- ~624 rows: `us`, `az`, and the matching `is_error=False` portion
## of `mi`/`ma`

**No separate backfill script needed.** Once OPEN-263's skip-check fix lands (treating
`archive_location IS NULL` as retryable, not "done" -- still needs to be written, not done yet),
a normal archive run against `us`/`az`/`mi`/`ma` will naturally pick these back up and retry them,
since the fix itself is what makes them retryable again. So the sequence is: fix merges → deploys
→ next real archive run (or a manually triggered one, your call) for those four jurisdictions
recovers this set as a side effect, not a dedicated one-off script.

## OPEN-266 (new, filed) -- ~123 rows: MA's extra `is_error=False` excess, all `is_error=True`
## rows (ma/mi/wa), VA's 4 rows

Explicitly **not** part of this incident's recovery. Separate, older, needs its own
investigation whenever picked up -- not blocking OPEN-263's close-out.

## Net effect on what to do right now

Nothing new to run immediately -- both tickets are filed with clear scope, and the actual code
fix for OPEN-263 (the skip-check + the counter-visibility fix from earlier) still needs to be
written. Once that PR is up, re-testing it should double as the recovery mechanism for the
~624-row set -- worth watching for that PR rather than a separate backfill request when it lands.
