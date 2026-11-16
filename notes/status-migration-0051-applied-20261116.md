# Status: migration `data.0051_billversiondocument_diff_baseline_id` APPLIED on RDS (OPEN-539), 2026-11-16 05:59 UTC (prod agent)

Answers `835b631b` steps 1 to 4; your HOLD (`eadf20b8`) ends on this note. **User's words in session:** after I recommended running it right after the scorecard chain with step 8, they asked **"are you able to run that migration 0051 during the scorecard build chain? it shouldn't touch the broker, right?"**; I checked it did not (below) and ran it then, which is the user's change of timing, not mine.

## Does it touch the broker? (checked before running, read-only)
- It changes `ddp_bill_version_document` in the **`openstates` database**, which has **no** broker tables (`common_organization` and `common_bill` absent there). The broker's own database is separate.
- What does read that table is **api-v3**, which the scorecard chain calls. At 05:58 the only sessions in the database were api-v3's 16 pooled connections, **all idle, last query 36 to 56 minutes earlier** (so the chain was not hitting the table then); **no locks on the table, no transaction older than 10 s**; 0 ddp-sync pipeline lines in 10 minutes and 0 running scraper tasks.

## Step 1 (gates, restore point)
**Restore point 05:58 UTC:** `data` latest migration `0050_billdocumentnotfound`; column `diff_baseline_id` **absent**; table 230,990 rows; slot `ddp_legbot_subscription` active.

## Step 2 (apply)
Core **`e964183b33f6e3f9b18a406bf2e043107467354d`** in a throwaway worktree on `PYTHONPATH`, host venv (Python 3.9.2), through core's `init_django()`. `sqlmigrate data 0051` first: exactly `ALTER TABLE "ddp_bill_version_document" ADD COLUMN "diff_baseline_id" integer NULL;` and `migrate data 0051 --plan` listed only `data.0051_billversiondocument_diff_baseline_id`. **`lock_timeout` was set to 5 s on the migration's own connection (read back: `5s`). Applied 05:58:41 to 05:58:42, `Applying data.0051_billversiondocument_diff_baseline_id... OK`, first attempt, no retry needed.**

## Step 3 (after, read-only)
- Column present: `integer`, nullable, **no default**, **0 non-null values**. `ddp_bill_version_document` still **230,990 rows**.
- Latest `data` migration **`0051_billversiondocument_diff_baseline_id`**; **exactly 1 migration applied in the last 10 minutes** (nothing else new). Replication slot `ddp_legbot_subscription` still active; **0 waiting locks** on the table. (The Mac side of replication I cannot read from here; the column was already there per your note.)
- **api-v3 on EC2 (still on `8214db7`, not yet `306b4f5`):** `/ddp/enrollment` 200 (13 states, `newest_first` us only), `/bills?jurisdiction=pa&per_page=1` 200, a bill detail with versions 200. **api-v3 log since 05:58:30: 0 tracebacks, 0 errors.** Broker web, celery and beat: 0 new errors; **0 nginx 5xx**; **the scorecard chain was still running undisturbed** at 05:59.
- **Not done:** the OPEN-539 stamping pass (`recompute-diff-order --baseline-only`) and any other migration, as you said.

## What is next
- **Step 8 (api-v3 to `306b4f5`)** still waits for the scorecard chain to end (about 07:03 UTC; the user chose that timing), then the manual scrapes under their gates. I am **not** launching any scrape before step 8 is done and checked, per `1f19165e`'s own order.
- Rollback for 0051, if ever wanted: `ALTER TABLE ddp_bill_version_document DROP COLUMN diff_baseline_id;` and delete the `django_migrations` row `data / 0051_billversiondocument_diff_baseline_id`. Not needed.
- **Tonight's nightlies on revision 63 (wa 02:30, usa 03:00, pa 04:00, 11-17) can now archive.**
