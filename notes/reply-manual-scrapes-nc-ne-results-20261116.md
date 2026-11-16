# Reply: manual scrapes of nc and ne on revision 63, RESULTS: both completed, clean. 2026-11-16 07:24 UTC (prod agent)

Answers `1f19165e` section 2 for nc and ne; follows my launch note `f9e4f214`. One launch each, no retry. **Nothing failed: 0 `Traceback`, `ERROR` or `CRITICAL` lines in `/aws/ecs/ddp-scrapers` since 06:07, no alert, both pipelines `status=completed failed=0`.**

## nc: run `nc-01a875a2f3a6`
- **Revision:** `ddp-scrapers:63` (read from ECS, task `0e5be9c39d7c4ecca7716fe69902173e`).
- **Times (UTC):** launched 06:07:12; scrape task summary 07:14:35, collection done 07:15:18; RDS load 07:15:18 to 07:19:57 (4 min 39 s); archive done 07:21:28; **pipeline done 07:21:41** (`duration_seconds=4468.6`, `archived=True`, `failed=0`, `sessions=1`, `status=completed`).
- **Scrape line:** `{"mode": "incremental", "status": "ok", "found": 3848, "duration_s": 3876}`. Sunday's incremental on revision 61 found 3,128, so **+720**. The task's own report: **vote_event: 1501**.
- **Vote events in RDS: 781 before, 1,501 after (+720)**; bills 2,343 before and after. This matches your "about 719 more roll calls (OPEN-573)".
- **Archive** (`nc-archive-3c8491f441ac`, ok, 18 s): checked 2,343, fetched 0, skipped 6,207, archived 0, `fetch_errors 0`, blocked 0, `extract_errors 0`, conflicts 0, `persist_errors 0`.
- **LegBot:** `archiver_triggered_legbot_no_sessions_touched` (no new documents, so **no trigger was sent**; SYNC-162's first live trigger is therefore still not seen). Search refresh `calls=1 drained=True refreshed=2343 with_text=2343`.

## ne: run `ne-dcaf452fc46f`
- **Revision:** `ddp-scrapers:63` (task `aabf9d67e1834894851a7b13353f9cab`).
- **Times (UTC):** launched 06:07:17; scrape task summary 07:10:12, collection done 07:10:48; load 07:10:48 to 07:14:40 (3 min 52 s); archive done 07:16:11; **pipeline done 07:16:12** (`duration_seconds=4134.4`, `archived=True`, `failed=0`, `status=completed`).
- **Scrape line:** `{"mode": "incremental", "status": "ok", "found": 3621, "duration_s": 3623}` (Sunday's: 3,621). Task report: **vote_event: 1772**.
- **Vote events in RDS 1,772 before and after; bills 1,847 before and after** (the same objects re-saved).
- **Archive** (`ne-archive-da33470402f9`, ok, 10 s): checked 1,847, fetched 0, skipped 3,383, archived 0, 0 fetch errors, 0 extract errors, 0 persist errors.
- **LegBot:** `archiver_triggered_legbot_no_sessions_touched`: no trigger.
- Both runs logged the usual `no usable filing figures for a successful run` warning (marker file missing; the same as every state).

## What I did not check (yours, on the Mac)
Whether 0 bills are now stored newest first for nc and ne, and nc's motion classifications. I did not run a `reverse-action-order` dry run (the manifest says false for both states now, so the command would refuse without the override, which is not authorized).

## What is next
The 10-minute ddp-sync quiet gate for **step 8** ends at 07:31:41 (nc's pipeline ended 07:21:41); I run step 8 right after (api-v3 `306b4f5`, tag `pre-306b4f5`), then launch **al** and then **la** under your gates (al first; at most two at once). Alabama's section B follows Alabama's run. No second launch of nc or ne.
