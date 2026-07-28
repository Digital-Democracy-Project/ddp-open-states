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
# Sync the LOCAL cherry-pick-line ref to the DDP fork's real remote tip before using it as
# the range-pick source below. Found missing 2026-07-27: this script previously refreshed
# `main` (public upstream) on every run but never touched cherry-pick-line itself, so any
# commit merged to that branch on GitHub sat invisible to every nightly rebuild until someone
# manually fast-forwarded the local ref. Confirmed via reflog: the local ref had been frozen
# at its creation-time commit since 2026-07-25, silently missing two already-merged PRs
# (#1 archive-downloader retry settings, #2 vote-person-identifier-resolution) — found because
# the missing retry settings caused ~499 unretried HTTP 429s during the 2026-07-26 FL
# full-archive backfill (scraper.retry_attempts stayed at scrapelib's default of 0).
git fetch ddp cherry-pick-line
git branch -f cherry-pick-line ddp/cherry-pick-line
git branch -D local-patches 2>/dev/null || true
git checkout -b local-patches
# Range-pick everything on cherry-pick-line not yet upstream (PLAN-fork-management.md
# recommendation H, 2026-07-25). Add new DDP-only commits to that branch going forward —
# never hand-list individual SHAs here again. --empty=drop preserves the old per-commit
# cherry_pick() helper's behavior of silently skipping any commit upstream has already merged.
# -m 1 (added 2026-07-27): a normal GitHub "Merge pull request" merge onto cherry-pick-line
# produces a 2-parent merge commit, which `git cherry-pick` refuses to replay without a
# mainline parent number -- confirmed this crashes the whole rebuild (set -euo pipefail exits
# the script) the moment any cherry-pick-line PR is merged the ordinary (non-squash) way, not
# just a theoretical edge case. -m 1 tells cherry-pick to treat the merge's first parent as
# mainline; harmless no-op for the plain (non-merge) commits that make up most of this range.
git cherry-pick --empty=drop -m 1 "$(git merge-base main cherry-pick-line)..cherry-pick-line"
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
