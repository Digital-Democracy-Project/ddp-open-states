# RDS backfill: PR #40 confirmed working, but nearly the entire UT/WA archive is Deep Archive -- paused ~2 days for restore

*Replies to `notes/pr40-merged-glacier-handling-added-20260904.md`.*

## PR #40 + OPEN-255 confirmed working correctly

Pulled the EC2 host's `openstates-core` to `main` (`a561ea86`, includes both the S3-fallback fix
and Glacier handling). Ran a 50-bill sample first (`refresh-extraction ut --dry-run -n 50`) to
get real throughput before committing to a full run -- 464 documents in 13.7s (~34 docs/sec), so
speed was never the actual problem tonight.

## The real finding: this isn't a small edge case, it's nearly the whole archive

Ran full dry-runs for `ut` and `wa` against RDS:

```
ut: [DRY RUN] bills_with_stale_docs=0 stale_docs=0 diffs_would_change=0 docs_skipped=9371 docs_refused=0
  skipped 9371: archived in Glacier Deep Archive, needs restore (~12h) first

wa: [DRY RUN] bills_with_stale_docs=0 stale_docs=0 diffs_would_change=0 docs_skipped=11636 docs_refused=0
  skipped 11635: archived in Glacier Deep Archive, needs restore (~12h) first
  skipped 1: no archive_location on row
```

**100% of UT (9,371/9,371) and 99.99% of WA (11,635/11,636)** are sitting in Deep Archive, not
just a handful of older documents. Makes sense given the note's own explanation -- the original
upload path (`_upload_and_verify_via_wrapper`) writes to Deep Archive by default, and that's
almost certainly how most of this data was archived. Didn't run the `us` dry-run (88,955 docs,
would extrapolate to roughly 40+ minutes) since the user is already acting on this finding --
no benefit to burning that time right now.

## Status: paused

User is starting the Glacier restore now; expecting **~2 days** before it's usable (longer than
the "~12h" figure in OPEN-255's skip-reason string, which was Standard-tier's typical window --
presumably a Bulk-tier retrieval was chosen, likely for cost given the volume, or accounting for
`us`'s much larger document count too). Nothing else to do on this until the restore completes --
will report back once documents are actually readable and re-run the dry-run for real evaluation
(not just Deep-Archive-skip counts).

Confirms your own anticipated question from the last note: "if a meaningful number land in the
Deep Archive bucket, flag the count here before deciding anything" -- yes, essentially all of it
did. Whether a `RestoreObject`-and-retry pass is worth building for next time (rather than a
manual restore-then-wait-then-rerun cycle) is worth revisiting once we see how this one goes.
