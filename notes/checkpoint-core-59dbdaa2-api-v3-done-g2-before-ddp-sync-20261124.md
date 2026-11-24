# Checkpoint (2026-11-24 04:54 UTC): core 59dbdaa2 rollout NOW (Ramon, pop-up: "can you go now before the scorecard chain starts?" to the plan "core 59dbdaa2 + ddp-sync 60791f5"). api-v3 DONE; in-flight list before ddp-sync.

- **api-v3 (EC2):** rollback tag `ddp-openstates-api:pre-core59dbdaa2` = 80bb4d883fdc; `DDP_CORE_SHA=59dbdaa2f3628821baa4cd45f1fabeb2cf936c7a`; build and recreate 18 s, **down about 7 s**, `/healthz` 200 at **04:54:18 UTC** (before the 05:00-07:00 window).
- **G1:** `/opt/ddp-sync` at `85c8888`, clean; `git log --first-parent HEAD..origin/main` = exactly **#306 (8653f08) and #307 (60791f5)**; origin/main = `60791f53f0ee9360229ee02c742d01e95a173dbf`.
- **G2 in flight (04:55 UTC):** collecting on Fargate, no load or archive in progress (no "collection done" line in 15 min): **fl 2026** (`fl-6264ea52502d`, rev 88), **ma** (weekly, rev 83), **pa** (the 04:00 nightly, rev 87). Held locks: fl, pa. Not in flight: ok, ia (S3 import locks until about 23:03 and 23:50 UTC), wa (failed 02:31).
- **After the restart:** collections resume (and with SYNC-189 a resumed run releases its own lock); archives for the resumed runs by hand when they load; nothing else re-triggered.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
