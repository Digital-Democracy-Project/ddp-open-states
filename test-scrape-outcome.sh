#!/usr/bin/env bash
# test-scrape-outcome.sh — fixture tests for scrape_output_shows_unreachable_site() (OPEN-152)
#
# No network, no production paths, no database: every fixture is a text file in a mktemp dir
# holding real scraper output. Run it anywhere:
#     bash test-scrape-outcome.sh
# Exits 0 with "ALL PASS" or 1 with the first failing assertion.
#
# Same shape as test-import-summary.sh (OPEN-139) and test-check-scrape-staleness.sh (OPEN-40).
#
# What is being guarded: openstates-core raises the same "no objects returned" whenever a
# scraper yields nothing, so run-scrape.sh cannot tell "nothing changed since the cutoff" from
# "I could not read the site". Taking the no-op path for the second case records `ok:0:0:0` AND
# advances the watermark past a window that was never examined. These tests pin the
# discrimination, because getting it wrong in either direction is silent:
#   * a false "unreachable" turns every quiet week into a failure alert
#   * a false "no-op" is the bug itself, and loses data without saying so

set -u

. "$(cd "$(dirname "$0")" && pwd)/import-summary.sh"

TMPDIR_ROOT=$(mktemp -d /tmp/scrape-outcome-test.XXXXXX)
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

PASS=0
FAIL=0

fixture() {
    local name="$1"; shift
    local path="$TMPDIR_ROOT/$name"
    printf '%s\n' "$@" > "$path"
    printf '%s' "$path"
}

assert_unreachable() {
    local desc="$1" path="$2"
    if scrape_output_shows_unreachable_site "$path"; then
        PASS=$((PASS + 1)); echo "  ok   $desc"
    else
        FAIL=$((FAIL + 1)); echo "  FAIL $desc — expected unreachable, got benign"
    fi
}

assert_benign() {
    local desc="$1" path="$2"
    if scrape_output_shows_unreachable_site "$path"; then
        FAIL=$((FAIL + 1)); echo "  FAIL $desc — expected benign, got unreachable"
    else
        PASS=$((PASS + 1)); echo "  ok   $desc"
    fi
}

echo "== genuinely quiet runs must stay benign =="

# The exact line MI logs when it parses a real results page with no rows. This is the common
# case and the one that must never start alerting.
assert_benign "MI genuine empty result" "$(fixture mi_empty \
    "12:00:01 INFO scrapelib: GET - 'https://legislature.mi.gov/Search/ExecuteSearch?...'" \
    "12:00:02 INFO openstates: MI search returned a results page with no matching bills -- genuine empty result for this window" \
    "openstates.exceptions.ScrapeError: no objects returned from MIBillScraper scrape")"

# A jurisdiction that emits none of the markers behaves exactly as it did before this change.
# VA is the real example: a genuinely quiet run that logs nothing distinctive at all.
assert_benign "output with no markers at all (unchanged behaviour)" "$(fixture va_quiet \
    "openstates.exceptions.ScrapeError: no objects returned from VaBillScraper scrape")"

assert_benign "empty output file" "$(fixture empty_file "")"

echo "== unreachable runs must be caught =="

# The real 2026-08-24 shape: MI blocked, scraper warns the page was neither results nor bill.
assert_unreachable "MI unrecognised page (the 2026-08-24 incident)" "$(fixture mi_blocked \
    "12:00:01 INFO scrapelib: GET - 'https://legislature.mi.gov/Search/ExecuteSearch?...'" \
    "12:00:02 WARNING openstates: MI search response is neither a results page nor a usable bill page (no tableScrollWrapper and no h1#BillHeading) -- treating as no results, but this is probably a site change or an unrecognised block page" \
    "openstates.exceptions.ScrapeError: no objects returned from MIBillScraper scrape")"

