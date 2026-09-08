# Glacier restore from 09-04 actually succeeded — but the re-tier copy job and the backfill itself never ran

*Follows up on `notes/glacier-restore-status-and-close-out-20260904.md`.* Not something I was
asked to chase — I was just reading through `notes/ops-handoff` for context and noticed a 4-day
gap on this thread, so I checked the live S3 state directly from this EC2 host while I was here.

## What I found

- The 2026-09-04 restore Batch Operations job (`job-9dcab5ee-850f-4142-bcbe-120acb05077f`)
  **did complete successfully**, at `2026-09-04T13:33:31Z` (~8h after starting — the Standard-tier
  estimate, not the ~2-day Bulk-tier one). Its report shows `TaskExecutionStatus: succeeded`.
- Confirmed live on a sample UT object (`bills/raw/ut/2025S2/lower/HB2001--.../Enrolled-....bin`):
  `HeadObject` shows `Restore: ongoing-request="false", expiry-date="Mon, 14 Sep 2026 00:00:00
  GMT"` — it's genuinely readable right now, not still pending.
- **But `StorageClass` on that same object is still `DEEP_ARCHIVE`** — this was only ever the
  temporary restore, not the permanent re-tier to `GLACIER_IR`. There's no second batch job
  anywhere under `batch-reports/` in `ddp-bill-archive` — only the one 2026-09-04 restore job.
  Step 2 of the recorded plan (the re-tier copy job) has not run.
- No note on this branch since 09-04 mentions steps 2-4 (re-tier copy / `refresh-extraction
  --dry-run` / `--commit`) happening. As far as this branch shows, the backfill has been sitting
  paused since the restore finished, not actively blocked on anything anymore.

## Time-sensitive part

That sample object's temporary-restore window expires **2026-09-14** (6 days from today,
2026-09-08). If the re-tier copy job doesn't run before then, the objects fall back to
inaccessible Deep Archive and the whole restore has to be redone. I have no visibility into
whether this is already scheduled from the `ddp-infra` side (no access to that repo from this
session) — flagging in case it's genuinely just stalled rather than already in hand.

## Next step

1. Confirm whether the re-tier copy job (`StorageClass=GLACIER_IR`) is already scheduled/running
   from `ddp-infra` — if so, nothing to do, this note is redundant, just reply here saying so.
2. If not: run it before 2026-09-14, then re-run `refresh-extraction {ut,wa,us} --dry-run`
   against RDS for a real read, then proceed to `--commit` per `PLAN-rds-data-quality-backfill.md`
   §4, same as the original 09-04 sequence.

Report back on this branch either way.
