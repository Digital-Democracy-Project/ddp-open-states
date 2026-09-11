# Local (Mac-side) scripts for LegBot's RDS logical replication

Part of the [OPEN-269](https://digitaldemocracyproject.atlassian.net/browse/OPEN-269) epic,
building `PLAN-rds-local-postgres-replication.md`. These scripts run ON the Mac Studio (unlike
`ops/postgres-replica/rds/`, which needs RDS admin access this session doesn't have).

## `network-check.sh` (OPEN-270)

Confirms the Mac's real network path to RDS. Read-only, no side effects. See
`ops/postgres-replica/NETWORK-PATH-CONFIRMED-OPEN-270.md` for the findings this produced.

## `rebuild-local-replica.sh` (OPEN-272)

Builds a fresh local Postgres database from an RDS schema-only dump, alongside the existing
`openstates` database (does not touch it), and confirms `api-v3` can start against the new
schema. **Does not** repoint the real `ddp-openstates-api-1` container or touch the existing
database — see the script's own header for exactly what it stops short of and why.

```bash
./rebuild-local-replica.sh <schema-only-dump.sql> <new-database-name>
```

The schema-only dump must come from RDS (`pg_dump --schema-only` against the 7 tables, per
`ops/postgres-replica/rds/`, run by whoever has RDS access) — this script doesn't fetch it.

**Real findings from actually running this** (not just reading the plan's SQL):

- `opencivicdata_jurisdiction` has a foreign key to `opencivicdata_division`, a table outside
  this plan's 7-table scope (§3.2) — a schema-only dump of just the 7 tables fails to apply that
  one constraint. The script strips that specific constraint (confirmed to be the only statement
  referencing that table) before applying the rest; `division_id` remains a normal, readable
  column, just without FK enforcement against a table this replica doesn't carry. This is exactly
  the kind of gap the plan's own §7.4 flagged as a risk ("a `-t`-scoped dump can still reference
  an object outside the named tables... the restore step itself is the real test") — confirmed
  real, not hypothetical, by actually running it once and fixing what broke.
- The plan's own full api-v3 smoke test (`curl .../bills/<id>?include=versions`, checking for
  real `raw_text`) **cannot run at this stage** — it needs real bill data, which doesn't exist
  until OPEN-273's subscription completes its initial copy, and every api-v3 route that touches
  data (confirmed by reading `api-v3/api/jurisdictions.py`/`auth.py`) requires an API key checked
  against a `Profile` table that isn't one of the 7 replicated tables at all and has zero rows
  regardless — there's no unauthenticated route to route around this through. The full
  data-bearing smoke test is OPEN-273's job, once real data exists.

**Correction from pm-review round 1**: the original version claimed the api-v3 container-startup
check "catches an ORM/schema mismatch." It doesn't — `/openapi.json` is generated from route and
model definitions and doesn't require a database connection (confirmed by reading
`api-v3/api/main.py`), so a successful response only proves the container started, not that the
schema actually works. Since there's no unauthenticated HTTP route that touches real data, the
real schema-compatibility check is now a set of direct SQL queries against all 7 tables (plus a
check that the filtered FK constraint is genuinely gone) — the container-startup check is kept,
but now described honestly as just that.

Also fixed from round 1: the FK-constraint filter was anchored to the exact known
`ALTER TABLE ... FOREIGN KEY (division_id) REFERENCES ... opencivicdata_division` statement shape
(not a broad "any statement mentioning this table name" match, which could have silently
swallowed something unrelated); the database name is now validated as a safe identifier before
use; the schema-only dump path no longer gets interpolated into a Python source string; the
existence check distinguishes a real query failure from "database doesn't exist"; the schema is
now filtered and validated *before* the database is created, so a filtering problem leaves
nothing behind; and the smoke-test container no longer uses `--rm`, so a crash's logs are still
collectable before cleanup removes it.

Tested end-to-end against a schema-only dump of the Mac's own current `openstates` database
(same 7 tables, real data/schema shape) as a stand-in for an RDS dump — a temporary test
database and a temporary `api-v3` container, both cleaned up afterward, nothing in the real
`openstates` database or the real `ddp-openstates-api-1` container touched. Also verified the
database-name validation rejects an unsafe name before touching anything.
