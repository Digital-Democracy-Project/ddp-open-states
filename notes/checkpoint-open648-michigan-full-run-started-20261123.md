# Checkpoint: OPEN-648 Michigan full run of 2025-2026 STARTED on task revision 81 (v79). Run id mi-b8b23c2b5df9

From DDP Prod Agent, 2026-11-23 04:25 UTC. Ramon said go in my session ("launch all the scrapers now", then pop-up answers) after reading your `eb3e203`. Notes re-fetched at 04:23 and 04:24 UTC; nothing withdrawn.

- **Gates:** (1) The running scrapers image contains #209: v79 is scrapers `0292506c` (your notes), and the mi task runs **ddp-scrapers:81** (read from ECS). I cannot read the image tag or its tree; I rely on your check of v79. (2) Step 4 of `1f1e692` done (core 7f531958 loaded in ddp-sync, drift check exit 0 earlier today). (3) No mi task and no mi lock before; locks held were fl, ok, pa, ri.
- **Trigger:** `POST /ddp-sync/v1/trigger/openstates-scrape/mi?full=true&sessions=2025-2026` at **04:24:37 UTC**: **202**, `{"status":"started","target":"mi","sessions":["2025-2026"],"full":true}`. No 409.
- **Time:** expect about 6 h (your estimate). Michigan's weekly run is Sunday 02:00 UTC, well after.
- **Report when it ends:** run id and revision, the collection record's "mode": "full" if my logs show it, any firewall-block lines, load status with counts, and MI related-bill links by type and label on RDS (before: 0 related; expect about 2,270 related, no companion; spot check HB 5807 to HB 5805, HB 5806, SB 966).
- **Not done:** no rebuild of ddp-sync or api-v3 (Ramon chose to launch first and rebuild later); the v79 core rollout stays open.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
