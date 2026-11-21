# STATUS: step 1 of `1f1e692` done. The Mac replica has `ddp_relation_label`; replication still streaming. 2026-11-21 16:40 UTC (Mac side, State Specific Handling)

Answers `f3c311d`. Your step 2 (migrate RDS to `data.0052`) can go; Ramon's pre-approval stands as you quoted it. Nothing on production was touched from the Mac.

**What was run, Mac replica only** (database `openstates_rds_repl_20260911`, container `ddp-openstates-postgres-1`, not recreated):

```sql
SET lock_timeout = '5s';
ALTER TABLE opencivicdata_relatedbill ADD COLUMN ddp_relation_label varchar(100) NULL;
```

It ran exactly as the request's step 1 says, at 16:38 UTC, first try, with no lock wait.

**Checks:**
* **Before:** the table had `id, identifier, legislative_session, relation_type, bill_id, related_bill_id`, without the column, as on RDS.
* **Column now:** `ddp_relation_label`, `character varying(100)`, nullable. All 47,585 rows are NULL (the same row count you read on RDS).
* **Subscription `ddp_legbot_subscription`:**
  * the worker is running;
  * `apply_error_count` 0 and `sync_error_count` 0;
  * the position moved from `17F/30000548` (16:37:56, before the change) to `17F/30000578` (16:38:53, after it), so changes from RDS are still being applied.
* **Mac api-v3 (:8002):** `/bills?jurisdiction=us&per_page=1&include=related_bills` answered 200, and that bill's detail answered 200.

**After your step 2**, the Mac side will:
* confirm the subscription is still streaming (your step 2 check 3d);
* run `sync-structure.sh --dry-run`, which must report nothing to add for `opencivicdata_relatedbill`.

**Unchanged:** step 3 (the next scrapers image) waits for your step 2 status note; step 4 follows the image. The rollback in `1f1e692` is unchanged; the Mac replica keeps its column harmlessly either way.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
