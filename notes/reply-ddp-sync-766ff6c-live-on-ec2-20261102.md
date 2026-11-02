# Reply: ddp-sync `766ff6c` is LIVE on the EC2 broker host (answers `8ff3b44`), 2026-11-02 20:02 UTC

**The operator told me to do the release as written** (with report-first on a failed check, not an automatic rollback).

- **Gates:** 0 ECS tasks, ddp-sync healthy 17 h, 19:59 to 20:00 UTC (nowhere near 02:00, 02:30 or 03:00). Checkout was clean at `2ea2c06`.
- **Before:** container log saved (`ddp-sync-pre-766ff6c-20261102T2000Z.gz`); the running image `d374619e205d` is tagged `ddp-sync:pre-766ff6c` (rollback).
- **Pull and restart:** `git merge --ff-only` to `766ff6c` (clean). `sudo systemctl restart ddp-sync` at 20:00:49 UTC; the start-up line appeared at 20:01:33 and health was `healthy` by about 20:02. **Revision running: `766ff6c`, image `464651ec650d`.**
- **Checks:** `jurisdiction_manifest_agrees manifest_mtime=2026-11-02T01:32:44... mode=authoritative`; **`Scheduler started with 19 jobs`** (same as before); **0** `Traceback` or `[error` lines; the loaded code reads `_UNSCHEDULED_STATUSES = ('paused', 'probing')`. No job was started. No in-flight job to resume (no `resuming` line).
- **Nothing unexpected.** ddp-open-states was **not** pulled and the Stage 2 drafts (ddp-sync #262, ddp-open-states #322) were not touched.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
