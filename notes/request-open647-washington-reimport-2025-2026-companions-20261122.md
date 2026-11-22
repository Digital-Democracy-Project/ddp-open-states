# REQUEST (not a GO): Washington full re-import of 2025-2026, so every bill carries the companion the legislature lists (OPEN-647), once the image holds scrapers #207 and step 4 of `1f1e692` is done. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Ramon's go comes in your session. **#207 is not merged yet;** gate 1 below stays unmet until it is merged and built into an image.

## Why
* Scrapers #207 (OPEN-647) makes Washington store the companion bill the legislature lists.
  * The source is its web service field `wa:Companions`, shown on the bill page as "Companion bill: …".
  * Each is stored as `companion`, label "Companion bill".
* **In 2025-26:** 1,168 bills have one, exactly one each, and every pair lists the other back.
* Links appear only on bills scraped after the change. Washington's runs are incremental, so unchanged bills would never get them: hence a full run of the one session that holds polled bills (2025-2026, 21 polled bills).
* **The scorecard gate:** measured on a dev broker copy (broker main `7ce53986`), all 3,411 Washington bills imported with and without the links.
  * **0 broker links added and 0 of 2,335 scorecard files changed.** The broker links only companions it creates, and it already holds every Washington bill; that gap is BROKER-540 item 2.
  * So this re-import changes what api-v3 serves, not any scorecard.

## Gates (stop and report if one fails)
1. **The running scrapers image contains #207's merge commit** (the image after v75; the Mac side posts the commit when #207 merges). If it does not, this waits for that image.
2. **Step 4 of `1f1e692` is done:** ddp-sync on EC2 is at `DDP_CORE_SHA=7f5319583f9d30684ef3f042ea308554f1cc0676`, and the drift check exits 0. The old core drops the label on load.
3. **Nothing Washington is running:** no `wa` collection, load, archive or text-extract task in ECS, and `GET ddp:pipeline_lock:wa` is empty.

## The re-import (SYNC-181's trigger, as for the US on 11-20)
```
POST /ddp-sync/v1/trigger/openstates-scrape/wa?full=true&sessions=2025-2026
```
* **Answer:** must be **202**, with `"full": true` and the session echoed. A 409 means a Washington run holds the lock: wait, do not force.
* **Report:**
  * the run id and the image revision;
  * the collection's record, which must say `"mode": "full"`;
  * the load's final status, with bill and vote counts.

## Go/no-go after (read only, on RDS and through EC2 api-v3)
* **Washington 2025-2026 related-bill links by type and by label.**
  * Before: **0**.
  * After: about **1,168 `companion` links labelled "Companion bill"**, and no other type. The count can be a little different if bills were added or changed since 11-22.
  * Spot check: HB 1198 ↔ SB 5167, HB 1052 ↔ SB 5038.
* **Broker (no action asked):** Washington's `BillRelation` count stays as it is (0 on the dev copy). The scorecard checks after its next Washington sync stay clean (dev copy: 161 legislators, 0 discrepancies; reconcile 0 missing).

## Not authorized
Any other state or session; any recompute; any broker change, including the link reconcile (BROKER-548).

Tickets: OPEN-647, OPEN-634, BROKER-540. Plan: PLAN-companion-lineage §5.3 (ddp-infra #560 corrects §5.3.1 for Washington).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
