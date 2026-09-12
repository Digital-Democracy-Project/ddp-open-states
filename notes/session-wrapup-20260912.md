# Wrapping up for today -- OPEN-272/273 process gap found, please don't route through EC2

Ramon caught something important before I got further into OPEN-272/273 -- flagging it here
so it's not repeated next session.

## OPEN-272/273's `local/*` scripts are Mac-only, don't ask this EC2 host to run or stage anything for them

Before running `rebuild-local-replica.sh` or `setup-subscription-and-readonly-role.sh`
(per your standing-authorization note), I read both first and confirmed they hard-code
`PG_CONTAINER="ddp-openstates-postgres-1"` and reference `ddp-openstates-api:local` on
network `ddp-agents_default` -- your Mac's own Docker environment. Confirmed directly that
none of that exists on this EC2 host (`docker ps -a` here has no
`ddp-openstates-postgres-1` at all; this host's own `ddp-openstates-api-1` points straight
at RDS, a different topology). Correctly held off rather than trying to fabricate a
stand-in environment.

I'd started producing the one RDS-side artifact `rebuild-local-replica.sh`'s own docstring
says needs to come from here (`pg_dump --schema-only` of the 7 tables) to hand off to you --
Ramon stopped that specifically and said this EC2 host shouldn't be where a schema dump gets
staged or routed through at all, not just that the Mac-side scripts themselves can't run
here. I deleted the (schema-only, no data) dump file immediately.

**What this means going forward:** OPEN-272/273 need a different hand-off mechanism than
"EC2 produces an artifact, dev agent picks it up" -- Ramon and you should sort out directly
what that should be (maybe you get scoped RDS read access of your own for a one-time
`pg_dump`, maybe a different channel entirely). Not something I should guess at or
re-attempt on my own initiative next time this comes up.

## Still open from earlier today, for whenever this resumes

- **`us`'s `refresh-extraction --commit` retry**: the earlier attempt failed ~56% through
  (dropped DB connection, a recurrence of the old SYNC-58-style bug). Confirmed via a fresh
  dry-run that the completed ~56% survived cleanly (idempotent, per-bill transactions) --
  currently `bills_with_stale_docs=16560 stale_docs=20343 diffs_would_change=3118
  docs_skipped=0 docs_refused=0` remaining. Holding the retry for Ramon's explicit go-ahead,
  same discipline as every other jurisdiction this backfill.
- **OPEN-271 is fully closed** (role/publication/secret/RDS reboot all done and
  independently verified for real) -- nothing further needed there. PR #240 (the
  write-refusal script's pipefail bug) is confirmed correct and still just needs a merge
  whenever convenient.
- **IAM scope**: narrowed back down today per Ramon's request -- the RDS
  parameter-group/reboot and one-time secret-generation permissions are gone from this
  host's role now; only the ongoing scraper/archiver + read-only RDS-discovery permissions
  remain.

Session's ending here for today -- nothing currently running, no open background work, no
scheduled polling left active.
