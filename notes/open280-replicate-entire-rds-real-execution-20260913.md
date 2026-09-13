# OPEN-280: replicate the ENTIRE RDS schema for real -- Ramon's direct instruction

Correcting course. Ramon's actual instruction (2026-09-12/13, restated directly just now):
replicate the **entire** RDS schema to the Mac -- not the curated 7/12-table subset OPEN-280's
merged PR (#249) only documented and verified in a throwaway Docker loopback. That PR was
explicit that the real execution was never done ("blocked on RDS admin access, out of scope
for this PR") -- this note is asking you to actually do it, since you have real RDS access
this session and I don't.

**Why this matters right now, concretely**: running OPEN-191's Tier 1/2 quality checks against
the Mac's replica just hit a real wall -- `opencivicdata_billsponsorship` doesn't exist in the
replica at all (confirmed directly, `\dt` only shows 8 tables: `opencivicdata_bill`,
`_billversion`, `_billversionlink`, `_jurisdiction`, `_legislativesession`, `_organization`,
`ddp_bill_version_document`, plus the one-time `profiles_profile` snapshot). That table was
never even in scope for OPEN-280's own proposed 5-table addition (person/personidentifier/
membership/personvote/voteevent) -- it's a different gap entirely. Going to the full schema
closes this and every future one like it in one pass, instead of discovering missing tables
one at a time forever.

## What I need from you

1. **Get the real, complete table list** from the actual RDS `openstates` database (not
   assumed from any doc): `\dt public.*` or `select tablename from pg_tables where
   schemaname='public';` against RDS directly.
2. **For every table not already in scope** (the 8 above are already replicating -- don't
   touch those), on the RDS side:
   - `GRANT SELECT ON public.<table> TO ddp_local_replication;` for each one -- **before**
     adding it to the publication, not after (OPEN-277's crash-loop gotcha: a table added to
     the publication without SELECT already granted crash-loops the tablesync worker
     indefinitely, not just once).
   - `ALTER PUBLICATION ddp_legbot_publication ADD TABLE <all the new tables, comma-separated>;`
3. **One real simplification going to full schema instead of a curated subset**: none of the
   cross-scope FK `DROP CONSTRAINT` work OPEN-280's own README documented (for
   `jurisdiction.division_id`, `membership.post_id`, `voteevent.bill_action_id`) should be
   needed anymore -- every table those FKs point to will now be in scope too. Worth confirming
   this once you're doing it for real, not just assuming my reasoning holds.

Once you've done the RDS-side GRANT/ALTER PUBLICATION work, let me know and I'll run
`ALTER SUBSCRIPTION ddp_legbot_subscription REFRESH PUBLICATION;` on the Mac side myself and
verify the new tables actually sync (row counts + a real content spot-check, same discipline
this epic's earlier work already established) -- that half doesn't need your access, just
needs the RDS side done first.

If you don't have sufficient privileges on the real RDS instance to run `GRANT`/`ALTER
PUBLICATION` yourself (as opposed to just being able to query it), say so plainly rather than
guessing -- that's Ramon's own action to take directly, not something to work around.
