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

## `replica-status.sh` (OPEN-274)

The health-check script (plan §7.6) — a small CLI check, not a service. Reports subscription
status, LSN-based apply lag (not just message-receipt time), retained WAL, and an overall
HEALTHY/LAGGING/DISCONNECTED/BROKEN status, then registers with `cams status`'s existing
generic background-jobs display (the `cams:background_jobs` Redis hash) — written directly via
`redis-cli`, matching the exact JSON schema `ddp-agents/src/cams/background_jobs.py`'s own
`report_heartbeat()` helper uses, without a cross-repo Python import (this script lives in
`ddp-open-states-dev`, that module lives in `ddp-agents(-dev)`) — no new `cams status` display
code needed, per that mechanism's own "any job reporting a heartbeat there shows up automatically"
design.

```bash
RDS_MONITORING_DATABASE_URL=<resolved live, e.g. via resolve_rds_database_url()> \
  ./replica-status.sh <database-name>
```

**Tested all four local-side status paths for real**, using a fully isolated Docker loopback
(same pattern as OPEN-273): HEALTHY (subscription enabled, active apply worker), DISCONNECTED via
a disabled subscription, DISCONNECTED via an unreachable publisher (active subscription, no apply
worker), and BROKEN (local Postgres container down). Also verified the `cams status` heartbeat
write/read round-trip against the real `ddp-agents-redis-1` container (under a clearly-named test
job, deleted immediately after) and that `started_at` persists correctly across repeated
invocations rather than resetting on every run, matching `report_heartbeat()`'s own semantics
exactly.

**The RDS-side portion (retained WAL, apply lag from RDS's own `pg_replication_slots`) is
documented but not exercised from this session** — it needs a resolved RDS monitoring credential
this session doesn't have (same constraint as everywhere else in this epic that touches RDS
directly). The script degrades to a local-only `HEALTHY (local-only, ...)` status when
`RDS_MONITORING_DATABASE_URL` isn't set, rather than silently claiming a check it didn't perform.

## `drop-subscription-for-rebuild.sh` (OPEN-274) — the rebuild/recovery procedure, exercised

Covers plan §7.8's "the only recovery path is rebuild, never repair in place": drops the local
subscription, handling both the reachable-publisher case (drops the remote RDS slot automatically)
and the unreachable-publisher case (detaches locally without touching a slot it can't reach).
Re-running `rebuild-local-replica.sh` (OPEN-272) and `setup-subscription-and-readonly-role.sh`
(OPEN-273) against a fresh database completes the cycle — both already independently tested with
real execution in their own tickets, not re-duplicated here.

**Actually exercised this drill, not just written it** — using a fresh Docker loopback: tested the
reachable-publisher path (confirmed the remote slot really is dropped automatically) and the
unreachable-publisher path (stopped the "RDS" container mid-subscription, confirmed the local
subscription detaches cleanly without hanging).

**A real bug found only by exercising this, not by reading the plan's own §7.8 text**: killing the
publisher *during* the initial copy (not just after it) can leave behind an additional
per-table **temporary tablesync slot** (named like `pg_<oid>_sync_<relid>_<random>`, distinct
from the main `ddp_legbot_subscription` slot) that a recovery check for only the main slot name
would miss entirely — confirmed by triggering exactly this scenario and finding the orphaned slot
still present after cleanup. Fixed: the script's RDS-side cleanup guidance now checks for both the
named subscription slot and any `pg_%_sync_%` pattern match, not just the former.

**Correction from pm-review round 1, both confirmed real by actually exercising the script again
(not just reading the diff)**:

- The round-1 fix bounded the primary reachable-publisher `DROP SUBSCRIPTION` with
  `SET statement_timeout = '15s'` — but combining `SET statement_timeout = ...; DROP SUBSCRIPTION
  ...;` in one `-c "..."` string fails outright with `ERROR: DROP SUBSCRIPTION cannot run inside a
  transaction block`, because a multi-statement string passed to one `-c` is sent as a single
  simple-query message and Postgres wraps it in an implicit transaction. Fixed by passing `SET
  statement_timeout` and `DROP SUBSCRIPTION` as two separate `-c` flags on the same `psql`
  invocation — confirmed a `SET` from one `-c` flag persists to a later `-c` flag on the same
  connection, and confirmed the retimed `DROP` genuinely gets cancelled (not just documented) by
  pausing the simulated publisher and watching it fail with `canceling statement due to statement
  timeout` after ~15s instead of the earlier fix's untested claim.
- The unreachable-publisher fallback path (`DISABLE` → `slot_name = NONE` → `DROP SUBSCRIPTION`)
  had no timeout of its own and was not checked for failure at all (this script has no `set -e`).
  Testing it against a publisher that was paused (not just stopped) — simulating a genuinely hung
  connection rather than a clean refusal — showed `DISABLE` and the `slot_name` change both return
  instantly, but the final `DROP SUBSCRIPTION` still blocks waiting for the apply worker to
  actually exit, and a worker stuck retrying a hung connection can block that wait indefinitely,
  defeating the entire point of the "unreachable publisher" path. Confirmed a real, unbounded hang
  first (the script sat unresponsive for 99+ seconds until the test publisher was manually
  unpaused), then fixed by applying the same `statement_timeout` pattern to this block too, and by
  capturing its exit code explicitly so a real failure now prints `FAIL` with the actual partial
  state (`pg_subscription.subenabled`/`subslotname`) and exits 1, instead of silently falling
  through to a `PASS` message regardless of what happened. Re-tested end to end: the hung-worker
  case now fails cleanly within ~30s (both timeouts combined) instead of hanging, and a follow-up
  retry after the publisher becomes reachable again completes normally and still re-confirms the
  orphaned-tablesync-slot cleanup guidance above.