# The circuit breaker's own marker, which run-scrape.sh already matched but only AFTER
# finish_no_op had exited — so it could never fire on this path before.
assert_unreachable "WAF block detected marker" "$(fixture waf1 \
    "WAF block detected even after cookie re-warm; consecutive blocks: 3" \
    "openstates.exceptions.ScrapeError: no objects returned from MIBillScraper scrape")"

assert_unreachable "consecutive waf blocks marker" "$(fixture waf2 \
    "consecutive WAF blocks: 5 — aborting" \
    "openstates.exceptions.ScrapeError: no objects returned from MIBillScraper scrape")"

echo "== matching details that would silently break the guard =="

# Case-insensitivity is load-bearing: the scraper's wording is sentence-cased in some paths and
# the circuit breaker's is not. A case-sensitive match would miss the real incident text.
assert_unreachable "marker in a different case" "$(fixture case_mix \
    "NEITHER A RESULTS PAGE NOR A USABLE BILL PAGE")"

# Both spellings, because the codebase contains British and American forms in different files
# and a guard that only knows one is a guard that fails on half the fleet.
assert_unreachable "unrecognised (British spelling)" "$(fixture brit "probably an unrecognised block page")"
assert_unreachable "unrecognized (American spelling)" "$(fixture amer "probably an unrecognized block page")"

# A marker anywhere in a long log must be found, not just on the last line — the scrape output
# is the whole run's stdout and the warning is emitted long before the final exception.
assert_unreachable "marker buried in a long log" "$(fixture buried \
    "$(for i in $(seq 1 60); do echo "12:00:0$i INFO scrapelib: GET - 'https://example.gov/$i'"; done)" \
    "WARNING openstates: MI search response is neither a results page nor a usable bill page" \
    "$(for i in $(seq 1 60); do echo "12:01:0$i INFO something else"; done)")"

echo "== negated marker text must not count as a marker =="

# Nothing in the fleet logs these today, but the WAF markers are short fragments shared with
# ddp-sync's WAF_BLOCK_MARKERS, and a future diagnostic line could contain one harmlessly. The
# failure mode would be quiet and nasty: every genuinely quiet week for that jurisdiction would
# start alerting and its watermark would stop advancing.
assert_benign "'no WAF block detected'" "$(fixture neg1 \
    "12:00:02 INFO openstates: no WAF block detected; proceeding normally" \
    "openstates.exceptions.ScrapeError: no objects returned from XxBillScraper scrape")"

assert_benign "'not a waf block'" "$(fixture neg2 \
    "12:00:02 INFO openstates: this was not a waf block, the session simply has no bills" \
    "openstates.exceptions.ScrapeError: no objects returned from XxBillScraper scrape")"

assert_benign "'without an unrecognised block page'" "$(fixture neg3 \
    "12:00:02 INFO openstates: completed without an unrecognised block page")"

# But a negated line must not mask a REAL marker elsewhere in the same output. Dropping negated
# lines and matching the rest is what makes this hold; a whole-file negation check would not.
assert_unreachable "a real marker alongside a negated one" "$(fixture neg_mixed \
    "12:00:01 INFO openstates: no WAF block detected on the first attempt" \
    "12:00:09 WARNING openstates: MI search response is neither a results page nor a usable bill page")"

echo "== absent file =="

# Defensive: a missing $SCRAPE_OUT must read as benign rather than erroring under `set -e`.
# Returning true here would turn every no-op into a failure the moment the file was cleaned up
# early, which is exactly the kind of change that looks harmless and pages someone at 2am.
if scrape_output_shows_unreachable_site "$TMPDIR_ROOT/does-not-exist"; then
    FAIL=$((FAIL + 1)); echo "  FAIL missing file — expected benign"
else
    PASS=$((PASS + 1)); echo "  ok   missing file reads as benign"
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "ALL PASS ($PASS assertions)"
    exit 0
fi
echo "$FAIL FAILED, $PASS passed"
exit 1
