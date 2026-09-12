# Re: us backfill status check, and a real access gap on OPEN-281

## us refresh-extraction --commit status (run_id=us-refresh-extraction-commit-300e99728ee3)

Still `RUNNING` as of 21:02 UTC (launched 18:35:47 UTC -- ~2h26m elapsed so far).

- ECS task status: `RUNNING`.
- CloudWatch log: fresh, last line within seconds of every check -- no gap suggesting a
  stall.
- `pg_stat_activity`: real, active connection from the task's own source IP throughout --
  no repeat of the earlier dropped-DB-connection crash
  (`django.db.utils.OperationalError: server closed the connection unexpectedly`).
- No live bill-count/percent-progress signal available -- this pipeline only logs
  "launched" and "done" (with duration), not incremental counts, so I can't give you a
  precise "X% through" number. For a rough ETA: the prior `us` dry-run for comparison
  (`run_id=us-refresh-extraction-dry-run-3a425dfea6b8`) took 14610s (~4h3m) end to end. If
  this commit run is similar, that points to a finish around ~22:39 UTC -- but the earlier
  commit attempt failed at ~56% before completing, so durations aren't directly comparable;
  treat this as a loose estimate, not a real ETA.

Will report the real final result (success or failure, pulled from CloudWatch directly, not
the truncated docker logs capture) as soon as it completes. Per Ramon's standing instruction,
if it fails again I will not retry automatically -- I'll report and hold for direction.

## OPEN-281: real access gap, need direction before I can act

I don't currently have any way to reach the `10.0.0.1` host from this EC2 box. Checked for
real before assuming otherwise (same discipline as the OPEN-272/273 Mac-only-scripts finding
earlier today):

- `10.0.0.1` is genuinely a different, distinct machine -- reachable over this host's own
  WireGuard tunnel (`ip route get 10.0.0.1` resolves via `wg0`, this host's own interface is
  `10.0.0.11`), not this same box under another name.
- No SSH config or prior `known_hosts` entry here for it, and a direct `ssh 10.0.0.1` attempt
  got `Permission denied (publickey)` -- this host's key isn't authorized there.
- This host's own `/opt/ddp-sync` (the `ddp-sync-ddp-sync-1` container I've been using all
  day for the `us` backfill) is a **separate deployment** from whatever `ddp-sync` instance
  OPEN-281 is describing on `10.0.0.1` (webflow/votebot) -- different purpose, different box.

I can't find/repoint/verify anything on `10.0.0.1` without either (a) SSH access to that host
from here, or (b) confirmation that this ticket is meant for a different session that already
has access to it. Please let me know which -- happy to pick this up the moment I have a real
way in, but I'm not going to guess at credentials or assume access that isn't there.
