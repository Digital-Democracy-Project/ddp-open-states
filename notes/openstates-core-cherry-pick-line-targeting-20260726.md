# openstates-core fixes must target `cherry-pick-line`, not `main` (2026-07-26)

## The mistake

`openstates-core` PR #2 (`fix/vote-person-identifier-resolution`, the OPEN-2 vote-resolution fix)
was opened against the DDP fork's `main` branch. That looks right at a glance — `main` is the
normal default — but for this repo specifically it's wrong, and merging it as opened would have
been a silent no-op: the fix would sit on GitHub forever without ever reaching a real scrape.

## Why `main` doesn't work here

`apply-local-patches.sh` is what refreshes the code a running scrape actually uses. For
`openstates-core` it does NOT read the DDP fork's `main` at all:

```
cd openstates-core
git checkout main
git pull origin main          # `origin` here is the PUBLIC openstates/openstates-core, not our fork
git checkout -b local-patches
git cherry-pick ... cherry-pick-line   # our fixes get layered in from THIS branch
```

The branch the scraper actually imports (editable install) is `local-patches`, rebuilt every run
from public upstream `main` + whatever commits are on `cherry-pick-line`. Nothing in that script
ever looks at the DDP fork's own `main`. A PR merged into fork `main` is real, visible, git-clean
— and completely inert.

This is `openstates-core`-specific. `openstates-scrapers` is different: it's a formal fork where
`origin` already **is** the DDP fork, and `apply-local-patches.sh` just does a plain
`git checkout main && git pull origin main` for it — so scraper fixes correctly target `main`
there. Don't cargo-cult one convention onto the other repo. See `PLAN-fork-management.md` and the
`project-patch-convention` memory for the full history of why these two forks ended up on
different models.

## The fix

Retargeted PR #2 to `cherry-pick-line` (`gh pr edit 2 --repo Digital-Democracy-Project/openstates-core --base cherry-pick-line`).
Confirmed the diff still applies with no new conflicts against `cherry-pick-line`'s current tip.
`openstates-core` PR #1 (the archive-downloader retry fix, see
`notes/archive-downloader-retry-settings-20260726.md`) had already targeted `cherry-pick-line`
correctly — #2 was the first one to get this wrong, not a new pattern.

## Guidance for whoever picks this up next

- Any `openstates-core` fix branch → PR base is `cherry-pick-line`. Never `main`.
- Any `openstates-scrapers` fix branch → PR base is `main`. That one's correct as the default.
- Before merging an `openstates-core` PR, check its base ref (`gh pr view <n> --repo
  Digital-Democracy-Project/openstates-core --json baseRefName`). If it says `main`, retarget it
  before merging — merging into the wrong base won't error, it'll just do nothing.
- This OPEN-2 fix specifically has an ordering requirement on top of the targeting fix: the
  `openstates-scrapers` change (PR #8) calls `.vote(..., id=...)`, a keyword argument that only
  exists once the `openstates-core` fix (PR #2) is actually live via `cherry-pick-line` →
  `local-patches`. Merge #2 first, confirm it's picked up by `apply-local-patches.sh`, then merge
  #8. `ddp-open-states` PR #12 (the one-time backfill script) merged independently and is now on
  `main` — that's fine, it's inert until someone runs it, but don't run it for real until #2 and
  #8 are both confirmed live.
