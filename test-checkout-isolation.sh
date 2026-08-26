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

# OPEN-164: build a sandboxed copy of the checkout whose idea of "production" is a
# throwaway directory. Shared by run_guard() and the LOG_DIR block further down.
#
# Echoes the sandbox path.
make_sandbox() {   # <fake-production-dir> [production-checkout-override]
    local fake_prod="$1"
    local prod_constant="${2:-$fake_prod}"
    local sandbox; sandbox=$(mktemp -d "$TMP_ROOT/sandbox.XXXXXX")
    mkdir -p "$fake_prod/logs/last-run"
    # ONLY run-scrape.sh is rewritten. activate.sh is copied verbatim on purpose: its
    # production fallbacks are INPUTS (the venv, the scrapers tree, the people checkout)
    # and OPEN-159's rule explicitly permits those -- pointing them at an empty fake
    # directory would break the run for an unrelated reason. What must be neutralised is
    # every production path in run-scrape.sh, because those are the OUTPUT ones.
    sed "s|/Users/agentsmith/Developer/repos/ddp-open-states|$prod_constant|g" \
        "$SCRIPT_DIR/run-scrape.sh" > "$sandbox/run-scrape.sh"
    cp "$SCRIPT_DIR/activate.sh" "$SCRIPT_DIR/import-summary.sh" "$sandbox/"
    chmod +x "$sandbox/run-scrape.sh"

    # DEFENCE IN DEPTH (pm-review round 1, and its strongest point). Everything above
    # depends on run-scrape.sh's refusal guard firing. If that guard is ever reordered or
    # broken -- exactly the regression this suite exists to catch -- the sandbox alone would
    # not stop a real scrape, because DATABASE_URL_OVERRIDE is deliberately unset here (it
    # has to be: its absence is what the refusal is being tested for).
    #
    # So the sandbox gets its own venv holding a SENTINEL os-update. activate.sh prefers a
    # checkout-local .venv, so this is what any scrape or import would actually execute. It
    # cannot reach a database or a legislature site; it records that it was reached and
    # fails. Callers assert the marker never appears.
    mkdir -p "$sandbox/.venv/bin"
    cat > "$sandbox/.venv/bin/os-update" <<SENTINEL
#!/usr/bin/env bash
echo "REACHED" >> "$TMP_ROOT/sentinel-os-update-was-run"
echo "SENTINEL: a real os-update would have run here" >&2
exit 87
SENTINEL
    chmod +x "$sandbox/.venv/bin/os-update"
    # Creating a .venv makes activate.sh prefer it over production's, so the interpreter
    # run-scrape.sh uses to inspect which scrapers a jurisdiction registers has to exist
    # too. Symlinked to the real one: running python is harmless, and it is os-update --
    # the thing that reaches a database and a legislature site -- that must stay a sentinel.
    if [ -x "$PRODUCTION_CHECKOUT/.venv/bin/python" ]; then
        ln -sf "$PRODUCTION_CHECKOUT/.venv/bin/python" "$sandbox/.venv/bin/python"
    fi
    echo "$sandbox"
}

run_guard() {
    # OPEN-164: runs a SANDBOXED COPY, not $SCRIPT_DIR/run-scrape.sh directly.
    #
    # The old comment here read "this worktree's run-scrape.sh, which is by definition not
    # the production checkout" -- and that assumption inverts the moment somebody runs this
    # suite from the production checkout, which is the ordinary place to run a repo's own
    # tests. There run-scrape.sh does NOT refuse: it starts a REAL Virginia scrape, against
    # the live site and the production database, because DATABASE_URL_OVERRIDE is unset.
    # A test asserting "a real scrape is refused" would have performed one.
    #
    # A sandbox fixes it structurally rather than by asking the operator to remember: the
    # copy is never the production checkout, wherever this suite is run from, so the refusal
    # the assertions below expect is the real behaviour rather than an accident of location.
    local logdir="$TMP_ROOT/logs-$RANDOM"
    mkdir -p "$logdir/last-run"
    local sandbox; sandbox=$(make_sandbox "$TMP_ROOT/fake-prod-$RANDOM")
    # Recorded to a file, not a variable: run_guard is called inside $( ), so any
    # assignment it makes dies with the subshell.
    echo "$sandbox" > "$TMP_ROOT/last-guard-checkout"
    env LOG_DIR="$logdir" SKIP_PATCHES=1 "$@" \
        bash "$sandbox/run-scrape.sh" va >"$logdir/out" 2>&1
    local rc=$?
    printf '%s|%s' "$rc" "$(cat "$logdir/out")"
}

