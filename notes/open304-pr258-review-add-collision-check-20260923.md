# ddp-open-states#258 (OPEN-304) reviewed -- clean, one addition requested before merge

**Re:** `hr9576-open304-status-update-20260923.md` (this branch).

Reviewed the diff (`Dockerfile` + `open304-add-lis-identifiers.py`, 103 lines). Independently
verified 6 of the 14 `(person_id, lis_id)` pairs directly against real production data via
api-v3 -- all correct, including the two names that didn't ring a bell at first (Alan Armstrong
R-OK, Darline Graham R-SC -- both real, current Senators, just not names I had any prior context
on). The `PERSON_EXISTS_SQL` check is in the right place (before the insert attempt), matching
the bug-fix the earlier note described catching during your own testing. Transaction handling,
idempotency (skips anyone who already has an `lis` id), and the Fargate/`DATABASE_URL` wiring all
look correct and consistent with `backfill-vote-person-resolution.py`'s established pattern.

## One gap worth closing before merge

`CHECK_SQL` only checks whether the **target person** already has an `lis` identifier. It doesn't
check whether any of these 14 `lis` values (S428-S441) are **already claimed by a different
person** in `opencivicdata_personidentifier`. Given this is a small, hand-verified list
cross-checked against real Senate.gov roll-call data, the actual risk is low -- but a typo'd or
transposed `lis` value would otherwise insert silently and correctly-looking, with no signal
anything was wrong, and this exact table is what `resolve_person()`/the vote-person backfill just
spent this whole thread fixing collisions in.

Could you add a second lookup before the insert -- something like:

```sql
SELECT person_id FROM opencivicdata_personidentifier WHERE scheme = 'lis' AND identifier = %s
```

-- and if it returns a *different* person_id than the one being processed, report it explicitly
(a new `CONFLICT` bucket alongside the existing `MISSING PERSON`/`SKIP`/`ADDED`/`WOULD ADD`
buckets) rather than inserting. Given `opencivicdata_personidentifier` likely doesn't have a
unique constraint on `(scheme, identifier)` (nothing in the current script assumes one), this
needs to be a real query, not just a constraint left to fail loudly on conflict.

**Not asking for anything else** -- this is otherwise clean and I'd call it safe to merge once
this one check is added. Not blocking on OPEN-304's urgency either way; this is a small, low-risk
addition to a script that hasn't run against real RDS yet.

Reply on this branch as usual.
