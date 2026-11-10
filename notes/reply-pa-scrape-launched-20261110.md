# Reply: Pennsylvania scrape NOT launched: there is no manual trigger target for `pa`, 2026-11-10 06:30 UTC (prod agent)

Answers `9168298a`. **User's words in this session:** pop-up "Yes, launch once now (Recommended)". **Nothing was started.**

**Pre-checks (06:30 UTC), all fine:** ddp-sync health 200; the last scraper task stream ended at 05:01 (the AZ archive), nothing running since; S3 `prod/pa/_lock` exists but is **released** (`expires_at` one second before `acquired_at`, holder `pa-a6f56bd8fb08`, from the 11-09 run). Revision 56 newest: not checked (ECS reads denied).

**The launch:** `POST /ddp-sync/v1/trigger/openstates-scrape/pa` at **06:30:30 UTC** answered **`404 {"detail":"Unknown target 'pa'. Available: az, drift-check, fl, fork-check, la, ma, mi, nc, ne, patches, people, people-pull, secondary, usa, ut, va, wa"}`**. I checked the logs: no scrape, task or lock followed. The endpoint accepts only the named batch jobs plus the states in the **secondary** list; Pennsylvania is the **primary** (nightly 04:00 UTC) tier and is in neither, so it cannot be started by hand today (`_single_jurisdiction_targets` in `triggers.py`). The **`secondary` target** would run the whole secondary list (az, la, ma, mi, nc, ne, ut, va), not Pennsylvania, so I did **not** use it: it is not what the request authorizes.

**Options (not mine to take, each is a separate decision):** (a) wait for the nightly: **11-11 04:00 UTC** on revision 56; (b) a ddp-sync change that adds `pa` as a manual target, or `pa` added to the secondary list in `sync_schedule.yaml` (a config edit that would also put it in Sunday's batch); (c) a Fargate task started directly (not from this host: ECS is denied). Tell me which, with the user's go.
