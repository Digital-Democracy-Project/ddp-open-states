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

## `generate-readonly-role-secret.sh` and `setup-subscription-and-readonly-role.sh` (OPEN-273)

`generate-readonly-role-secret.sh` creates a Secrets Manager secret for `ddp_local_readonly`'s
password, mirroring `ops/postgres-replica/rds/00-generate-role-secret.sh`'s existing convention
for `ddp_local_replication` — run once by whoever has Secrets Manager access (not this session).

`setup-subscription-and-readonly-role.sh` fetches both secrets, creates the actual
`CREATE SUBSCRIPTION` against RDS and the local `ddp_local_readonly` role, waits for initial sync
(`pg_subscription_rel.srsubstate = 'r'` for all 7 *expected* tables specifically, not just a count
of 7), and verifies the read-only role can read all 7 tables and genuinely cannot write.

```bash
RDS_HOST=<rds-endpoint> RDS_CA_BUNDLE_PATH=<path to the RDS CA bundle> \
  ./setup-subscription-and-readonly-role.sh <new-database-name>
```

**Prerequisite, confirmed missing on this Mac**: the RDS CA bundle `sslmode=verify-full` needs.
AWS publishes it at `https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem` — fetch
it and pass its path as `RDS_CA_BUNDLE_PATH`. Neither this bundle nor an equivalent exists inside
`ddp-openstates-postgres-1` right now (checked directly) — this is a real prerequisite to fetch
before running for real, not assumed to already be there.

**Tested end-to-end against a real, fully isolated logical-replication loopback** — not just
syntax-checked. Since neither RDS nor the Mac's own local Postgres has `wal_level=logical`
enabled yet (RDS needs OPEN-271's still-pending parameter-group change + reboot; the Mac's real
`ddp-openstates-postgres-1` container wasn't restarted to test this, since it's the actual
container serving live `api-v3`/LegBot traffic), this was validated using two throwaway
`postgres:16-alpine` containers on a dedicated Docker network — one configured with
`wal_level=logical` as a stand-in "RDS", one as the "Mac" subscriber — both torn down afterward,
nothing in real infrastructure touched or restarted. This loopback test does not, and cannot,
validate the RDS CA bundle prerequisite above (`sslmode=disable` was substituted just for the
test containers, which don't have their own certificates configured); confirm that separately
against the real endpoint before trusting `verify-full` works there.

**Round 1 found several real bugs, all fixed and re-verified by re-running the full loopback:**

- **A race in the initial-sync wait loop.** The original version ran two *separate* queries (a
  not-ready count, then a total count) — if relations registered between the two queries, a
  transient state could misreport as "0 not ready, 7 total" before all 7 were genuinely ready.
  Fixed to a single query returning every expected table's exact state from one snapshot, and now
  checks the specific expected table *names*, not just a count of 7 (a count alone can't tell the
  right 7 tables from some other 7).
- **A silent timeout.** If sync never completed within the poll loop, the original version fell
  through to the later steps anyway and printed "initial sync is complete" regardless. Fixed to
  track completion explicitly and exit non-zero with the last observed state if the loop times out.
- **`default_transaction_read_only` is a session default, not the real security boundary** — a
  session can override it with `SET default_transaction_read_only = off`. The write-refusal check
  now runs twice: once relying on the session default (as before), and once after explicitly
  disabling it, to prove the underlying `GRANT`-level boundary (no INSERT/UPDATE/DELETE grant at
  all) holds even when the convenience default is bypassed. Both wrapped in an explicit
  transaction that's always rolled back, so an unexpected successful write wouldn't leave
  `__write_check_probe__` sitting in real replicated data.
- **The read-only role's read access was only verified against 1 of the 7 tables.** Now checks
  all 7.
- **No guard against a partial/repeat run.** Re-running against a database that already has the
  subscription or role produced a raw Postgres duplicate-object error. Now checked explicitly
  upfront, failing with guidance pointing at the plan's own "rebuild, never repair in place"
  recovery philosophy (§3.7) rather than trying to patch a partial state.
- **The readonly-role password was a positional shell argument** (visible in shell history and
  `ps` output) and the RDS-side password came from an env var instead of the same Secrets-Manager
  convention `ops/postgres-replica/rds/00-generate-role-secret.sh` already established. Both now
  fetched from Secrets Manager directly (via the new `generate-readonly-role-secret.sh` for the
  new role), matching that convention, plus a defense-in-depth check that neither fetched password
  contains a single quote before it's interpolated into SQL/conninfo strings.
- **A `pipefail` bug in the write-refusal check** (same root cause as the identical bug found and
  fixed in the already-merged `ops/postgres-replica/rds/03-verify-role-can-read.sh`, OPEN-271, in
  a separate follow-up PR): `psql -c "INSERT ..." | grep -q "..."` inside an `if` condition, with
  `set -o pipefail` active, reports the pipeline's exit status as whichever command failed last
  scanning right-to-left — since the INSERT is *expected* to fail, `psql` itself exits non-zero,
  and `pipefail` reports that even when `grep` had already found the expected message. Fixed by
  capturing output into a variable first, then grepping the variable.
- **An apostrophe inside a `${VAR:?message}` parameter-expansion message broke bash's parser**,
  even though the whole thing was double-quoted — a genuine, if obscure, bash quoting gotcha
  specific to `:?`/`:-`/`:=`/`:+` expansion words, only caught by actually running `bash -n`, not
  by reading the diff.

With all of those fixed, the loopback test confirmed the whole pipeline works as designed: initial
sync completed for all 7 expected tables (verified by name, not just count), a row present on the
"RDS" side before the subscription was created replicated correctly (`copy_data=true` initial
copy), a **new** row inserted on the "RDS" side *after* the subscription was live replicated
within seconds (confirming live/steady-state replication, not just the initial copy), the
read-only role could read all 7 tables, and both write-refusal checks (session-default and
post-override) passed. Also re-verified the pre-existing-object guard fails with the correct
guidance on a repeat run against an already-populated database.
