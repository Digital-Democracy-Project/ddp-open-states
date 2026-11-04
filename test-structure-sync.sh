#!/usr/bin/env bash
# test-structure-sync.sh -- OPEN-314: end-to-end test of ops/postgres-replica/local/sync-structure.sh against a
# THROWAWAY publisher/subscriber pair (two postgres:16 containers on their own Docker network, real
# CREATE PUBLICATION / CREATE SUBSCRIPTION, the same loopback pattern OPEN-273/277/280 used). It never touches
# the real replica, the real subscription or RDS: every name here is os314-*.
#
#     bash test-structure-sync.sh            # needs docker and the postgres:16 image; takes about 2 minutes
#     SYNC_SCRIPT=/path/to/mutant.sh bash test-structure-sync.sh    # mutation checks: expect failures
#
# Exits 0 with "ALL PASS", or 1 after listing every failing assertion. Skips (exit 0) when docker is absent.

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SYNC="${SYNC_SCRIPT:-$HERE/ops/postgres-replica/local/sync-structure.sh}"
command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1 || { echo "SKIPPED: docker is not available"; exit 0; }
docker image inspect postgres:16 >/dev/null 2>&1 || { echo "SKIPPED: image postgres:16 is not present (docker pull postgres:16)"; exit 0; }

PUB=os314-pub; SUB=os314-sub; NET=os314-net
T="$(mktemp -d /tmp/structure-sync-test.XXXXXX)"
PASS=0; FAIL=0; ALL=""
cleanup() { docker rm -f "$PUB" "$SUB" >/dev/null 2>&1; docker network rm "$NET" >/dev/null 2>&1; rm -rf "$T"; }
trap cleanup EXIT
cleanup_old() { docker rm -f "$PUB" "$SUB" >/dev/null 2>&1; docker network rm "$NET" >/dev/null 2>&1; }
cleanup_old

ok()   { echo "PASS: $1"; PASS=$((PASS + 1)); }
bad()  { echo "FAIL: $1"; [ -n "${2:-}" ] && { echo "--- output was:"; echo "$2"; }; FAIL=$((FAIL + 1)); }
assert_contains()     { if printf '%s' "$2" | grep -qF -- "$3"; then ok "$1"; else bad "$1 -- expected to find: $3" "$2"; fi; }
assert_not_contains() { if printf '%s' "$2" | grep -qF -- "$3"; then bad "$1 -- expected NOT to find: $3" "$2"; else ok "$1"; fi; }
assert_eq()           { if [ "$2" = "$3" ]; then ok "$1"; else
                          case "$1" in exit*|*"exit "*) bad "$1 -- expected '$3', got '$2'" "${OUT:-}" ;; *) bad "$1 -- expected '$3', got '$2'" ;; esac; fi; }

pc() { docker exec "$PUB" psql -U postgres -d openstates -v ON_ERROR_STOP=1 -tAq -c "$1" 2>&1; }
sc() { docker exec "$SUB" psql -U postgres -d repl -v ON_ERROR_STOP=1 -tAq -c "$1" 2>&1; }
wait_ready() { local c="$1" n=0; until [ "$(docker logs "$c" 2>&1 | grep -c 'ready to accept connections')" -ge 2 ]; do sleep 1; n=$((n+1)); [ $n -gt 60 ] && { echo "container $c never became ready"; exit 1; }; done; }
wait_for() {  # <label> <sql on sub> <expected> [timeout_s]  -> sets WAITED (seconds)
  local n=0 lim="${4:-40}" got
  while [ $n -lt $lim ]; do got="$(sc "$2")"; [ "$got" = "$3" ] && { WAITED=$n; ok "$1"; return 0; }; sleep 1; n=$((n+1)); done
  WAITED=$n; bad "$1 -- waited ${lim}s, last value '$got', wanted '$3'"; return 1
}
run_sync() {  # [flags] -> OUT, RC
  OUT="$(env PG_CONTAINER=$SUB PG_USER=postgres RDS_HOST=$PUB RDS_DATABASE=openstates RDS_SSLMODE=disable \
      RDS_REPLICATION_PASSWORD=replpw STRUCTURE_SYNC_STATE_DIR="$T/state" STRUCTURE_SYNC_ENV_FILE="$T/none.env" \
      bash "$SYNC" "$@" repl 2>&1)"; RC=$?
  ALL="$ALL
$OUT"
}

