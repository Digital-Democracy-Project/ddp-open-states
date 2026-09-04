# Real fix for the archive-mirror gap -- no bulk sync needed, PR open

*Replies to `notes/rds-backfill-blocked-missing-local-archive-20260904.md`.* Ramon pushed back
on the "sync 14GB or switch hosts" framing -- right to: `refresh-extraction`'s local-disk-only
read was a design choice (its own docstring said "no re-fetching, no S3 involvement"), not a
hard limit, and the exact S3 client/bucket plumbing needed already existed on the archive's
upload side. Wrote a proper fix instead of working around it.

## What shipped

**`openstates-core` PR #40** (open, pm-reviewed, not yet merged):
https://github.com/Digital-Democracy-Project/openstates-core/pull/40

`_reextract_document()` (shared by `refresh-extraction` and `reextract`) now reads local disk
first, falls back to an S3 `GetObject` on a local miss -- reusing `_get_s3_client()`/
`S3_BILL_ARCHIVE_BUCKET`, already built for the archive's own upload side. Only genuinely-stale
documents get fetched, so this scales with what's actually broken, not with the archive's total
size (no 14GB sync, no host-switching, no new network path to verify).

pm-review caught two real things worth knowing about since they affect what you'll see in the
report: the fetch-failure reason string is now deliberately **poolable** (a genuine 404 groups
as `"not found locally or in S3"`; anything else -- bad credentials, network, throttling --
groups by its own error code instead) so a *systemic* problem would show up as one large count
in the existing top-10 report rather than hiding as dozens of one-count "different" reasons (the
original version would have had the same blind spot that hid tonight's actual bug in the first
place). Also cached the S3 client across a run instead of rebuilding it per document.

Filed as **OPEN-255**, In Review, linked to the PR.

## Before you re-run Step 1

1. **Get PR #40 merged** (not by me -- routing for independent review same as everything else
   tonight).
2. **Pull the EC2 host's `openstates-core` checkout to include it** -- same revision-confirmation
   step as last time, now needs both the OPEN-224/246 fixes AND this one present before
   `refresh-extraction ut/wa/us --dry-run` will genuinely evaluate anything.
3. Re-run exactly the sequence from `notes/rds-backfill-execution-request-20260904.md` --
   nothing about that sequence or the VA/UT predicted counts changes, this only fixes Step 1's
   read path.

Sorry for the churn -- the original request should have asked "why can't this just read from S3"
before proposing a workaround.
