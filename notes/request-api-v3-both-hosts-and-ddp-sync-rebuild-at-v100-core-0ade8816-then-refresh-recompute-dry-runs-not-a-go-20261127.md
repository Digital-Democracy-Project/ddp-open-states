# REQUEST (not a GO): **rebuild api-v3 on both hosts and ddp-sync on EC2 at the v100 image's core `0ade8816`, then the refresh and recompute dry runs, in the order below.** 2026-11-27 (Mac side, Onboard New States)

Ramon gives each go in the prod agent's session. Nothing here runs without it.

## What I need from you
1. **Read first (no write):** the core recorded in the scrapers image the pipeline launches (tag v100; task definitions `ddp-scrapers:102` and `ddp-scrapers-db:29` per Ramon's build output, relayed by the PM; I cannot read task definitions or the image digest). It should be exactly `0ade881650ca921b0d7f3d5e4a64dc25239ac5ce`. Report the digest and the sha. If they differ, stop and tell me.
2. **api-v3 on EC2** rebuilt at that core (RUNBOOK "api-v3 release", EC2 form), `api` only recreated.
3. **ddp-sync on EC2** rebuilt with `DDP_CORE_SHA=0ade881650ca921b0d7f3d5e4a64dc25239ac5ce` and `DDP_SCRAPERS_SHA` (see Part 3), recreated under the narrow rule.
4. **The pin check** with all three named; paste the output. The Mac's api-v3 copy is Ramon's step (RUNBOOK: `refresh-api-v3.sh` with the v100 image named, or `SCRAPERS_IMAGE_CORE`); the check on the Mac side is mine.
5. **Then the dry runs of Part 6, in that order**, each on its own go; the commits hold for go notes.

## Why, and what the core holds
The script says the core pin check fails until both api-v3 copies run the image's core, and SYNC-180/188 say ddp-sync's own core copy must match too (cloud loads import with ddp-sync's copy). Core `0ade8816` is the openstates-core #190 merge, current `main` of the fork (I checked: it is `origin/main`, and it contains `3ebaf5e0`, the #189 merge). It therefore carries #183, #185, #186, #187, #188, #189 and the #190 comment fix (OPEN-914, OPEN-909, OPEN-917 and the earlier text fixes; #190 changes a comment only).

## Part 1. Gates before any write
* Core in the launched image = `0ade8816...` (ask 1). The core fork's `main` is that commit.
* **No cloud load or pipeline lock** (the Virginia 2026 and 2026S1 re-imports and their archive finish first; you told me the rebuild needs every lock clear), no ddp-sync job in the last 10 to 12 minutes, none near a trigger. Avoid Sunday from 02:00 UTC, each nightly state's start, and the broker windows you already keep.
* Record "now" as the restore point (you cannot read RDS's latest restorable time).

## Part 2. api-v3 on EC2 (nothing is committed to data)
* Tag the running image for rollback: `docker tag <api-v3 image>:local ddp-openstates-api:pre-v100`.
* `DDP_CORE_SHA=0ade881650ca921b0d7f3d5e4a64dc25239ac5ce docker-compose -f /opt/ddp-open-states/deploy/docker-compose.rds.yml build api` (the build imports the app before it finishes, OPEN-616; a failure there leaves the running container untouched; do not remove the step), then recreate `api` only.
* The manifest copy: the build and refresh scripts run `deploy/sync-manifest.sh`; the checkout is already at `4c78d958` or newer from the Alabama rollout, so nothing should change; if the validator stops it, paste the reason.

## Part 3. ddp-sync on EC2 (SYNC-180/188)
* Tag the running image: `docker tag ddp-sync:prod ddp-sync:pre-<its sha>`. Then in `/opt/ddp-sync`: `DDP_CORE_SHA=0ade881650ca921b0d7f3d5e4a64dc25239ac5ce DDP_SCRAPERS_SHA=<sha> docker-compose -f infrastructure/docker-compose.prod.yml build ddp-sync`, recreate `ddp-sync` only, with the log saved first as last time.
* **`DDP_SCRAPERS_SHA`: my best reading is scrapers `main` `744f02125ff272080f98271d34f0104a436da72f`** (the #310 merge, 11-26 23:07 UTC; no newer merge on the fork when I fetched). The image prints no scrapers commit and I could not read it (the Mac's Docker is paused for me). **Please confirm it from the launched image:** compare the md5 of `scrapers/or/bills.py` and `scrapers/nc/bills.py` in the image with those files at that commit. If Ramon's build output names a scrapers commit, use that one. If the md5s differ, stop and tell me the commit you find.

## Part 4. The pin check (paste every line)
`python3 check-core-pin-drift.py --image-core 0ade881650ca921b0d7f3d5e4a64dc25239ac5ce --container <api-v3 container> --sync-container ddp-sync-ddp-sync-1` from the checkout (confirm the container name with `docker ps`). Expect exit 0 and ddp-sync's scrapers commit printed. Also report: both containers healthy, `/schedule` still 35 jobs, 0 errors in the first minutes of ddp-sync's log.

## Part 5. Rollback
* api-v3: retag `ddp-openstates-api:pre-v100` as `ddp-openstates-api:local` and `docker-compose -f <compose file> up -d --force-recreate --no-deps api`.
* ddp-sync: retag `ddp-sync:pre-<sha>` as `ddp-sync:prod` and recreate `ddp-sync` only.
* Rolling back the rebuild does not undo a stored recompute; none is part of this note.
* Scrapers image: deregister revisions 102 and 29 (Ramon's step, per the build output).

## Part 6. The order after the rebuild (this replaces the order in my earlier notes)
Every dry run needs the rebuild first, because the refresh and recompute read the core they run on, and the earlier notes assumed an image that carries `3ebaf5e0` or newer. That is now this image. **All dry runs are dry runs; nothing is saved; each commit holds for its own go note.** In order:
1. **Nevada** `recompute-diff-order nv --dry-run` again on the new core. Your dry run at core `1e138376` (`177570b`) gave `217 bills checked | unchanged=230 corrected=32 nulled=26`; expect the same lines. If anything differs, stop and report. The commit (request `0d84735`) is still held for Ramon's go.
2. **The v99 steps still open** (request `231f011`, steps 3 to 10): Kentucky, Maryland, Missouri, Georgia and Maine dry runs. Georgia and Maine now run on the new core too; Maine's commit still waits on openstates-core OPEN-907.
3. **From `f5df751` and its companions**, unchanged except for their order: `refresh-extraction` dry runs for Iowa (about 395 changed), Wyoming (230), Oklahoma (about 12,863 of 17,574, 0 shorter, 0 errors) and the US (about 3,687 resolutions plus some bills; resolution text grows about 2.6 times, Ramon approves by size); then `recompute-diff-order` dry runs for ia, wy, ok, nd (about 648 Enrollment changelogs) and us. Their exact commands, baselines and expected lines are in those notes (`336247b`, `167545b`, `f5df751`); read them as written, but run them after Parts 2 to 4 here.

## Not authorized
Any commit; any `--commit` recompute; a refresh that saves; a scrape or re-import other than the ones Ramon already approved in your session; a manifest change; a ddp-sync restart beyond the rebuild; the Alabama people load and re-import (request `2bc1578`, its own go); `legbot_replica`; VoteBot's state list; any state or `all` beyond those named.

## What I check on the Mac side afterwards
The Mac's pin check and api-v3 copy (Ramon's step), then the replica reads of each dry run's lines you paste, and a `reply-verified` note after any commit.

Tickets: OPEN-914, OPEN-909, OPEN-917, OPEN-849, OPEN-588; SYNC-180, SYNC-188; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
