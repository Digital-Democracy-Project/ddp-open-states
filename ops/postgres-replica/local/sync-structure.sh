#!/usr/bin/env bash
# sync-structure.sh -- OPEN-314: keep the Mac replica's table STRUCTURE in step with RDS, without a person.
#
# WHY. Logical replication copies rows, never structure. A new column on a replicated RDS table makes the
# Mac's apply worker fail on the first row that carries it (and retry every ~5 s) until the Mac has the same
# column; a new published table never arrives until it exists locally and the subscription is refreshed.
# Until now a person did that by hand, in order (README "Django migration procedure"). This script does the
# safe, additive part of it. compare-schema.sh stays the independent check that the two sides agree.
#
# WHAT IT DOES (RDS is only ever READ; nothing here changes the publication, grants or anything else on RDS):
#   a. A column that exists on RDS but not locally, on a table the publication carries: ADD COLUMN, same type.
#      Only when it is nullable or its default is a plain constant (true/false, a number, a quoted literal): a
#      function default (now(), gen_random_uuid(), nextval(), ...) would be evaluated again on the Mac and give
#      existing rows different values than RDS, for good. A NOT NULL column with no default, an identity or
#      generated column, or a non-constant default is REFUSED (FAIL line), never applied. All of one table's
#      additions go in ONE transaction, and only if none of its columns was refused: a table is changed all or not at all.
#   b. A column present on both sides whose type or NOT NULL differs: REFUSED (FAIL line). Never altered.
#   c. A table the publication carries that does not exist locally: created from RDS's definition (columns,
#      types, NOT NULL, primary key, other indexes; no foreign keys, no defaults, no triggers: the Mac copy is
#      read-only), in one transaction; a table with a GENERATED column is refused (its value is not replicated).
#      Then ALTER SUBSCRIPTION ... REFRESH PUBLICATION, which subscribes EVERY pending published table, so it runs
#      only when ALL of them exist locally and the replication role can SELECT them on RDS (otherwise a table-copy
#      worker crash-loops): until then it prints a FAIL line saying the prod agent must GRANT SELECT, and refreshes
#      nothing.
#   d. A table that exists on RDS but is NOT in the publication: never acted on. Reported (FAIL line) only if it
#      is new since the known list was seeded (--seed-known-unpublished) -- see KNOWN below.
#   Local-only tables (profiles_profile, the locally built ddp_bill_search, ...) and the foreign keys the Mac
#   deliberately dropped are never touched, because nothing here compares or alters anything it did not read
#   from the publication's own table list. A column that exists only locally is logged, never dropped.
#
# EXIT CODES: 0 = nothing wrong (changes applied or none needed; also "another run in progress");
#             1 = at least one FAIL line (something refused or failed: needs a person);
#             3 = SKIPPED, no credential configured (the health check treats this as "not enabled").
# Last line is always "== Structure sync: ... ==".
#
# USAGE:  sync-structure.sh [--dry-run] [--seed-known-unpublished] [<local-database-name>]
#   --dry-run                  print "WOULD: ..." lines, change nothing.
#   --seed-known-unpublished   record every table RDS has that the publication does not carry as "known and
#                              intentionally not copied" (run once at install), then exit.
#   <local-database-name>      default: the database that carries the subscription (its name changes on rebuild).
#
# CREDENTIAL: the existing read-only replication login (ddp_local_replication), never printed or logged. Either
# RDS_HOST + RDS_REPLICATION_PASSWORD in the environment, or a KEY=VALUE file (RDS_HOST, RDS_REPLICATION_PASSWORD,
# optional RDS_PORT / RDS_DATABASE) at STRUCTURE_SYNC_ENV_FILE (default /Users/agentsmith/.config/ddp/
# replica-structure-sync.env) that MUST be mode 600 or 400 -- any other mode is refused. Parsed line by line,
# never sourced.
#
# SAFETY: one run at a time (lock directory), at most MAX_RUN_S seconds (watchdog), lock_timeout 5 s and
# statement_timeout 60 s on every local statement, idempotent (a second run finds nothing to do).
#
# Scheduled by check-replica-health.sh (stage 3, every 5 minutes, only when the credential file exists), which
# also turns a persistent FAIL into ONE Slack message and a recovery message. bash 3.2 compatible (no
# associative arrays, no mapfile).

set -uo pipefail
set +x

