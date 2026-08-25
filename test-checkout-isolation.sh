#!/usr/bin/env bash
# test-checkout-isolation.sh — OPEN-159: a checkout must use ITS OWN environment, not production's
#
#     bash test-checkout-isolation.sh
#
# Same shape as the other test-*.sh here: no network, no database, no production paths, a mktemp
# dir per run, "ALL PASS (N assertions)" and exit 0 or the first failure and exit 1.
#
# What is being guarded, and why it is worth a suite of its own:
#
# run-scrape.sh used to source activate.sh by ABSOLUTE PATH into the production checkout. Since
# activate.sh is git-tracked and every checkout's copy is byte-identical, the dev checkout at
# ~/Developer/repos/ddp-open-states-dev inherited production's data dirs AND production's
# database. So `./run-scrape.sh az` there scraped into production's _data/az -- which
# openstates-core wipes at scrape start -- and imported into the production database. The dev
# checkout, whose entire purpose is isolation, provided none for the repo's main entrypoint.
#
# Two halves, and BOTH are needed or neither works:
#   * activate.sh derives its paths from $SCRIPT_DIR (the dir it lives in), so files follow the
#     checkout. In production these resolve byte-identically to the old hardcoded values.
#   * a database NAME cannot be derived from a path, so run-scrape.sh refuses to run a real
#     scrape from a non-production checkout unless DATABASE_URL_OVERRIDE says where to import.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PRODUCTION_CHECKOUT="/Users/agentsmith/Developer/repos/ddp-open-states"
TMP_ROOT=$(mktemp -d /tmp/checkout-isolation-test.XXXXXX)
trap 'rm -rf "$TMP_ROOT"' EXIT

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

assert_contains() {
    local desc="$1" needle="$2" haystack="$3"
    case "$haystack" in
        *"$needle"*) PASS=$((PASS + 1)); echo "  ok   $desc" ;;
        *) FAIL=$((FAIL + 1)); echo "  FAIL $desc — expected to find [$needle]" ;;
    esac
}

# ---------------------------------------------------------------------------
echo "== activate.sh follows the checkout it lives in =="

# Source this repo's activate.sh from a COPY placed in a throwaway directory, and confirm the
# paths it exports point at that directory rather than at production. Uses a subshell so the
# exports cannot leak into the rest of this test run.
# A checkout that HAS the gitignored nested checkouts — i.e. what production and
# ddp-open-states-dev look like. Everything must resolve to itself.
FAKE_CHECKOUT="$TMP_ROOT/pretend-checkout"
mkdir -p "$FAKE_CHECKOUT/openstates-scrapers/scrapers" "$FAKE_CHECKOUT/people" "$FAKE_CHECKOUT/.venv"
cp "$SCRIPT_DIR/activate.sh" "$FAKE_CHECKOUT/activate.sh"

got=$(
    # shellcheck disable=SC1091
    source "$FAKE_CHECKOUT/activate.sh" >/dev/null 2>&1
    printf '%s|%s|%s|%s|%s' \
        "$SCRAPED_DATA_DIR" "$CACHE_DIR" "$PYTHONPATH" "$OS_PEOPLE_DIRECTORY" "$OS_VENV"
)
check "SCRAPED_DATA_DIR follows the checkout" \
    "$FAKE_CHECKOUT/openstates-scrapers/_data" "$(echo "$got" | cut -d'|' -f1)"
check "CACHE_DIR follows the checkout" \
    "$FAKE_CHECKOUT/openstates-scrapers/_cache" "$(echo "$got" | cut -d'|' -f2)"
check "PYTHONPATH follows the checkout when it has scrapers" \
    "$FAKE_CHECKOUT/openstates-scrapers/scrapers" "$(echo "$got" | cut -d'|' -f3)"
check "OS_PEOPLE_DIRECTORY follows the checkout when it has people" \
    "$FAKE_CHECKOUT/people" "$(echo "$got" | cut -d'|' -f4)"
check "OS_VENV follows the checkout when it has one" \
    "$FAKE_CHECKOUT/.venv" "$(echo "$got" | cut -d'|' -f5)"

# The regression that matters most: for a fully-populated checkout, nothing may still name
# production. This is the assertion that would have caught the original bug.
case "$got" in
    *"$PRODUCTION_CHECKOUT"*)
        FAIL=$((FAIL + 1)); echo "  FAIL no exported path still points at production" ;;
    *) PASS=$((PASS + 1)); echo "  ok   no exported path still points at production" ;;
esac

echo "== inputs may fall back to production; outputs never may =="

# A git WORKTREE: no gitignored nested checkouts at all. This is the case that broke the existing
# test suites when the first version of this fix made everything strictly checkout-relative.
BARE_WORKTREE="$TMP_ROOT/pretend-worktree"
mkdir -p "$BARE_WORKTREE"
cp "$SCRIPT_DIR/activate.sh" "$BARE_WORKTREE/activate.sh"

got=$(
    # shellcheck disable=SC1091
    source "$BARE_WORKTREE/activate.sh" >/dev/null 2>&1
    printf '%s|%s|%s|%s|%s' \
        "$PYTHONPATH" "$OS_PEOPLE_DIRECTORY" "$OS_VENV" "$SCRAPED_DATA_DIR" "$CACHE_DIR"
)
# Inputs: borrowing production's code and interpreter is what lets a worktree run at all.
check "PYTHONPATH falls back to production" \
    "$PRODUCTION_CHECKOUT/openstates-scrapers/scrapers" "$(echo "$got" | cut -d'|' -f1)"
check "OS_PEOPLE_DIRECTORY falls back to production" \
    "$PRODUCTION_CHECKOUT/people" "$(echo "$got" | cut -d'|' -f2)"
