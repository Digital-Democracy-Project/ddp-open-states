# Checkpoint: OPEN-642 Florida re-run of 2024, 2025, 2026 STARTED

From DDP Prod Agent, 2026-11-23 00:49 UTC. Ramon said go in my session (pop-up, 11-23), after reading your cause note `c506b00a`. Notes re-fetched before acting; nothing withdrawn.

- **Gates:** (1) Florida's scraper is the image's (v78 = rev 80; every image since v75 holds #187). (2) `check-core-pin-drift.py --image-core 7f531958... --sync-container ddp-sync-ddp-sync-1` **exit 0**: image, api-v3 and the ddp-sync loader all at 7f5319583f9d30684ef3f042ea308554f1cc0676. (3) No fl task; locks held were ok only; fl lock empty. (4) `curl -sI https://flhouse.gov/Sections/Bills/bills.aspx`: **HTTP/1.1 200 OK**, no Location (checked twice, 00:2x and 00:4x UTC).
- **Trigger:** `POST /ddp-sync/v1/trigger/openstates-scrape/fl?full=true&sessions=2024,2025,2026` at **00:49:20 UTC**: **202**, `{"status":"started","target":"fl","sessions":["2024","2025","2026"],"full":true}`. No 409.
- **Time:** expect about 40 h (your estimate). Next scheduled Florida run is Sunday 11-29 02:00 UTC, well after.
- **If a session fails:** I report the error and minute and do not retry. 2023, 2023B, 2023C, 2026D, 2026E, 2026F are not touched.
- **Report when it ends:** run ids, image revision, each load's status with counts, FL links by session/type/label on RDS (before: 0), and the FL validators after the broker's next FL sync.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
