# UPDATE to `125fc5e` (SYNC-180, rebuild EC2's ddp-sync): build at core **`c983ae68599e94494a94edc23d576b483922302e`**, image v69's core, not `5c1455e1`. 2026-11-19 (Mac side, State Specific Handling)

**Not a GO.** Everything in `125fc5e` stands except the core.

* **Why the change:**
  * The live scrapers image is now **v69** (revision 72, `58430e9`), built at core `c983ae68`.
  * EC2 api-v3 already runs `c983ae68` (your checkpoints `47e3abd`, `9f2e06a`).
  * ddp-sync has to match, so the drift check sees one commit everywhere.
  * `c983ae68` contains `5c1455e1` and adds only New Mexico's "Amendments in Context" rule (OPEN-637). The import doesn't read that rule.
  * The reason `125fc5e` gives for not using v67's core (Utah's conference rule) still holds.
* **Wherever `125fc5e` says `5c1455e1`, read `c983ae68599e94494a94edc23d576b483922302e`:**
  * Gate 3 is now "v69 is registered (revision 72, done)".
  * The build is `DDP_CORE_SHA=c983ae68599e94494a94edc23d576b483922302e docker-compose -f infrastructure/docker-compose.prod.yml build ddp-sync`.
  * The check is `check-core-pin-drift.py --image-core c983ae68599e94494a94edc23d576b483922302e --container ddp-openstates-api-1 --sync-container ddp-sync-ddp-sync-1`. Expect **exit 0**: api-v3 is already on this core.
* **Gates 1 and 2 are still yours to confirm:** ddp-sync #298 merged and `/opt/ddp-sync` at or after it; ddp-open-states #426 merged and `/opt/ddp-open-states` at or after it. Gate 4 (no cloud scrape or load in flight) applies as before.
* **What waits on this rebuild:**
  * Utah's stored-history runs (`2b0abe4`, gate 1). Its gate 2 is already met by broker `81cce950`.
  * The import-time half of OPEN-547 to 551.
  * OPEN-603.
  * The Oregon proof (931 joint-committee votes linked).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
