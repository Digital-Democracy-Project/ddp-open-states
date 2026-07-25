#!/usr/bin/env bash
# Rebuild local-patches branch for openstates-core; keep openstates-scrapers
# checked out on its fork's main and up to date.
# openstates-scrapers is a formal fork (Digital-Democracy-Project/openstates-scrapers) —
# fixes merge via a normal branch+PR, not a cherry-pick, so it only needs a
# checkout+pull (see the openstates-scrapers section below), not a rebuild.
# Run after every upstream git pull in openstates-core.
set -euo pipefail

# Worktree lock — openstates-core is installed as a pip editable package; a running scrape
# reads its code live. Skip the cherry-pick rebuild rather than mutate the tree mid-scrape.
# Stale markers from dead scrapes are cleaned (kill -0) so they can't block forever.
SCRAPE_MARKER_DIR=/tmp/ddp-openstates-scrapes
if [ -d "$SCRAPE_MARKER_DIR" ]; then
    for _m in "$SCRAPE_MARKER_DIR"/*; do
        [ -e "$_m" ] || continue
        if kill -0 "$(basename "$_m")" 2>/dev/null; then
            echo "apply-local-patches: scrape (pid $(basename "$_m")) is running — skipping core patch refresh (run manually after scrape completes)" | tee -a /Users/agentsmith/Developer/repos/ddp-open-states/logs/scraper.log
            exit 0
        fi
        rm -f "$_m"   # stale marker from a dead scrape
    done
fi

# ── openstates-core ──────────────────────────────────────────────────────────
cd /Users/agentsmith/Developer/repos/ddp-open-states/openstates-core
git checkout main
git pull origin main
git branch -D local-patches 2>/dev/null || true
git checkout -b local-patches
# Range-pick everything on cherry-pick-line not yet upstream (PLAN-fork-management.md
# recommendation H, 2026-07-25). Add new DDP-only commits to that branch going forward —
# never hand-list individual SHAs here again. --empty=drop preserves the old per-commit
# cherry_pick() helper's behavior of silently skipping any commit upstream has already merged.
git cherry-pick --empty=drop "$(git merge-base main cherry-pick-line)..cherry-pick-line"
echo "openstates-core: patches applied — on local-patches branch"

# ── openstates-scrapers ──────────────────────────────────────────────────────
# Formal fork — fixes are merged to fork main via a normal branch+PR, so this
# is a plain checkout+pull, not a rebuild. Added 2026-07-23: a fix branch
# (fix/fl-floor-vote-source-url) sat checked out here for 2 days after its
# commits were pushed, because nothing ever re-synced this checkout back to
# main -- the running scraper kept reading that branch's content indefinitely
# instead of whatever landed on main. This closes that gap the same way the
# openstates-core section above already self-heals on every run.
cd /Users/agentsmith/Developer/repos/ddp-open-states/openstates-scrapers
git checkout main
git pull origin main
echo "openstates-scrapers: on main ($(git rev-parse --short HEAD))"