REPO_DIR="${REPO_DIR:-/Users/agentsmith/Developer/repos/ddp-open-states}"
STATE_DIR="${STRUCTURE_SYNC_STATE_DIR:-$REPO_DIR/logs/last-run}"
ENV_FILE="${STRUCTURE_SYNC_ENV_FILE:-/Users/agentsmith/.config/ddp/replica-structure-sync.env}"
PG_CONTAINER="${PG_CONTAINER:-ddp-openstates-postgres-1}"
PG_USER="${PG_USER:-openstates}"
PUBLICATION="${PUBLICATION:-ddp_legbot_publication}"
SUBSCRIPTION="${SUBSCRIPTION:-ddp_legbot_subscription}"
MAX_RUN_S="${STRUCTURE_SYNC_MAX_RUN_S:-240}"
SSLMODE="${RDS_SSLMODE:-verify-full}"
# RDS tables intentionally not copied (the Mac builds its own search table); more via the env var, or the
# seeded KNOWN file.
ALWAYS_UNPUBLISHED="ddp_bill_search ${STRUCTURE_SYNC_KNOWN_UNPUBLISHED:-}"
KNOWN="$STATE_DIR/structure-sync.known-unpublished"
LOCK_DIR="$STATE_DIR/structure-sync.lock"
PGOPT="-c statement_timeout=60000 -c lock_timeout=5000"
US="$(printf '\037')"   # field separator inside query rows: cannot appear in a type or default expression

export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"
if [ -z "${DOCKER_HOST:-}" ]; then
  for _sock in "${HOME:-/var/root}/.colima/default/docker.sock" "/Users/agentsmith/.colima/default/docker.sock"; do
    [ -S "$_sock" ] && export DOCKER_HOST="unix://$_sock" && break
  done
fi

DRY=0; SEED=0; LOCAL_DB=""
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --seed-known-unpublished) SEED=1 ;;
    -*) echo "FAIL: unknown option $a" >&2; exit 1 ;;
    *) LOCAL_DB="$a" ;;
  esac
done

FAILS=0; ACTIONS=0
FAIL_LOG=""   # every FAIL message, so the refresh step can tell which tables had a refusal
fail() { echo "FAIL: $*"; FAILS=$((FAILS + 1)); FAIL_LOG="$FAIL_LOG"$'\n'"$*"; }
did()  { echo "APPLIED: $*"; ACTIONS=$((ACTIONS + 1)); }
would() { echo "WOULD: $*"; ACTIONS=$((ACTIONS + 1)); }
finish() {
  local pre=""; [ "$DRY" = 1 ] && pre="DRY RUN, "
  if [ "$FAILS" -gt 0 ]; then echo "== Structure sync: NEEDS ATTENTION (${pre}$FAILS problem(s), $ACTIONS change(s)) =="; exit 1; fi
  echo "== Structure sync: OK (${pre}$ACTIONS change(s)) =="; exit 0
}

# --- credential ---------------------------------------------------------------------------------------------
load_credential() {
  if [ -n "${RDS_REPLICATION_PASSWORD:-}" ] && [ -n "${RDS_HOST:-}" ]; then return 0; fi
  [ -f "$ENV_FILE" ] || return 3
  local mode k v
  mode="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || stat -f '%Lp' "$ENV_FILE" 2>/dev/null)"
  case "$mode" in
    600|400) ;;
    *) fail "$ENV_FILE has mode ${mode:-unknown}; it holds a credential and must be mode 600 (chmod 600) -- not read"; return 1 ;;
  esac
  while IFS='=' read -r k v; do
    v="${v%\"}"; v="${v#\"}"
    case "$k" in
      RDS_HOST|RDS_PORT|RDS_DATABASE|RDS_REPLICATION_PASSWORD) export "$k=$v" ;;
    esac
  done < "$ENV_FILE"
  [ -n "${RDS_HOST:-}" ] && [ -n "${RDS_REPLICATION_PASSWORD:-}" ] || return 3
  return 0
}
load_credential; rc=$?
if [ "$rc" -eq 3 ]; then echo "SKIPPED: no RDS credential configured (set RDS_HOST and RDS_REPLICATION_PASSWORD, or create $ENV_FILE)"; echo "== Structure sync: SKIPPED (not enabled) =="; exit 3; fi
[ "$rc" -ne 0 ] && finish
RDS_PORT="${RDS_PORT:-5432}"; RDS_DATABASE="${RDS_DATABASE:-openstates}"
RDS_CONN="host=$RDS_HOST port=$RDS_PORT dbname=$RDS_DATABASE user=ddp_local_replication sslmode=$SSLMODE connect_timeout=10"

