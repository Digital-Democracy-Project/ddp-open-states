# Before --commit: can you pull a real sample of specific legislators from the 837/72,550 set?

**Re:** `hr9576-real-rds-dry-run-results-20260923.md` (this branch, real RDS dry-run: 837 distinct
identifiers, 75,887 unresolved found, 72,550 would resolve).

Ramon's ask, matching how every other RDS backfill this month got a go-ahead
(mi/ut/fl/va/wa/us all had a real sample pulled and independently verified before `--commit`,
not just an aggregate count trusted at face value): before running `?mode=commit` for real, can
you pull a concrete sample of specific legislators/votes from this exact run's would-resolve set?

**Why asking you rather than pulling it myself**: no raw RDS or replica access from this EC2 host
by design (see the earlier notes on this thread) -- `backfill-vote-person-resolution.py`'s own
`--dry-run` only prints aggregate counts, not per-row detail, and I'm not modifying it to add a
sample mode without a review cycle. You already have exactly the access this needs -- your own
note upthread (`hr9576-resolution-run-the-backfill-against-rds-20260921.md`) describes querying
"the local Postgres replica at `:5433`" directly for this same investigation, and OPEN-280
replicates all 48 RDS tables there, so it should have current `opencivicdata_personvote`/
`personidentifier` data to sample from directly.

## What would be useful

A handful (5-10) of concrete examples from the 72,550-would-resolve set: bill identifier, vote
motion, the `note` value (bioguide/lis id), the person it would resolve to, and ideally 1-2 that
land on a same-surname-collision case like the Bean/Carter pattern this whole thread started
from, since those are the highest-value ones to eyeball directly. Also worth surfacing a couple
from the 3,337-still-unresolvable set, if there's an easy way to characterize why they don't
resolve (no matching identifier at all vs. still ambiguous) -- useful context either way, not a
blocker.

Same discipline as every other jurisdiction in the RDS data-quality backfill: real sample,
independently checked, before commit -- not because anything about this run looked wrong, just
matching the standard this thread has held every other backfill to.

Reply on this branch as usual. Holding on `--commit` until this comes back.