check "OS_VENV falls back to production" \
    "$PRODUCTION_CHECKOUT/.venv" "$(echo "$got" | cut -d'|' -f3)"
# Outputs: must NOT fall back. A worktree that writes into production's _data is the bug.
check "SCRAPED_DATA_DIR does NOT fall back to production" \
    "$BARE_WORKTREE/openstates-scrapers/_data" "$(echo "$got" | cut -d'|' -f4)"
check "CACHE_DIR does NOT fall back to production" \
    "$BARE_WORKTREE/openstates-scrapers/_cache" "$(echo "$got" | cut -d'|' -f5)"

echo "== production is unchanged (this must be a no-op there) =="

# Sourcing the real production activate.sh must produce exactly the paths it always did. If this
# fails, the fix has moved production's data and that is a far worse bug than the one being fixed.
if [ -f "$PRODUCTION_CHECKOUT/activate.sh" ]; then
    prod=$(
        # shellcheck disable=SC1091
        source "$PRODUCTION_CHECKOUT/activate.sh" >/dev/null 2>&1
        printf '%s|%s' "$SCRAPED_DATA_DIR" "$CACHE_DIR"
    )
    check "production SCRAPED_DATA_DIR unchanged" \
        "$PRODUCTION_CHECKOUT/openstates-scrapers/_data" "$(echo "$prod" | cut -d'|' -f1)"
    check "production CACHE_DIR unchanged" \
        "$PRODUCTION_CHECKOUT/openstates-scrapers/_cache" "$(echo "$prod" | cut -d'|' -f2)"
else
    echo "  skip production checkout not present"
fi

echo "== DATABASE_URL takes an explicit override, and only an explicit one =="

db_from_env() {
    (
        # shellcheck disable=SC1091
        source "$FAKE_CHECKOUT/activate.sh" >/dev/null 2>&1
        printf '%s' "$DATABASE_URL"
    )
}

got=$(db_from_env)
assert_contains "no override -> the production database" "/openstates" "$got"

got=$(DATABASE_URL_OVERRIDE="postgresql://u:p@localhost:5433/openstates_dev" db_from_env)
check "DATABASE_URL_OVERRIDE is honoured" \
    "postgresql://u:p@localhost:5433/openstates_dev" "$got"

# Keyed on a purpose-named variable rather than DATABASE_URL itself, deliberately. This script is
# invoked by ddp-sync, which passes its entire process environment through — so honouring a bare
# inherited DATABASE_URL would let an unrelated service's connection string silently become the
# import target. A variable named DATABASE_URL_OVERRIDE cannot be set by accident.
got=$(DATABASE_URL="postgresql://someone-elses-service/whatever" db_from_env)
check "a stray inherited DATABASE_URL is ignored, not adopted" \
    "postgresql://openstates:openstates_dev@localhost:5433/openstates" "$got"

echo "== run-scrape.sh refuses a real run from a non-production checkout =="

run_guard() {
    # Runs this worktree's run-scrape.sh, which is by definition not the production checkout.
    # LOG_DIR is redirected so nothing is written to production's scraper.log.
    local logdir="$TMP_ROOT/logs-$RANDOM"
    mkdir -p "$logdir/last-run"
    env LOG_DIR="$logdir" SKIP_PATCHES=1 "$@" \
        bash "$SCRIPT_DIR/run-scrape.sh" va >"$logdir/out" 2>&1
    local rc=$?
    printf '%s|%s' "$rc" "$(cat "$logdir/out")"
}

out=$(run_guard); rc="${out%%|*}"; body="${out#*|}"
check "refuses with EXIT_DO_NOT_RETRY (90)" "90" "$rc"
assert_contains "says why" "refusing to run from a non-production checkout" "$body"
assert_contains "names the checkout it is in" "$SCRIPT_DIR" "$body"
# The message has to say what to DO, not just that it stopped — this fires on a machine where
# somebody is trying to test something and needs the next step, not a diagnosis.
assert_contains "says how to proceed" "DATABASE_URL_OVERRIDE" "$body"

echo "== but it does not block the legitimate ways to run from elsewhere =="

# A stub os-update means nothing reaches a database, which is how every other test-*.sh here
# drives this script. Those suites must keep working without declaring a database.
STUB="$TMP_ROOT/stub-os-update"
printf '#!/usr/bin/env bash\necho "openstates.exceptions.ScrapeError: no objects returned from VaBillScraper scrape"\nexit 1\n' > "$STUB"
chmod +x "$STUB"
out=$(run_guard OS_UPDATE_OVERRIDE="$STUB" \
                SCRAPED_DATA_DIR_OVERRIDE="$TMP_ROOT/data" \
                CACHE_DIR_OVERRIDE="$TMP_ROOT/cache")
rc="${out%%|*}"; body="${out#*|}"
if [ "$rc" = "90" ]; then
    FAIL=$((FAIL + 1)); echo "  FAIL a stubbed os-update must not be refused (this would break every other suite)"
else
    PASS=$((PASS + 1)); echo "  ok   a stubbed os-update is not refused"
fi

# An explicit database override is the documented way to run a real scrape from a dev checkout.
out=$(run_guard DATABASE_URL_OVERRIDE="postgresql://u:p@localhost:5433/openstates_dev" \
                OS_UPDATE_OVERRIDE="$STUB" \
                SCRAPED_DATA_DIR_OVERRIDE="$TMP_ROOT/data2" \
                CACHE_DIR_OVERRIDE="$TMP_ROOT/cache2")
rc="${out%%|*}"
if [ "$rc" = "90" ]; then
    FAIL=$((FAIL + 1)); echo "  FAIL an explicit DATABASE_URL_OVERRIDE must be accepted"
else
    PASS=$((PASS + 1)); echo "  ok   an explicit DATABASE_URL_OVERRIDE is accepted"
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
