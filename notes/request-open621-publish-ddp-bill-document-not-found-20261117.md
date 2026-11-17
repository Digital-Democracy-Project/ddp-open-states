# REQUEST (waits on Ramon's go): add `ddp_bill_document_not_found` to the RDS publication so the Mac copy of RDS stays in lockstep (OPEN-621). 2026-11-17 (Mac side)

**Not a GO yet.** It changes the RDS publication, a production write.

**Why:** Ramon, 2026-11-17 (OPEN-621): "i would rather keep the logical RDS replica on the Mac in perfect lockstep, so that we don't have database drift."
* The table came with core migration `data.0050` (OPEN-506: bill document addresses the site answered "not found", so the Massachusetts archive stops asking for them). It exists on RDS but isn't in `ddp_legbot_publication`, so the Mac never receives it.
* The replica monitor has said so since 11-17 02:15 UTC (`FAIL: ddp_bill_document_not_found: a table on RDS that the publication does not carry`).
* The Mac's only intentional exceptions stay `ddp_bill_search` (the Mac builds its own) and `profiles_profile` (each server's own API keys). This table is **not** to be added to the "known unpublished" list.

## What I need from you (RDS, after the go)
1. **Read first:**
   * `select count(*) from public.ddp_bill_document_not_found;`
   * `select tablename from pg_publication_tables where pubname='ddp_legbot_publication' and tablename='ddp_bill_document_not_found';`, which should return 0 rows today;
   * that the table has a primary key (logical replication of UPDATE/DELETE needs one): `\d public.ddp_bill_document_not_found`.

   Report all three.
2. **Grant FIRST:** `GRANT SELECT ON public.ddp_bill_document_not_found TO ddp_local_replication;`. Order matters: a table added to the publication before the grant crash-loops the Mac's table-copy worker (OPEN-277).
3. **Then:** `ALTER PUBLICATION ddp_legbot_publication ADD TABLE public.ddp_bill_document_not_found;`.
4. **Report:** the time, both statements' results, the publication query again (1 row now), and the row count from step 1 again.

**Rollback:** `ALTER PUBLICATION ddp_legbot_publication DROP TABLE public.ddp_bill_document_not_found;` (the grant is harmless to leave). Nothing on RDS changes except these two statements. The table's rows aren't touched.

## Mac side, afterwards (mine; no need to wait)
* `ops/postgres-replica/local/sync-structure.sh` (OPEN-314) creates the table on the Mac from RDS's definition and runs `ALTER SUBSCRIPTION … REFRESH PUBLICATION`, which copies its rows.
* I check:
  * the Mac's row count equals your step 4 count;
  * the replica monitor no longer reports the table;
  * `compare-schema.sh` passes.

  I'll post `reply-verified-open621-…`.

## Timing
No reason to wait for a slot: it's two metadata statements. Just not during another publication or subscription change.

## Not authorized
Any other table, any other grant or role change, dropping anything from the publication, touching the table's rows, or any image, manifest, broker or ddp-sync change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
