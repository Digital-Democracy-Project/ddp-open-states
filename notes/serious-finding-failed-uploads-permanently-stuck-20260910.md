# Serious finding: yesterday's failed S3 uploads are permanently stuck, will never retry

*Replies to `notes/s3-putobject-iam-granted-please-rerun-20260909.md`.* Re-ran the full batch
against `ddp-scrapers:21` with the new IAM grant. All 9 exited 0 again -- but this run is NOT a
clean re-test of the fix, and the reason why is itself a real bug, worse than yesterday's two.

## What happened this run

`fetched=0` for every jurisdiction, including `az`/`ma`/`mi`/`us` -- the four that had real
pending documents (32/74/12/506) last run. `skipped` went up by exactly those same amounts.
The IAM fix never actually got exercised on new documents, because the system now believes
those specific documents are already handled.

## Root cause: the skip-check doesn't check for success

Traced `archive_bill_versions()` (`text_extract.py`) precisely:

- The skip-check (line ~1550): `BillVersionDocument.objects.filter(bill=..., version_note=...,
  version_date=..., source_url=link.url).first()` -- if **any row exists** for that natural key,
  `counters["skipped"] += 1` and the link is never touched again. **This filter never checks
  `archive_location`.**
- The insert (line ~1674): `BillVersionDocument.objects.create(..., archive_location=
  archive_location, archived_at=archived_at)` -- runs, and `counters["archived"] += 1`
  **unconditionally**, regardless of whether `archive_location` is `None` (i.e., regardless of
  whether the S3 upload actually succeeded). "archived" has never meant "verified in S3" -- it
  means "a document row now exists," full stop.

So: a row gets created the first time a link is processed, upload fails, `archive_location`
stays `None` -- and every future run's skip-check sees that row exists and never tries again.
**A failed upload is not a retry candidate. It's a permanent dead end**, silently, with nothing
in the summary line able to reveal it (that's `notes/batch-fetch-errors-full-detail-20260909.md`'s
OPEN-263 finding, but this is a step worse: it's not just invisible, it's unrecoverable without
manual intervention).

## Confirmed directly against RDS, not inferred

```python
BillVersionDocument.objects.filter(source_url__icontains='SCM1004')
```
Real row: `https://www.azleg.gov/legtext/57leg/2r/bills/scm1004s.pdf | archive_location: None |
archived_at: None` -- sitting right next to sibling rows for the same bill from
2026-07-28/08-11 (the old pre-migration pipeline) that succeeded normally. This exact row is
from yesterday's failed-IAM run and will never be retried by any future archive run as things
stand.

**`BillVersionDocument.objects.filter(archive_location__isnull=True).count()` = 747, all-time.**
I can't tell from here how many of those 747 are yesterday's incident specifically vs.
pre-existing nulls from unrelated causes (extraction failures, older issues, etc.) -- that split
needs someone who can correlate against `created_at`/timestamps properly. But at minimum, the
`az`/`ma`/`mi`/`us` documents from yesterday's two failed runs are confirmed among them.

## Next step

Two separate things: (1) a code fix so the skip-check (or a periodic sweep) treats
`archive_location IS NULL` as retryable, not as "done" -- probably belongs in the same ticket as
OPEN-263's counter-visibility fix, since they're the same underlying design gap (a failed
persist/upload attempt is currently indistinguishable from success at every layer above the raw
log line); (2) a one-time backfill to re-attempt every currently-stuck `archive_location IS
NULL` row now that the IAM grant is in place, since the normal archive run will never pick them
up on its own. Not doing either myself -- this needs someone who owns the actual data-recovery
call, not just the code fix.

Given this, I'd hold off calling Step 3 "closed" even once a future run does produce a real
`s3_verified > 0` -- that would prove the pipeline works for *new* documents going forward, not
that yesterday's already-stuck ones get recovered.
