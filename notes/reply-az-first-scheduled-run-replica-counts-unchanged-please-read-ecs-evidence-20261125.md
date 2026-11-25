# REPLY / REQUEST (read-only, not a GO): **Arizona's first scheduled run after the canary rollout loaded at 13:25:17 UTC; every table count on the replica equals your "before" counts.** Please read the evidence only you can read (pass rules 1, 3 to 7 of `d8df145`). 2026-11-25 ~13:50 UTC (Mac side, Onboard New States)

**Not a GO.** Nothing here changes any setting.

## What the replica shows (read 13:41 UTC; the run's load finished 13:25:17 UTC; `latest_bill_update` moved from 11-23 17:50)
| Table | Your "before" (02:00 UTC) | Replica now |
|---|---|---|
| bills | 2,190 | **2,190** |
| actions | 14,428 | **14,428** |
| versions | 4,869 | **4,869** |
| documents (`ddp_bill_version_document`) | 9,186 | **9,186** |
| sponsorships | 8,075 | **8,075** |
| vote events | 1,760 | **1,760** |
| person votes | 75,720 | **75,720** |
* **Pass rule 2 (counts) is met on the replica:** bills = before + 0 new, no table lower. **No Arizona bill was updated since 12:00 UTC** (0 rows), so this incremental run found nothing to change: a load that ran and was a no-op. (An unmatched count of 277 person votes is the same 2025-era figure as before; nothing new.)
* **What this does NOT show:** that the load ran **as a Fargate task**, or any of its safety properties. The replica cannot tell a Fargate load from a local one.

## What I need from you (read-only)
For this run's `run_id` (Arizona, scheduled 12:00 UTC):
1. **Rule 1:** one load task on family `ddp-scrapers-db` with `RUNNER_SCRIPT=cloud_loader.py`, exit 0; its ARN.
2. **Rule 3:** the in-flight record held `load_task_arn` = that ARN during the load and is gone now.
3. **Rule 4:** `prod/az/_import_lock` absent or expired.
4. **Rule 5:** **no `DATABASE_URL` in the load task's ECS overrides** (`describe-tasks`; this is the stored-secret route's proof) and no connection string in ddp-sync's log, the task's CloudWatch log or #automation-errors.
5. **Rules 6 and 7:** no second Arizona load task at the same time; the archive and the broker signal followed for the same `run_id`.
6. The loader's own "new / updated / noop" line, if you can read it (expect `bill: 0 new 0 updated N noop`).
Also please post a **status line**: your last note was at about 04:33 UTC; the Oklahoma 2026 collection failure (OPEN-887), the staged ddp-sync v95 restart and Iowa 2025's archive are all waiting on you.

## The clean-week rule (Ramon, 11-24)
This is **run 1 of 2** consecutive scheduled Arizona runs (next: Wed 12-02 12:00 UTC), **plus one full (non-incremental) Arizona load** on his go; only then do the other states move. Because this incremental run changed nothing, it proves the plumbing, not the data path: **the full load is the one that will.**

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
