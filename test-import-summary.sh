#!/usr/bin/env bash
# test-import-summary.sh — fixture tests for import-summary.sh (OPEN-139)
#
# No network, no production paths, no database: every fixture is a text file in a mktemp dir
# holding real openstates-core import output. Run it anywhere:
#     bash test-import-summary.sh
# Exits 0 with "ALL PASS" or 1 with the first failing assertion.
#
# Same shape as test-check-scrape-staleness.sh (OPEN-40).

set -u

. "$(cd "$(dirname "$0")" && pwd)/import-summary.sh"

TMPDIR_ROOT=$(mktemp -d /tmp/import-summary-test.XXXXXX)
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

PASS=0
FAIL=0

fixture() {  # <name> <heredoc content on stdin> -> echoes the path
    local p="$TMPDIR_ROOT/$1"
    cat > "$p"
    echo "$p"
}

assert_eq() {  # <label> <actual> <expected>
    if [ "$2" = "$3" ]; then
        PASS=$((PASS + 1)); echo "  ok   $1"
    else
        FAIL=$((FAIL + 1)); echo "  FAIL $1"; echo "         expected: '$3'"; echo "         actual:   '$2'"
    fi
}

assert_stuck() {  # <label> <mode> <scraped> <new> <updated>
    if import_looks_stuck "$2" "$3" "$4" "$5"; then
        PASS=$((PASS + 1)); echo "  ok   $1"
    else
        FAIL=$((FAIL + 1)); echo "  FAIL $1 — expected STUCK, got not-stuck"
    fi
}

assert_not_stuck() {  # <label> <mode> <scraped> <new> <updated>
    if import_looks_stuck "$2" "$3" "$4" "$5"; then
        FAIL=$((FAIL + 1)); echo "  FAIL $1 — expected not-stuck, got STUCK"
    else
        PASS=$((PASS + 1)); echo "  ok   $1"
    fi
}

assert_collapsed() {  # <label> <mode> <prev_mode> <prev_new> <this_new>
    if new_bills_collapsed "$2" "$3" "$4" "$5"; then
        PASS=$((PASS + 1)); echo "  ok   $1"
    else
        FAIL=$((FAIL + 1)); echo "  FAIL $1 — expected COLLAPSED, got not-collapsed"
    fi
}

assert_not_collapsed() {  # <label> <mode> <prev_mode> <prev_new> <this_new>
    if new_bills_collapsed "$2" "$3" "$4" "$5"; then
        FAIL=$((FAIL + 1)); echo "  FAIL $1 — expected not-collapsed, got COLLAPSED"
    else
        PASS=$((PASS + 1)); echo "  ok   $1"
    fi
}

echo "== parse_import_bill_counts =="

# Arizona, verbatim from logs/scraper.log for the 2026-08-08 run. The whole reason this ticket
# exists: 895 files collected, nothing new in any of them.
AZ=$(fixture az.txt <<'EOF'
23:34:16 INFO root: Module: az
23:34:16 INFO openstates: import jurisdictions...
23:34:16 INFO openstates: import bills...
az (import)
  events: {}
  bills: {}
import:
  bill: 0 new 0 updated 895 noop
  jurisdiction: 0 new 0 updated 1 noop
EOF
)
assert_eq "arizona's real stuck report" "$(parse_import_bill_counts "$AZ")" "0:0:895"

HEALTHY=$(fixture healthy.txt <<'EOF'
import:
  bill: 37 new 83 updated 168 noop
  jurisdiction: 0 new 0 updated 1 noop
EOF
)
assert_eq "a healthy run with real new bills" "$(parse_import_bill_counts "$HEALTHY")" "37:83:168"

# Sweep-import (OPEN-86) performs several imports in one run, each printing its own report.
# Only the last covers the whole run.
SWEEP=$(fixture sweep.txt <<'EOF'
import:
  bill: 5 new 0 updated 0 noop
import:
  bill: 12 new 4 updated 30 noop
import:
  bill: 40 new 9 updated 51 noop
EOF
)
assert_eq "sweep-import takes the last report" "$(parse_import_bill_counts "$SWEEP")" "40:9:51"

# A report with no bill line at all (e.g. a people-only import). Must echo nothing, NOT "0:0:0" —
# the caller has to be able to tell "couldn't measure" from "measured zero".
NOBILLS=$(fixture nobills.txt <<'EOF'
import:
  jurisdiction: 0 new 0 updated 1 noop
processed 631 person files, 0 created, 0 updated
EOF
)
assert_eq "no bill line yields empty, not a fake zero" "$(parse_import_bill_counts "$NOBILLS")" ""

TRUNCATED=$(fixture truncated.txt <<'EOF'
import:
  bill: 12 new 3 upd
EOF
)
assert_eq "a truncated line yields empty rather than a wrong number" "$(parse_import_bill_counts "$TRUNCATED")" ""

assert_eq "an unreadable file yields empty" "$(parse_import_bill_counts "$TMPDIR_ROOT/does-not-exist")" ""

# 'bill' must not match 'billsomething' or a vote/person line that happens to contain the word.
OTHER=$(fixture other.txt <<'EOF'
import:
  vote_event: 8 new 0 updated 12 noop
  bill_version: 3 new 0 updated 0 noop
EOF
)
assert_eq "does not match vote_event or bill_version lines" "$(parse_import_bill_counts "$OTHER")" ""

echo "== import_looks_stuck =="
assert_stuck     "arizona: incremental, 895 scraped, 0 new, 0 updated"  incremental 895 0 0
assert_not_stuck "healthy: 200 scraped, 37 new, 83 updated"             incremental 200 37 83
assert_not_stuck "changes only: 200 scraped, 0 new, 12 updated"         incremental 200 0 12
assert_not_stuck "new only: 200 scraped, 5 new, 0 updated"              incremental 200 5 0
# The out-of-session case. Nothing scraped and nothing imported is an ordinary quiet run, and
# must stay silent or every recess would page somebody every night.
assert_not_stuck "quiet: 0 scraped, 0 new, 0 updated"                   incremental 0 0 0
# A full re-scrape of an already-imported session writes every file and imports nothing new.
# That is "already up to date", not stuck -- and it is a real workflow: FL's 2023/2024/2025
# historical backfills each re-scraped 1,800+ bills. This is the false positive pm-review raised.
assert_not_stuck "full rescrape of an up-to-date session is not stuck"  full 1828 0 0
assert_not_stuck "full mode never fires even at arizona's numbers"      full 895 0 0
assert_not_stuck "missing args stay quiet"                              "" "" "" ""

echo "== new_bills_collapsed =="
assert_collapsed     "120 new last run, 3 this run"                 incremental incremental 120 3
assert_collapsed     "exactly at the boundary: 100 -> 19"           incremental incremental 100 19
assert_not_collapsed "at the threshold, not under it: 100 -> 20"    incremental incremental 100 20
assert_not_collapsed "steady: 120 -> 118"                           incremental incremental 120 118
assert_not_collapsed "growing: 40 -> 300"                           incremental incremental 40 300
# Below 11 the ratio is noise -- same floor the original bills_scraped check used.
assert_not_collapsed "small previous run: 8 -> 0 is not a signal"   incremental incremental 8 0
# Only incremental-to-incremental is comparable. A full run's count is a different quantity.
assert_not_collapsed "previous run was full: not comparable"        incremental full        900 4
assert_not_collapsed "this run is full: not comparable"             full        incremental 120 4

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