echo "== building the throwaway pair"
docker network create "$NET" >/dev/null
docker run -d --name "$PUB" --network "$NET" -e POSTGRES_PASSWORD=pubpw postgres:16 -c wal_level=logical -c max_replication_slots=10 -c max_wal_senders=10 >/dev/null
docker run -d --name "$SUB" --network "$NET" -e POSTGRES_PASSWORD=subpw postgres:16 -c max_logical_replication_workers=8 >/dev/null
wait_ready "$PUB"; wait_ready "$SUB"
docker exec "$PUB" psql -U postgres -c "CREATE DATABASE openstates" >/dev/null
docker exec "$SUB" psql -U postgres -c "CREATE DATABASE repl" >/dev/null
docker exec "$PUB" psql -U postgres -c "CREATE ROLE ddp_local_replication LOGIN REPLICATION PASSWORD 'replpw'" >/dev/null
pc "CREATE TABLE opencivicdata_jurisdiction (id text PRIMARY KEY, division_id text);
    CREATE TABLE opencivicdata_bill (id text PRIMARY KEY, title text, jurisdiction_id text REFERENCES opencivicdata_jurisdiction(id));
    CREATE TABLE ddp_bill_version_document (id int PRIMARY KEY, version_note text NOT NULL, raw_text text);
    CREATE TABLE ddp_bill_search (id int PRIMARY KEY, doc text);
    CREATE TABLE django_session (k text PRIMARY KEY);
    INSERT INTO opencivicdata_jurisdiction VALUES ('j1','d1');
    INSERT INTO opencivicdata_bill VALUES ('b1','first','j1');
    INSERT INTO ddp_bill_version_document VALUES (1,'Introduced','text');
    GRANT SELECT ON opencivicdata_jurisdiction, opencivicdata_bill, ddp_bill_version_document TO ddp_local_replication;
    CREATE PUBLICATION ddp_legbot_publication FOR TABLE opencivicdata_jurisdiction, opencivicdata_bill, ddp_bill_version_document" >/dev/null
# the Mac copy: same tables WITHOUT the foreign key (deliberately dropped locally), plus local-only tables and one local-only column
sc "CREATE TABLE opencivicdata_jurisdiction (id text PRIMARY KEY, division_id text);
    CREATE TABLE opencivicdata_bill (id text PRIMARY KEY, title text, jurisdiction_id text, local_only_col text);
    CREATE TABLE ddp_bill_version_document (id int PRIMARY KEY, version_note text NOT NULL, raw_text text);
    CREATE TABLE profiles_profile (id int PRIMARY KEY, api_key text);
    CREATE TABLE ddp_bill_search (id int PRIMARY KEY, doc text);
    INSERT INTO profiles_profile VALUES (1,'local-only');
    INSERT INTO ddp_bill_search VALUES (1,'built locally')" >/dev/null
sc "CREATE SUBSCRIPTION ddp_legbot_subscription CONNECTION 'host=$PUB port=5432 dbname=openstates user=ddp_local_replication password=replpw' PUBLICATION ddp_legbot_publication" >/dev/null
wait_for "initial copy finished" "SELECT count(*) FROM pg_subscription_rel WHERE srsubstate <> 'r'" 0 60

echo; echo "== 1. no drift: nothing to do, and no known-unpublished list yet is said, not alerted"
run_sync
assert_eq "exit 0" "$RC" 0
assert_contains "says nothing to do" "$OUT" "Nothing to do"
assert_contains "tells the person to seed the known list" "$OUT" "--seed-known-unpublished"
assert_contains "the local-only column is left alone and said so" "$OUT" "opencivicdata_bill.local_only_col exists only locally"

echo; echo "== 2. seed: RDS tables the publication does not carry become 'known'"
run_sync --seed-known-unpublished
assert_eq "exit 0" "$RC" 0
KNOWN_TXT="$(cat "$T/state/structure-sync.known-unpublished" 2>/dev/null)"
assert_contains "ddp_bill_search is known" "$KNOWN_TXT" "ddp_bill_search"
assert_contains "django_session is known" "$KNOWN_TXT" "django_session"
run_sync; assert_not_contains "no unpublished-table alert after seeding" "$OUT" "does not carry"

