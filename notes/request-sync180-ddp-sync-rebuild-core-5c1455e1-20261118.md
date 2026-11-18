# REQUEST (waits on Ramon's go and two merges): rebuild EC2's ddp-sync so cloud loads import with the scrapers image's core (SYNC-180), at core `5c1455e1` with image v68. 2026-11-18 (Mac side, State Specific Handling)

**Not a GO.** This answers your report on the Oregon run (`or-8290a384c248`) and question 3 in `f47111f`: **your cause is right.** `cloud_scrape_trigger.py` runs `cloud_loader.py` → `os-update` inside ddp-sync's container, on the core built into ddp-sync's image. That copy was cloned from core `main` at build time, so it stayed at `44c3b8dc`.

Ramon decided (SYNC-180, 11-18): "rebuild + drift check now"; "Rebuild with current core". Moving the load into Fargate is OPEN-633, later.

## What changes (not merged yet)
* **ddp-sync #298** (`fix/SYNC-180-core-at-image-commit`):
  * The image now fetches core at **`DDP_CORE_SHA`**, with no default: a build without a full 40-character commit stops.
  * It writes `/opt/openstates-core/DDP_CORE_COMMIT`, like the scrapers image.
  * `infrastructure/docker-compose.prod.yml` passes the variable.
  * **From then on, every ddp-sync build needs `DDP_CORE_SHA`.**
* **ddp-open-states #426** (`fix/SYNC-180-ddp-sync-core-drift`):
  * `check-core-pin-drift.py --sync-container <name>` compares that record with the image's core.
  * The RUNBOOK's image release now includes this rebuild.
* **Tested on the Mac:** a full ddp-sync image built at `5c1455e1`. The record matches, `os-update` runs, no `.git` is left, and the check reads it. A build with no commit stops.

## Which core, and why not earlier
* **The commit:** core **`5c1455e1679bbdac8f00fe050d57c0152e17c648`**, the core of image v68 (`05a7643` with addendum `abef131`). The loader and the image must run one commit.
* **Why not v67's `94082df4`:** do **not** rebuild at it. Its Utah rule takes `passage` off "<chamber> Conference Committee - Final Passage" lines. The next Utah import would then drop HB 136's final votes from the scorecard (its score falls from 50 to 0, OPEN-547's gate). `5c1455e1` carries the fix.
* **So this waits for v68 to be registered.** If v68 ends up recording a later core, use v68's and say so.
* **What the rebuild changes on load:** from the next import, re-imported bills get the action rules already approved and in the image since v65: Nebraska, Massachusetts, Utah, Michigan and Virginia (OPEN-547 to 551). It also brings the voter-id fix (OPEN-603) and Oregon's joint-committee lookup (OPEN-608). Stored history outside re-imported bills is untouched; the relabels are their own requests.

## Prod agent, after the GO (EC2)
**Gates:**
1. ddp-sync #298 is merged, and `/opt/ddp-sync` is at or after its merge commit.
2. ddp-open-states #426 is merged, and `/opt/ddp-open-states` is at or after its merge commit.
3. v68 is registered, and its `update-` note names its core (`5c1455e1` expected).
4. No cloud scrape or load is in flight: no running `ddp-scrapers` ECS task, and no `cloud_loader.py` / `os-update` process in `ddp-sync-ddp-sync-1`. A restart in the middle of a load would cut it off.

**Steps:**
1. **Record what runs now:**
   * `docker exec ddp-sync-ddp-sync-1 sh -c 'cat /opt/openstates-core/DDP_CORE_COMMIT 2>/dev/null || echo none'` (expect `none`);
   * then `docker tag ddp-sync:prod ddp-sync:pre-sync180` for rollback.
2. **Build:** `cd /opt/ddp-sync && DDP_CORE_SHA=5c1455e1679bbdac8f00fe050d57c0152e17c648 docker-compose -f infrastructure/docker-compose.prod.yml build ddp-sync`.
   * Supply the GitHub token secret the same way as your 11-17 build.
   * The build log shows `DDP openstates-core: 5c1455e1…`.
   * A stop at "DDP_CORE_SHA must be …" means the variable did not reach the build: fix it and do not work around the guard.
3. **Recreate:** `docker-compose -f infrastructure/docker-compose.prod.yml up -d --no-deps ddp-sync`. Confirm it is healthy and that the schedule is loaded, as after your last restart.
4. **Check:** `cd /opt/ddp-open-states && python3 check-core-pin-drift.py --image-core 5c1455e1679bbdac8f00fe050d57c0152e17c648 --container ddp-openstates-api-1 --sync-container ddp-sync-ddp-sync-1`. **Expect exit 0.**
   * If EC2's api-v3 is not yet rebuilt at `5c1455e1` (`05a7643` Part B1), it shows one DRIFT line for api-v3 only. Report it; that part is the other request's.
   * Any DRIFT or ERROR for ddp-sync: roll back and report.

**Proof on load (acceptance):** Oregon's next run on the rebuilt ddp-sync, either its scheduled run or an extra run if Ramon approves one. Report the same numbers as your Oregon report:
* the joint-committee ("legislature") member votes linked out of 931 (expect **931 of 931**);
* the overall unlinked share (expect it to fall from 4.75% to about 0).

## Rollback
1. `docker tag ddp-sync:pre-sync180 ddp-sync:prod`.
2. `docker-compose -f infrastructure/docker-compose.prod.yml up -d --no-deps ddp-sync`.
3. Report.

## Not authorized
* An extra scrape of any state without Ramon's say.
* Any relabel or stored-data run.
* Any `.env` or `sync_schedule.yaml` change.
* The api-v3 rebuild: that is `05a7643` Part B1, its own go.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
