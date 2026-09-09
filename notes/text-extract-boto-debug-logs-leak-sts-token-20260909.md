# refresh-extraction's S3 fallback logs full boto3 requests at DEBUG -- including the live STS session token

*Found while running the RDS backfill's Step 3 (`refresh-extraction {ut,wa,us} --dry-run`) from
this EC2 host.* Not the deploy-token question from the other open note — a separate, real
finding.

## What happened

`os-text-extract refresh-extraction ut` (dry run) printed full `botocore` request-signing debug
output to stdout for every S3 `GetObject` call, including the complete
`X-Amz-Security-Token` header value — a live temporary AWS session token, in plaintext, in the
command's own output. I redacted it out of what I'm writing here, but it was genuinely on
screen/in a log file for this run.

## Root cause

`openstates/settings.py`'s Django `LOGGING` config sets the **root logger to `DEBUG` with
`propagate: True`**, with no override for the AWS SDK loggers. `openstates/cli/people.py`
already guards against exactly this — it explicitly does
`logging.getLogger("boto3"/"botocore"/"s3transfer"/"urllib3").setLevel(logging.WARNING)` before
touching S3. `text_extract.py` has no equivalent, so now that PR #40 gave `refresh-extraction`/
`reextract` a real S3 fallback path, every S3 call under `os-text-extract` inherits root's
`DEBUG` level and logs full signed requests, including credentials, to stdout/wherever that gets
captured (in my case, a background task's stdout file). WA/US will do the same when they run.

## Impact

The exposed token is EC2-instance-profile-issued (`ASIA...`, short-lived, auto-rotated) — not a
long-lived credential — so this isn't as bad as it could be, but it's still a real, reproducible
credential leak from a normal, expected invocation of a production data tool, and it'll happen
again on every future `refresh-extraction`/`reextract` run (dry or `--commit`) that touches S3,
by any agent or human running it, until fixed.

## Suggested fix

Add the same logger-silencing `people.py` already does to `text_extract.py` (or better: fix it
once in `openstates/settings.py`'s `LOGGING` config / `init_django()` so every CLI gets it, not
just the ones someone remembered to patch one at a time).

## Meanwhile: UT dry-run result (the actual task)

`ut: [DRY RUN] bills_with_stale_docs=1021 stale_docs=3100 diffs_would_change=2079
docs_skipped=0 docs_refused=6270` — the 6,270 refused docs (stored text fine, current extractor
returns empty/errored, not overwritten) are a separate thing worth someone looking at
eventually, not blocking this backfill. WA and US dry-runs are still running in the background
from this host; will report those numbers once they land, being careful this time to only pull
the summary line out of their output rather than the raw log.
