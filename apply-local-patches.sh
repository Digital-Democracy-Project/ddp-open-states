#!/usr/bin/env bash
# Rebuild local-patches branches for openstates-core and openstates-scrapers.
# Commits on ddp-patches (core) or direct cherry-pick hashes (scrapers) are
# applied on top of current upstream main after every git pull.
# Run after every upstream git pull in either subdir.
set -euo pipefail

# Worktree lock (WRITER) — macOS has no flock, so we use PID-marker files. Rebuilding
# local-patches mutates the shared openstates-scrapers / openstates-core trees that running
# scrapes read via PYTHONPATH. If any LIVE scrape (see run-scrape.sh) is reading the tree, skip
# this refresh rather than rebuild the branch out from under it — it'll refresh next cycle.
# Stale markers from dead scrapes are cleaned (kill -0) so they can't block forever.
SCRAPE_MARKER_DIR=/tmp/ddp-openstates-scrapes
if [ -d "$SCRAPE_MARKER_DIR" ]; then
    for _m in "$SCRAPE_MARKER_DIR"/*; do
        [ -e "$_m" ] || continue
        if kill -0 "$(basename "$_m")" 2>/dev/null; then
            echo "apply-local-patches: scrape (pid $(basename "$_m")) is reading the worktree — skipping patch refresh"
            exit 0
        fi
        rm -f "$_m"   # stale marker from a dead scrape
    done
fi

# Apply a cherry-pick, silently skipping commits that upstream already merged.
# Upstream merges change the commit SHA, so content-match via patch-id isn't
# reliable; we catch the "empty cherry-pick" exit state instead.
cherry_pick() {
    local sha="$1"; shift
    local output
    if output=$(git cherry-pick "$sha" 2>&1); then
        echo "$output"
    elif echo "$output" | grep -q "nothing to commit\|is now empty"; then
        echo "  skipping (already merged upstream): $sha $*"
        git cherry-pick --skip
    else
        echo "$output" >&2
        return 1
    fi
}

# ── openstates-core ──────────────────────────────────────────────────────────
cd /Users/agentsmith/Developer/repos/ddp-open-states/openstates-core
git checkout main
git pull origin main
git branch -D local-patches 2>/dev/null || true
git checkout -b local-patches
cherry_pick d6653a5  # fix: read CACHE_DIR/SCRAPED_DATA_DIR from env vars (ddp-patches)
echo "openstates-core: patches applied — on local-patches branch"

# ── openstates-scrapers ──────────────────────────────────────────────────────
cd /Users/agentsmith/Developer/repos/ddp-open-states/openstates-scrapers
git checkout main
git pull origin main
git branch -D local-patches 2>/dev/null || true
git checkout -b local-patches
# ade373f (MI House votes, PR #5696) merged upstream 2026-06-15 — removed
# 38e0206 + 8003157 (UT votes, PR #5695) merged upstream 2026-06-16 — removed
cherry_pick 357a9a6  # FL: don't let flhouse.gov bot detection crash the scrape
cherry_pick 371e7e6  # fix(usa): correct start= datetime format string
cherry_pick 5ccf523  # feat(fl): add start= incremental filtering
cherry_pick 8bc4525  # feat(wa): add start= incremental filtering
cherry_pick b9e2d6f  # feat(mi): add start= incremental filtering
cherry_pick 4cb3f8d  # feat(ut): add start= incremental filtering
cherry_pick e9e4c28  # feat(ma): add start= incremental filtering
cherry_pick 939b4b7  # feat(az): add start= incremental filtering
cherry_pick bdd256b  # feat(va): add start= incremental filtering
cherry_pick ef4cdaa  # feat(ma): re-enable house and senate vote scraping
echo "openstates-scrapers: patches applied — on local-patches branch"
