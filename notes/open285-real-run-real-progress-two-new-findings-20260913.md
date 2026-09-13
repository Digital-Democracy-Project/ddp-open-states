# OPEN-285: real triggered run, real progress (5/9 clean, up from 0/9), two new findings -- not closeable yet

Confirmed PR #144/#145/#146/#149 are all deployed on this host (`git log` at `781c666`).
Triggered `openstates_people_refresh` for real via `POST /trigger/openstates-scrape/people`.

**Real progress**: 5 of 9 states (wa, us, va, mi, ma) now complete cleanly -- the first time
this job has ever gotten that far on this host. The venv fix (#252), exit-code fix (#252), and
both DATABASE_URL fixes (#145/#146) are all confirmed genuinely working together for the first
time.

**But 4 states (fl, ut, az, al) still fail, for two distinct, precisely-diagnosed reasons --
not the same bug repeating:**

**1. fl/ut/al: `os-people`'s own "N went missing, run with --purge to remove" safety gate.**
Ran the script by hand to get full stderr (the wrapper's `stderr_tail` capture came back empty
in the Redis flow-status -- worth a look separately, minor). This is NOT a bug -- `os-people
to-database` deliberately refuses to delete a person no longer present in the source YAML
unless `--purge` is passed, a real confirmation gate. **This is a policy question, not a code
fix**: should the scheduled job pass `--purge` (accepting automatic deletion of legitimately
-removed people), or should "went missing" be treated as a non-fatal warning that doesn't fail
the whole run? Given this job has never once completed successfully before today, this
"went missing" list may just be accumulated backlog from six-plus never-finished attempts --
plausibly shrinks a lot (or clears entirely) after one confirmed `--purge` catch-up run. Not
deciding this myself -- deleting person rows, even legitimately-gone ones, needs a real
go-ahead.

**2. az: a genuinely missing RDS table.** Real traceback:
```
psycopg2.errors.UndefinedTable: relation "people_admin_unmatchedname" does not exist
```
Hit specifically because AZ's run included a real person-merge event ("13 removed via merge").
Traced the source: `openstates-core`'s own `openstates/cli/people.py` (`to_database`'s merge
path) runs raw SQL directly against three tables --
`people_admin_unmatchedname`/`people_admin_persondelta`/`people_admin_personretirement` --
**none of which are defined anywhere in the `openstates-core` checkout itself** (no model, no
migration -- just raw SQL assuming they exist). Confirmed directly against RDS
(`information_schema.tables`, no schema restriction): **all three are absent from the
`openstates` database entirely.** These look like they belong to a separate legacy Django admin
app that ran alongside the original on-prem openstates Postgres, never carried over when RDS
was stood up (OPEN-269) -- since [[open280_full_schema_replication]]'s own 48-table audit never
mentioned them either, this predates even that. Whoever owns the source for this legacy admin
app needs to find its real schema and create these three tables on RDS (or decide the merge
path shouldn't attempt this on RDS at all, if this bookkeeping is no longer meaningful post-
migration) -- flagging, not fixing, since it's schema-shaped and outside what I should DDL
unilaterally without knowing the correct source-of-truth schema.

**Net: closer than before, but not closeable.** Three real items left, not one:
1. Decide the `--purge` policy for fl/ut/al (and possibly do one confirmed catch-up run).
2. Create (or otherwise resolve) the three missing `people_admin_*` tables for az (and any
   other jurisdiction with pending merges).
3. IAM EventBridge/Scheduler visibility (`events:ListRules`/`scheduler:ListSchedules`) --
   re-confirmed still `AccessDenied` on this host's role, unchanged.

Ramon asked directly what's left to close this ticket -- gave him this same breakdown.
