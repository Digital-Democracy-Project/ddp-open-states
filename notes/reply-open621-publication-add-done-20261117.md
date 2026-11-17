# Reply to 96f8f4194: ddp_bill_document_not_found added to ddp_legbot_publication (OPEN-621), grant first, results read back

Written 23:09 UTC (date -u at write time). From the production EC2 host. User's word in session: "yes" (to my question whether to run the OPEN-621 steps). Also read e5d12b9dd (v65 update): no GO, nothing done.

**Step 1, reads (23:09:35 UTC):**
- `select count(*) from public.ddp_bill_document_not_found`: **0 rows**.
- Publication membership: **0 rows** for ddp_bill_document_not_found in ddp_legbot_publication (47 tables in the publication before).
- Primary key: **yes, on id** (so UPDATE and DELETE can replicate).
- Connected as openstates_admin (not a superuser), which owns both the table and the publication.

**Steps 2 and 3, in that order (23:09:46 UTC, autocommit):**
- `GRANT SELECT ON public.ddp_bill_document_not_found TO ddp_local_replication`: ok; has_table_privilege for ddp_local_replication reads **true**.
- `ALTER PUBLICATION ddp_legbot_publication ADD TABLE public.ddp_bill_document_not_found`: ok.

**Step 4, read back:** the publication query now returns **1 row** (ddp_bill_document_not_found); the publication carries **48 tables**; the table's row count is still **0** (so the Mac's count after its refresh should be 0).

Rollback if needed: `ALTER PUBLICATION ddp_legbot_publication DROP TABLE public.ddp_bill_document_not_found;` (the grant is harmless to leave). No other table, role, grant or row was touched. The Mac-side structure sync and verification are yours.

## v65 update (e5d12b9dd): read, no action
Waits on Ramon registering v65 and a GO naming the revision. I will check ECS just before any registration is needed and skip the EC2 step A as you say; the api-v3 rebuild would use DDP_CORE_SHA=67f307abc2d660d9eba9e637f0c333a90a431707, tag pre-v65, and the drift gate.
