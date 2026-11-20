# CHECKPOINT (done): SYNC-181 ddp-sync rebuild, US 118/119 re-import started, NE relabel committed (650), archive IAM works. 2026-11-20 05:58 UTC (EC2 prod agent)

**1. Archive IAM works.** Washington's scheduled archive retry launched an ECS task at ~05:39:09 and finished 05:41:11 (121 s), `archive_after_scrape_succeeded attempt=2`. No denied launch. (US archive retry result not seen in the log; the rebuild cleared its loop. The next archive catches up: the archiver has no cutoff.)

**2. ddp-sync rebuilt (SYNC-181)** 05:53:51 to 05:54:52 UTC, Ramon's pre-approval ("Yes, both, when the dev confirms") and your `07bde0554`. `/opt/ddp-sync` fast-forwarded `4675299` to `becbceb8` (`becbceb` is in HEAD; log since `4675299` = the SYNC-181 commits only). Core `10f32ce08088e544e88d54ec64aa325aea80756f`. New image `38596a47977a`; rollback tag `ddp-sync:pre-sync181` = 4574b524130c; old log gzipped to /home/bitnami/ops/log-archive/. Healthy 05:55:28; 22 jobs; signals off. **Resume observed:** `cloud_scrape: resuming a Fargate job orphaned by a previous restart jurisdiction=pa run_id=pa-97d146e7bde3`. `pipeline_locks_cleared_at_startup count=2` (wa, us archive-retry loops: those retries are gone). `POST .../usa?sessions=118%3Bx` answered **400** "bad session entry '118;x'"; `ddp:pipeline_lock:us` stayed empty. Drift check with `--image-core 10f32ce0`: exit 0.

**3. US 118/119 re-import started** 05:56:22 UTC: **202**, `"full": true`, four sessions echoed (`118 chamber=lower`, `118 chamber=upper`, `119 chamber=lower`, `119 chamber=upper`). Run id `usa-d9d5d6800035`. First collection task running (118 chamber=lower). One log line at start: `stall check could not read the task log ... log stream does not exist` (a warning at task start, as usual). Collections, loads, archive and Part C will be reported when they finish; hours of run.

**4. Nebraska relabel (OPEN-550), request `f78246b35`**, pre-approved by Ramon for exactly 650/0/300.
- Prerequisite: `openstates/ddp_states/ne.py` exists in a worktree of core `10f32ce0` (production's os-text-extract env reads core via PYTHONPATH; the host checkout `openstates-core` is at the older `5c79b47d` and has no ne.py).
- Dry run: **actions changed=650 unchanged=17558, all `passage -> (none)`; bills changed=0; latest_passage_date on 300 bills.** List md5 `fbf494cad8c9b7e734fe2de125953eb4` (651 lines).
- Gate: nothing for `ne` in ECS or ddp-sync (running: pa, usa).
- Commit 05:57:16 UTC: `relabel ne --commit --expect 650` -> **[COMMITTED] changed=650 unchanged=17558, bills 0, latest_passage_date 300.** Committed list (undo record) /home/bitnami/ops/ne-relabel-committed-20261120.list, same md5. A second dry run afterward: changed=0 unchanged=18208, all computed fields 0.

**5. BROKER-560 / #780:** your reply `a63dc45b` read. Ramon decided the same: hold, and a full broker release later after testing. I changed nothing. Note: Louisiana LegBot (LA/2026, started 05:47:09 UTC, ~16-17 h) is in flight; Ramon accepts re-running skipped bills if a restart is needed, but the release waits for his go.

**Next:** watch the US run; LA skipped-bill re-run after the LA call returns; PA load/archive after ~11:00 UTC.
