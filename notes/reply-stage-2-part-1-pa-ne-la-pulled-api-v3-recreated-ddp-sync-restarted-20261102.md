# Reply (Stage 2 PA, NE, LA; `e8a1e5c`), Part 1 DONE and CLEAN: both repos pulled, api-v3 recreated, ddp-sync restarted, 2026-11-02 22:24 UTC

**The operator chose "Part 1 and Part 2 now (Recommended)"** (his pop-up answer). Part 2 (the three launches) follows this note.

- **Gates (22:22 UTC):** in-flight Fargate records **0** (read from the store), 0 ECS tasks, no ddp-sync job in the last 5 to 10 minutes, nowhere near 02:00, 02:30 or 03:00. **Revisions recorded before:** ddp-open-states **`2b71a9d`**, ddp-sync **`766ff6c`**. Logs saved (`ddp-sync-pre-pa-ne-la-20261102T2222Z.gz`, `api-v3-pre-pa-ne-la-20261102T2222Z.gz`); the running ddp-sync image **`464651ec650d`** is tagged **`ddp-sync:pre-pa-ne-la`** (rollback).
- **Pull (both fast-forward, clean):** ddp-open-states **`7853dbb`** (one file, `jurisdictions.yaml`, 6 lines changed); ddp-sync **`b73983d`** (exactly `config/sync_schedule.yaml`, `jurisdiction_names.py`, `tests/test_jurisdiction_names.py`). I read both diffs before pulling; they are as you described.
- **api-v3:** `up -d --no-deps --no-build --force-recreate api` at 22:22:23; healthy by 22:22:39 (about 16 s); same image `31d95356e4ba` (OPEN-481); host and container `jurisdictions.yaml` md5 equal (`351dd7e41e5d…`). **`/ddp/enrollment` read back through the broker's own client: 13 jurisdictions; `pa`, `ne`, `la` each `status: scraping` and `cloud_path: true`; `mtime 2026-11-02T22:22:23.118963+00:00`.**
- **Combined drift check before the restart:** `check-jurisdiction-drift.py --ddp-sync-root /opt/ddp-sync`: **`OK: every list compared agrees with jurisdictions.yaml (13 jurisdictions).`**, exit 0.
- **ddp-sync restart:** 22:23:40 UTC, healthy at 22:24:46; **image `d4a9b4edf9a4`**. Log: **`jurisdiction_manifest_agrees manifest_mtime=2026-11-02T22:22:23.118963+00:00 mode=authoritative`**; **`Scheduler started with 19 jobs`** (unchanged from before); **0 `Traceback` or `[error` lines**; no `resuming` line (nothing was in flight). Loaded config: `pa`, `ne`, `la` are in the Sunday `secondary` batch and in the cloud-path list. ddp-sync's routed list is unchanged (**AZ FL MA MI NC US UT VA WA**).
- **The broker's routed list is unchanged:** AZ FL MI NC US UT VA WA.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
