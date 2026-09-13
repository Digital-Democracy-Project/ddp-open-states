# OPEN-285: real code fix for the purge gate and AZ schema crash

Per Ramon's direct instruction ("no reason to ever purge data, remove that expectation from the
code"), shipped the actual fix rather than leaving this as a standing manual decision:

**`openstates-core` PR #46**: https://github.com/Digital-Democracy-Project/openstates-core/pull/46

- `os-people to-database` no longer fails the run or requires `--purge` when a person is absent
  from source data -- always a warning now, never a deletion. `--purge` removed entirely
  (fl/ut/al's failure mode).
- Also fixes AZ's crash: the person-merge path ran raw SQL against three tables
  (`people_admin_unmatchedname`/`persondelta`/`personretirement`) confirmed absent from every
  DDP Postgres (checked the Mac's pre-migration DB, its dev DB, and the RDS replica directly).
  These belong to upstream openstates.org's own SaaS-only admin app, never installed by this
  fork -- not a migration gap, dead code for DDP. Removed.
- pm-reviewed (2 rounds): added a real DB-backed merge-path regression test that reproduces
  AZ's exact crash scenario, a CLI-level test confirming `--purge` is rejected publicly, fixed
  an imprecise comment. Verified via grep across `ddp-open-states`/`ddp-open-states-dev`/
  `ddp-sync-dev` that nothing passes `--purge` today, so nothing breaks. Full suite: 721 passed.

Not merging myself -- over to you or Ramon, same as everything else today.

Once this deploys (needs `openstates-core`'s own image rebuild, same as PR #146's people-refresh
fixes did), a re-triggered `openstates_people_refresh` should get all 9 states clean for the
first time. That plus the IAM item (now closed, per Ramon) means the only remaining piece is
confirming that clean run for real.