# --- one run at a time, bounded -----------------------------------------------------------------------------
mkdir -p "$STATE_DIR"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  holder="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  age=$(( $(date +%s) - $(stat -c '%Y' "$LOCK_DIR" 2>/dev/null || stat -f '%m' "$LOCK_DIR" 2>/dev/null || echo 0) ))
  if [ -n "$holder" ] && kill -0 "$holder" 2>/dev/null && [ "$age" -lt $(( MAX_RUN_S * 2 )) ]; then
    echo "SKIPPED: another structure sync is running (pid $holder)"; echo "== Structure sync: OK (skipped, another run in progress) =="; exit 0
  fi
  rm -rf "$LOCK_DIR"; mkdir "$LOCK_DIR" || { fail "could not take the lock $LOCK_DIR"; finish; }
fi
echo $$ > "$LOCK_DIR/pid"
# The watchdog must not hold this script's stdout/stderr open: a caller capturing our output with $(...) would
# otherwise wait for its sleep to finish even after we have exited. Its child sleep is killed first (killing the
# subshell first would orphan it).
# On timeout the watchdog kills everything the script is waiting on, whole process tree (bash holds a TERM trap
# until its foreground child finishes, and an orphaned grandchild would keep a caller's $(...) open), then the
# script itself. It reads its own pid from a file so it never kills itself.
( sleep "$MAX_RUN_S"
  kt() { local c; for c in $(pgrep -P "$1" 2>/dev/null); do kt "$c"; done; kill -TERM "$1" 2>/dev/null; }
  me="$(cat "$LOCK_DIR/watchdog.pid" 2>/dev/null)"
  for c in $(pgrep -P $$ 2>/dev/null); do [ "$c" != "$me" ] && kt "$c"; done
  kill -TERM $$ 2>/dev/null ) >/dev/null 2>&1 & WATCHDOG=$!
echo "$WATCHDOG" > "$LOCK_DIR/watchdog.pid"
cleanup() { pkill -P "$WATCHDOG" 2>/dev/null; kill "$WATCHDOG" 2>/dev/null; rm -rf "$LOCK_DIR"; }
trap cleanup EXIT
trap 'echo "FAIL: structure sync timed out after ${MAX_RUN_S}s"; echo "== Structure sync: NEEDS ATTENTION (timeout) =="; exit 1' TERM

# --- the two databases --------------------------------------------------------------------------------------
# RDS is reached from INSIDE the local Postgres container (the Mac has no host psql and the container already
# reaches RDS as the subscriber); the password goes by env-var NAME so it never appears in an argument list.
rds_psql() {  # <sql>
  PGPASSWORD="$RDS_REPLICATION_PASSWORD" docker exec -e PGPASSWORD -e PGOPTIONS="$PGOPT" "$PG_CONTAINER" \
    psql "$RDS_CONN" -v ON_ERROR_STOP=1 -tA -c "$1" 2>&1
}
local_psql() {  # <sql>
  docker exec -e PGOPTIONS="$PGOPT" "$PG_CONTAINER" psql -U "$PG_USER" -d "$LOCAL_DB" -v ON_ERROR_STOP=1 -tA -c "$1" 2>&1
}
local_tx() {  # <multi-statement sql>, one transaction
  printf '%s\n' "$1" | docker exec -i -e PGOPTIONS="$PGOPT" "$PG_CONTAINER" psql -U "$PG_USER" -d "$LOCAL_DB" -v ON_ERROR_STOP=1 -1 -q -f - 2>&1
}
ident_ok() { [[ "$1" =~ ^[a-z_][a-z0-9_]*$ ]]; }   # names from a remote system are interpolated into SQL below

if [ -z "$LOCAL_DB" ]; then
  LOCAL_DB="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d postgres -tAc \
    "SELECT d.datname FROM pg_subscription s JOIN pg_database d ON d.oid = s.subdbid WHERE s.subname = '$SUBSCRIPTION'" 2>&1)" \
    || { fail "cannot query the local Postgres container $PG_CONTAINER: $LOCAL_DB"; finish; }
  [ -n "$LOCAL_DB" ] || { fail "no subscription named $SUBSCRIPTION on this Postgres server"; finish; }
