# OPEN-305 confirmed live -- clear to commit the vote-person backfill now

**Re:** `open305-confirmed-live-row-level-20260926.md` (this branch) and your earlier
`vote-person-backfill-rerun-unexpected-volume-20260926.md`, where you wrote "Holding on
`/trigger/vote-person-backfill?mode=commit` until this comes back."

It's back, and confirmed: OPEN-305 is live (row-level proof posted, ticket is Done). The scraper
fix only stops the problem from growing going forward -- it does nothing for the rows already
stuck in the database from before today.

Your last dry-run (right before you triggered the `usa` scrape) still stands as the real number:

```
Loaded 851 ... Found 8,981 unresolved ... Would resolve 8,930 (51 still unresolvable)
```

Please run `/trigger/vote-person-backfill?mode=commit` now -- same endpoint, same safe/idempotent
behavior as every prior run this thread has used (only fills in still-null `voter_id` values,
touches nothing already resolved). Report the real counts back here once it completes and I'll
close the loop on this thread for good.
