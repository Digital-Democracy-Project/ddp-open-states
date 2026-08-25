#!/usr/bin/env bash
# import-summary.sh — read an openstates-core import report and judge what it says (OPEN-139)
#
# Sourced by run-scrape.sh. Exists as its own file for one reason: the stuck-run detector below
# is the check that would have caught Arizona's 14-day outage, and it needs a regression test
# against Arizona's real output. run-scrape.sh cannot be sourced for a unit test (it runs a
# scrape top-to-bottom), so the decisions live here where test-import-summary.sh can reach them.
# Kept flat at the repo root alongside run-scrape.sh / run-archive.sh / check-scrape-staleness.sh
# rather than inventing a lib/ directory, which is OPEN-43's call to make when it extracts the
# shared Slack helper.
#
# Deliberately no logging, no alerting, no I/O beyond reading the file it is handed: these are
# pure decisions so the test can assert on them without seams.
#
# ---------------------------------------------------------------------------------------------
# THE .imported FILE CONTRACT — read this before writing a consumer
#
#   $LAST_RUN_DIR/<SCRAPE_KEY>.imported   one line:   <status>:<new>:<updated>:<noop>:<mode>
#
#   status=ok         counts are this run's real figures.       e.g.  ok:37:83:168:incremental
#   status=unparsed   counts are EMPTY. The import ran but its
#                     report could not be read, so there is no
#                     figure for this run.                     e.g.  unparsed::::incremental
#
# Three properties a consumer can rely on:
#
#   1. WRITTEN EVERY RUN THAT REACHES THE IMPORT STEP, including no-ops and unparseable reports.
#      So the file is never stale with respect to the last completed run. An earlier version of
#      this change skipped the write on a parse failure, which left the previous run's counts in
#      place looking current -- pm-review flagged that as worse than either alternative, and it
#      is: a rolling series built on it would silently repeat an old figure.
#   2. A parse failure is NEVER reported as zero. `unparsed` and `0` mean completely different
#      things -- "we could not measure" versus "this jurisdiction filed nothing" -- and a
#      consumer deciding whether a jurisdiction has gone quiet must not conflate them.
#   3. ABSENT means the jurisdiction has never completed a run since this shipped, not zero.
#      Treat a missing file as no data, not as silence.
#
# The file is not written when a run fails before or during the import: a failed run has no
# meaningful count, and the failure alert already fired.
# ---------------------------------------------------------------------------------------------

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
# run. Echoing nothing on no match is also on purpose -- see property 2 above.
parse_import_bill_counts() {
    local file="$1" line
    [ -r "$file" ] || return 0
    line=$(grep -E '^[[:space:]]*bill: [0-9]+ new [0-9]+ updated [0-9]+ noop' "$file" | tail -1)
    [ -n "$line" ] || return 0
    echo "$line" | sed -E 's/.*bill: ([0-9]+) new ([0-9]+) updated ([0-9]+) noop.*/\1:\2:\3/'
}

# import_looks_stuck <mode> <bills_scraped> <bills_new> <bills_updated>
#
# True (exit 0) when an INCREMENTAL run wrote bill files and the import found nothing new and
# nothing changed in any of them.
#
# This is the Arizona signature. From 2026-08-08's real log:
#     === SCRAPE SUMMARY: az | mode=incremental | bills_scraped=895 | prev_run=895 ===
#       bill: 0 new 0 updated 895 noop
# 895 files collected, nothing new in any of them, fourteen nights running -- a frozen
# incremental cutoff re-collecting one window forever. Invisible to the file count (895 vs 895 is
# a flat line, so the old <20%-drop check never fired) and invisible to an exit-status check (the
# run succeeded every night).
#
# Two cases this must NOT fire on:
#
#   * mode=full. A full re-scrape of an already-imported session legitimately writes every bill
#     file and imports nothing new -- that is what "already up to date" looks like, and it is a
#     real workflow here (FL's 2023/2024/2025 historical backfills each re-scraped 1,800+ bills).
#     pm-review raised the false-positive risk; this is the concrete case behind it.
#   * zero scraped files. That is an ordinary no-op, which is what an out-of-session jurisdiction
#     looks like every week, and it must stay quiet.
import_looks_stuck() {
    local mode="${1:-}" scraped="${2:-0}" new="${3:-0}" updated="${4:-0}"
    [ "$mode" = "incremental" ] || return 1
    [ "$scraped" -gt 0 ] && [ "$new" -eq 0 ] && [ "$updated" -eq 0 ]
}

