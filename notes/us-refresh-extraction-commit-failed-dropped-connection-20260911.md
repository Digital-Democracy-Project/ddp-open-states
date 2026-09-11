# us refresh-extraction --commit FAILED -- dropped DB connection, ~4.5h in

The `us refresh-extraction --commit` I'd flagged as suspiciously silent (2+ hours with no
new CloudWatch log line, no active DB connection when I checked `pg_stat_activity`
directly) has now confirmed failed for real: `exit_code=1` after `duration_seconds=16197.8`
(~4.5 hours).

## Real error, pulled directly from CloudWatch (not the truncated ddp-sync capture)

```
django.db.utils.OperationalError: server closed the connection unexpectedly
```

Hit inside `refresh_extraction()`'s per-bill loop, `text_extract.py:2688`
(`for doc in bill.version_documents.all():` -- a lazy Django queryset fetch). My earlier
`pg_stat_activity` check finding no active connection from this task was accurate evidence,
not a false alarm -- the connection had already been dropped by the DB server side by the
time I looked, well before the process itself finally gave up and exited.

**This is the same failure mode as the earlier "SYNC-58" crash** from the original OPEN-192
Fargate validation thread (also `us`, also a lazy Django FK/queryset load, also
`server closed the connection unexpectedly`) -- a recurring, unhandled connection-drop bug
that specifically surfaces on very long-running jobs against `us`'s scale (37,672+ bills).
Whatever caused the earlier one apparently wasn't actually fixed, or this is a distinct
recurrence of the same underlying gap (no reconnection/retry logic for a dropped
long-lived DB connection during a multi-hour batch job).

## What I did, and didn't do

- **Did not retry blindly.** `refresh_extraction()`'s own docstring says it's idempotent
  ("a second run finds nothing stale and rewrites nothing") and it commits bill-by-bill, not
  in one giant transaction -- so a mid-run crash shouldn't have corrupted anything, just left
  it partially done. Launched a fresh `refresh-extraction us --dry-run`
  (`run_id=us-refresh-extraction-dry-run-c7347f8ed481`) to see the actual current remaining
  stale count before deciding whether to just re-run the commit.
- Not investigating the connection-drop root cause myself (RDS-side timeout setting? no
  Django `CONN_MAX_AGE`/keepalive handling? a network blip coinciding with something else on
  this host?) -- flagging for whoever owns that reconnection-handling gap, since it's now
  confirmed to have recurred at least twice on this exact jurisdiction.

Will report the dry-run's current stale count once it lands (expect another multi-hour
run given `us`'s scale, dry-run or not) and whether to proceed with re-running the commit.
