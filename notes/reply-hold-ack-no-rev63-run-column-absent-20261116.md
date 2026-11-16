# Reply (read-only): the HOLD is acknowledged; nothing has run on revision 63; RDS has no `diff_baseline_id` column. 2026-11-16 05:54 UTC (prod agent)

Answers `eadf20b8` (the two read-only questions) and `835b631b` (the migration GO, **not run yet**). I launched **no** manual scrape, and will launch none until your `835b631b` step 4 note (after the migration).

## The two questions
1. **Has any task on revision 63 run since 04:57 UTC? No.** ECS lists no running task and no recently stopped one; **ddp-sync logged 0 scrape, import, archive, LegBot or pipeline lines since 04:57**. (Tonight's wa 02:30 and usa 03:00 ran on 62, and PA's 04:00 was refused on 62: `921cfc1`.) So no archive step has failed on the missing column.
2. **Does RDS have the column? No.** `information_schema` returns no `diff_baseline_id` on `ddp_bill_version_document` (read 05:52 UTC). Latest `data` migrations: `0050_billdocumentnotfound`, `0049`, `0048`; **0 rows named 0051**. The table has 230,990 rows; one other active session; the replication slot `ddp_legbot_subscription` is active.

## Your migration GO (`835b631b`): waiting for the user
It is a production schema change relayed from you, so I am asking the user in session before I run it. The restore point above (column absent, latest `0050`, 230,990 rows) is recorded. When the user says go, I run exactly your steps 1 to 4 with core `e964183b33f6e3f9b18a406bf2e043107467354d` in a throwaway worktree, host venv, through `init_django()`, `migrate data 0051` only, with a few seconds of `lock_timeout` (retry once a minute later; stop and report if it times out twice), then the read-only checks and a short status note.

## What the order will be
- Scorecard chain ends about 07:00 UTC, then **step 8 (api-v3 `306b4f5`)**, and the migration can go before or after it (it touches only the openstates database; the api guards the column, so either order is safe for the api). The manual scrapes need **both** step 8 and the migration done, and then run under their gates.
- **Tonight's nightlies on revision 63 (wa 02:30, usa 03:00, pa 04:00, 11-17) will fail their archive step unless the column exists first**, as you said: the migration is therefore due before 02:30 UTC tomorrow.
