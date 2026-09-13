# OPEN-180 epic: real recheck on the 4 flagged items

## OPEN-191 addendum first: item 2 (freshness), fully resolved now that item 3 is confirmed

Ramon confirmed the broker cutover directly, and I confirmed the underlying data question:
`ddp-openstates-api-1` (the api-v3 instance the broker now reads from) and `cloud_path` (the
feed OPEN-193/AC6's freshness measurement checked) both point at the **exact same RDS
instance and database** (`ddp-openstates.cvxdhm1ogxug.../openstates` -- confirmed directly via
each service's own `RDS_HOST`/`RDS_DBNAME` env vars). Same underlying rows, no separate copy
in between. **Today's freshness measurement is checking the freshness of the exact data the
broker's real cutover traffic reads from right now** -- no separate check needed.

## OPEN-253 -- still true right now, confirmed live

`OPENSTATES_SCRAPE_ENABLED=true` confirmed directly in the running `ddp-sync` container's env
on this EC2 host, right now -- survived today's several restarts/redeploys with no
regression. I have zero visibility into the Mac side's own `.env`/running state from here --
that half needs your own check if you want it confirmed too.

## OPEN-257 -- backlog re-tier looks genuinely complete

Sampled 5000 objects across `ddp-bill-archive`'s `bills/raw/` prefix (alphabetical listing, so
spread across many jurisdictions/bills, not just recent uploads): 4999 `GLACIER_IR`, 1
`STANDARD_IA` (a known `_open192_sync_validation_test` marker file, not a real archived
document), zero `DEEP_ARCHIVE` found anywhere in the sample. No bucket-level lifecycle
configuration exists at all (`NoSuchLifecycleConfiguration`) -- consistent with
`cloud_archiver.py`'s own comment that storage class is set explicitly at upload time, not via
an S3 lifecycle rule. Real, reasonably broad evidence this is done; not an exhaustive
full-bucket scan, but a 5000-object alphabetical sample finding zero exceptions is a strong
signal.

## OPEN-215 -- can't verify, wrong identity

Checked precisely: `ddp-scraper` is a separate, standalone IAM **user** (long-lived
credentials), not the same identity as this EC2 host's own assumed role
(`EC2ServiceAccessReadOnlyRole`) that I've been using all day for CloudWatch reads. My
successful log reads today prove nothing about whether `ddp-scraper`'s own CloudWatch Logs
access was ever restored -- that's a different principal entirely. Can't check its permissions
from here; someone with access to that IAM user (or admin IAM read access) needs to check it
directly.

## OPEN-258 -- real finding: this is NOT still open, already fixed

Contradicts the note's premise. This was fixed 2026-09-09: `openstates-core` PR #42 added
`logging.getLogger("boto3"/"botocore"/"s3transfer"/"urllib3").setLevel(logging.WARNING)` to
`text_extract.py` (same pattern `people.py` already had), merged to `main` (`5c79b47d`).
**Verified directly, right now, in this host's current checkout** -- confirmed those exact
four lines are present and live in `openstates-core/openstates/cli/text_extract.py` (lines
55-58). If Jira still shows this as open, that's the stale one, not the code -- exactly the
kind of gap this epic review is for.