fi
ident_ok "$LOCAL_DB" || { fail "'$LOCAL_DB' is not a safe database name"; finish; }

published="$(rds_psql "SELECT tablename FROM pg_publication_tables WHERE pubname = '$PUBLICATION' AND schemaname = 'public' ORDER BY 1")" \
  || { fail "could not read publication $PUBLICATION from RDS: $(printf '%s' "$published" | head -2 | tr '\n' ' ')"; finish; }
[ -n "$published" ] || { fail "RDS publication $PUBLICATION lists no tables"; finish; }
while IFS= read -r t; do ident_ok "$t" || { fail "refusing unexpected table name from the RDS publication: '$t'"; finish; }; done <<< "$published"

rds_all="$(rds_psql "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")" \
  || { fail "could not list RDS tables: $(printf '%s' "$rds_all" | head -2 | tr '\n' ' ')"; finish; }

# --- --seed-known-unpublished -------------------------------------------------------------------------------
unpublished="$(comm -23 <(printf '%s\n' "$rds_all" | LC_ALL=C sort) <(printf '%s\n' "$published" | LC_ALL=C sort))"
if [ "$SEED" = 1 ]; then
  printf '%s\n' "$unpublished" > "$KNOWN"
  echo "Seeded $KNOWN with $(printf '%s\n' "$unpublished" | grep -c .) RDS table(s) the publication does not carry."
  echo "== Structure sync: OK (seeded) =="; exit 0
fi

# --- columns ------------------------------------------------------------------------------------------------
# One row per column, in column order: name US type US notnull US default US identity+generated
COLUMN_QUERY="
  SELECT a.attname || chr(31) || format_type(a.atttypid, a.atttypmod) || chr(31) || a.attnotnull::text || chr(31)
         || coalesce(pg_get_expr(d.adbin, d.adrelid), '') || chr(31) || a.attidentity::text || a.attgenerated::text
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
  WHERE n.nspname = 'public' AND c.relname = '__TABLE__' AND a.attnum > 0 AND NOT a.attisdropped
  ORDER BY a.attnum"

field() { printf '%s' "$1" | awk -F"$US" -v n="$2" '{print $n}'; }
row_for() { printf '%s\n' "$1" | awk -F"$US" -v c="$2" '$1==c {print; exit}'; }

# A default is applied on the Mac by evaluating it AGAIN, and logical replication never replays RDS's backfill of
# existing rows, so only a plain constant is safe (true/false, a number, a quoted literal with an optional cast).
# now(), gen_random_uuid(), random(), nextval(), any function: refused, or existing rows would differ for good.
safe_default() {
  local d="$1" num='^-?[0-9]+(\.[0-9]+)?$' str
  str=$'^\'([^\']|\'\')*\'(::[a-zA-Z0-9_ ]+(\\([0-9, ]+\\))?(\\[\\])?)?$'
  case "$d" in true|false) return 0 ;; esac
  [[ "$d" =~ $num ]] && return 0
  [[ "$d" =~ $str ]] && return 0
  return 1
}

