# Checkpoint 11-26 16:30 UTC: v97 rebuild DONE on EC2 (drift OK); Iowa 2026s1 started

Ramon's go: one rebuild at v97's values (core `647bb3994ed819ba4194820b379147f525219479`, scrapers `d0bd1826f8990f738ee626a7fe7ec01823a37264`).

* Rollback images tagged first: `ddp-sync:pre-v97-da9641d` and `ddp-openstates-api:pre-v97`.
* **api-v3** rebuilt at the v97 core and recreated by service name 16:25:16 to 16:25:22 UTC (health 200 before and after, no restart loop). Outside 05:00 to 07:00 UTC.
* **ddp-sync** image built at `DDP_CORE_SHA` and `DDP_SCRAPERS_SHA` above (no #315 / policy_statement pull; checkout still `da9641d`). Narrow-rule guard: no state held a pipeline lock, no db-family task not STOPPED, nothing loading, no local loader or people process, not within [T-2, T+1] of a trigger; three checks. Old container log saved right before the recreate. Recreated 16:26:07 UTC; startup clean: 35 schedule jobs, `pipeline_locks_cleared_at_startup count=0`, 0 resumed runs.
* **Core-pin drift check: exit 0** (the scrapers image, 1 api-v3 container and 1 ddp-sync container all on `647bb399`).
* Mac host's api-v3 is Ramon's step (this role has no access).
* **Iowa `ia?full=true&sessions=2026s1` triggered 16:27:02 UTC (202, `full: true`).** It runs on the v97 image. Expect the session lines first (that the special session is found); I will report them and the end counts. After it: the v96 Iowa re-import (`ia?full=true&sessions=2025,2026,2026s1`, I will first check that list against what the manifest and the replica hold), then the recompute dry run, no commit.
* Louisiana's failed nightly (my 16:24 note) is untouched: no retry.
