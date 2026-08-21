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
# actually using the range-pick path anymore. Since that move both repos' refresh step is
# identical, so this file no longer has two differently-shaped halves (simplified 2026-08-21,
# PLAN-fork-management.md §2/§5.G's "keep it, it does two jobs" premise no longer holds) --
# one shared loop replaces what used to be two near-duplicate blocks.
#
# Run periodically (ddp-sync's nightly openstates_patch_refresh job) or whenever someone's
# already touching either repo.
set -euo pipefail

REPOS=(
    /Users/agentsmith/Developer/repos/ddp-open-states/openstates-core
    /Users/agentsmith/Developer/repos/ddp-open-states/openstates-scrapers
)

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

# Added 2026-07-23 (originally scrapers-only, now identical for both repos): a fix branch
# (fix/fl-floor-vote-source-url) sat checked out in openstates-scrapers for 2 days after its
# commits were pushed, because nothing ever re-synced the checkout back to main -- the running
# scraper kept reading that branch's content indefinitely instead of whatever landed on main.
# This loop's checkout+pull self-heals that every run, for both repos.
for repo in "${REPOS[@]}"; do
    cd "$repo"
    git checkout main
    git pull origin main
    echo "$(basename "$repo"): on main ($(git rev-parse --short HEAD))"
done