created=""   # tables created locally this run (dry run: that would be)
for table in $published; do
  q="${COLUMN_QUERY//__TABLE__/$table}"
  rds_cols="$(rds_psql "$q")" || { fail "$table: could not read its columns from RDS: $(printf '%s' "$rds_cols" | head -1)"; continue; }
  [ -n "$rds_cols" ] || { fail "$table: in the publication but the replication login cannot see its columns on RDS"; continue; }
  local_cols="$(local_psql "$q")" || { fail "$table: could not read its columns locally: $(printf '%s' "$local_cols" | head -1)"; continue; }

  if [ -z "$local_cols" ]; then
    # ---- c. table missing locally: create it from RDS's definition (everything checked BEFORE anything is created)
    defs=""; bad=""
    while IFS= read -r row; do
      c="$(field "$row" 1)"; ty="$(field "$row" 2)"; nn="$(field "$row" 3)"; gen="$(field "$row" 5)"
      ident_ok "$c" || { bad="column name '$c'"; break; }
      # A generated column's value is NOT sent by logical replication (the Mac would hold NULL for ever); an identity
      # column is an ordinary value on the wire, so it becomes a plain column (the Mac copy is read-only).
      case "$gen" in *s*|*v*) bad="generated column $c (its value is not replicated)"; break ;; esac
      defs="${defs:+$defs, }\"$c\" $ty$([ "$nn" = true ] && printf ' NOT NULL')"
    done <<< "$rds_cols"
    [ -n "$bad" ] && { fail "$table: not created, has a $bad; create it by hand (README, break-glass)"; continue; }
    pk="$(rds_psql "SELECT string_agg('\"' || a.attname || '\"', ', ' ORDER BY array_position(i.indkey::int2[], a.attnum)) FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) WHERE i.indisprimary AND i.indrelid = 'public.\"$table\"'::regclass")" \
      || { fail "$table: could not read its primary key from RDS"; continue; }
    [ -n "$pk" ] || { fail "$table: has no primary key on RDS, so the Mac cannot apply updates to it; create it by hand (README, break-glass)"; continue; }
    idx="$(rds_psql "SELECT pg_get_indexdef(i.indexrelid) FROM pg_index i WHERE NOT i.indisprimary AND i.indrelid = 'public.\"$table\"'::regclass ORDER BY 1")" \
      || { fail "$table: could not read its indexes from RDS"; continue; }
    sql="CREATE TABLE public.\"$table\" ($defs);
ALTER TABLE public.\"$table\" ADD PRIMARY KEY ($pk);"
    [ -n "$idx" ] && sql="$sql
$idx;"
    if [ "$DRY" = 1 ]; then would "create table $table locally (primary key $pk, $(printf '%s\n' "$idx" | grep -c . ) other index(es))"; created="$created $table"; continue; fi
    out="$(local_tx "$sql")" || { fail "$table: not created locally (rolled back): $(printf '%s' "$out" | head -2 | tr '\n' ' ')"; continue; }
    did "created table $table locally (primary key $pk)"; created="$created $table"
    continue
  fi

  # ---- a/b. table exists locally: check EVERY column first; apply the additions only if none was refused, all in one
  # transaction, so a table is never left half-changed. A refusal anywhere in a table means nothing is applied to it.
  stmts=""; adds=""; refused=0
  while IFS= read -r row; do
    c="$(field "$row" 1)"; ty="$(field "$row" 2)"; nn="$(field "$row" 3)"; df="$(field "$row" 4)"; gen="$(field "$row" 5)"
    lrow="$(row_for "$local_cols" "$c")"
    if [ -z "$lrow" ]; then
      ident_ok "$c" || { fail "$table.$c: unexpected column name, not added"; refused=1; continue; }
      if [ -n "$gen" ]; then fail "$table.$c: new identity/generated column, not added (add it by hand: README break-glass)"; refused=1; continue; fi
      if [ "$nn" = true ] && [ -z "$df" ]; then fail "$table.$c: new NOT NULL column with no default, not added: existing rows could not satisfy it (decide by hand)"; refused=1; continue; fi
      if [ -n "$df" ] && ! safe_default "$df"; then fail "$table.$c: new column whose default ($df) is not a plain constant, not added: the Mac would evaluate it again and give existing rows values that differ from RDS (decide by hand)"; refused=1; continue; fi
      ddl="ALTER TABLE public.\"$table\" ADD COLUMN \"$c\" $ty"
      [ -n "$df" ] && ddl="$ddl DEFAULT $df"
      [ "$nn" = true ] && ddl="$ddl NOT NULL"
      stmts="$stmts$ddl;
"
      adds="$adds$c $ty
"
    else
      lty="$(field "$lrow" 2)"; lnn="$(field "$lrow" 3)"
      if [ "$ty" != "$lty" ] || [ "$nn" != "$lnn" ]; then
        fail "$table.$c: differs (RDS $ty notnull=$nn, local $lty notnull=$lnn); changed types are never applied automatically (README break-glass)"
        refused=1
      fi
    fi
  done <<< "$rds_cols"
  if [ -n "$stmts" ]; then
    if [ "$refused" = 1 ]; then
      echo "INFO: $table: nothing applied, because a column of this table was refused (a table is changed all or not at all)"
    elif [ "$DRY" = 1 ]; then
      printf '%s' "$stmts" | while IFS= read -r l; do [ -n "$l" ] && echo "WOULD: ${l%;}"; done
      ACTIONS=$((ACTIONS + $(printf '%s' "$stmts" | grep -c .)))
    else
      out="$(local_tx "$stmts")" \
        && printf '%s' "$adds" | while IFS= read -r l; do [ -n "$l" ] && echo "APPLIED: added column $table.${l%% *} (${l#* })"; done \
        || { fail "$table: ADD COLUMN failed (rolled back, table unchanged): $(printf '%s' "$out" | head -1)"; continue; }
      ACTIONS=$((ACTIONS + $(printf '%s' "$adds" | grep -c .)))
    fi
  fi
  # a column only the Mac has is harmless to the subscriber: say so, never drop it
  while IFS= read -r lrow; do
    c="$(field "$lrow" 1)"
    [ -z "$(row_for "$rds_cols" "$c")" ] && echo "INFO: $table.$c exists only locally (left alone)"
  done <<< "$local_cols"