# new_bills_collapsed <mode> <prev_mode> <prev_new> <this_new>
#
# True when this incremental run found drastically fewer new bills than the last one did -- the
# same <20%-of-previous shape the removed warning used, rewired onto the count that can actually
# see it (OPEN-139's acceptance criteria allow "rewired or removed"; pm-review pointed out that
# plain removal drops a real failure mode, so it is rewired).
#
# Why the old version could not work: it compared bills_scraped, which counts JSON files written
# including unchanged bills, so a stuck cutoff produced an identical number every night. New-bill
# counts collapse when a filter breaks, a date signal changes meaning, or pagination silently
# truncates.
#
# Only compares incremental-to-incremental, and only when the previous run found more than 10 --
# below that the ratio is noise, which is the same floor the original check used.
new_bills_collapsed() {
    local mode="${1:-}" prev_mode="${2:-}" prev_new="${3:-0}" this_new="${4:-0}" threshold
    [ "$mode" = "incremental" ] && [ "$prev_mode" = "incremental" ] || return 1
    [ "$prev_new" -gt 10 ] || return 1
    threshold=$(( prev_new / 5 ))
    [ "$threshold" -lt 1 ] && threshold=1
    [ "$this_new" -lt "$threshold" ]
}


# OPEN-152: is a zero-object scrape a genuine no-op, or did we fail to reach the site?
#
# openstates-core raises the same "no objects returned from <X>Scraper scrape" whenever a
# scraper yields nothing, and run-scrape.sh treats that as a clean no-op -- correctly, for the
# common case of an incremental run where nothing changed since the cutoff. But the message
# cannot distinguish that from "the scraper could not read the site at all", and on 2026-08-24 a
# WAF-blocked MI run was recorded as `ok:0:0:0` with a freshly advanced watermark. That is worse
# than a misleading marker: the watermark moved past a window whose bills were never examined,
# so an incremental run will never look at it again.
#
# The scrapers already say which case it is, in their own output -- run-scrape.sh just was not
# reading it. MI logs a distinct warning when the response is neither a results page nor a bill
# page, precisely because OPEN-132 made that case noisy instead of invisible. Match on those
# statements rather than trying to infer intent from request counts or elapsed time, both of
# which were tried and neither of which separates the cases (a blocked MI run made 2 requests
# and a genuinely quiet VA run made 0).
#
# Deliberately a deny-list, not an allow-list. A jurisdiction that emits none of these markers
# behaves exactly as it does today, so this cannot make a currently-working scraper start
# failing -- it only rescues cases that are currently silent. The cost of that choice is that a
# new jurisdiction's block page stays silent until someone adds its marker, which is the same
# position we are in now rather than a regression.
#
# The two WAF strings are deliberately identical to ddp-sync's WAF_BLOCK_MARKERS
# ("consecutive waf blocks detected", "waf block detected") and to the pair run-scrape.sh
# already greps for further down. Matching something narrower here would be safer against false
# positives but would diverge from the fleet's one agreed spelling of "this was a WAF block",
# which is a worse trade: three places would then disagree about the same event.
_SCRAPE_UNREACHABLE_MARKERS='neither a results page nor a usable bill page|waf block detected|consecutive waf blocks|unrecognised block page|unrecognized block page'

# A line that NEGATES a marker must not count as one. Nothing in the fleet currently logs
# "no WAF block detected", but the markers above are short enough that a future diagnostic line
# could contain one harmlessly, and the failure mode would be ugly and quiet: every genuinely
# quiet week for that jurisdiction would start alerting and its watermark would stop advancing.
# Cheap to guard now, unpleasant to debug later.
_SCRAPE_NEGATED_MARKER='(^|[^[:alnum:]])(no|not|never|without|isn.t|wasn.t)[[:space:]]+(an?[[:space:]]+)?(waf block|consecutive waf|unrecognised block|unrecognized block|results page)'

# Usage: scrape_output_shows_unreachable_site <path-to-scrape-output>
# Returns 0 (true) when the output positively indicates the site could not be read.
#
# Naming note: this lives in import-summary.sh because that is already the helper run-scrape.sh
# sources, and adding a second sourced file for one function is not worth it. It is
# scrape-outcome logic in an import-named file, which is a little muddy -- if a third such
# helper appears, that is the moment to split them.
scrape_output_shows_unreachable_site() {
    local out="$1"
    [ -f "$out" ] || return 1
    # Drop negated lines first, then look for a marker in what remains.
    grep -viE "$_SCRAPE_NEGATED_MARKER" "$out" 2>/dev/null \
        | grep -qiE "$_SCRAPE_UNREACHABLE_MARKERS"
}
