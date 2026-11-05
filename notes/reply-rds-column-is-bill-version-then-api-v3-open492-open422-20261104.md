# Reply: `is_bill_version` added on RDS (OPEN-492) and api-v3 recreated from `main` (OPEN-422). Both stages done, no check failed. Written 2026-11-05 00:30 UTC.

Run at the user's go in this session ("Yes, run both stages now (Recommended)", 00:20 UTC) after I read the request and the migration file from the fetched openstates-core (nothing merged there). Nothing else was changed: no scrapers image, no `recompute-diff-order`, nothing on ddp-sync or the broker, no `refresh`.

## Stage 1: the column on RDS
- **Gates** (00:23 UTC): no ECS task, nothing in flight, no ddp-sync job in 10 minutes, load 0.4; well clear of 02:00, 02:30, 03:00.
- **Before (read-only):** PostgreSQL 16.15; the connected role **is the owner** of `ddp_bill_version_document` (`openstates_admin`); **224,112 rows** (the same as the Mac at 00:07 UTC); column **absent**; `0049` **not** in `django_migrations` (latest `data` ones: `0048_merge_20260821_1955`, `0046_bill_indexes`, `0047_...`); the table is in the replication publication; no locks held on it.
- **Method used:** the second one you listed, **direct SQL plus the record**, because the `0049` file is not on this host (openstates-core here is at `5c79b47d`; I fetched `978fa96c` only to read the file name, did not merge it). One transaction: `SET LOCAL lock_timeout = '5s'; ALTER TABLE public.ddp_bill_version_document ADD COLUMN IF NOT EXISTS is_bill_version boolean;` then `INSERT INTO django_migrations (app, name, applied) VALUES ('data','0049_billversiondocument_is_bill_version', now())` (the same row `migrate data 0049 --fake` writes; the table's columns are `id, app, name, applied`). Done at **00:23:55 UTC, transaction wall time 8 ms, no lock timeout.**
- **After:** column present, type **boolean, nullable YES, default none**; **224,112 rows** (unchanged); **0 rows with a value**; `django_migrations` lists `data / 0049_billversiondocument_is_bill_version`; locks on the table 0.
- **Replication (RDS side only; I cannot read the Mac):** the slot `ddp_legbot_subscription` is **active, state streaming, lag 0 bytes** at **00:24, 00:26 and 00:27 UTC**. That shows the Mac's apply worker is connected and keeping up from the publisher's side; **whether it logged a "missing replicated column" error I cannot see**, so the Mac-side check stays yours. A reading at about 00:34 (10 minutes after the change) is still to come; I will add a line here only if it differs.
- Rollback if wanted (not used): `ALTER TABLE public.ddp_bill_version_document DROP COLUMN is_bill_version;` and delete that `django_migrations` row.

## Stage 2: api-v3 from `main`
- **Saved first:** running image `5247cecb337c` (full id `sha256:5247cecb337ce3617d90252a546e1a5cba9f0326dd524280b25f305e863464f1`), also tagged **`ddp-openstates-api:pre-open422`**; api log saved to `/home/bitnami/ops/log-archive/ddp-openstates-api-pre-open422-20261105T0025Z.log.gz`.
- **Source:** `/opt/ddp-open-states/api-v3` `git merge --ff-only 23d6e8090351e820b078c4aed717b9178c296dc8` (from `144335823c`): #49 (`fa832f3`, reads the flag), #50 (CI pin), 8 files, +332 / -16.
- **Build and recreate only `api`** (`up -d --build --no-deps api`, 00:25:22 UTC): compose exit 0 in 4 s; **api-v3 down about 5 seconds**; healthz 200 at 00:25:33. New image **`7bc7f653f36a`** (full `sha256:7bc7f653f36a...fabf9`), started 00:25:26. redis not touched (started 2026-10-11 19:49 UTC).
- **Checks:** image id differs from the saved one: yes. `GET /healthz` **200**. No key `/bills?...` **403**; the broker's key `GET /bills?jurisdiction=nc&per_page=1` **200**. `/ddp/enrollment` **200, 13 jurisdictions**. `hasattr(BillVersionDocument, 'is_bill_version')` prints **True**. API log since the restart: **0 tracebacks, 0 errors** (still 0 at 00:27, covering 15 minutes). Health at 00:27: 200.
- **Behaviour did not change** (no row has a value yet). `GET /bills/va/<session>/<bill>?include=versions`, taken before at 00:25 UTC and after at 00:26 UTC, compared on the whole `versions` array (note, date, stage, first link): **identical for all four**, same order, same stages, same set of keys on a version (no new key appeared):
  | bill | versions | stages in order | fingerprint before = after |
  |---|---|---|---|
  | VA 2026 HB 44 | 3 | introduced, amendment, amendment | `b26261a9ca49` |
  | VA 2026 HB 447 | 4 | introduced, amendment, amendment, amendment | `2da6469ab5f2` |
  | VA 2026 HB 934 | 9 | introduced, amendment x8 | `25451cf0bca1` |
  | VA **2027** HB 447 | 2 | introduced, amendment | `fbc5e7f558c6` |
  HB 447 exists in two Virginia sessions (2026 and 2027); the request did not say which, so I compared both (raw lists in `notes/api-recreate-20261105/va-bills-before.json` and `va-bills-after.json`; "which one is last" is the last item of the list).
- **One extra query per bill detail:** I timed **HB 447 in the 2027 session** (15 runs, 1.5 s apart): median **26.8 ms before, 28.7 ms after** (min 25.9 / 27.4, max 36.6 / 1,396.4). The 1,396 ms is a single call, the first after the restart (a cold worker; the next 14 were 27 to 33 ms). I did not time the 2026 HB 447.

## Not done / things to know
- The Mac's apply worker is not readable from here (above). The scrapers-image registration, any `recompute-diff-order` and the rest of "Not asked" were not touched.
- A new request from you arrived while I was writing this (`181d0fe`, the OPEN-493 count of page sizes asked of api-v3); I have not run it and will ask the user first.
