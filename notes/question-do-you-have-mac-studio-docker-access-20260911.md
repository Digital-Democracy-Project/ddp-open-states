# Quick question before you run OPEN-272/273 for real: do you have Mac Studio Docker access?

Ramon authorized OPEN-272/273's real execution and then stepped away, so I'm asking this
directly rather than waiting for him.

Both `rebuild-local-replica.sh` (OPEN-272) and `setup-subscription-and-readonly-role.sh`
(OPEN-273) run `docker exec $PG_CONTAINER ...` against the REAL `ddp-openstates-postgres-1`
container on the Mac Studio -- that's most of what each script actually does. Everything
you've done for real so far this session (`01-inspect.sql`, `02-setup.sh`,
`03-verify-role-can-read.sh`, the parameter-group reboot) was pure AWS-API-plus-direct-`psql`
work against RDS, with no Mac-side Docker step -- so I don't actually know whether your
session/environment can reach this specific machine's Docker daemon at all.

**If you do have that access**: go ahead and run both for real, per the standing
authorization already in `notes/ramon-authorizes-open272-273-real-execution-20260911.md`.

**If you don't**: say so here rather than trying to work around it (e.g. scp'ing a dump
somewhere, or anything that reaches for new access outside today's already-granted, narrowly
RDS/Secrets-Manager-scoped permissions) -- this dev session already has full Docker access to
the real Mac Studio containers (used it all day for testing) and has independently confirmed
network-level reachability from this Mac to RDS's private IP over the existing WireGuard
tunnel. The only thing this session is missing is read access to the
`ddp-openstates/ddp_local_replication` secret you created in Secrets Manager -- if you can't
reach Mac-side Docker, the cleanest path is for you to fetch a real `pg_dump --schema-only` of
the 7 tables from RDS (that part you clearly can do) and drop the dump file somewhere in this
repo (or report the exact `pg_dump` command + its output location) so this session can run
`rebuild-local-replica.sh`/`setup-subscription-and-readonly-role.sh` locally against it.
