# PLAN: Managing the OpenStates Forks

**Status:** DRAFT — analysis complete 2026-07-24, no implementation started yet.

**Goal:** Both `openstates-core` and `openstates-scrapers` are now formal GitHub forks
(`Digital-Democracy-Project/openstates-core`, `Digital-Democracy-Project/openstates-scrapers`)
rather than local-patch-only checkouts (scrapers went formal 2026-07-17, core went formal
2026-07-19). Forking solved "how do we ship our own fixes," but nothing was ever set up to
answer "how do we keep receiving *upstream's* fixes." This plan documents the current state,
the gap, and a concrete process to close it.

---

## 1. Current State — What Each Fork Actually Is

Both repos live at `~/Developer/repos/ddp-open-states/<repo>` and are installed editable into
the shared `.venv` (see `project-pydantic-people-fix` memory). Both have a nightly refresh step
in `apply-local-patches.sh` (run via `ddp-sync`'s `openstates_patch_refresh` cron, 01:00 UTC).
But the two repos use **different fork models**, and the nightly script treats them differently:

| | `openstates-core` | `openstates-scrapers` |
|---|---|---|
| Local remotes | `origin` = public `openstates/openstates-core`; `ddp` = fork | `origin` = fork `Digital-Democracy-Project/openstates-scrapers`; `upstream` = public `openstates/openstates-scrapers` |
| Fork model | Cherry-pick: nightly script rebuilds a throwaway `local-patches` branch from fresh public `main` + a short cherry-pick list | Formal: fixes land on the fork's own `main` via branch + PR, normal git history |
| DDP's own diff surface | 1 commit (`d6653a5`, read `CACHE_DIR`/`SCRAPED_DATA_DIR` from env) | 24 commits (see §3), all scoped to specific state scraper files — WAF session fix, vote-count reconciliation, dedup, incremental `start=` filtering, motion classification, etc. |
| What the nightly script does | `git checkout main && git pull origin main` (pulls **public** upstream directly into local `main`) → `git branch -D local-patches` → recreate from `main` → cherry-pick `d6653a5` | `git checkout main && git pull origin main` (pulls the **fork's own** `main` — never touches `upstream`) |
| Net effect | Local working tree is fresh every night, straight from public upstream | Local working tree just re-syncs to whatever's already on the DDP fork — upstream is never consulted |

---

## 2. Is `apply-local-patches.sh` Still Necessary?

Now that both repos are formal forks, it's fair to ask whether this script is legacy leftover
from the pre-fork local-patch-only era. **No — but it's doing two different jobs under one
name now, and only one of them still deserves the name "patches."**

**`openstates-core`: still doing real, necessary patch work.** The cherry-pick rebuild
(`git branch -D local-patches` → recreate from a fresh public `main` pull → cherry-pick
`d6653a5`) isn't legacy — it's the only thing keeping the local checkout both (a) genuinely
current with public upstream and (b) carrying the one DDP fix not yet merged upstream (the
script's own comment marks `d6653a5` as `upstream PR pending`). Checking out the fork's own
`main` instead wouldn't be equivalent: per §3 below, `ddp/main` isn't reliably kept current with
public upstream, so the cherry-pick model is currently *more* robust than trusting the fork
directly. This half of the script goes away only when that one patch actually lands upstream.

**`openstates-scrapers`: the "patch" part is gone; a safety net remains.** There's no
cherry-picking anymore — just `git checkout main && git pull origin main` against the fork. But
that line isn't vestigial: it's the fix for a real incident (see §4.1) where a merged fix branch
sat checked out for two days, silently feeding stale code to the running scraper, until this
forced-recheckout was added 2026-07-23. Removing it would reopen that exact failure mode. It's
just no longer "applying a patch" — it's a freshness-and-safety guard against the checkout
drifting off of `main`.

**Recommendation:** keep the script. Its role for `openstates-core` remains load-bearing and
patch-shaped; its role for `openstates-scrapers` has quietly become a sync/safety guard rather
than a patch mechanism. Worth a low-priority rename or a clarifying header comment (e.g. split
the file's top-of-file comment into "core: patch rebuild" and "scrapers: checkout freshness
guard" — it already documents each section's *why*, just not that they're now doing
categorically different jobs) so a future reader doesn't assume both halves work the same way.
Not worth splitting into two separate scripts unless the two halves' schedules or failure
handling ever need to diverge.

---

## 3. The Gap: Nobody Merges Public Upstream Into Either Fork's `main`

### `openstates-scrapers` — the real, active gap

Checked 2026-07-24: `Digital-Democracy-Project/openstates-scrapers`'s `main` is **22,098
commits behind** `openstates/openstates-scrapers`'s `main` (upstream's most recent commit:
`be55e4fc2`, merged 2026-07-23 — this project is very actively maintained upstream). Every
per-state bug fix landing upstream for FL, WA, VA, MI, MA, UT, AZ, or USA is invisible to us
unless we independently rediscover and fix it ourselves (as just happened with the FL
floor-vote bug — see `project-fl-historical-backfill` memory).

The good news: DDP's own changes are a small, well-scoped diff (24 commits, `git merge-base
main upstream/main` → `c999752`), almost entirely confined to individual `scrapers/<state>/`
files. That means a merge from upstream is very unlikely to be an unmanageable conflict storm —
but it has never been attempted, so the actual conflict surface is unverified.

### `openstates-core` — a quieter version of the same gap

The local working tree looks fresh (nightly pull from public `origin`), which masks the fact
that the **fork itself** (`ddp` remote) is never pushed to after its initial creation. Checked
2026-07-24: `ddp/main` currently equals public `origin/main` exactly (`90289f2`, 2026-07-16) —
but that's coincidental timing (the fork was created 2026-07-19 and public upstream simply
hasn't moved since), not a sync mechanism. The moment public upstream gets a new commit, the
fork's `main` on GitHub will start silently drifting behind with nothing to correct it.

Two long-lived branches on the fork sit entirely outside the nightly automation:
- **`ddp-patches`** — 1 commit ahead of / 3 behind current `main` (stale; predates 3 commits
  that have already landed on `main` from upstream since it branched)
- **`phase1-bill-provenance`** — the intentional WIP hold from `project-bill-provenance-phase1-hold`
  memory; 3 commits ahead of `main`, 0 behind (hasn't needed a rebase yet only because
  upstream's been quiet)

Neither branch is touched by `apply-local-patches.sh`. Both will eventually need a manual
rebase onto a moving `main`, and nothing currently reminds anyone to do it.

---

## 4. Secondary Risks Found During This Analysis

1. **Stale branch checkouts.** `fix/fl-floor-vote-source-url` still exists both locally and on
   `origin` in `openstates-scrapers`, a day after PR #6 merged it into `main`. This is the exact
   failure mode the 2026-07-23 comment in `apply-local-patches.sh` describes — a merged fix
   branch left checked out silently fed stale content to the running scraper for 2 days until
   the script was changed to force a re-checkout of `main` every night. The script now
   self-heals the *checkout*, but the *branch* itself is never deleted, so the same class of
   mistake (someone manually checking it back out, or a future script bug) remains possible.

2. **`local-patches` is destroyed and rebuilt nightly** (`git branch -D local-patches` then
   recreate). Any commit made directly to `local-patches` instead of being added to the
   `cherry_pick` list in `apply-local-patches.sh` is silently lost the next night. This isn't
   documented anywhere obvious outside the script's own comments.

3. **No alerting on drift.** Nothing currently measures or reports how far either fork is
   behind upstream. The 22,098-commit gap on `openstates-scrapers` was discovered only because
   this conversation happened to ask about it — it could just as easily have gone unnoticed
   indefinitely.

---

## 5. Recommendations

### A. Document the branch model explicitly (this doc + a short note in each repo's README)

- **`openstates-core`:** `main` mirrors public upstream exactly and is rebuilt fresh nightly —
  treat it as read-only/generated. `local-patches` is an ephemeral nightly build artifact — never
  commit to it directly. `ddp-patches` and `phase1-bill-provenance` are long-lived hold branches
  that need periodic manual rebasing (see C below).
- **`openstates-scrapers`:** `main` is DDP's real, stable branch — fixes land via branch + PR
  and stay there permanently. It needs periodic upstream merges (see B) or it calcifies exactly
  as it already has.

### B. Establish a periodic upstream-merge cadence for `openstates-scrapers`

Recommended: **monthly**, or before any large historical backfill (backfills are exactly when a
scraper bug is most likely to surface, as happened with FL 2024 this week).

Process for each sync:
1. `git fetch upstream`
2. Review `git log main..upstream/main --oneline -- scrapers/fl scrapers/wa scrapers/va scrapers/mi scrapers/ma scrapers/ut scrapers/az` (scope the review to jurisdictions DDP actually tracks first — the full upstream project covers all 50 states, most of which are irrelevant here)
3. Merge (not rebase, to preserve DDP's fork history) `upstream/main` into `main` via a normal branch + PR, same as any other fork change
4. Resolve conflicts against DDP's 24-commit diff surface — expected to be localized since DDP's changes are per-state and don't touch shared infrastructure
5. Smoke-test the jurisdictions with the largest DDP-specific deltas (FL, WA, VA — see the classifier/dedup/WAF fixes in §3) before trusting the merge in the nightly rotation

### C. Rebase the core fork's long-lived branches periodically

Same cadence as B (monthly, or opportunistically whenever someone is already touching
`openstates-core`): rebase `ddp-patches` and `phase1-bill-provenance` onto current `main`, push,
and confirm the intentional hold (`phase1-bill-provenance`) still applies cleanly on top of a
fresh upstream base.

### D. Keep the core fork's `main` itself in sync (cheap, mostly automatic)

Since the local working tree already does `git pull origin main` (from public upstream) every
night as part of the existing rebuild, add one line to `apply-local-patches.sh` right after that
pull: `git push ddp main`. This is a plain fast-forward (nothing else pushes to `ddp/main`), so
it's low-risk and keeps the GitHub fork honest instead of relying on the current coincidence.

### E. Branch hygiene

Delete merged fix branches (local *and* remote) as part of closing out each PR — for both
repos. Cheap habit, directly prevents the stale-checkout failure mode from §4.1 from recurring
in a form the nightly script doesn't already guard against.

### F. Lightweight drift visibility

Add a short manual check (or a small script, low priority) to run alongside the monthly sync:

```bash
# scrapers: how far behind is our main?
cd openstates-scrapers && git fetch upstream --quiet && \
  echo "scrapers behind upstream: $(git log --oneline main..upstream/main | wc -l)"

# core: does the fork's main match what we think it does?
cd openstates-core && git fetch origin ddp --quiet && \
  git rev-list --left-right --count main...ddp/main
```

Not worth a cron job or an alert threshold yet at DDP's current scale (single-Mac operation,
small team) — a monthly manual glance tied to the sync in B/C is proportionate. Revisit if the
gap is ever allowed to reopen past a few hundred commits.

### G. Clarify `apply-local-patches.sh`'s two roles (see §2)

Low priority: update the script's header comment to name the two halves' actual current
purposes (core = patch rebuild, still load-bearing; scrapers = checkout freshness/safety guard,
no patching left) so the naming doesn't mislead a future reader. No behavior change.

---

## 6. Implementation Order

1. **D** — one-line addition to `apply-local-patches.sh` (push `ddp main`), ships independently, no risk
2. **E** — delete the already-stale `fix/fl-floor-vote-source-url` branch (local + `origin`) now, as cleanup
3. **G** — clarify the script's header comment while D is already touching the file
4. **B** — first upstream-merge attempt for `openstates-scrapers`, scoped to DDP's tracked jurisdictions; treat as a trial run to learn actual conflict cost before committing to "monthly" as the right cadence
5. **C** — rebase `ddp-patches` and `phase1-bill-provenance` onto fresh `main` once B has established the merge is safe
6. **A** — write up the branch-model note in each repo's README once the process in B/C has actually been run once and proven out

---

## 7. Open Questions

- Is monthly the right cadence for B, or should it be tied to backfill/session-start events
  instead (FL's session opens ~November — natural checkpoint)?
- Should the upstream merge in B be a required gate before *any* historical backfill (2023
  regular is still unstarted — worth doing the first sync before that, not after)?
- Does anyone besides this Mac need `ddp/main` (core) to be current — e.g., would a second
  engineer cloning the fork expect it to be usable standalone? If not, D may be lower priority
  than it looks.
