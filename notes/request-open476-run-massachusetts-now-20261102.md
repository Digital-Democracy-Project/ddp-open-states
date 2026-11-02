# Request: run the Massachusetts weekly scrape once now, under the 24-hour limit (OPEN-476), 2026-11-02

Ramon's decision (2026-11-01, /ask-me): **run Massachusetts again now** instead of waiting for Sunday 11-08. The 11-01 run was stopped at 12 h and loaded nothing; your reply (commit 2903a29) confirms the 24-hour limit is live (`476d6d4`, restarted 00:36 UTC).

## What I need
1. **Launch one Massachusetts scrape the way the normal weekly run does** (same ddp-sync path, so it uses the 24 h limit and the same archive and load steps). Use whatever the sanctioned manual launch is on your side. Do not hand-edit the task definition or launch it outside ddp-sync.
2. **Before launching, check it is safe:** no MA job in flight (in-flight record 0), no other long scrape running that the shared archive relay cannot take (you have flagged that box as small before), and the collector lock for MA is free. If any of those is not true, say so and wait; do not force it.
3. **Reply when it starts** with: launch time (UTC), the task id, the wait limit it started with (it should read 86,400 s), and the live in-flight record. **Reply again when it ends** with: finish time, duration, the load outcome (bills and vote events before and after, against 11,840 / 529), and whether the archive step ran. Redact secrets.
4. Please watch for the **24-hour lock**: the collector lock lasts 24 h, the same as the wait limit. If the run is still going at about 22 h, tell me before anything else starts for MA.

## Not asked
No change to the Sunday 11-08 02:00 UTC schedule (it still runs), no limit change beyond what is already live, and no other state. If this run overlaps the WA 02:30 or USA 03:00 nightly runs and you think it should wait, say so and pick the quiet window.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
