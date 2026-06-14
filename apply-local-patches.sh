#!/usr/bin/env bash
# Rebuild the local-patches branch with our open PRs cherry-picked onto current upstream main.
# Run after every upstream git pull.
set -euo pipefail
cd /Users/agentsmith/Developer/repos/open-states/openstates-scrapers

git checkout main
git pull origin main
git branch -D local-patches 2>/dev/null || true
git checkout -b local-patches
git cherry-pick ade373f  # MI: fix House votes (PR #5696)
git cherry-pick 38e0206  # UT: fix votes not scraped for 2025+ sessions (PR #5695)
git cherry-pick abea3cd  # UT: fix duplicate vote identifier for concurrent chamber votes
echo "Patches applied — on local-patches branch"
