# RDS backfill Step 3 -- UT and WA dry-run results (US still running)

*Follows up on `notes/glacier-restore-completed-but-retier-and-backfill-stalled-20260908.md`, now
that the re-tier is confirmed done.* Ran `refresh-extraction {ut,wa,us} --dry-run` against RDS
from this EC2 host, in parallel as background tasks.

## Results so far

- `ut: [DRY RUN] bills_with_stale_docs=1021 stale_docs=3100 diffs_would_change=2079
  docs_skipped=0 docs_refused=6270`
- `wa: [DRY RUN] bills_with_stale_docs=3411 stale_docs=5818 diffs_would_change=2270
  docs_skipped=1 docs_refused=5817`

`us` (~89k docs) is still running — will post its number separately once it lands, this note
isn't waiting on it.

## Two things worth a second look before `--commit`, neither one blocking

1. **The `docs_refused` counts are large relative to `stale_docs`** — 6,270/3,100+6,270 for UT,
   5,817/5,818+5,817 for WA. Per the tool's own message, these are cases where the stored text is
   fine but the *current* extractor now returns empty/errored output on the same document, so
   they're deliberately left alone rather than overwritten with worse text. That's the right
   default behavior, but a refused-rate this high (roughly double the stale-and-fixable count, in
   both states) seems worth understanding before assuming it's just noise — might point at an
   extractor regression, not just expected edge cases.
2. Found running this, reported separately on its own thread
   (`notes/text-extract-boto-debug-logs-leak-sts-token-20260909.md`): `os-text-extract` leaks the
   live STS session token via DEBUG-level boto3 logging whenever it touches S3. Not blocking this
   backfill, but flagging again here since it'll recur on the `--commit` runs too if run before
   it's fixed.

Also saw the deploy-secret reply (`notes/open257-deploy-secret-flag-confirmed-20260909.md`) —
understood, waiting on Ramon to provision `GITHUB_PERSONAL_ACCESS_TOKEN` on this host before the
OPEN-257 deploy can proceed. Not chasing that further from here.
