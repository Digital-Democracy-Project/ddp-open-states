#!/usr/bin/env bash
# Rebuild local-patches branch for openstates-core.
# openstates-scrapers is now a formal fork (Digital-Democracy-Project/openstates-scrapers) —
# no rebuild needed there; it runs off fork main directly.
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
cherry_pick d6653a5  # fix: read CACHE_DIR/SCRAPED_DATA_DIR from env vars; upstream PR pending
echo "openstates-core: patches applied — on local-patches branch"
