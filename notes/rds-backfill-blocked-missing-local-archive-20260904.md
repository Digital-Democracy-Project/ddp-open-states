# RDS backfill: stopped before Step 2 -- refresh-extraction can't run from this host without a local archive sync first

*Replies to `notes/rds-backfill-execution-request-20260904.md`.*

## First, the revision check caught something real

Host's `openstates-core` checkout (`/opt/ddp-open-states/openstates-core`) was **18 commits
behind `origin/main`** -- `refresh-extraction` (OPEN-211) was present, but **OPEN-224 and
OPEN-246 were completely missing**, only OPEN-211/217/219 were reachable from the old HEAD.
Those two are exactly the fixes behind the VA (~1,827 nulled) and UT (~563 nulled) predictions in
your note. Pulled to latest `main` (`b84cb71e`, PR #39 tip); re-verified all five tickets
(`OPEN-211/217/219/224/246`) are now reachable from HEAD before running anything. Editable
install (`os-text-extract` resolves straight to this checkout's files), so no reinstall needed --
the pull was immediately live.

## Then the Step 1 dry-run surfaced a real blocker, not a numbers mismatch

Confirmed no in-flight Fargate tasks first, exported `DATABASE_URL` to RDS, ran
`refresh-extraction {ut,wa,us} --dry-run`. All three came back `stale_docs=0` -- but not because
there's nothing to fix. **Every single document was skipped**, not evaluated: UT 9,371/9,371,
WA 11,636/11,636, US 88,955/88,955 (US: 6 more "no archive_location on row" on top of that), all
tagged `local file missing: /opt/ddp-open-states/_archive/bills/raw/...`.

Traced the actual code (`openstates-core/openstates/cli/text_extract.py` around line 2310):
`refresh-extraction`'s read path only ever looks at local disk under `ARCHIVE_ROOT_DIR`,
reconstructing the relative path by stripping the S3 bucket prefix off each row's
`archive_location` (confirmed in RDS: real values look like
`s3://ddp-bill-archive/bills/raw/fl/2026D/lower/HJR23D--.../H_23D_Filed-....pdf`). There is no S3
read fallback anywhere in this path -- S3 only appears on the *archive/upload* side
(`_upload_and_verify`, a boto3 `PutObject`). This EC2 host has no local `_archive/` directory at
all (`ls` confirms it doesn't exist), so nothing was ever going to be found here.

This isn't the "VA/UT come back materially different" mismatch your note anticipated for
Step 2 -- it's Step 1 processing zero real documents in three-for-three jurisdictions, a
different failure mode entirely. Per your own "stop and flag rather than continue" instruction,
stopped here -- **did not run Step 2 (`recompute-diff-order`) at all**, since I wanted this
resolved first rather than assume Step 2 is unaffected.

## Scope, if syncing the archive locally is the fix

- Whole `s3://ddp-bill-archive/` bucket: 199,183 objects / 52.1 GB.
- Just the three jurisdictions Step 1 needs (`ut`+`wa`+`us`): **110,098 objects / 13.8 GB**.
- This host has 220 GB free (`/opt` on `/`, 296 GB total, 64 GB used) -- plenty of room.

## What I need from you

Two ways forward, your call:

1. **Sync `s3://ddp-bill-archive/bills/raw/{ut,wa,us}` down to this host's `ARCHIVE_ROOT_DIR`
   first**, then re-run the dry-run. Straightforward, just a real ~14 GB/110k-object transfer
   nobody had budgeted for before now.
2. **Run Step 1 from wherever the archive already exists locally** -- almost certainly Ramon's
   Mac, since `cloud_archiver.py`/`run-archive.sh` write local files first and only mirror them
   to S3 afterward, meaning a local copy likely already exists there and this EC2 host never had
   one.

Not proceeding to Step 2 or any `--commit` until this is resolved one way or the other.
