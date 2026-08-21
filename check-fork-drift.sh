#!/usr/bin/env bash
# OPEN-100: lightweight drift-visibility check -- how far behind is each fork's own `main`
# vs. the real public project? Both openstates-core and openstates-scrapers now use the same
# origin=fork/upstream=public convention (openstates-core moved 2026-08-01,
# PLAN-fork-management.md §6), so one shared check covers both, same as apply-local-patches.sh
# collapsed to one shared loop for the same reason (OPEN-119).
#
# --first-parent is deliberate, not a plain `git log main..upstream/main` count: the latter
# includes ~17 years of upstream history not reachable from the shared merge-base along main's
# own line (found 2026-07-25 on openstates-scrapers -- raw count read ~22,000, the real gap was
# ~28). --first-parent walks only main's own mainline, which is what the raw number is trying
# to answer in the first place. This counts first-parent MAINLINE commits only -- a single
# upstream merge commit for a large PR counts as one, not the size of what it carries, so
# treat the number as "how many mainline steps behind", not "how much has changed" or "how
# risky the eventual merge will be".
#
# Deliberately NOT wired to cron or alerting -- PLAN-fork-management.md §5.F's own call: not
# worth it yet at DDP's current scale (single-Mac, small team). Run manually alongside each
# upstream-merge sync (§5.B) or whenever a gut check is useful. Never mutates the working tree
# or checked-out branch -- git fetch only updates remote-tracking refs, and this compares
# against `origin/main` (the fork's own remote HEAD after fetching), not the possibly-stale
# local `main`, so a checkout that hasn't run apply-local-patches.sh recently still gets an
# accurate number.
set -euo pipefail

REPOS=(
    /Users/agentsmith/Developer/repos/ddp-open-states/openstates-core
    /Users/agentsmith/Developer/repos/ddp-open-states/openstates-scrapers
)

for repo in "${REPOS[@]}"; do
    name=$(basename "$repo")
    cd "$repo"
    git fetch origin --quiet
    git fetch upstream --quiet
    behind=$(git rev-list --count --first-parent origin/main..upstream/main)
    echo "$name: $behind first-parent mainline commit(s) behind public upstream (origin/main..upstream/main)"
done
