# OPEN-293: exact invocation for the 29-bill backfill (please run this, not me -- real production write)

Answering the ask in `open293-backfill-needs-explicit-bill-no-not-a-routine-run-20260916.md`.
Your `bill_no=` diagnosis is exactly right. One addition you wouldn't have had: **USA is
cloud-owned** (`cloud_path.jurisdictions` in `sync_schedule.yaml`), so this doesn't go through
`run-scrape.sh` or a plain `os-update` call at all -- it needs the same Fargate-launch-then-RDS-load
path `_run_scrape()`/`run_cloud_scrape()` already use for the routine schedule, just with a
custom `session_arg` carrying `bill_no=` instead of the routine `chamber=lower`/`chamber=upper`
split. `run_single_scrape_job()` (the existing manual-trigger job) won't work as-is -- it hardcodes
`session_arg=None`.

## The 29 identifiers

```
HJRES1,HJRES104,HJRES105,HJRES106,HJRES117,HJRES130,HJRES131,HJRES139,HJRES140,HJRES142,HJRES20,HJRES24,HJRES25,HJRES35,HJRES42,HJRES60,HJRES61,HJRES72,HJRES75,HJRES78,HJRES87,HJRES88,HJRES89,SJRES11,SJRES13,SJRES18,SJRES28,SJRES31,SJRES80
```

## Preferred way to run it: call the existing tested function directly

From wherever `ddp-sync`'s own code already runs (so config loading, RDS secret resolution, and
`boto3` credentials are all already set up the same way the real scheduler gets them) -- no new
mechanism, just a one-off call to the function the schedule already uses:

```python
import asyncio
from ddp_sync.pipelines.openstates_scrape import _run_scrape

session_arg = ("session=119 bill_no=HJRES1,HJRES104,HJRES105,HJRES106,HJRES117,HJRES130,"
               "HJRES131,HJRES139,HJRES140,HJRES142,HJRES20,HJRES24,HJRES25,HJRES35,HJRES42,"
               "HJRES60,HJRES61,HJRES72,HJRES75,HJRES78,HJRES87,HJRES88,HJRES89,SJRES11,"
               "SJRES13,SJRES18,SJRES28,SJRES31,SJRES80")

result = asyncio.run(_run_scrape("usa", session_arg, openstates_root, config=config))
print(result)
```

(`openstates_root`/`config` however your own environment already resolves them for a normal
run -- same values the scheduled `run_usa_scrapes_job()` uses.) This goes through
`_cloud_path_owns("usa", config)` -> `run_cloud_scrape()` exactly like a scheduled run: launches
one Fargate task (command override `["usa", "session=119", "bill_no=<the list>"]`, a fresh
`RUN_ID`), waits for it to stop, then runs `cloud_loader.py` against RDS automatically. No chamber
split needed -- with no `chamber=` param, `USBillScraper.scrape()` walks every session-119 sitemap
(hr/s/hjres/sjres/hres/sres/hconres/sconres) and `bill_no=` filters down to just these 29 across
all of them in one pass.

You confirmed Fargate tasks can run in parallel with the routine schedule, so no need to wait for
a quiet window -- go ahead whenever.

## Fallback: raw AWS calls, if calling `_run_scrape` directly isn't convenient

Same two steps `run_cloud_scrape()` does internally, by hand:

1. **Launch**: `aws ecs run-task` against `cluster=ddp-scrapers`, `taskDefinition=ddp-scrapers`
   (bare family name -- picks up the latest revision, 27/v23, automatically), the same
   subnets/security-groups `cloud_path.fargate` already lists in `sync_schedule.yaml`,
   `containerOverrides` on the `scraper` container: `command=["usa", "session=119",
   "bill_no=<the list above>"]`, `environment=[{"name": "RUN_ID", "value": "<generate:
   usa-<12 hex chars>>"}]`.
2. **Load**: once that task stops (poll `describe-tasks`), run `python3 cloud_loader.py usa
   <same RUN_ID> session=119 bill_no=<the list above>` with `DATABASE_URL` resolved live from
   Secrets Manager (same as every other load), `MEMORY_BUCKET=ddp-openstates-scraper-memory`,
   `MEMORY_PREFIX=prod`.

## Verifying it worked

`HJRES 1`'s roll-293 vote is the cleanest single check -- it should go from zero votes to one
after this runs. Real per-bill roll numbers for all 29 (for a fuller check) are in
`open293-corrected-backfill-scope-29-votes-house-only-20260915.md` above.

Not running this myself -- confirmed I can't from the Mac side: `aws ecs run-task` is blocked by
Claude Code's own auto-mode classifier (same category as the `docker push` you ran by hand
earlier), and this dev checkout has no RDS connectivity or IAM permissions at all (checked
directly -- `rds:DescribeDBInstances` denied outright, no `RDS_HOST` configured anywhere here).
This one's yours to run.