# REQUEST (not a GO): step 4 of `1f1e692`: api-v3 (main `7a2e5e0d`, with OPEN-641) and ddp-sync rebuilt at the new image's core `130c40bd`. 2026-11-21 17:10 UTC (Mac side, State Specific Handling)

**Runs only after** step 3's image is registered and its tag and core are posted (request `request-1f1e692-step3-scrapers-image-core-130c40bd-scrapers-e71cb3a3-20261121.md`). Use the core the build log actually shows: `130c40bdf313f68f13bb65703879249be1a8b31c` if main has not moved. **There is no release skill for api-v3 or ddp-sync**, so this is written by hand, in the shape of `bc30545` and `125fc5e`.

## 1. EC2 api-v3
* **To:** api-v3 main **`7a2e5e0d9e3097980d13b34ea5c982a4add61bfd`** (#76, OPEN-641), built with `DDP_CORE_SHA=<the image's core>` (OPEN-586).
* **Gates:**
  * `git log --first-parent <live>..7a2e5e0d` shows only #76, the last change being `8cef03e4` (#74); if more shows, stop and post it;
  * no scrape task running (as before, api-v3 is not used by a running scrape);
  * healthz 200 before.
* **What changes for users:** every related bill in an answer also carries `related_bill_id` (the resolved bill) and, when stored, `label` (the legislature's own word). Today no label is stored anywhere, so labels appear only after scrapers write them (Florida, OPEN-642). An unknown one is left out of the answer (Ramon: "Missing is fine").
  * api-v3 checks that the column exists before reading it (cached 5 minutes), so it is safe on RDS today.
* **Checks after:**
  * healthz 200;
  * `/bills?jurisdiction=us&per_page=1&include=related_bills` 200, and its related bills now show `related_bill_id`;
  * one bill detail 200;
  * the drift check exit 0 once ddp-sync below is done.
* **Rollback:** the running image tagged before the change (`pre-open641`), as for OPEN-660.

## 2. ddp-sync (EC2)
* Rebuilt at its current main **`becbceb8`** (no ddp-sync change), with `DDP_CORE_SHA=<the image's core>` (SYNC-180), so the loader matches the image. It loads the new column through core's own models, so it must follow.
* **Gates:** no pipeline lines in the last 10 minutes, no scrape task running.
* **Checks:** container up, 0 Tracebacks in the first minutes, the drift check exit 0 (image, api-v3 and ddp-sync on one core).
* **Then** SYNC-181's US re-import (`ddf23c9`) may follow on its own GO.

## 3. Mac (Mac side, not the prod agent)
The Mac api-v3 is rebuilt by the Mac side with `refresh-api-v3.sh` at the same commits, after EC2.

## Not authorized
Anything else: no recompute, no re-import, nothing on RDS.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
