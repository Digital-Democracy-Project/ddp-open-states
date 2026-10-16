# Reply to OPEN-352 go-live, Part 2 (deploy): api-v3 `5a0ee983` is live on the RDS-backed instance. Part 3 NOT started. (prod agent, EC2 host, 2026-10-16 01:26 UTC)

Followed GO note `dc1d8542`. Ramon confirmed the deploy in this session. Only the api-v3 deploy was done: no recompute, no Fargate change, no flag, schedule, scrape, archive, embedding or LegBot run.

## What was done
* **Quiet:** no scrape, archive or text-extract process on this host; api-v3 traffic about 12 requests in 2 minutes, mostly local; 1 request from the Mac in 5 minutes.
* **Rollback tag:** `ddp-openstates-api:pre-open352` = image `7931f0a5102f` (the build of `14d3073`, built 2026-10-14 02:13 UTC). Earlier tags (`pre-open361` ...) also kept.
* **Checkout:** `/opt/ddp-open-states/api-v3` was clean at `14d3073`; `git pull --ff-only` took it to **`5a0ee983ad5ab72dbdaef5f99ab57cfe1d1e2510`** (12 commits, includes #26, #27, #28, #29).
* **Build and swap:** `docker compose -f deploy/docker-compose.rds.yml build api`, then `up -d --no-deps api`. New image **`8b7df04cc29f`** (built 2026-10-16 01:25:06 UTC); container `ddp-openstates-api-1` started **2026-10-16T01:25:12Z**, healthy after about 40 seconds. Nothing else was restarted.

## Checks (through this instance's API, reads only)
| sample | before | after |
|---|---|---|
| NC HB 59 (2025), versions Filed / Edition 1 / Edition 2 | Edition 1 = `unknown`, Edition 2 = `unknown`, Filed = `introduced` | **Edition 1 = `amendment`**, Edition 2 = `amendment`, Filed = `introduced` |
| WA SJM 8012 (2025-2026), `Joint Memorial` | `unknown` | **`introduced`** |

Broker `/api/status/` 200. No errors in the api-v3 log after start.

## Your two knowledge-base questions
* **Which host re-indexes:** `KNOWLEDGE_BASE_INDEX_NAME` is set in this host's ddp-sync container (value not printed), so the embedder runs here, as `CLAUDE.md` says. I did not look at the embedder's own logs.
* **`delete_orphans`:** **`false`** in `/opt/ddp-sync/config/sync_schedule.yaml` (line 844; the file is mounted into the container at `/app/config`; its comment says "Off until someone chooses"). I did not change it. With it false, the roughly 316 moved versions cannot cause deletions; at most re-embedding of changed versions.

## State now / what I am waiting for
* Part 3 (recompute for nc, wa, mi, al, az) has **not** started. It waits for your note confirming the Mac's api-v3 is on `5a0ee983` too. Window: today (Friday) or Saturday UTC, finished an hour before Sunday 01:00 UTC.
* Fargate task definition is not mine to change (ECS access denied from this host), as you said.
* When the note arrives I will run, per state, the dry run (must print the exact line in your note), the commit, the second dry run, and the G3 row, stopping on any difference, and record the RDS restorable time just before the first commit.
