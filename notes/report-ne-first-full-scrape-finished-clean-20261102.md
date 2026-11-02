# Report (Stage 2, `e8a1e5c`): the NEBRASKA first scrape FINISHED CLEAN, 2026-11-02 23:33 UTC

Run **`ne-209bb6c96905`**, ECS task **`abb6c2829f7b4fb3a301e0029c27a7ae`**, launched **22:25:25 UTC**, once. Wait limit read from the in-flight record: **43,200 s**.

- **Times (UTC):** scrape log first line 22:26:03, last 23:28:39; **`cloud_scrape: collection done, loading into RDS` at 23:29:06**; **`cloud_scrape: done duration_seconds=4069.6` at 23:33:16** (about 68 minutes from launch to loaded). **Far under your 2 to 3 hour guess and the 12 h limit.** The bills scrape itself: `duration 1:00:24.3`. ECS: task `STOPPED`, `EssentialContainerExited`, **exit code 0**. The load took about 4 minutes (limit 7,200 s).
- **First lines of the scrape (redacted):** `Module: ne`, `ne (scrape)`, **`bills: {}`** (so **`start=` was not given**: a full walk, as you said), an `InsecureRequestWarning` for `nebraskalegislature.gov`, then the saves. **Session: the log says `WARNING openstates: no session provided, using active sessions: {'109'}`**, so it walked **session 109**.
- **What it found (the scraper's own summary and sidecar):** `bill: 1847`, `vote_event: 1772`, `jurisdiction: 1`, `organization: 1`; sidecar `{"mode": "full", "status": "ok", "found": 3621, "duration_s": 3626}` (1847 + 1772 + 1 + 1 = 3621).
- **Log levels:** INFO 7,244, DEBUG 1, **WARNING 1 (the session line above), ERROR 0**, no `Traceback`.
- **429, 403, "Too Many", Barracuda, WAF: none.** My watcher matched on HTTP status patterns and on those words; **0 matches** in all 14,509 lines (the watcher ran from 22:26 to 23:31). **What I cannot give you:** **the number of distinct bill pages fetched, repeats, and 404 or retry counts.** The scrape's log is at INFO and **does not record individual requests** (I counted: 0 request lines), so those figures are **not readable** from CloudWatch or ddp-sync. The nearest evidence is that **1,847 bill objects were saved, exactly one `save bill` line each**.
- **What production holds for Nebraska now (read-only, through the api container's own session with `SET TRANSACTION READ ONLY`, plus the route):** **bills 1,847** (the route `GET /bills?jurisdiction=Nebraska&per_page=1` also gives `total_items` **1,847**), **vote events 1,772**, **person votes 86,723**. Before the run all three were **0**. **The bill and vote-event counts equal what the scraper found.**
- **S3 lock `prod/ne/_lock`:** held by `ne-209bb6c96905`, **released** (its expiry is one second before its start).
- **Not done, as you said:** no archive, no LegBot, no routing, no embedding.
- **Pennsylvania and Louisiana are still running** (about 70 minutes in at 23:36 UTC, no stop condition). I will report each when it finishes and at about 01:25 UTC (3 h) if either is still going.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
