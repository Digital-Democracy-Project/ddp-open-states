# REQUEST (not a GO): Utah re-import of 2026 for OPEN-775 (coordination-clause links), after the image that carries it. 2026-11-23 (Mac side, State Specific Handling)

**Not a GO.** Ramon's go comes in your session. This runs after the image in `request-next-scrapers-image-after-v80-ut-coordination-20261123.md`.

## Why
* **Scrapers #229 (OPEN-775, `414311c6`)** makes Utah store each bill a summary's "coordination clause" names as `related`, labelled "coordination clause". It never stores one as `companion`. Ramon decided this ("Store as related", OPEN-650).
* **The links appear only on bills scraped after the change.** 2026 is the only Utah session with a polled bill: 20 polled of 1,016 bills, on the dev broker copy.
* **No scorecard change:** the broker follows and creates only `companion` links (`openstates_service.py`, `allowed_related_bill_relation_types = ["companion"]`). This is checked in the code, not by a dev-copy run.

## Gates (stop and report if one fails)
1. **The live scrapers image contains `414311c6`** (#229). Name the image tag and the task-definition revision.
2. **ddp-sync on EC2 is at the image's core:** the drift check exits 0.
   * **Why:** the loader must be at core `7f531958` or later to keep the link label. Every core since then does.
3. **Nothing Utah is running:** no `ut` collection, load, archive or text-extract task in ECS, and `GET ddp:pipeline_lock:ut` is empty.

## The re-import (SYNC-181's trigger, as for Arizona and Washington)
```
POST /ddp-sync/v1/trigger/openstates-scrape/ut?full=true&sessions=2026
```
* **Answer:** `202`, with `"full": true` and the session echoed. A `409` means a Utah run holds the lock: wait, do not force.
* **How long:** not measured, about 1,016 bills.
* **If it fails:** report the error and the minute; do not retry on your own.

## Report (read only)
* The run id, the image revision, the collection record with `"mode": "full"`, and the load's status with bill and vote counts.
* **Utah 2026 related-bill links, by type and label,** on RDS and through EC2 api-v3:
  * **Before:** 0 links of any type (Mac replica, 2026-11-23).
  * **After:** every link is `related` "coordination clause", and **0 `companion`**.
  * **On the 20 polled bills, the dev copy expects 3 links on 2 bills:** HB 223 → HB 32; SB 153 → HB 209 and HB 361.
  * Report the whole-session count too; I have no number for it.
* **Spot check through EC2 api-v3:** HB 223 lists HB 32, and SB 153 lists HB 209 and HB 361, each `related`, "coordination clause".
* **Broker, after its next Utah sync:** Utah `BillRelation` rows unchanged, and the Utah scorecard checks clean:
  * `validate_scorecards --jurisdiction UT --all`;
  * `validate_scorecards --bills --all`;
  * `reconcile_scorecards --jurisdiction UT`.

## Not authorized
Any other Utah session or state, any recompute, any broker change.

Tickets: OPEN-775, OPEN-650. Plan: PLAN-companion-lineage §5.3.1.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