out=$(run_guard); rc="${out%%|*}"; body="${out#*|}"
check "refuses with EXIT_DO_NOT_RETRY (90)" "90" "$rc"
assert_contains "says why" "refusing to run from a non-production checkout" "$body"
# The property is "the message names the checkout the run happened in", which is the
# sandbox now, not $SCRIPT_DIR. Same assertion, correct subject.
assert_contains "names the checkout it is in" "$(cat "$TMP_ROOT/last-guard-checkout")" "$body"
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

echo "== OPEN-172: LOG_DIR follows the checkout, so a dev run cannot touch production's markers =="

# This block runs the scrape against a SANDBOXED COPY of the checkout whose idea of
# "production" is a throwaway directory. That is structural, not a convention: pm-review
# round 1 rightly refused to accept a comment warning here, and it was right to -- verifying
# the assertion by reintroducing the old absolute default made the test itself overwrite
# production's real va.ts on 2026-08-26, which had to be recovered from scraper.log. A test
# whose entire purpose is preventing production-state corruption must not be able to cause
# it, on any version of the code it might be pointed at.
FAKE_PROD="$TMP_ROOT/fake-production"
SANDBOX=$(make_sandbox "$FAKE_PROD")
# Deliberately NOT creating $SANDBOX/logs -- run-scrape.sh must create it itself, which is
# a real requirement now that LOG_DIR follows the checkout.
mkdir -p "$SANDBOX/data/va" "$SANDBOX/cache"

OK_STUB="$TMP_ROOT/stub-os-update-ok"
printf '#!/usr/bin/env bash\nexit 0\n' > "$OK_STUB"
chmod +x "$OK_STUB"

fake_prod_fingerprint() {
    find "$FAKE_PROD/logs/last-run" -type f 2>/dev/null | sort | while read -r f; do
        printf '%s ' "$f"; cat "$f" 2>/dev/null; printf '\n'
    done | (md5 2>/dev/null || md5sum)
}
FP_BEFORE=$(fake_prod_fingerprint)

# LOG_DIR deliberately unset -- the exact shape ddp-sync uses, which passes SKIP_PATCHES
# but never LOG_DIR. This is what makes the default itself the thing under test.
env -u LOG_DIR OS_UPDATE_OVERRIDE="$OK_STUB" \
    SCRAPED_DATA_DIR_OVERRIDE="$SANDBOX/data" \
    CACHE_DIR_OVERRIDE="$SANDBOX/cache" \
    SUPPRESS_FAILURE_ALERT=1 SKIP_PATCHES=1 \
    bash "$SANDBOX/run-scrape.sh" va > "$TMP_ROOT/sandbox-run.log" 2>&1

if [ -f "$SANDBOX/logs/last-run/va.ts" ]; then
    PASS=$((PASS + 1)); echo "  ok   markers land in the running checkout's own logs/last-run"
else
    FAIL=$((FAIL + 1)); echo "  FAIL markers did not land in the running checkout's logs/last-run"
fi

if [ "$FP_BEFORE" = "$(fake_prod_fingerprint)" ]; then
    PASS=$((PASS + 1)); echo "  ok   the production checkout's logs/last-run is untouched"
else
    FAIL=$((FAIL + 1)); echo "  FAIL a run from another checkout wrote the production checkout's markers"
fi

# The sweep AC: the only absolute production path left must be the refusal guard's own
# constant. Asserted by identifying the line, not by counting occurrences -- a count of one
# would still pass if some future absolute OUTPUT path replaced the guard.
STRAY=$(grep -n "/Users/agentsmith/Developer/repos/ddp-open-states" "$SCRIPT_DIR/run-scrape.sh" \
        | grep -vc "^[0-9]*:PRODUCTION_CHECKOUT=")
if [ "$STRAY" -eq 0 ]; then
    PASS=$((PASS + 1)); echo "  ok   the only absolute production path is PRODUCTION_CHECKOUT itself"
else
    FAIL=$((FAIL + 1)); echo "  FAIL $STRAY absolute production path(s) outside PRODUCTION_CHECKOUT"
fi

echo "== OPEN-164: this suite is safe to run from the production checkout =="

