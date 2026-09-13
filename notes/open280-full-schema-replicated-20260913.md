# OPEN-280: full RDS schema now replicated, real DDL done

With Ramon's explicit go-ahead. Confirmed I had sufficient privileges first (`openstates_admin`
is the publication's own owner; a test `GRANT` in a rolled-back transaction succeeded) before
doing anything for real.

**Real numbers**: 48 total tables in RDS's `openstates` public schema; only 7 were in
`ddp_legbot_publication` before this. Checked REPLICA IDENTITY for all 41 remaining tables
first -- every one already has a real primary key (`relreplident='d'`, default/PK-based), so
no OPEN-277-style remediation was needed anywhere.

**Done, in the correct order** (GRANT before ALTER PUBLICATION, per your own crash-loop
warning):
1. `GRANT SELECT ON public.<table> TO ddp_local_replication;` for all 41 remaining tables --
   all 41 succeeded.
2. `ALTER PUBLICATION ddp_legbot_publication ADD TABLE <all 41, one statement>;` -- succeeded.

**Verified, not just assumed clean:**
- `pg_publication_tables` now shows exactly 48 rows for `ddp_legbot_publication`, and a
  `pg_tables` diff against it returns zero rows -- full schema, no mismatch either direction.
- `information_schema.role_table_grants` confirms `ddp_local_replication` has real `SELECT` on
  all 48 tables now, not just publication membership.

Included all 41 -- the Django/pupa internal bookkeeping tables (`django_content_type`,
`django_migrations`, `bulk_dataexport`, `pupa_*`) too, per Ramon's explicit "go ahead with all
41" after I flagged that distinction.

Your side: `ALTER SUBSCRIPTION ddp_legbot_subscription REFRESH PUBLICATION;` on the Mac,
whenever you're ready -- this end is fully done and verified. Also: your OPEN-280 note
mentioned this should let the cross-scope `DROP CONSTRAINT` FK work (jurisdiction.division_id,
membership.post_id, voteevent.bill_action_id) become unnecessary now that every table those
FKs point to is in scope too -- I didn't check that part myself (it's schema/constraint logic
on your replica, not something I can verify from the RDS side), your call to confirm once you
refresh.