echo; echo "== 3. the OPEN-492 case: a new nullable column arrives with no manual step (and the stall is measured)"
pc "ALTER TABLE ddp_bill_version_document ADD COLUMN is_bill_version boolean" >/dev/null
T0="$(date +%s)"
pc "INSERT INTO ddp_bill_version_document VALUES (2,'Engrossed','t2', true)" >/dev/null
sleep 7
assert_eq "before the sync the row has NOT arrived (the apply worker is stalled)" "$(sc "SELECT count(*) FROM ddp_bill_version_document WHERE id = 2")" 0
assert_contains "the subscriber log shows the missing-column stall" "$(docker logs "$SUB" 2>&1)" "missing replicated column"
S0="$(date +%s)"; run_sync; S1="$(date +%s)"
assert_eq "exit 0" "$RC" 0
assert_contains "applied ADD COLUMN" "$OUT" "added column ddp_bill_version_document.is_bill_version (boolean)"
wait_for "the stalled row arrives after the sync" "SELECT count(*) FROM ddp_bill_version_document WHERE id = 2 AND is_bill_version" 1 30
T2="$(date +%s)"
echo "MEASURED: sync job took $((S1 - S0))s; row visible $WAITED s after the sync; $((T2 - T0))s from the first row on RDS carrying the column (includes the 7 s this test waited before running the sync)"
STALL_LINE="job $((S1 - S0))s + $WAITED s for the apply worker's next retry after the column existed"

echo; echo "== 3b. a NOT NULL column that has a default is added with its default"
pc "ALTER TABLE opencivicdata_bill ADD COLUMN flag boolean NOT NULL DEFAULT false" >/dev/null
run_sync
assert_contains "applied with default and NOT NULL" "$OUT" "added column opencivicdata_bill.flag"
assert_eq "local column is NOT NULL with default false" "$(sc "SELECT is_nullable||'/'||column_default FROM information_schema.columns WHERE table_name='opencivicdata_bill' AND column_name='flag'")" "NO/false"

echo; echo "== 4. a NOT NULL column with no default is REFUSED, never applied"
pc "ALTER TABLE opencivicdata_jurisdiction ADD COLUMN must text NOT NULL DEFAULT 'x'; ALTER TABLE opencivicdata_jurisdiction ALTER COLUMN must DROP DEFAULT" >/dev/null
run_sync
assert_eq "exit 1" "$RC" 1
assert_contains "FAIL line names the column and the reason" "$OUT" "opencivicdata_jurisdiction.must: new NOT NULL column with no default, not added"
assert_eq "local table did not get the column" "$(sc "SELECT count(*) FROM information_schema.columns WHERE table_name='opencivicdata_jurisdiction' AND column_name='must'")" 0
pc "ALTER TABLE opencivicdata_jurisdiction DROP COLUMN must" >/dev/null

echo; echo "== 5. a changed column type is REFUSED, never altered"
pc "ALTER TABLE opencivicdata_bill ALTER COLUMN title TYPE varchar(40)" >/dev/null
run_sync
assert_eq "exit 1" "$RC" 1
assert_contains "FAIL line says the type differs" "$OUT" "opencivicdata_bill.title: differs (RDS character varying(40)"
assert_eq "local type is untouched" "$(sc "SELECT data_type FROM information_schema.columns WHERE table_name='opencivicdata_bill' AND column_name='title'")" "text"
pc "ALTER TABLE opencivicdata_bill ALTER COLUMN title TYPE text" >/dev/null

echo; echo "== 5b. a function default is REFUSED (the Mac would evaluate it again and existing rows would differ for good)"
pc "ALTER TABLE ddp_bill_version_document ADD COLUMN created_at timestamptz DEFAULT now()" >/dev/null
run_sync
assert_eq "exit 1" "$RC" 1
assert_contains "FAIL says the default is not a plain constant" "$OUT" "ddp_bill_version_document.created_at: new column whose default (now()) is not a plain constant"
assert_eq "local table did not get the column" "$(sc "SELECT count(*) FROM information_schema.columns WHERE table_name='ddp_bill_version_document' AND column_name='created_at'")" 0
pc "ALTER TABLE ddp_bill_version_document DROP COLUMN created_at; ALTER TABLE ddp_bill_version_document ADD COLUMN u uuid DEFAULT gen_random_uuid()" >/dev/null
run_sync
assert_eq "gen_random_uuid(): exit 1" "$RC" 1
assert_contains "gen_random_uuid() refused too" "$OUT" "ddp_bill_version_document.u: new column whose default (gen_random_uuid()) is not a plain constant"
pc "ALTER TABLE ddp_bill_version_document DROP COLUMN u" >/dev/null

