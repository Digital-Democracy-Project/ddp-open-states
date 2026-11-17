# Checkpoint: OPEN-544 last step done on EC2: manifest 487c06f and api-v3 7160cbcf live (reply to ef4087780)

Written 05:18 UTC (date -u at write time). From the production EC2 host. User's words in session: go "with --skip-ecs-check" (PA's run was in flight; the script's cloud-task gate would refuse; it never touches ddp-sync).

## Checks first (git ls-remote, 05:16 UTC)
api-v3 main 7160cbcf190415fa5253becdc5d535bde5f23cbd; ddp-open-states main 487c06f6d4432d05eb37ca8937eceb8ff7325a42 (checkout fast-forwarded from 8afea0a1d, no later docs-only commit); openstates-core main b5728c4326fea4bdc33b721738ecdbe5ac4d8b02. All exactly as the GO says.

## Manifest rollout (05:17:08-05:17:09, exit 0, --skip-ecs-check)
- 8afea0a1d -> 487c06f6d. 16 jurisdictions valid; combined drift check: every list agrees (16). openstates-core not compared against the code by this script (no root given).
- md5 6301f403f729b940d1e62533fe8d94f8 equal in the checkout, api-v3's copy and the api container. api container healthy, directory mount, no recreate.
- grep -c newest_first jurisdictions.yaml gives 1, and no line is a `newest_first:` key (comment only). Live: az fl ma mi nc us ut va wa. Scraping: al ga la ne nv or pa.

## api-v3 (05:17:22-05:17:42)
- Running image tagged `ddp-openstates-api:pre-7160cbc` (image d90b042c2903, = d552fabd on core 44c3b8dc) for rollback. api-v3 checkout d552fabd -> 7160cbcf. Build and `up -d --no-deps api` only: compose exit 0, 12 s, down about 5 s, healthz 200 before and after. Postgres: none on this host (RDS).

## Gates
- Healthy; the container imports openstates.utils.version_ordering: ok.
- `check-core-pin-drift.py --image-core 44c3b8dc82a0f296b68c3bf2a2e6e2454e5b29b9 --container ddp-openstates-api-1`: **exit 1, exactly one disagreement, as expected**: "installed in ddp-openstates-api-1 is b5728c4326fea4bdc33b721738ecdbe5ac4d8b02, but image (--image-core) is 44c3b8dc82a0f296b68c3bf2a2e6e2454e5b29b9". This is the gap Ramon accepted (core #116). No other disagreement; exit was 1, not 2. The tool's output ends with its usual advice to bring both to one commit.
- /ddp/enrollment read from the broker's web container (direct to api-v3): 200, 16 jurisdictions (same as before), **0 entries with an `actions` key**; each entry's keys are now archive, enrollment, name, status.
- Virginia HB 1432 (2026) versions in order: Introduced, Criminal Subcommittee Substitute, Courts of Justice Substitute, Delegate Mehta Substitute (latest = Mehta).
- Broker logs 05:14-05:18 UTC (web and celery, read at 05:18): no Traceback or ERROR, and no line about enrollment or newest_first. (The only "actions" lines are the broker's own bill fetches with include=actions, not the enrollment field.)

## Not done / owed
- The broker's own enrollment cache re-read (about 1 hour): I will read web and celery for enrollment or actions errors after about 06:20 UTC and report the time.
- Rollback if needed: retag pre-7160cbc as :local and recreate api only (the manifest stays; the broker treats a missing field as oldest first, now true everywhere).
- The 05:00 scorecard chain was still running at 05:18.
- No scrapers image, task definition, broker, ddp-sync or data change was made.
