# REQUEST (not a GO): **the v92 release.** One image (v92) that carries the stored RDS login **and** the OPEN-879 fixes, ONE core rollout at core `a7035d68`, the Hawaii people load, a second Hawaii re-import, then the Arizona canary. Each step on Ramon's go. 2026-11-25 ~00:40 UTC (Mac side, Onboard New States)

**Not a GO.** It replaces the order in `update-v91-built-…` for the canary and adds OPEN-879. Please confirm each step with Ramon in your session. Everything below was checked on GitHub just now.

## What the code is (all merged)
| Repo | main now | What is new since v91 |
|---|---|---|
| openstates-core | **`a7035d68d1344f99783042e2492ba120d110e603`** | #174 (OPEN-879): a vote dated before its session began matches whoever held that seat on the vote's day, **only when the session window finds nobody** (no name that matches today can change) |
| openstates-scrapers | **`79c25838290d4bfe76880dd960884155e59bffe3`** | #290 (OPEN-879): Hawaii's ".." in a name list collapses to "." |
| people | **`c59386b98b2a00bb1b9aad3fca04a5f3d40d4dc9`** | #54 (OPEN-879): the alias "Lee, C" for Chris Lee |
| ddp-sync | `6d56c64146a055e288f519f4242326daed6dfde4` | unchanged (already on EC2; includes #311) |
| api-v3 | `254389aa8dbb754834b5600ad752b514284d7a9f` | unchanged (EC2 is on it); only its core changes |

## Step 1: image v92 (Ramon, Mac)
* `bash ~/Developer/repos/ddp-open-states/deploy-scrapers-image.sh` with **`TASK_RDS_SECRET_ARN`, `TASK_RDS_HOST`, `TASK_RDS_PORT=5432`, `TASK_RDS_DBNAME` set this time** (v91's run had none set). It builds at scrapers main `79c25838…` with core main `a7035d68…`.
* **I check on the Mac:** `DDP_CORE_COMMIT` = `a7035d68…`, the scrapers content, and post the revision numbers for you.
* **Read back, names only (yours or Ramon's):** the new `ddp-scrapers-db` revision lists `RDS_USERNAME`, `RDS_PASSWORD` under `secrets` and `RDS_HOST`, `RDS_PORT`, `RDS_DBNAME` under `environment`; the new `ddp-scrapers` revision lists none of the five. **Then watch the first task launched from the new `ddp-scrapers-db` revision (the next archive) reach RUNNING and exit 0** before anything else; if ECS cannot read the secret every launch from that revision fails to start: deregister that revision and the previous one is latest again (details in `9ad05ee`).

## Step 2: ONE core rollout at `a7035d68…` (the usual rules; after Step 1)
* **EC2 api-v3:** rollback tag; build from api-v3 main (`254389aa`) with `DDP_CORE_SHA=a7035d68…`; `up -d --no-deps api`; not 05:00–07:00 UTC.
* **EC2 ddp-sync:** `/opt/ddp-sync` is already at `6d56c64`. Build with `DDP_CORE_SHA=a7035d68…` and `DDP_SCRAPERS_SHA=79c25838…`; the import check must pass; tag a rollback; **wait until no run is in its load phase and no `ddp-scrapers-db` task is up**; never 02:15–04:45 UTC. **This rebuild restarts ddp-sync with the new config, so it replaces the staged `#311` restart (cancel that job if it is still pending, or let it fire first; either is fine).**
* **Mac api-v3:** `refresh-api-v3.sh` with `SCRAPERS_IMAGE_CORE=a7035d68…` is Ramon's (my earlier attempt was refused by the permission classifier; I do not retry).
* **Then:** `check-core-pin-drift.py --image-core a7035d68…` exits 0 everywhere; `DDP_SCRAPERS_COMMIT` in ddp-sync reads `79c25838…`.

## Step 3: Hawaii people load (after Step 2)
* Pull `/opt/ddp-open-states/people` to **`c59386b9…`**. The only data change is Chris Lee's file (alias "Lee, C").
* `os-people` `--safe` then real for **hi** only. **Expect: 0 created, 1 updated**, no "went missing" or retirement line. Anything else: stop and report.

## Step 4: Hawaii second re-import (Ramon approved ONE; this needs his new go)
* `POST /ddp-sync/v1/trigger/openstates-scrape/hi?full=true&sessions=2026` must answer 202 with `"full": true`; the task must run **v92's revision or later**, and the load must run on core `a7035d68` (Step 2 done).
* **Pass (I read it on the replica):** unmatched person votes for "Ward", "Gene Ward", "Aquino", "Henry Aquino", "Rachele Lamosao", "Lamosao", "Lee, C" and the stray "C." and "M." are **0** (measured offline: **178 remain** before the re-scrape, all "C." 147, "M." 30 and "Garcia; and" 1; after it only "Garcia; and" should remain); **no vote that matched before changes person**; 0 Senate passage roll calls without person votes still holds; bills 6,728 unchanged.
* Then the Hawaii archive (a resumed run does not start one by itself).

## Step 5: the Arizona canary (`d8df145`, after Step 1's read-back and Step 2)
* #311's setting is already pulled; the rebuild in Step 2 picks it up. Then #488 (the one-line manifest rollout), on Ramon's go and once #488 is merged, as in `d8df145`. The pass rules and the clean-week rule there stand.

## Also, any time (each on Ramon's go; no dependency on the above)
* **Rhode Island:** `ri?full=true&sessions=2026` on v91's revision or later (`update-v91-…`).
* **Oklahoma 2025+2026:** after its current archive, on the latest revision.

## Not authorized
Any step before its go; a third Hawaii run; any other state's re-import beyond those listed; the `#310` cleanup endpoint; `rds_from_task_secret: true` in the **archive** block; a core rollout at any sha other than `a7035d68…`; any certificate exception; deleting a lock, S3 object or Redis key.

Tickets: OPEN-879, OPEN-633, OPEN-639, OPEN-873, OPEN-146. Rollback: the api-v3 and ddp-sync rollback tags; for the image, deregister the new task definition revisions (the script prints the commands).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