echo; echo "== 5c. constant defaults are added, in one transaction, and the EXISTING rows end up equal on both sides"
pc "ALTER TABLE ddp_bill_version_document ADD COLUMN lang text DEFAULT 'en', ADD COLUMN weight int NOT NULL DEFAULT 0, ADD COLUMN tags jsonb DEFAULT '{}'::jsonb" >/dev/null
run_sync
assert_eq "exit 0" "$RC" 0
assert_contains "lang added" "$OUT" "added column ddp_bill_version_document.lang (text)"
assert_contains "weight added" "$OUT" "added column ddp_bill_version_document.weight (integer)"
assert_contains "tags added" "$OUT" "added column ddp_bill_version_document.tags (jsonb)"
assert_eq "existing row 1 holds the same default on RDS and on the Mac" "$(sc "SELECT lang||'/'||weight||'/'||tags FROM ddp_bill_version_document WHERE id=1")" "$(pc "SELECT lang||'/'||weight||'/'||tags FROM ddp_bill_version_document WHERE id=1")"

echo; echo "== 5d. a table is changed all or not at all: an allowed column is NOT added when another column of the same table is refused"
pc "ALTER TABLE opencivicdata_jurisdiction ADD COLUMN ok_col text, ADD COLUMN bad_col text NOT NULL DEFAULT 'x'; ALTER TABLE opencivicdata_jurisdiction ALTER COLUMN bad_col DROP DEFAULT" >/dev/null
run_sync
assert_eq "exit 1" "$RC" 1
assert_contains "the refused column is named" "$OUT" "opencivicdata_jurisdiction.bad_col: new NOT NULL column with no default"
assert_contains "says nothing was applied to that table" "$OUT" "opencivicdata_jurisdiction: nothing applied"
assert_eq "the allowed column was NOT left behind" "$(sc "SELECT count(*) FROM information_schema.columns WHERE table_name='opencivicdata_jurisdiction' AND column_name='ok_col'")" 0
pc "ALTER TABLE opencivicdata_jurisdiction DROP COLUMN ok_col, DROP COLUMN bad_col" >/dev/null
run_sync; assert_eq "clean again: exit 0" "$RC" 0

echo; echo "== 6. a new published table is created locally (primary key and indexes) and refreshed; its rows arrive"
pc "CREATE TABLE committee (id int PRIMARY KEY, name text NOT NULL, note text);
    CREATE INDEX committee_name_idx ON committee (name);
    INSERT INTO committee VALUES (1,'a','x'),(2,'b','y'),(3,'c','z');
    GRANT SELECT ON committee TO ddp_local_replication;
    ALTER PUBLICATION ddp_legbot_publication ADD TABLE committee" >/dev/null
run_sync
assert_eq "exit 0" "$RC" 0
assert_contains "created locally" "$OUT" "created table committee locally"
assert_contains "refreshed the subscription" "$OUT" "ALTER SUBSCRIPTION ddp_legbot_subscription REFRESH PUBLICATION"
wait_for "its 3 existing rows are copied" "SELECT count(*) FROM committee" 3 40
assert_eq "primary key + the other index exist locally" "$(sc "SELECT count(*) FROM pg_indexes WHERE tablename='committee'")" 2
assert_eq "no foreign keys or defaults were invented" "$(sc "SELECT count(*) FROM pg_constraint WHERE contype='f'")" 0

echo; echo "== 7. a published table the login cannot read yet: created locally, refresh WAITS, says who must grant"
pc "CREATE TABLE committee2 (id int PRIMARY KEY, name text); INSERT INTO committee2 VALUES (1,'p'),(2,'q');
    ALTER PUBLICATION ddp_legbot_publication ADD TABLE committee2" >/dev/null