done

# --- subscription refresh ---------------------------------------------------------------------------------------------
# ALTER SUBSCRIPTION ... REFRESH PUBLICATION subscribes EVERY published table that is not yet subscribed, not just the
# ready one. So it runs only when every such table exists locally AND the login can SELECT it on RDS; if any one is not
# ready (a FAIL line says which and why), nothing is refreshed, so no table-copy worker can start crash-looping.
subscribed="$(local_psql "SELECT c.relname FROM pg_subscription_rel r JOIN pg_class c ON c.oid = r.srrelid JOIN pg_subscription s ON s.oid = r.srsubid WHERE s.subname = '$SUBSCRIPTION'")" \
  || { fail "could not read the subscription's table list: $(printf '%s' "$subscribed" | head -1)"; subscribed="__unknown__"; }
pending=0; unready=0
for table in $published; do
  printf '%s\n' "$subscribed" | grep -qx "$table" && continue
  pending=1
  # a table whose own structure sync was refused or failed (any FAIL naming it: type change, refused column, no primary
  # key, rolled-back transaction) is not ready, even if it already exists locally: the copy would fail against it
  if printf '%s\n' "$FAIL_LOG" | grep -q "^$table[:.]"; then unready=1; continue; fi
  if [ "$DRY" = 1 ]; then
    case " $created " in *" $table "*) ;; *) [ -n "$(local_psql "SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = '$table'")" ] || { unready=1; continue; } ;; esac
  else
    [ -n "$(local_psql "SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = '$table'")" ] || { unready=1; continue; }   # creation was refused above
  fi
  priv="$(rds_psql "SELECT has_table_privilege('public.\"$table\"', 'SELECT')")"
  if [ "$priv" != "t" ]; then
    fail "$table: in the publication but ddp_local_replication cannot SELECT it on RDS; the prod agent must GRANT SELECT ON public.$table TO ddp_local_replication (the refresh waits for it)"
    unready=1
  fi
done
if [ "$pending" = 1 ] && [ "$subscribed" != "__unknown__" ]; then
  if [ "$unready" = 1 ]; then
    echo "INFO: REFRESH PUBLICATION not run: it would subscribe every pending table, including the one(s) above that are not ready"
  elif [ "$DRY" = 1 ]; then would "ALTER SUBSCRIPTION $SUBSCRIPTION REFRESH PUBLICATION"
  else
    out="$(local_psql "ALTER SUBSCRIPTION $SUBSCRIPTION REFRESH PUBLICATION")" \
      && did "ALTER SUBSCRIPTION $SUBSCRIPTION REFRESH PUBLICATION" \
      || fail "REFRESH PUBLICATION failed: $(printf '%s' "$out" | head -1)"
  fi
fi

# --- d. tables RDS has that the publication does not carry ------------------------------------------------------
if [ -f "$KNOWN" ]; then
  for t in $unpublished; do
    case " $ALWAYS_UNPUBLISHED " in *" $t "*) continue ;; esac
    grep -qx "$t" "$KNOWN" && continue
    fail "$t: a table on RDS that the publication does not carry (new since the list was seeded). If the Mac should have it, the prod agent adds it to the publication and grants SELECT; if not, add its name to $KNOWN"
  done
else
  echo "INFO: no known-unpublished list yet ($KNOWN): run with --seed-known-unpublished once so new unpublished RDS tables are reported"
fi

[ "$ACTIONS" -eq 0 ] && [ "$FAILS" -eq 0 ] && echo "Nothing to do: structure matches for all $(printf '%s\n' "$published" | grep -c .) published tables."
finish
