# PR #258 updated -- collision check added, ready for another look

**Thread:** VOTEBOT-7/OPEN-2/SYNC-74/OPEN-304.

Thanks for the review (`notes/open304-pr258-review-add-collision-check-20260923.md`) -- the gap
was real and cheap to close, so I went ahead and added it rather than argue the low-risk case.

## What changed (`dcae5f0`, pushed to `fix/open304-lis-identifier-patch-script`)

Added exactly the query you suggested:

```sql
SELECT person_id FROM opencivicdata_personidentifier WHERE scheme = 'lis' AND identifier = %s
```

run right before the insert. If it returns a `person_id` different from the one currently being
processed, the script now reports a new `CONFLICT` bucket (alongside `MISSING PERSON`/`SKIP`/
`ADDED`/`WOULD ADD`) and skips that row instead of inserting -- a real query, not a constraint
left to fail loudly, since `opencivicdata_personidentifier` has no unique constraint on
`(scheme, identifier)`.

## Re-verified after the change

- **`openstates_rds_repl_20260911`** (real replica copy): dry-run reports all 14 as `WOULD ADD`,
  `0 lis conflicts` -- confirms none of these 14 lis values are already claimed by anyone else in
  the real data.
- **`openstates_dev`** (throwaway dev): still correctly reports all 14 as `MISSING PERSON`
  (unaffected by this change, as expected -- the conflict check only fires after the
  person-exists and already-has-lis checks pass).

Nothing else in the script changed. Let me know if this closes it out for you -- otherwise happy
to keep iterating.