run_sync
assert_eq "exit 1" "$RC" 1
assert_contains "FAIL says the prod agent must GRANT SELECT" "$OUT" "committee2: in the publication but ddp_local_replication cannot SELECT it on RDS"
assert_eq "table exists locally" "$(sc "SELECT count(*) FROM pg_tables WHERE tablename='committee2'")" 1
assert_eq "but is not subscribed yet (no crash-looping table-copy worker)" "$(sc "SELECT count(*) FROM pg_subscription_rel r JOIN pg_class c ON c.oid=r.srrelid WHERE c.relname='committee2'")" 0
pc "GRANT SELECT ON committee2 TO ddp_local_replication" >/dev/null
run_sync
assert_eq "after the grant: exit 0" "$RC" 0
assert_contains "refreshed" "$OUT" "REFRESH PUBLICATION"
wait_for "its rows arrive" "SELECT count(*) FROM committee2" 2 40

echo; echo "== 7b. one ready table and one the login cannot read yet: NOTHING is refreshed (a refresh subscribes every pending table)"
pc "CREATE TABLE ready_t (id int PRIMARY KEY, v text); INSERT INTO ready_t VALUES (1,'r');
    CREATE TABLE unready_t (id int PRIMARY KEY, v text); INSERT INTO unready_t VALUES (1,'u');
    GRANT SELECT ON ready_t TO ddp_local_replication;
    ALTER PUBLICATION ddp_legbot_publication ADD TABLE ready_t, unready_t" >/dev/null
run_sync
assert_eq "exit 1" "$RC" 1
assert_contains "FAIL names the table that needs the grant" "$OUT" "unready_t: in the publication but ddp_local_replication cannot SELECT it"
assert_contains "says the refresh was held back" "$OUT" "REFRESH PUBLICATION not run"
assert_not_contains "no refresh was executed" "$OUT" "APPLIED: ALTER SUBSCRIPTION"
assert_eq "neither table is subscribed (so no table-copy worker can crash-loop)" "$(sc "SELECT count(*) FROM pg_subscription_rel r JOIN pg_class c ON c.oid=r.srrelid WHERE c.relname IN ('ready_t','unready_t')")" 0
assert_eq "both exist locally, ready for the refresh" "$(sc "SELECT count(*) FROM pg_tables WHERE tablename IN ('ready_t','unready_t')")" 2
pc "GRANT SELECT ON unready_t TO ddp_local_replication" >/dev/null
run_sync
assert_eq "after the grant: exit 0" "$RC" 0
wait_for "both tables' rows arrive" "SELECT (SELECT count(*) FROM ready_t) + (SELECT count(*) FROM unready_t)" 2 40

echo; echo "== 7c. a generated column is not replicated, so a table with one is REFUSED before anything is created; an identity column is fine"
pc "CREATE TABLE gen_t (id int PRIMARY KEY, a int, b int GENERATED ALWAYS AS (a * 2) STORED); GRANT SELECT ON gen_t TO ddp_local_replication;
    ALTER PUBLICATION ddp_legbot_publication ADD TABLE gen_t" >/dev/null
run_sync
assert_eq "exit 1" "$RC" 1
assert_contains "FAIL says why" "$OUT" "gen_t: not created, has a generated column b (its value is not replicated)"
assert_eq "no local table was created" "$(sc "SELECT count(*) FROM pg_tables WHERE tablename='gen_t'")" 0
pc "ALTER PUBLICATION ddp_legbot_publication DROP TABLE gen_t; DROP TABLE gen_t" >/dev/null
pc "CREATE TABLE ident_t (id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY, v text); INSERT INTO ident_t (v) VALUES ('a'),('b');
    GRANT SELECT ON ident_t TO ddp_local_replication; ALTER PUBLICATION ddp_legbot_publication ADD TABLE ident_t" >/dev/null
run_sync
assert_eq "identity table: exit 0" "$RC" 0
wait_for "identity table's rows arrive (as plain values)" "SELECT count(*) FROM ident_t" 2 40
assert_eq "the Mac column is a plain column, not identity" "$(sc "SELECT is_identity FROM information_schema.columns WHERE table_name='ident_t' AND column_name='id'")" "NO"

