#!/usr/bin/env bash
# Keep openstates-core and openstates-scrapers checked out on their fork's main and up to
# date. Both are formal forks (Digital-Democracy-Project/openstates-{core,scrapers}) — DDP's
# fixes merge via a normal branch+PR onto the fork's own main, so this is a plain
# checkout+pull for both, not a rebuild.
#
# openstates-core moved to this model 2026-08-01 (PLAN-fork-management.md §6, "drop the
# cherry-pick-line model entirely and just become a clean fork like openstates-scrapers") --
# it previously rebuilt an ephemeral `local-patches` branch every run by range-picking a
# separate `cherry-pick-line` branch. That model needed constant upkeep (this file's own git
# history has three separate incidents: a frozen local ref silently missing two merged PRs, a
# `git cherry-pick` crash on ordinary merge commits, and a PR merged to the wrong branch
# entirely going unnoticed until the next rebuild) and had drifted out of sync with actual
# practice anyway -- the last three DDP fixes (PRs #3, #5, #6) all merged straight to the
# fork's own `main`, bypassing cherry-pick-line, because that's simpler and nobody was
# actually using the range-pick path anymore. This file now treats both repos identically.
#
# Run periodically (ddp-sync's nightly openstates_patch_refresh job) or whenever someone's
# already touching either repo.
set -euo pipefail

# Worktree lock — both repos are installed as pip editable packages; a running scrape reads
# their code live. Skip the refresh rather than mutate the tree mid-scrape. Stale markers
# from dead scrapes are cleaned (kill -0) so they can't block forever.
SCRAPE_MARKER_DIR=/tmp/ddp-openstates-scrapes
if [ -d "$SCRAPE_MARKER_DIR" ]; then
    for _m in "$SCRAPE_MARKER_DIR"/*; do
        [ -e "$_m" ] || continue
        if kill -0 "$(basename "$_m")" 2>/dev/null; then
            echo "apply-local-patches: scrape (pid $(basename "$_m")) is running — skipping patch refresh (run manually after scrape completes)" | tee -a /Users/agentsmith/Developer/repos/ddp-open-states/logs/scraper.log
            exit 0
        fi
        rm -f "$_m"   # stale marker from a dead scrape
    done
fi

# ── openstates-core ──────────────────────────────────────────────────────────
cd /Users/agentsmith/Developer/repos/ddp-open-states/openstates-core
git checkout main
git pull origin main
echo "openstates-core: on main ($(git rev-parse --short HEAD))"

# ── openstates-scrapers ──────────────────────────────────────────────────────
# Added 2026-07-23: a fix branch (fix/fl-floor-vote-source-url) sat checked out here for 2
# days after its commits were pushed, because nothing ever re-synced this checkout back to
# main -- the running scraper kept reading that branch's content indefinitely instead of
# whatever landed on main. This closes that gap the same way the openstates-core section
# above self-heals on every run.
cd /Users/agentsmith/Developer/repos/ddp-open-states/openstates-scrapers
git checkout main
git pull origin main
echo "openstates-scrapers: on main ($(git rev-parse --short HEAD))"
