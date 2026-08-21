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
# to answer in the first place.
#
# Deliberately NOT wired to cron or alerting -- PLAN-fork-management.md §5.F's own call: not
# worth it yet at DDP's current scale (single-Mac, small team). Run manually alongside each
# upstream-merge sync (§5.B) or whenever a gut check is useful. This is read-only (fetch + log),
# never touches the working tree or checked-out branch.
set -euo pipefail

REPOS=(
    /Users/agentsmith/Developer/repos/ddp-open-states/openstates-core
    /Users/agentsmith/Developer/repos/ddp-open-states/openstates-scrapers
)

for repo in "${REPOS[@]}"; do
    name=$(basename "$repo")
    cd "$repo"
    git fetch upstream --quiet
    behind=$(git log --oneline --first-parent main..upstream/main | wc -l | tr -d ' ')
    echo "$name: $behind commit(s) behind public upstream (first-parent main..upstream/main)"
done
