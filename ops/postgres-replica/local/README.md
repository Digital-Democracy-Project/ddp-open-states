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

## `compare-schema.sh` (OPEN-277)

The schema-comparison script (plan §7.7). Compares, for exactly the 7 tables this plan's
publication carries (§3.2) — not a general schema-diff tool — whether the table exists on both
sides and whether its column name/type/nullability triples match. Compared keyed by **column
name** (not physical ordinal position, correction from pm-review round 1 — see below) via
`pg_attribute`/`format_type()`. Run manually after any Django migration touching these 7 tables
(§7.9's own procedure below), not on a schedule.

```bash
RDS_HOST=<rds-endpoint> RDS_REPLICATION_PASSWORD=<ddp_local_replication's password, from
  Secrets Manager — ops/postgres-replica/rds/00-generate-role-secret.sh> \
  ./compare-schema.sh <local-database-name>
```

Reuses the `ddp_local_replication` credential (§3.4 item 1) for this read — it already has
`SELECT` scoped to exactly these 7 tables (OPEN-271). Not a new credential. The password is
passed via `PGPASSWORD`, not embedded in the connection string, so it doesn't appear in this
process's own argv.

**Correction from pm-review round 1**: the original version compared columns by physical ordinal
position via `information_schema.columns`' `data_type`/`character_maximum_length` pair. Both were
real gaps: (a) Postgres logical replication itself matches columns by **name**, not position, so
two schemas with the same named columns in a different physical order — plausible if a table was
independently recreated at some point in either side's own history — replicate perfectly
correctly, but ordinal comparison would have falsely flagged that as a mismatch; (b) confirmed
against this schema's own actual array-typed columns (`opencivicdata_bill.classification`/
`subject`, both `text[]`) that `information_schema.columns`' type pair doesn't capture element
type or full precision the way `format_type(atttypid, atttypmod)` does in one string. Fixed by
comparing sorted-by-name `pg_attribute` rows using `format_type()`.

**Tested for real** (not just written): this Mac has no host-level `psql` binary, so the RDS-side
connection — like `replica-status.sh`'s own RDS-side portion (OPEN-274) — assumes a runtime where
`psql` is actually available, and isn't exercised directly from a bare shell on this Mac. Worked
around that gap for testing only (not a change to the script itself) with a small `psql` shim
that forwards to a throwaway container, letting the real script run genuinely end-to-end against
a Docker-simulated "RDS" (schema dumped from the real local `openstates` database, `pg_dump
--schema-only` against the same 7 tables, `ddp_local_replication` role created with the same
`SELECT` grants OPEN-271 documents) — confirmed, both before and after the round-1 fixes: all 7
tables PASS when schemas genuinely match (including correctly matching the real `text[]` columns
after the fix); a column-type change (`media_type varchar(100)` → `varchar(50)`) is correctly
caught as a column mismatch; a renamed table is correctly caught as "does not exist on RDS"; and a
real connection failure (a deliberate `sslmode=verify-full` mismatch against a test container with
no TLS configured) is correctly reported as FAIL with exit 1, not silently ignored. Real
infrastructure (`ddp-openstates-postgres-1`, `ddp-openstates-api-1`, `ddp-agents-redis-1`)
confirmed untouched throughout via `docker ps` and a row-count check on the real (not test)
`opencivicdata_billversionlink` table.

## Django migration procedure (OPEN-277, plan §7.9)

Not a script — a documented procedure for when a Django migration touches any of the 7 tables
this plan replicates. Logical replication does **not** propagate DDL, so RDS and the local
replica never automatically agree on schema after a migration; how to reconcile them depends on
the migration's own shape:

