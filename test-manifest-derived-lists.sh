#!/usr/bin/env bash
# test-manifest-derived-lists.sh -- OPEN-327: the scripts that used to carry a hand-typed jurisdiction list
# now derive it from jurisdictions.yaml. This pins the behavior that matters, under the real /bin/bash 3.2:
#   - activate.sh exports ARCHIVE_ENABLED_STATES equal to the manifest's archive.enabled set
#   - a missing or broken manifest leaves that list EMPTY with a loud warning (fail closed), never a stale list
#   - the people-refresh, smoke-test and allow-duplicates sets are readable from the real manifest
# No network, no database, no production paths. The drift checker (check-jurisdiction-drift.py) separately
# fails if a script stops deriving or grows a literal list again.
#
#     bash test-manifest-derived-lists.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PASS=0
FAIL=0

check() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        PASS=$((PASS + 1)); echo "  ok   $desc"
    else
        FAIL=$((FAIL + 1)); echo "  FAIL $desc"
        echo "         expected: [$expected]"
        echo "         actual  : [$actual]"
    fi
}

# activate.sh sources the checkout's .env and exports paths; none of that is touched here beyond reading
# ARCHIVE_ENABLED_STATES afterwards. DATABASE_URL_OVERRIDE is set so its production-database warning stays quiet.
export DATABASE_URL_OVERRIDE="postgresql://unused/unused"

expected=$("$SCRIPT_DIR/jurisdiction-field.sh" --codes archive.enabled)
actual=$(bash -c 'source "$1/activate.sh" >/dev/null 2>&1; echo "$ARCHIVE_ENABLED_STATES"' _ "$SCRIPT_DIR")
check "activate.sh: ARCHIVE_ENABLED_STATES is the manifest's archive.enabled set" "$expected" "$actual"

case ",$actual," in *,nc,*) hasnc=yes ;; *) hasnc=no ;; esac
check "activate.sh: NC (archive.enabled in the manifest) is on the list" "yes" "$hasnc"

# fail closed and loud: an unreadable manifest must not leave a stale list behind
actual=$(JURISDICTIONS_YAML=/nonexistent/jurisdictions.yaml bash -c 'source "$1/activate.sh" 2>/dev/null >/dev/null; echo "[$ARCHIVE_ENABLED_STATES]"' _ "$SCRIPT_DIR")
check "activate.sh: missing manifest leaves the list empty" "[]" "$actual"

warn=$(JURISDICTIONS_YAML=/nonexistent/jurisdictions.yaml bash -c 'source "$1/activate.sh" 2>&1 >/dev/null' _ "$SCRIPT_DIR" | grep -c "WARNING: could not read archive.enabled")
check "activate.sh: missing manifest prints a loud warning" "1" "$warn"

BAD=$(mktemp /tmp/manifest-bad.XXXXXX.yaml)
trap 'rm -f "$BAD"' EXIT
printf 'us:\n  archive: {enabled: "maybe"}\n' > "$BAD"
actual=$(JURISDICTIONS_YAML="$BAD" bash -c 'source "$1/activate.sh" 2>/dev/null >/dev/null; echo "[$ARCHIVE_ENABLED_STATES]"' _ "$SCRIPT_DIR")
check "activate.sh: a non-boolean archive.enabled leaves the list empty" "[]" "$actual"

# the other derived lists are non-empty on the real manifest (an empty one is an error in run-people-refresh.sh)
for f in enrollment.people_refresh enrollment.api_smoke_test scrape.allow_duplicates enrollment.qa_sweep; do
    out=$("$SCRIPT_DIR/jurisdiction-field.sh" --codes "$f")
    [ -n "$out" ] && ok=yes || ok=no
    check "real manifest: $f lists at least one jurisdiction" "yes" "$ok"
done

# NC is the state the hand-kept people-refresh list forgot; once the manifest says so it is picked up
printf 'nc:\n  enrollment: {people_refresh: true}\nfl:\n  enrollment: {people_refresh: false}\n' > "$BAD"
out=$("$SCRIPT_DIR/jurisdiction-field.sh" --codes enrollment.people_refresh "$BAD" 2>&1 || true)
check "enrolling a state in the manifest is all it takes" "nc" "$out"

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
