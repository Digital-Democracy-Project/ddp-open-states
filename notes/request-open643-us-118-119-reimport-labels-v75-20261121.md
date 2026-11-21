# REQUEST (not a GO): the US 118th/119th re-import again, so every federal link keeps congress.gov's own label (OPEN-643), after step 4 of `1f1e692`. 2026-11-21 (Mac side, State Specific Handling)

**Not a GO.** Ramon's go comes in your session. The route is the one you ran on 11-20 for phase 1 (`ddf23c9`, checkpoint `1e6cd8c`): SYNC-181's full re-import trigger.

## Why
* Scrapers #194 (OPEN-643, merged `b3d4c154` at 21:38 UTC 11-21) stores congress.gov's own relationship types as each federal link's label, for example "Identical bill" or "Related bill; Procedurally related".
* **Which links are companions does not change** (companion exactly when "Identical bill" is among the types, OPEN-638). So the scorecard list for this run is empty by construction, and the go/no-go below checks it.
* New labels appear only on bills scraped after the change.

## Gates (stop and report if one fails)
1. **The running image contains #194.** v75 (`ddp-scrapers:77`) was built at about the time #194 merged.
   * The Mac side confirms from v75's build log (Ramon's) that its scrapers commit contains `b3d4c154`.
   * **If it does not, this waits for the next image.** The re-import would otherwise store no labels.
2. **Step 4 of `1f1e692` is done:** ddp-sync at core `7f531958`, and the drift check exits 0. The old core drops the label on load.
3. **Nothing US is running:** no `us` task in ECS, and `GET ddp:pipeline_lock:us` is empty.

## The re-import (the same call as 11-20)
```
POST /ddp-sync/v1/trigger/openstates-scrape/usa?full=true&sessions=118%20chamber%3Dlower,118%20chamber%3Dupper,119%20chamber%3Dlower,119%20chamber%3Dupper
```
* **Answer:** must be **202**, with `"full": true` and the four sessions echoed. A 409 means wait, do not force.
* **Expected, as on 11-20:** hours of run time, the "still running" alert, and the 03:00 UTC nightly logging `PipelineBusy`.
* **Report:**
  * the run ids and the image revision (77 or later);
  * each collection's `"mode": "full"`;
  * each load's final status, with bill and vote counts.

## Go/no-go after (read only, on RDS and through EC2 api-v3)
* **Federal links by Congress, by type and by label.**
* **Companion counts must equal phase 1's** (after the 11-20 run). Any change between companion and related is a stop, and goes to Ramon as a scorecard list.
* **Labels:**
  * every link carries one (none empty unless congress.gov listed no type);
  * none is longer than 100 characters;
  * every companion's label starts with "Identical bill".

## Not authorized
Any other state; the broker's link reconcile (BROKER-548); any broker change.

Tickets: OPEN-643, OPEN-638, SYNC-181. Plan: PLAN-companion-lineage §5.3 (US Congress row).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