echo; echo "== 7d. a published table with no primary key is REFUSED (the Mac could not apply updates to it)"
pc "CREATE TABLE nopk_t (v text); GRANT SELECT ON nopk_t TO ddp_local_replication; ALTER PUBLICATION ddp_legbot_publication ADD TABLE nopk_t" >/dev/null
run_sync
assert_eq "exit 1" "$RC" 1
assert_contains "FAIL says why" "$OUT" "nopk_t: has no primary key on RDS"
assert_eq "no local table was created" "$(sc "SELECT count(*) FROM pg_tables WHERE tablename='nopk_t'")" 0
pc "ALTER PUBLICATION ddp_legbot_publication DROP TABLE nopk_t; DROP TABLE nopk_t" >/dev/null

echo; echo "== 7e. a pending table that ALREADY exists locally but had a change refused is not subscribed, and nor is any other pending table"
sc "CREATE TABLE acc_t (id int PRIMARY KEY, v text); CREATE TABLE refuse_t (id int PRIMARY KEY, v text)" >/dev/null
pc "CREATE TABLE acc_t (id int PRIMARY KEY, v text, extra text); INSERT INTO acc_t VALUES (1,'a','e');
    CREATE TABLE refuse_t (id int PRIMARY KEY, v text, bad text NOT NULL DEFAULT 'x'); INSERT INTO refuse_t (id, v) VALUES (1,'r');
    ALTER TABLE refuse_t ALTER COLUMN bad DROP DEFAULT;
    GRANT SELECT ON acc_t, refuse_t TO ddp_local_replication;
    ALTER PUBLICATION ddp_legbot_publication ADD TABLE acc_t, refuse_t" >/dev/null
run_sync
assert_eq "exit 1" "$RC" 1
assert_contains "the refused column is named" "$OUT" "refuse_t.bad: new NOT NULL column with no default"
assert_contains "the acceptable table was still changed (all or nothing is per table)" "$OUT" "added column acc_t.extra (text)"
assert_contains "the refresh was held back" "$OUT" "REFRESH PUBLICATION not run"
assert_eq "NEITHER pending table is subscribed" "$(sc "SELECT count(*) FROM pg_subscription_rel r JOIN pg_class c ON c.oid=r.srrelid WHERE c.relname IN ('acc_t','refuse_t')")" 0
pc "ALTER TABLE refuse_t DROP COLUMN bad" >/dev/null
run_sync
assert_eq "once the refusal is gone: exit 0" "$RC" 0
assert_contains "the refresh runs" "$OUT" "APPLIED: ALTER SUBSCRIPTION"
wait_for "both tables' rows arrive" "SELECT (SELECT count(*) FROM acc_t) + (SELECT count(*) FROM refuse_t)" 2 40

echo; echo "== 8. a new RDS table that is not published: reported once as needing a decision; the search table never is"
pc "CREATE TABLE new_unpublished (id int PRIMARY KEY)" >/dev/null
run_sync
assert_eq "exit 1" "$RC" 1
assert_contains "names the new table" "$OUT" "new_unpublished: a table on RDS that the publication does not carry"
assert_not_contains "never mentions the search table" "$OUT" "ddp_bill_search:"
assert_not_contains "never mentions django_session" "$OUT" "django_session:"
echo "new_unpublished" >> "$T/state/structure-sync.known-unpublished"
run_sync; assert_eq "once acknowledged: exit 0" "$RC" 0

echo; echo "== 9. idempotent: a second run changes nothing"
run_sync; assert_contains "nothing to do" "$OUT" "Nothing to do"; assert_not_contains "no APPLIED lines" "$OUT" "APPLIED:"

echo; echo "== 10. dry run prints what it would do and changes nothing"
pc "ALTER TABLE opencivicdata_bill ADD COLUMN note2 text" >/dev/null
run_sync --dry-run
assert_contains "prints WOULD" "$OUT" 'WOULD: ALTER TABLE public."opencivicdata_bill" ADD COLUMN "note2" text'
assert_contains "labelled as a dry run" "$OUT" "DRY RUN"
assert_eq "local table unchanged" "$(sc "SELECT count(*) FROM information_schema.columns WHERE table_name='opencivicdata_bill' AND column_name='note2'")" 0
run_sync; assert_contains "the real run applies it" "$OUT" "added column opencivicdata_bill.note2"

