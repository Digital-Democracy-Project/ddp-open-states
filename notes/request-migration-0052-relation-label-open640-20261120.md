# REQUEST (not a GO): migration `data.0052_relatedbill_ddp_relation_label` (OPEN-640), in this order: Mac replica column, then RDS on its own go, then the next scrapers image, then api-v3 and ddp-sync at that core. 2026-11-20 (Mac side, State Specific Handling)

**Why now.** openstates-core #135 is merged with Ramon's go, as **`1c367db5`**. ddp-open-states #436 (PRIMITIVES) is merged as `43fcf087`.
* Core main now carries 0052. A scrapers image is built at core main, so **the next image (after v74) would read and write a column RDS does not have yet.**
* Hence: **no scrapers image may be built until step 2's status note confirms 0052 on RDS.**
* v74 (`ddp-scrapers:76` / `ddp-scrapers-db:3`, core `83584c48`) predates the merge and is unaffected.

**What it is.**
* A new optional column `ddp_relation_label` (`varchar(100)`, nullable, no default) on `opencivicdata_relatedbill`: the legislature's own word for a bill link ("Identical bill", "Similar").
* The SQL is `ALTER TABLE opencivicdata_relatedbill ADD COLUMN ddp_relation_label varchar(100) NULL`. It changes the catalog only: no rewrite, no default, no index.
* Existing rows stay NULL. No scraper writes the column until the per-state companion tickets (after launch), so nothing a person sees changes.

This follows the 0051 precedent: `835b631` (the GO), `2f92468` (the status).

## Step 1 (Mac side, waits on Ramon's go for this request): the Mac replica gets the column first
* `ALTER TABLE opencivicdata_relatedbill ADD COLUMN ddp_relation_label varchar(100) NULL` on the Mac replica (`openstates_rds_repl_20260911`) **before** RDS has it. Replication then never stalls on a missing column.
  * `sync-structure.sh` (OPEN-314) would add it by itself only **after** RDS has it, with the apply worker retrying in between.
  * After RDS has it, `sync-structure.sh --dry-run` must report nothing to add for this table.
* **Checks:**
  * the column is `character varying(100)`, nullable;
  * the subscription worker is running and its LSN advancing;
  * Mac api-v3 bill detail answers 200.
* The Mac side posts these on this branch as `status-…` before step 2.
* Today on the Mac replica the table has `id, identifier, legislative_session, relation_type, bill_id, related_bill_id`, without the column.

## Step 2 (prod agent, its own GO): migrate RDS
1. **Gates:**
   * No archive, text-extract, recompute or import running: 0 ddp-sync pipeline lines in the last 10 minutes, 0 running `ddp-scrapers` tasks.
   * Record the latest `data` migration, which should be **`0051_billversiondocument_diff_baseline_id`**, and that the column is absent. That is your restore point.
   * Step 1's status note exists.
2. **Apply** as for 0051:
   * core **`1c367db5`** in a throwaway worktree on `PYTHONPATH`, with the host venv, through core's `init_django()`;
   * `migrate data 0052_relatedbill_ddp_relation_label` only;
   * `lock_timeout` a few seconds. If it times out, retry once a minute later; if it times out again, stop and report.
3. **After (read only):**
   * the column exists (`character varying(100)`, nullable, 0 non-null values);
   * the latest `data` migration is `0052_relatedbill_ddp_relation_label`, and nothing else is new;
   * EC2 api-v3 still answers `/bills?jurisdiction=us&per_page=1` 200 and one bill detail 200;
   * the Mac replica's subscription is still streaming (the Mac side confirms).
4. Post a short status note with these values. **It lifts the image hold.**

**Rollback** (not expected): `ALTER TABLE opencivicdata_relatedbill DROP COLUMN ddp_relation_label;` and delete the `django_migrations` row `data / 0052_relatedbill_ddp_relation_label`. Do that only while no image at core `1c367db5` or later is registered. The Mac replica keeps its extra column harmlessly.

## Step 3 (Ramon builds): the next scrapers image, only after step 2's status note
* It is built at core main (`1c367db5` or later), as usual.
* The drift check then shows api-v3 and ddp-sync behind the image's core; that is expected until step 4.
* Register only when no scrape task is running, as for every image.

## Step 4 (after the image): api-v3 and ddp-sync at the image's core
* **EC2 api-v3:** rebuilt at the image's core, the core pin from the image (`DDP_CORE_SHA`, api-v3 #402 practice). Check: `/bills` 200 and one detail 200.
* **ddp-sync:** image rebuilt at the same core.
* **The Mac api-v3:** rebuilt with `refresh-api-v3.sh` by the Mac side.
* The core drift check then reads OK on both hosts.
* Serving the label is OPEN-641's work (not built yet). Until then api-v3 ignores the column.

## Not authorized
* Any other migration.
* Building or registering an image before step 2's status note.
* Any scraper or data change that writes the label (the per-state tickets, after launch).
* Anything in the v74 backfill note (`b85ce25`), which is unaffected.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
