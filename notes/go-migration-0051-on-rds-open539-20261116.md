# GO: migration `data.0051_billversiondocument_diff_baseline_id` on RDS now (OPEN-539), so v60 (`ddp-scrapers:63`, core `e964183b`) can archive. The Mac replica already has the column. 2026-11-16 ~05:50 UTC (Mac side)

**Ramon, 2026-11-16 (pop-up): "Add the column now"**, after being told v60 carries core `e964183b`, whose archive and text steps read `diff_baseline_id`, absent on RDS (my `eadf20b`).

## Done on the Mac first (order matters)
* **The Mac replica has the column**: `ALTER TABLE ddp_bill_version_document ADD COLUMN diff_baseline_id integer NULL` at about 05:48:30 UTC.
* It was added on the subscriber first so that replication cannot stop on "missing replicated column" when RDS gains it.
* Checked after:
  * `integer`, nullable;
  * subscription `ddp_legbot_subscription` worker running, receiving LSN advancing;
  * 47 tables in state `r`;
  * Mac api-v3 bill detail 200.
* The Push Button Onboarding session's facts: nothing has run on revision 63 yet (registered 04:57:57); tonight's wa/usa ran on 62; pa was refused on 62 (`921cfc1`).

## What I need from you
1. **Gates:** no archive, text-extract or recompute running (0 ddp-sync pipeline lines in the last 10 minutes, 0 running `ddp-scrapers` tasks). Record the latest `data` migration (expect `0050_billdocumentnotfound`) and that the column is absent: your restore point.
2. **Apply** the same way as 0050 (`49ee4fb`):
   * core **`e964183b33f6e3f9b18a406bf2e043107467354d`** (the core in v60) in a throwaway worktree on `PYTHONPATH`, with the host venv, through core's `init_django()`;
   * `migrate data 0051_billversiondocument_diff_baseline_id` only;
   * set `lock_timeout` to a few seconds. If it times out, retry once a minute later; if it times out again, stop and report.
   * The SQL is `ALTER TABLE ddp_bill_version_document ADD COLUMN diff_baseline_id integer NULL`: catalog-only, no rewrite, no default, no index.
3. **After (read-only):**
   * the column exists (`integer`, nullable, 0 non-null values);
   * the latest `data` migration is `0051_billversiondocument_diff_baseline_id`;
   * nothing else new;
   * api-v3 on EC2 still answers `/bills?jurisdiction=pa&per_page=1` 200 and one bill detail 200.
4. Post a short status note with these values. **Then the HOLD of `eadf20b` ends**, and `1f19165`'s manual scrapes may go ahead under their own gates (after step 8, staggered, each once).

**Rollback** (not expected): `ALTER TABLE ddp_bill_version_document DROP COLUMN diff_baseline_id;` and delete the `django_migrations` row `data / 0051_billversiondocument_diff_baseline_id`. The Mac replica keeps its extra column harmlessly.

## Not authorized
* Any other migration.
* The OPEN-539 stamping pass (`recompute-diff-order --baseline-only`).
* A task-definition change.
* Anything on the Mac (done).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
