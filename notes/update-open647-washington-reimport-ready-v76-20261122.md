# UPDATE to `f179ccc` (Washington 2025-2026 full re-import, OPEN-647): gates 1 and 2 are now met on image v76. Ready for Ramon's go. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Ramon's go comes in your session. Everything else in `f179ccc` stands: the trigger, the report, the go/no-go and what is not authorized.

## Gates
1. **Met.** The running image contains #207's merge commit `8cf0b939`.
   * The image is v76 (task definitions `ddp-scrapers:78` / `ddp-scrapers-db:5`), built by Ramon at about 16:40 UTC 11-22.
   * The PM session checked inside it and found everything on the image note `550e2f2`, through #207.
   * Core is unchanged at `7f531958`.
   * **Confirm before triggering** that the Washington collection's task definition is revision 78 or later.
2. **Met.** Step 4 of `1f1e692` is done, per your checkpoint `7310af7` (11-21): ddp-sync at core `7f531958`, drift check exit 0.
3. **Still to check at the time:** nothing Washington is running (no `wa` task in ECS, `GET ddp:pipeline_lock:wa` empty).
   * The Florida re-import running now (`5a1ef5a`) holds Florida's lock, not Washington's. The two do not conflict.

## The re-import (unchanged from `f179ccc`)
```
POST /ddp-sync/v1/trigger/openstates-scrape/wa?full=true&sessions=2025-2026
```
* **Answer:** 202, with `"full": true` and the session echoed. A 409 means wait, do not force.
* **Expected after:** about 1,168 `companion` links labelled "Companion bill" in Washington 2025-2026, and none of any other type. Before the run: 0.
* **Spot check:** HB 1198 ↔ SB 5167, HB 1052 ↔ SB 5038.

Tickets: OPEN-647, OPEN-634. Plan: PLAN-companion-lineage §5.3.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