**Additive changes — a new column on an already-replicated table** (nullable or with a default):
**local FIRST, then RDS** — the reverse of the order the plan's own §7.9 text originally
specified, and a real bug in that text, not just a documentation nit. Confirmed via an actual
Docker logical-replication loopback (postgres:16, real `CREATE PUBLICATION`/`CREATE SUBSCRIPTION`,
not a read of the docs): adding a column to the *publisher* first and then writing a row that
populates it crashes the subscriber's apply worker in a loop —
`ERROR: logical replication target relation "public.t" is missing replicated column: "extra"` —
until the local (subscriber) side gets the same column. Postgres logical replication matches
columns by name, and a row sent for a column the subscriber doesn't have is a hard error, not a
tolerated no-op; the FK constraint/dump-ordering intuition that "additive means order doesn't
matter" does not hold here. The reverse order (subscriber ahead of publisher) is safe: the
subscriber tolerates extra local-only columns it was never sent a value for, filling them with
their own default. Corrected order:
1. Apply the equivalent schema change to the Mac's local replica FIRST (nullable or with a
   default — the same shape the RDS-side migration will have).
2. Apply the migration to RDS (whatever process OPEN-193's own load path already uses).
3. Run `compare-schema.sh` to confirm the two sides agree after the change.
4. Confirm the subscription is still healthy (`replica-status.sh`, OPEN-274).

**Additive changes — a brand-new table**: no ordering hazard the way a new column has (nothing is
replicating a table that doesn't exist locally yet, so there's no crash-loop risk regardless of
which side is created first) — but `ALTER PUBLICATION ... ADD TABLE` alone does **not** make the
subscriber start receiving it, and there's a second, separate requirement beyond the publication
that's easy to miss. Confirmed via the same loopback: after adding a table to the publication, the
subscriber has no knowledge of it at all until **both** of these run:

```sql
-- On RDS:
-- 1. GRANT SELECT on the new table to ddp_local_replication -- separate from, and just as
--    required as, adding it to the publication. Confirmed via a real reproduction: without this
--    grant, the tablesync worker crash-loops forever on "ERROR: permission denied for table
--    <name>" / "could not start initial contents copy" (every ~5s) -- it does NOT fail once and
--    stop, and does NOT silently skip the table; it retries indefinitely, visible in the
--    subscriber's own logs, until the grant is added. This is the same GRANT SELECT statement
--    §7.3/02-setup.sh already runs for the original 7 tables -- a new table needs the identical
--    treatment, not just a publication membership change.
GRANT SELECT ON public.<new_table> TO ddp_local_replication;
ALTER PUBLICATION ddp_legbot_publication ADD TABLE public.<new_table>;

-- On the local replica:
-- 2. The table must already exist locally with the matching schema (logical replication never
--    creates tables) -- e.g. via rebuild-local-replica.sh's own dump-and-apply approach, or a
--    manual CREATE TABLE matching RDS's new one. Then:
ALTER SUBSCRIPTION ddp_legbot_subscription REFRESH PUBLICATION;
-- This is what actually triggers a new tablesync worker to copy the new table's existing rows --
-- confirmed: querying the new table locally before this returns "relation does not exist", and
-- (once the GRANT above is also in place) its pre-existing RDS-side rows are present locally
-- immediately after.
```

Then run `compare-schema.sh` and confirm subscription health, same as the column case above.
New tables are **not** automatically included in this plan's table-scoped publication, unlike
under `FOR ALL TABLES` — this has to be a deliberate, reviewable step each time, and forgetting
either the grant or the publication membership produces a real, visible failure rather than a
silent gap -- but the two are independent steps, and only checking one of them is a real trap.

**Destructive or incompatible changes** (drop/rename a replicated column, change a column's type,
add a `NOT NULL` without a default) — RDS must never be allowed to send a row shape the local
side isn't ready for, and applying the equivalent change to the local replica *ahead of* RDS does
not reliably avoid that either (RDS keeps emitting the OLD row shape until its own migration
lands, so a local schema already changed to the NEW shape can itself break apply in the
interim). **Default to a full replica rebuild** (`drop-subscription-for-rebuild.sh` +
`rebuild-local-replica.sh` + `setup-subscription-and-readonly-role.sh`, OPEN-274/272/273) —
simplest and safest, and this plan already treats "rebuild, never repair in place" as the
standing recovery philosophy, so this isn't a new procedure, just an existing one reused for
this trigger too.

**Explicit order for the full-rebuild default**: stop LegBot's batch pipeline and any other local
consumer first, **then** apply the migration to RDS, **then** run the rebuild/resubscribe/verify
steps and restart consumers. Applying the RDS migration before consumers are stopped risks a
dispatch reading through the old replica while RDS has already moved on.

## Ongoing jurisdiction widening (OPEN-277, plan §3.6, §6 step 8)

Not a one-time build — as [OPEN-193](https://digitaldemocracyproject.atlassian.net/browse/OPEN-193)
confirms each further jurisdiction is genuinely, currently RDS-fed, add it to
`LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST` (the mechanism OPEN-276 built, in `ddp-sync`) — not on
a fixed calendar schedule independent of OPEN-193's own rollout, and not by changing the
publication (which already carries all 7 tables' current contents regardless of jurisdiction).
This ticket has no fixed acceptance criteria of its own beyond the artifacts above — it tracks
that widening continuing to completion across every OPEN-193-migrated jurisdiction, alongside
running the schema-comparison script and migration procedure above whenever a relevant Django
migration lands.

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

**Correction found by review, not by pm-review round 1: the `override=true` write-refusal check
was a no-op.** `default_transaction_read_only` only controls the mode a *future* `BEGIN` starts
in — setting it after a transaction has already started (`BEGIN; SET default_transaction_read_only
= off; ...`) has no effect on that transaction's own read/write mode. Confirmed directly against a
real Postgres container: with that exact sequence the error is always `cannot execute INSERT in a
read-only transaction`, never a permission check — including with an explicit `INSERT` grant added
to the test role first. So `override=true` was silently identical to `override=false`; it would
still have printed `PASS` even if `ddp_local_readonly` were accidentally granted
INSERT/UPDATE/DELETE someday, exactly the regression this second check exists to catch. Fixed with
`SET TRANSACTION READ WRITE` instead, which does flip the *current* transaction's mode — confirmed:
with an `INSERT` grant added, the write now genuinely succeeds (correctly failing the check, as it
must for a real regression); with that grant removed again, it correctly fails with `permission
denied for table`, not `read-only transaction` — proving this check now actually exercises the
`GRANT`-level boundary it claims to, not the session-default convenience setting a second time.

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

**Correction from pm-review round 2**:

- Falling through to the destructive local-detach path after a normal `DROP SUBSCRIPTION` failure
  used to happen unconditionally, even though the printed guidance told the operator to
  "investigate... rather than proceeding" for a non-connectivity failure — a real inconsistency
  between what the script said and what it did. Fixed by actually distinguishing the two cases:
  a failure containing `canceling statement due to statement timeout` (our own bounded wait
  firing) is itself real evidence of an unreachable publisher and proceeds automatically, same as
  before; any other failure (a permission or lock problem on a fully-reachable RDS, where
  detaching locally would silently orphan the remote slot instead of dropping it) now requires
  explicit confirmation (`CONFIRM_AMBIGUOUS_DETACH=y`, or an interactive prompt) before the script
  touches anything. Verified both branches: the timeout case still proceeds without a prompt
  end-to-end via the same paused-publisher drill as round 1, and the confirmation gate itself
  (deny without confirmation, proceed with `CONFIRM_AMBIGUOUS_DETACH=y`) was verified directly.
- The recovery-drill's own recommended RDS-side cleanup query used `slot_name LIKE
  'pg_%_sync_%'` — in SQL `LIKE`, `_` is a single-character wildcard, not a literal underscore,
  so this matched more than the documented `pg_<oid>_sync_<relid>_<random>` shape. Replaced with
  an anchored regex (`slot_name ~ '^pg_[0-9]+_sync_[0-9]+_[0-9]+$'`) that matches only that exact
  shape.
- `replica-status.sh`'s `LAGGING_THRESHOLD_BYTES` (an env var with a sane numeric default) had no
  validation that an operator override was actually an integer, which would have made the later
  numeric comparison error out instead of failing status cleanly. Added a one-line integer check.
