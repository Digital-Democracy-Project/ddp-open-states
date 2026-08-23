#!/usr/bin/env bash
# import-summary.sh — read an openstates-core import report and judge what it says (OPEN-139)
#
# Sourced by run-scrape.sh. Exists as its own file for one reason: the stuck-run detector below
# is the check that would have caught Arizona's 14-day outage, and it needs a regression test
# against Arizona's real output. run-scrape.sh cannot be sourced for a unit test (it runs a
# scrape top-to-bottom), so the two decisions live here where test-import-summary.sh can reach
# them. Kept flat at the repo root alongside run-scrape.sh / run-archive.sh /
# check-scrape-staleness.sh rather than inventing a lib/ directory, which is OPEN-43's call to
# make when it extracts the shared Slack helper.
#
# Deliberately no logging, no alerting, no I/O beyond reading the file it is handed: these are
# pure decisions so the test can assert on them without seams or fixtures beyond a text file.

# parse_import_bill_counts <import-output-file>
#
# openstates-core prints one report line per object type:
#     import:
#       bill: 12 new 3 updated 40 noop
#       jurisdiction: 0 new 0 updated 1 noop
#
# Echoes "new:updated:noop" for the bill line, or nothing at all if there isn't one.
#
# Takes the LAST bill line on purpose. With sweep-import enabled (OPEN-86) a single run performs
# several imports as it goes, each printing its own report; only the final one covers the whole
# run. Echoing nothing on no match is also on purpose -- a caller must be able to tell "could not
# measure" from "measured zero", because reporting a confident zero for an unparseable report is
# exactly how a broken scraper comes to look like a quiet week.
parse_import_bill_counts() {
    local file="$1" line
    [ -r "$file" ] || return 0
    line=$(grep -E '^[[:space:]]*bill: [0-9]+ new [0-9]+ updated [0-9]+ noop' "$file" | tail -1)
    [ -n "$line" ] || return 0
    echo "$line" | sed -E 's/.*bill: ([0-9]+) new ([0-9]+) updated ([0-9]+) noop.*/\1:\2:\3/'
}

# import_looks_stuck <bills_scraped> <bills_new> <bills_updated>
#
# True (exit 0) when the scrape wrote bill files and the import found nothing new and nothing
# changed in any of them.
#
# This is the Arizona signature. From 2026-08-08's real log:
#     === SCRAPE SUMMARY: az | mode=incremental | bills_scraped=895 | prev_run=895 ===
#       bill: 0 new 0 updated 895 noop
# 895 files collected, nothing new in any of them, fourteen nights running -- a frozen
# incremental cutoff re-collecting one window forever. Invisible to the file count (895 vs 895 is
# a flat line, so the old <20%-drop check never fired) and invisible to an exit-status check (the
# run succeeded every night).
#
# Zero scraped files is NOT stuck: that is an ordinary no-op, which is what an out-of-session
# jurisdiction looks like and must stay quiet.
import_looks_stuck() {
    local scraped="${1:-0}" new="${2:-0}" updated="${3:-0}"
    [ "$scraped" -gt 0 ] && [ "$new" -eq 0 ] && [ "$updated" -eq 0 ]
}
