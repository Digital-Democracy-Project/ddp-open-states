# REQUEST (not a GO): Florida re-import of every session holding a polled bill (OPEN-642), on image v75, after step 4 of `1f1e692`. 2026-11-21 (Mac side, State Specific Handling)

**Not a GO.** Ramon's go comes in your session.

## Why
* Scrapers #187 (OPEN-642, in v75) makes Florida store its own related-bill links:
  * the Related Bills table: "Identical" is `companion`; Compare, Similar and Linked are `related`; the legislature's word is kept as the label;
  * the history line "companion bill(s) passed, see …", as a companion.
* New links appear only on bills scraped after the change. Florida's older sessions are no longer scraped, so they need a full re-import.
* **The scorecard gate is approved:** Ramon, "Approve now" (OPEN-642 comment 22288; final measurement 22318).
  * Measured on a dev copy (89 of the 90 polled 2026 bills): 203 links, 58 of them companions.
  * **0 scorecard files change and 0 counting votes move**, because the broker creates no new links from them yet (BROKER-540).

## Gates (stop and report if one fails)
1. **Step 4 of `1f1e692` is done:** ddp-sync on EC2 is rebuilt at `DDP_CORE_SHA=7f5319583f9d30684ef3f042ea308554f1cc0676`, and the drift check (`--image-core 7f531958… --sync-container …`) exits 0.
   * **Why:** cloud scrapes are loaded by ddp-sync with its own core. The old core `10f32ce0` has no `ddp_relation_label`, so the labels would be dropped on load.
2. **The image is v75** (task definitions `ddp-scrapers:77` / `ddp-scrapers-db:4`), and its scrapers commit contains `e71cb3a3` (#187, merged 16:52 UTC 11-21).
3. **Nothing Florida is running:** no `fl` collection, load, archive or text-extract task in ECS, and `GET ddp:pipeline_lock:fl` is empty.
   * Florida's weekly run starts Sunday 02:00 UTC; do not overlap it.

## The re-import (SYNC-181's trigger, as used for the US on 11-20)
```
POST /ddp-sync/v1/trigger/openstates-scrape/fl?full=true&sessions=2023,2023B,2023C,2024,2025,2026,2026D,2026E,2026F
```
* **Sessions:** every Florida session with a polled bill (the broker's polled bills: 2023 21, 2023B 13, 2023C 11, 2024 76, 2025 80, 2026 82, 2026D 2, 2026E 3, 2026F 3).
* **Answer:** must be **202**, with `"full": true` and the nine sessions echoed. A 409 means a Florida run holds the lock: wait, do not force.
* **What runs:** one Fargate collection per session, one after another, each followed by its load, then the usual archive and LegBot hand-off.
* **How long:** not measured. Florida goes through flhouse.gov's firewall, as every Florida run does; the regular sessions are the long ones.
* **Report:**
  * the run ids and the image revision;
  * each collection's record, which must say `"mode": "full"`;
  * each load's final status, with bill and vote counts.

## Go/no-go after (read only)
* **Florida related-bill links by session, by type and by label,** on RDS and through EC2 api-v3. Before the run: **0** in every session. After the run on 2026, about what the dev copy measured on the polled bills: 203 on 80 bills (companion "Identical" 28, companion "companion bill(s) passed" 30, related "Compare" 100, "Similar" 35, "Linked" 10). Report the same for every bill, not only polled ones.
* **Broker:** after its next Florida sync, the Florida scorecard checks (`validate_scorecards --jurisdiction FL --all`, `validate_scorecards --bills --all`, `reconcile_scorecards --jurisdiction FL`) are clean.
  * Before, on the dev copy: 229 legislators, 0 discrepancies; reconcile 0 missing, 2 later revotes set aside.
  * Count Florida's `BillRelation` rows before and after. The dev copy found the same single one, HB 1145 → HB 123.

## Not authorized
Any other state, any recompute, any broker change.

Tickets: OPEN-642, OPEN-634. Plan: PLAN-companion-lineage §5.2 and §5.3 step 4.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
