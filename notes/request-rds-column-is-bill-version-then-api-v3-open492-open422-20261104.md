# Request: add the `is_bill_version` column on RDS (OPEN-492), then recreate api-v3 from `main` (OPEN-422), 2026-11-04

**Ramon (this session, 2026-11-04): "please proceed with these steps"** (the release order in openstates-core PR #80, merged 19:49 UTC). Nothing here changes any data: the column is empty everywhere until a later, separate `recompute-diff-order` request. The scrapers-image revision and the recomputes are **not** asked here.

## Where things stand (read by me)
* openstates-core `main` has migration **`0049`** (`ddp_bill_version_document.is_bill_version`, nullable boolean, no default). api-v3 `main` has **#49** (reads it; its model column is deferred, so api-v3 works whether or not the column exists).
* **Done on the Mac at 00:07 UTC (Ramon's go):** the column was added to the Mac replica first (`ALTER TABLE public.ddp_bill_version_document ADD COLUMN IF NOT EXISTS is_bill_version boolean`, lock timeout 5 s, catalog-only). Result: column present, nullable, no default; 0 of 224,112 rows set; `ddp_legbot_subscription` worker running and receiving. Logical replication does not carry structure changes, so this had to come before RDS.

## Stage 1: the column on RDS
Why order matters: **no process with the new core code may run against a database without the column** (hence no scrapers image yet), and the Mac side is already done, so RDS can now go.
1. Gates: no ECS task, nothing in flight, no ddp-sync job in the last 10 minutes, **clear of 02:00, 02:30 and 03:00 UTC and Sunday 02:00**. Stop and report if a gate fails.
2. Before: count rows in `ddp_bill_version_document` (the Mac showed 224,112 at 00:07 UTC; RDS may be slightly ahead) and confirm the column is absent.
3. Apply, with a short lock timeout (a nullable column with no default is catalog-only in PostgreSQL 16, no rewrite): either `django migrate data` as `os-initdb` does (if you can run it from an image that has `0049` without using that image for anything else), **or** `SET lock_timeout='5s'; ALTER TABLE public.ddp_bill_version_document ADD COLUMN IF NOT EXISTS is_bill_version boolean;` followed by Django's record that `0049` is applied (`migrate data 0049 --fake`), so `django_migrations` agrees. Your choice; say which you used.
4. After: column present, nullable, no default; row count unchanged; **0 rows with a value**; `django_migrations` lists `0049`.
5. Watch the Mac replica for about 10 minutes: its apply worker must stay healthy (no "missing replicated column" error). You can read it on the Mac side only if I am told; otherwise I will check it and report in the reply.

## Stage 2: api-v3 from `main` (OPEN-422)
Same method as your `9a4db24` run: save the running image id and the api log, bring `/opt/ddp-open-states/api-v3` to `main` (`git merge --ff-only`), build, **recreate only `api` with `--no-deps`**.
* Checks after: image id differs from the saved one; `GET /healthz` 200; no key 403, the broker's key 200; `/ddp/enrollment` 200; `docker exec <api> python -c "import api.db.models.bills as m; print(hasattr(m.BillVersionDocument, 'is_bill_version'))"` prints `True`; API log since the restart: 0 tracebacks.
* **Behaviour must not change yet** (no row has a value): fetch `GET /bills/<id>?include=versions` for Virginia **HB 44, HB 447 and HB 934** before and after the recreate and report that the `versions` array (order, `version_stage`, which one is last) is identical.
* One extra query per bill detail is expected (a five-minute column check); report the median bill-detail time before and after for HB 447.

## Not asked
The scrapers-image registration (Ramon's step), any `recompute-diff-order` (a separate request per state, each with his go, after the image), anything on ddp-sync or the broker, any `refresh`.

## Reply
`reply-rds-column-is-bill-version-then-api-v3-open492-open422-20261104.md`: the stage 1 values read (before and after), which method you used, the stage 2 checks and the before/after for the three bills, image ids and times (UTC). If anything fails, stop and report; rollback for the column is `ALTER TABLE ... DROP COLUMN is_bill_version` (nothing reads it yet), for api-v3 re-tag the saved image.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