# The bug: run_guard used to invoke $SCRIPT_DIR/run-scrape.sh directly, on the assumption
# that it was "by definition not the production checkout". Run this suite from the
# production checkout -- the ordinary place to run a repo's own tests -- and that inverts.
# There run-scrape.sh does not refuse, so the test asserting "a real scrape is refused"
# would instead have STARTED one: a real Virginia scrape against the live site and the
# production database, since DATABASE_URL_OVERRIDE is unset.
#
# Asserted against the source, because the failure only manifests in the one location this
# suite cannot safely be run in to demonstrate it.
GUARD_BODY=$(sed -n '/^run_guard()/,/^}/p' "$SCRIPT_DIR/test-checkout-isolation.sh")
case "$GUARD_BODY" in
    *'bash "$SCRIPT_DIR/run-scrape.sh"'*)
        FAIL=$((FAIL + 1))
        echo "  FAIL run_guard invokes \$SCRIPT_DIR/run-scrape.sh — starts a REAL scrape in production" ;;
    *)
        PASS=$((PASS + 1))
        echo "  ok   run_guard does not invoke this checkout's run-scrape.sh directly" ;;
esac

case "$GUARD_BODY" in
    *make_sandbox*)
        PASS=$((PASS + 1)); echo "  ok   run_guard runs a sandboxed copy instead" ;;
    *)
        FAIL=$((FAIL + 1)); echo "  FAIL run_guard no longer uses a sandbox" ;;
esac

# And the sandbox's own production constant must not be the real one, or the sandbox is
# cosmetic.
SB=$(make_sandbox "$TMP_ROOT/fake-prod-assert")
if grep -q "^PRODUCTION_CHECKOUT=.*$TMP_ROOT/fake-prod-assert" "$SB/run-scrape.sh"; then
    PASS=$((PASS + 1)); echo "  ok   the sandbox's PRODUCTION_CHECKOUT is a throwaway directory"
else
    FAIL=$((FAIL + 1)); echo "  FAIL the sandbox still points at the real production checkout"
fi

# The behavioural proof this ticket actually wants, obtained safely. A sandbox whose
# PRODUCTION_CHECKOUT is ITSELF is, from run-scrape.sh's own point of view, the production
# checkout -- which is the situation that inverts the old assumption. Running it here
# reproduces "the suite launched from production" without going near the real one.
# Assert here, BEFORE the deliberate simulation below: no guard test may have reached a
# scraper at all. Counting afterwards is wrong -- the simulation legitimately invokes
# os-update more than once, because run-scrape.sh retries with --fastmode.
if [ -f "$TMP_ROOT/sentinel-os-update-was-run" ]; then
    FAIL=$((FAIL + 1))
    echo "  FAIL a guard test reached os-update — it attempted a real scrape"
else
    PASS=$((PASS + 1))
    echo "  ok   no guard test reached os-update"
fi

PROD_SIM=$(mktemp -d "$TMP_ROOT/prodsim.XXXXXX")
SB_PROD=$(make_sandbox "$TMP_ROOT/fake-prod-sim" "$PROD_SIM")
# Move it so its own path IS the production constant it was built with.
rm -rf "$PROD_SIM"; mv "$SB_PROD" "$PROD_SIM"
mkdir -p "$TMP_ROOT/prodsim-data/va" "$TMP_ROOT/prodsim-cache"

env LOG_DIR="$TMP_ROOT/prodsim-logs" SKIP_PATCHES=1 \
    SCRAPED_DATA_DIR_OVERRIDE="$TMP_ROOT/prodsim-data" \
    CACHE_DIR_OVERRIDE="$TMP_ROOT/prodsim-cache" \
    SUPPRESS_FAILURE_ALERT=1 \
    bash "$PROD_SIM/run-scrape.sh" va > "$TMP_ROOT/prodsim.out" 2>&1

# It does NOT refuse here -- that is the whole point, and why the old run_guard was unsafe.
if grep -q "refusing to run from a non-production checkout" "$TMP_ROOT/prodsim.out"; then
    FAIL=$((FAIL + 1))
    echo "  FAIL a checkout that IS production refused -- the premise of this ticket is wrong"
else
    PASS=$((PASS + 1))
    echo "  ok   a checkout that IS production does not refuse (this is why run_guard had to change)"
fi

# (The sentinel's own stderr goes into scraper.log via run-scrape.sh's tee pipeline, not
# into the captured stdout, so the marker file below -- not this output -- is what proves
# os-update was reached.)

# And it must have been the simulation that reached it -- otherwise the simulation proved
# nothing, and the sentinel would be passing for the wrong reason. This is also the
# assertion showing what the old run_guard would have cost: from a checkout that IS
# production, run-scrape.sh goes straight on to os-update, which in the real one is a live
# Virginia scrape against the production database.
if [ -f "$TMP_ROOT/sentinel-os-update-was-run" ]; then
    PASS=$((PASS + 1))
    echo "  ok   the simulation reached os-update, so the sentinel is what stopped a real scrape"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL the simulation never reached os-update — it is not exercising the risk"
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
