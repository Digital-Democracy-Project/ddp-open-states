# UPDATE to `22d7100` (the next scrapers image after v78): it also carries **OPEN-774**, the Florida House site outage retry. **Scrapers main is now `9493a09b`.** 2026-11-23 (Mac side, State Specific Handling)

**Not a GO.** Everything in `9e2caaa`, `a9fbb18`, `35b5cda` and `22d7100` stands. Core stays `42b48982`; only the scrapers commit moves.

## The change added
* **OPEN-774,** openstates-scrapers #225, merged by the PM session as `9493a09b`, head `3e1d2249`. It is the only scrapers change since `3be4dfce`.
* **What it does:** a Florida House visit that cannot reach flhouse.gov at all no longer stops the whole session's collection.
  * It covers the cookie visit failing, a redirect loop, and a dropped connection.
  * The scraper waits 60, 180, then 600 s and tries again, and gives up after the 4th try with a log line.
  * A "Request Rejected" page keeps its existing handling, with no wait.
  * **Why:** the 11-22 Florida re-import lost 2024, 2025 and 2026 to a 7-minute outage of the site (f47317d, c506b00).
* **Change size:** `scrapers/fl/bills.py` and its tests only. No settings, no core change.

## Changes to the release order in `a9fbb18` / `22d7100`
* **Step 1:** build at scrapers `main` **`9493a09b` or later** (full sha `9493a09ba99a70750d6508de9bc6d9089c96c3c4`; the Mac side checks the image's scrapers after the build).
* **Step 3, the EC2 ddp-sync rebuild:** the Florida re-run you started at 00:49 UTC 11-23 (7aad59d) is driven by that container, so check before rebuilding.
  * If `GET ddp:pipeline_lock:fl` is held, tell me instead of rebuilding.
  * **Why:** I have not checked what a container restart does to a running collection-and-load chain.
* **Step 1 is not affected:** registering the new image while the re-run is going does not touch a task already running.
  * Any Florida session that starts after it uses the new image, with this retry.
  * The loader then stays at core `7f531958` until step 3. That is enough for the link labels, which have been kept since `7f531958`.

Tickets: OPEN-774, OPEN-642, OPEN-536.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
