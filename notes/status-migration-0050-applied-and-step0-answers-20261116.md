# Status: migration data.0050 APPLIED on RDS (step 1), and the read-only answers (step 0), 2026-11-16 01:27 UTC (prod agent)

Answers `9963ec87` step 0 and step 1, and the read-only questions of `5f0f427`. User's words in session (pop-up, after I summarized the notes and said I would not act on the relayed go alone): **"Yes, apply 0050"** for step 1, and, for steps 3 to 8, **"Run each step if its dry run passes its gate"**. **Ramon: the migration is done; the image register (step 2) is yours.**

## Step 1: migration `data.0050_billdocumentnotfound` (OPEN-506)
- **Note on naming:** the migration's app label is `data` (as `0049`), not `openstates`.
- **Before (read-only, 01:25:47 UTC = restore point):** PostgreSQL 16.15; the connected role `openstates_admin` owns `ddp_bill_version_document`; latest `data` migration `0049_billversiondocument_is_bill_version`; **0 rows named 0050; table absent**; no archive running (0 ddp-sync pipeline lines in 10 min, 0 `ddp-scrapers` tasks).
- **Method:** with core **`eec94082b66bee9e5f684e65a3c78248fadca728`** in a throwaway worktree on `PYTHONPATH` and the host venv (Django 3.2.14, Python 3.9.2), through core's own `init_django()`. **I did not use direct SQL this time** (on 11-05 I did, because the 0049 file was not on the host; now the file is). `sqlmigrate data 0050` first: one `CREATE TABLE "ddp_bill_document_not_found"` plus one `varchar_pattern_ops` index on `source_url`, nothing on existing tables. `migrate data 0050 --plan` listed exactly `data.0050_billdocumentnotfound` (Create model BillDocumentNotFound). Quiet re-checked (0 lines, 0 tasks).
- **Applied 01:26:53 to 01:26:54 UTC:** `Applying data.0050_billdocumentnotfound... OK`.
- **After (read-only):** table **exists, 0 rows**; columns `id integer NOT NULL`, `source_url varchar NOT NULL`, `first_not_found_at timestamptz NOT NULL`, `last_checked_at timestamptz NOT NULL`; indexes: the primary key, the unique `source_url` key and the `..._like` index. **Latest migrations: `data.0050`, then 0049, 0048; exactly 1 migration applied in the last 10 minutes** (nothing else new). `ddp_bill_version_document` 231,446 rows (I took no row count of it before; nothing in this change touches it).
- **Rollback (not used):** `DROP TABLE ddp_bill_document_not_found;` and delete the `django_migrations` row `data / 0050_billdocumentnotfound`.

## A3: does the Mac replica need the new table?
- **I can read only the RDS side.** The publication is `ddp_legbot_publication`, an **explicit list of 47 tables (`puballtables = false`)**, and **the new table is NOT in it**; the slot `ddp_legbot_subscription` is active. So the table will not replicate, and logical replication would not have created it on the Mac anyway (it does not carry DDL). Whether the Mac needs the table depends on whether anything there reads it; the archiver that writes it runs against RDS (EC2 and Fargate). I did not change the publication (not authorized, and it is your decision). If you want it replicated, that is an `ALTER PUBLICATION ... ADD TABLE` plus creating it on the Mac first.

## A1: when do Louisiana and Nebraska scrape next on EC2?
- **ddp-sync:** only their own weekly jobs, `OpenStates: la (scrape, archive, LegBot)` and `...: ne ...`, registered at the restart as `day=sunday ... start_utc=02:00`: **next run Sunday 2026-11-22 02:00 UTC**. The other registered jobs are the other states' scrape jobs, `people pull`, `people refresh`, `scrape cadence review`, the drift check and GrantBot monthly; none scrapes la or ne bills.
- **Anything else that could run them before then:** a **manual trigger** (`POST /ddp-sync/v1/trigger/openstates-scrape/<target>`) exists, and nothing calls it on a schedule. I will not trigger them.
- **Broker:** no scheduled bill-event task. Its beat table has 9 tasks (backend cleanup, clear expired sessions, map data update, rebuild search documents, scorecard update, search coverage report, security heartbeat, voatz tally silence check, and `sync webflow organizations`, disabled); none is a bill-event check. So **step 5's silent re-bootstrap has nothing scheduled to pause or re-bootstrap on production**, as on 11-13.
- **Step 3 (pause):** with no scheduled la or ne run before 11-22 02:00, the cleanest hold is **no state-list or config change at all**: just not triggering them. I would not set `status: paused` (it changes ddp-sync's jobs and the drift check). Step 3 therefore needs no action from me beyond that rule; **everything through step 6 must finish before Sunday 11-22 02:00 UTC.**

## Also done tonight (separate note)
The search rebuild of `c4110ce` ran 01:19-01:24 and passed (`498aebb5`).

## What I am waiting for
Your step 2 (image register). I will run steps 4, 5, 6, 7, 8 only after your `update-image-...` note, each saved only if its dry run passes its gate, and stop and report on any failed gate. **Kept for those steps:** a throwaway core worktree at `eec94082b` under my scratch directory (registered in the production core checkout's worktree list; the checkout itself stays at `5c79b47d`, clean). No auto-undo.
