# OPEN-285: two of the three remaining items are now closed by Ramon's direct decision; one real item left

Ran both open questions from my last note past Ramon directly.

**1. The `--purge` policy for fl/ut/al: closed, no purge.** Ramon's answer: no compelling
reason to delete anyone, and he wasn't clear why this was even being asked. To be clear on my
end -- nobody requested a purge as a goal; it's just the fork `os-people to-database` presents
whenever it finds a person removed from the source YAML. Given his answer, we're leaving it:
those three states simply won't report a fully-clean weekly refresh going forward, and that's
an accepted, stable state, not something to keep chasing. Not a bug -- closing this thread.

**2. IAM EventBridge/Scheduler visibility: closed, no IAM grant needed.** Asked Ramon directly
whether AWS-native scheduling (EventBridge / EventBridge Scheduler) might be running any of
these jobs in parallel without our knowledge. He confirmed directly he wasn't even aware AWS
has its own scheduler and can guarantee it isn't in use. That's a real, direct answer to the
"or otherwise confirmed some other way" alternative your own status-check note offered --
treating this as settled, not pursuing the IAM grant.

**3. Still open, and now the only remaining item: the three missing `people_admin_*` tables
that block AZ (and any other jurisdiction that hits a real person-merge).** Ramon's direct ask:
**could you check what's on the Mac for these** -- `people_admin_unmatchedname`,
`people_admin_persondelta`, `people_admin_personretirement`. These aren't defined anywhere in
the `openstates-core` checkout itself (no model, no migration -- `people.py`'s merge path just
runs raw SQL assuming they exist), and they're confirmed absent from RDS's `openstates` schema
entirely (checked `information_schema.tables`, no schema restriction). My working theory is
these belong to a legacy Django admin app that ran alongside the Mac's original on-prem
Postgres and never got carried over when RDS was stood up (OPEN-269) -- but I have no way to
check the Mac's own database schema from here. If the Mac's `openstates` Postgres still has
these three tables, could you pull their real `CREATE TABLE` definitions (`pg_dump --schema-
only -t people_admin_unmatchedname -t people_admin_persondelta -t people_admin_personretirement`
or equivalent) so we can create the matching tables on RDS? If they're not on the Mac either,
that's useful too -- would mean tracking down an even older source, or deciding the merge path
shouldn't attempt this against RDS at all.

With items 1 and 2 closed, this is the only thing left standing between OPEN-285 and being
closeable.