echo; echo "== 11. what must survive: local-only tables, the locally built search table, no foreign keys, the local-only column"
assert_eq "profiles_profile row still there" "$(sc "SELECT api_key FROM profiles_profile WHERE id=1")" "local-only"
assert_eq "the locally built ddp_bill_search is untouched" "$(sc "SELECT doc FROM ddp_bill_search WHERE id=1")" "built locally"
assert_eq "no foreign key constraints locally" "$(sc "SELECT count(*) FROM pg_constraint WHERE contype='f'")" 0
assert_eq "the local-only column was not dropped" "$(sc "SELECT count(*) FROM information_schema.columns WHERE table_name='opencivicdata_bill' AND column_name='local_only_col'")" 1
assert_eq "ddp_bill_search is not in the subscription" "$(sc "SELECT count(*) FROM pg_subscription_rel r JOIN pg_class c ON c.oid=r.srrelid WHERE c.relname='ddp_bill_search'")" 0

echo; echo "== 12. one run at a time"
mkdir -p "$T/state/structure-sync.lock"; echo $$ > "$T/state/structure-sync.lock/pid"
run_sync
assert_eq "a live lock: exit 0" "$RC" 0
assert_contains "says another run is in progress" "$OUT" "another structure sync is running"
rm -rf "$T/state/structure-sync.lock"
sleep 0 & DEAD=$!; wait $DEAD
mkdir -p "$T/state/structure-sync.lock"; echo "$DEAD" > "$T/state/structure-sync.lock/pid"
run_sync
assert_contains "a stale lock (dead pid) is taken over" "$OUT" "Nothing to do"

echo; echo "== 13. bounded run time: a hung database call is cut off and the lock released"
mkdir -p "$T/stub"; printf '#!/bin/sh\nsleep 8\n' > "$T/stub/docker"; chmod +x "$T/stub/docker"
S0="$(date +%s)"
OUT="$(env PATH="$T/stub:$PATH" PG_CONTAINER=$SUB PG_USER=postgres RDS_HOST=$PUB RDS_DATABASE=openstates RDS_SSLMODE=disable \
    RDS_REPLICATION_PASSWORD=replpw STRUCTURE_SYNC_STATE_DIR="$T/state" STRUCTURE_SYNC_MAX_RUN_S=2 bash "$SYNC" repl 2>&1)"; RC=$?
ALL="$ALL
$OUT"
assert_eq "exit 1" "$RC" 1
assert_contains "says it timed out" "$OUT" "timed out after 2s"
[ $(( $(date +%s) - S0 )) -le 6 ] && ok "cut off well before the hung call would have finished" || bad "took too long"
[ ! -d "$T/state/structure-sync.lock" ] && ok "lock released" || bad "lock left behind"

echo; echo "== 14. the credential"
OUT="$(env -u RDS_HOST -u RDS_REPLICATION_PASSWORD STRUCTURE_SYNC_STATE_DIR="$T/state" STRUCTURE_SYNC_ENV_FILE="$T/none.env" bash "$SYNC" repl 2>&1)"; RC=$?
assert_eq "no credential: exit 3 (skipped, not failed)" "$RC" 3
printf 'RDS_HOST=%s\nRDS_DATABASE=openstates\nRDS_REPLICATION_PASSWORD=replpw\n' "$PUB" > "$T/ok.env"; chmod 644 "$T/ok.env"
OUT="$(env -u RDS_HOST -u RDS_REPLICATION_PASSWORD STRUCTURE_SYNC_STATE_DIR="$T/state" STRUCTURE_SYNC_ENV_FILE="$T/ok.env" bash "$SYNC" repl 2>&1)"; RC=$?
ALL="$ALL
$OUT"
assert_eq "a group/world-readable credential file is refused" "$RC" 1
assert_contains "says to chmod 600" "$OUT" "must be mode 600"
chmod 600 "$T/ok.env"
OUT="$(env -u RDS_HOST -u RDS_REPLICATION_PASSWORD PG_CONTAINER=$SUB PG_USER=postgres RDS_SSLMODE=disable STRUCTURE_SYNC_STATE_DIR="$T/state" STRUCTURE_SYNC_ENV_FILE="$T/ok.env" bash "$SYNC" repl 2>&1)"; RC=$?
ALL="$ALL
$OUT"
assert_eq "a mode-600 file is read and works" "$RC" 0
assert_not_contains "the password never appears in any output of any run" "$ALL" "replpw"

echo; echo "MEASURED STALL WINDOW: $STALL_LINE"
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && { echo "ALL PASS"; exit 0; } || exit 1
