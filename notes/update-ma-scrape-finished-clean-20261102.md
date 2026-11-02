# Update (OPEN-476): the Massachusetts run FINISHED CLEAN, 2026-11-02 13:44 UTC (read at 17:40 UTC)

- **Run `ma-d2c298dde063`** (launched once at 02:07:18 UTC; resumed by ddp-sync after the 02:41 restart, same ECS task): `cloud_scrape: collection done, loading into RDS` at **13:28:12 UTC**, then `cloud_scrape: done duration_seconds=39667.4` at **13:44:08 UTC**. No error or failure line for MA in the ddp-sync log since the restart. No ECS task is running. The S3 lock `prod/ma/_lock` is **released** (its expiry is one second before its start).
- **What the replica holds now** (read-only call to our own api-v3): **11,872 Massachusetts bills** (`total_items`), sessions listed from the 184th upward.
- **The 24-hour limit was not the deciding factor this time:** collection took about 11 h 21 min from the launch, under the old 12 h limit too. The first run (`ma-bf39ea282b19`) gave up at 43,200 s, so this run was faster; I do not know why.
- **Not read:** whether an archive or LegBot step followed (the log shows none after `done`; MA's archive is registered for Fridays 05:00), and the quality of the 11,872 (no sample checked). **The weekly run at 11-08 02:00 UTC is the first under the 24 h limit.**

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
