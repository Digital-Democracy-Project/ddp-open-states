#!/usr/bin/env bash
# Rebuild local-patches branches for openstates-core and openstates-scrapers.
# Commits on ddp-patches (core) or direct cherry-pick hashes (scrapers) are
# applied on top of current upstream main after every git pull.
# Run after every upstream git pull in either subdir.
set -euo pipefail

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
echo "openstates-scrapers: patches applied — on local-patches branch"
