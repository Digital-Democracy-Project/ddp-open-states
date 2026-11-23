# REQUEST (not a GO): Arizona re-import of 57th-2nd-regular for OPEN-649 (Arizona's own links between bills), after the image that carries it. 2026-11-23 (Mac side, State Specific Handling)

**Not a GO.** Ramon's go comes in your session. This runs after the image in `request-next-scrapers-image-after-v79-az-companions-20261123.md`.

## Why
* **Scrapers #227 (OPEN-649, `f33da22f`)** makes Arizona store azleg's own links from the bill feed (`NowPartOf`):
  * "Identical to" is stored as `companion`, label "Identical to";
  * "See" is stored as `related`, label "See".
* **Links appear only on bills scraped after the change.** 57th-2nd-regular (2026) is the only Arizona session with a polled bill: 50 polled of 2,188 bills, on the dev broker copy.
* **The scorecard change is approved: Ramon, "Approve"** (OPEN-649). It was measured on a dev broker copy at broker main `36e0bb51`:
  * the broker makes **8 companion links**;
  * which roll calls count does not change (1,416 of 3,411);
  * 3 bill scorecards change:
    * **HB 2689**, which has no passage vote of its own, takes companion SB 1051's House and Senate votes. Score: none before, 83.33 after;
    * **HCR 2004** gains SCR 1004's Senate vote (44.44 → 42.86);
    * **SB 1200** gains HB 2094's House vote (75.0, unchanged);
  * 90 legislator scorecards gain those votes: +180 entries, 120 House and 60 Senate;
  * validators and reconcile are clean.

## Gates (stop and report if one fails)
1. **The live scrapers image contains `f33da22f`** (#227). Name the image tag and the task-definition revision.
2. **ddp-sync on EC2 is at the image's core:** `check-core-pin-drift.py --image-core <the image's core> --sync-container …` exits 0.
   * **Why:** the loader must be at core `7f531958` or later to keep the link labels. Every core since then does.
3. **The broker is at main `36e0bb51` or later (BROKER-540)** for the scorecard result above.
   * **Why:** the measured links come from BROKER-540's companion step. If the live broker is older, say which commit, and report what it links instead of reading this as a fail.
4. **Nothing Arizona is running:** no `az` collection, load, archive or text-extract task in ECS, and `GET ddp:pipeline_lock:az` is empty.

## The re-import (SYNC-181's trigger, as used for Florida and Washington)
```
POST /ddp-sync/v1/trigger/openstates-scrape/az?full=true&sessions=57th-2nd-regular
```
* **Answer:** `202`, with `"full": true` and the session echoed. A `409` means an Arizona run holds the lock: wait, do not force.
* **How long:** not measured, about 2,188 bills.
* **If it fails:** report the error and the minute; do not retry on your own.

## Report (read only)
* The run id, the image revision, the collection record with `"mode": "full"`, and the load's status with bill and vote counts.
* **Arizona related-bill links for 57th-2nd-regular,** by type and by label, on RDS and through EC2 api-v3. Before: **0**. On the 50 polled bills, the dev copy expects 148 links on 26 bills: companion "Identical to" 8, related "See" 140. Report the counts for every bill too; I have no whole-session number.
* **Spot check through EC2 api-v3:**
  * HB 2042 lists SB 1278 as `companion` "Identical to", plus HB 2125, HB 2141, SB 1098 and SB 1279 as `related` "See";
  * HB 2689 lists SB 1051 as a companion.
* **Broker, after its next Arizona sync:**
  * Arizona `BillRelation` rows (dev copy: 0 before, 8 after);
  * the scorecards of HB 2689, HCR 2004 and SB 1200 against the numbers above;
  * `validate_scorecards --jurisdiction AZ --all`, `validate_scorecards --bills --all` and `reconcile_scorecards --jurisdiction AZ`, all clean.

## Not authorized
Any other Arizona session or state, any recompute, any broker change.

Tickets: OPEN-649, OPEN-536. Plan: PLAN-companion-lineage §5.3, steps 4 and 5.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
