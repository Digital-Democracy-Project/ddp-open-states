# VOTEBOT-7/OPEN-2/SYNC-74: committed for real, closing out this thread

**Re:** the whole HR9576/vote-person-resolution thread on this branch. Ramon gave the go-ahead
after the corrected spot-check came back clean.

Confirmed nothing else in flight first (zero running ECS tasks, zero recent trigger activity),
then called `POST /ddp-sync/v1/trigger/vote-person-backfill?mode=commit`.

```
Loaded 837 distinct person identifiers.
Found 75,887 unresolved vote records with a usable note/identifier.
Done. Resolved 72,550 records (3,337 still unresolvable).
```

`run_id=vote-person-backfill-commit-8c05dc2f166b`, real Fargate task
`54cbb5d7cfe44b3e959a74e46bcb6148`, 186.6s runtime, exit 0. **Matches the dry-run exactly** --
same 837/75,887/72,550/3,337 -- no surprises between prediction and real write.

**72,550 previously-null `voter_id` rows in production `opencivicdata_personvote` now correctly
resolve to a real person**, including every Bean/Carter-shaped same-surname-collision case this
whole investigation started from. The remaining 3,337 are the already-characterized, separate,
out-of-scope gap (16 senators missing an `lis`-scheme `PersonIdentifier` entirely) -- would need
its own fix (populating those identifiers), not a defect in this backfill.

## Recap of the full chain, for anyone picking this up later

1. VOTEBOT-7 (HR9576 "Unknown" party votes) traced to `resolve_person()` never retrying on a
   later scrape of unchanged content -- a one-time-miss-sticks-forever gap, not a live bug.
2. `backfill-vote-person-resolution.py` (OPEN-2's original fix, 2026-07-26) already existed for
   exactly this, just needed wiring into a proper Fargate-triggered path instead of a manual
   Secrets-Manager-on-the-EC2-host workaround (`ddp-open-states`#257 + `ddp-sync`#164, both
   merged, both reviewed clean).
3. `ddp-sync` rebuilt/restarted on this EC2 host via the correct `systemctl restart ddp-sync`
   path (not the initially-suggested raw `docker compose --force-recreate`, which would have
   created a wrongly-named, port-colliding container).
4. Dry-run against real RDS: 75,887/72,550/3,337. Spot-check initially queried the wrong
   database on the replica server, corrected, re-verified as an exact match to real production.
5. Commit: done, matches the dry-run exactly.

Thread closed as far as this side is concerned. Any follow-up on the 16-senator missing-`lis`-id
gap is a separate, new piece of work if anyone wants to pick it up.
