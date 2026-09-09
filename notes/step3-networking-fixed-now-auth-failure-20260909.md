# Networking is fixed -- third run reaches RDS, but auth fails

*Replies to `notes/rds-still-unreachable-egress-gap-found-20260909.md`.* Egress rule confirmed
live on `sg-09346518873d48a08` (TCP 5432 -> `sg-08ece6ced1406e4a8`, description "Allowing
Fargate access for ddp-scraper/archiver tasks"). Re-ran again, fresh RUN_ID
`ut-archive-d431aa2c03e6`.

## Good news: networking is confirmed fixed

Task ran for **1 second** this time (vs. the previous two runs' 130-second connection timeouts)
and got a real Postgres-level response instead of a network timeout. Both SG fixes together
(ingress on `sg-08ece6ced1406e4a8`, egress on `sg-09346518873d48a08`) are correct and sufficient
for reachability.

## New failure: authentication, not networking

```
psycopg2.OperationalError: connection to server at "ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com"
(172.31.97.157), port 5432 failed: FATAL:  password authentication failed for user "openstates_admin"
connection to server at "..." failed: FATAL:  no pg_hba.conf entry for host "172.31.4.250",
user "openstates_admin", database "openstates", no encryption
```

The `DATABASE_URL` this task used came straight from this host's `/opt/ddp-sync/.env`
`RDS_DATABASE_URL` — the same one the RDS backfill dry-runs used successfully just today, so it
was valid at least as of those runs. Worth checking whether the RDS master password has rotated
since then (there's a real precedent for this — `deploy/rotate-database-url.sh`, OPEN-193,
2026-09-02) without this host's `.env` being re-rendered, or whether there's something specific
to how `cloud_archiver.py`'s Fargate container receives/parses this env var differently than the
bare-host CLI tool does. Not investigating the credential itself further from here.

## Status

Image, task-def, dispatch, and now networking are all confirmed correct. This is purely a
credential-freshness or plumbing question at this point. Once resolved, same re-run recipe as
before — fresh RUN_ID, task-def `ddp-scrapers:19`, `ut`.
