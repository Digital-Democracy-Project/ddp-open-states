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
- ~~`phase1-bill-provenance`~~ — **superseded and deleted 2026-07-25.** The FL 2023 backfill's quiet
  window arrived the same day; recommendation H below was executed for real, not just designed:
  `cherry-pick-line` was cut from this branch's tip (`b1a87966`), `apply-local-patches.sh` switched
  to the range-pick form, the rebuild verified live (all 7 commits applied cleanly), and this
  branch deleted from both the local checkout and the `ddp` fork. `cherry-pick-line` is now the
  standing home for DDP's own not-yet-upstream `openstates-core` commits

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

**Done 2026-07-24:** `PRIMITIVES.md`'s own `apply-local-patches.sh` entry was found to be stale
during an unrelated cross-check — it still said the script "does not touch
[openstates-scrapers] anymore," which stopped being true the moment the 2026-07-23
checkout+pull safety net (§2 above) was added. Corrected in `PRIMITIVES.md` directly. The
script's own header comment (the original scope of this item) is still open.

### H. Stop hand-maintaining individual cherry-pick lines for DDP's own long-lived `openstates-core` work

**Added 2026-07-25, prompted by the bill-provenance work.** Every new commit added to a held
branch like `phase1-bill-provenance` currently needs its own new `cherry_pick <sha>` line added
to `apply-local-patches.sh` by hand, or it's silently never applied — exactly the risk §4 point 2
already names. This isn't hypothetical: it happened for real during Phase 2's S3 upload+verify
work (commit `b1a87966`), caught only because someone happened to check the script's cherry-pick
list before deploying, not because anything would have flagged the gap on its own.

**Fix: a permanent, obviously-named branch, and one range-based cherry-pick instead of a growing
list of individual SHAs.** Introduce `cherry-pick-line` as the standing home for all of DDP's own
`openstates-core` commits that aren't (yet, or ever going to be) merged upstream — named
deliberately so its purpose is unambiguous, unlike a feature-scoped branch name. `apply-local-patches.sh`
replaces its per-commit `cherry_pick <sha>` calls for this category with a single range pick:

```bash
git cherry-pick $(git merge-base main cherry-pick-line)..cherry-pick-line
```

Any commit added to `cherry-pick-line` going forward is picked up automatically the next time the
script runs — no further edits to `apply-local-patches.sh` needed, ever, for this category of
change. A standalone one-off patch expected to be genuinely temporary (like `d6653a5`, pending an
upstream PR) can still get its own individual `cherry_pick` line if keeping it separately trackable
is useful, or get folded into `cherry-pick-line` too — either works, since the existing
empty-cherry-pick handling (or `git cherry-pick --empty=drop`, available in modern git) already
tolerates a commit that turns out to already be upstream.

**Why not just keep using `phase1-bill-provenance` as the range target:** that branch was
deliberately scoped as a temporary hold — Ramon's call (2026-07-25) is to merge it once the FL
2023 backfill's quiet window arrives, at which point the branch gets deleted. Pointing the
range-pick at a branch that's about to disappear would just move the tedium (and the failure
mode) from "did I add a cherry-pick line" to "did I remember the range-source branch got deleted."
`cherry-pick-line` is meant to *outlive* any individual feature's branch — it's where a feature's
commits land once they're ready to go live and stay live, not a place work happens.

**Done for real, 2026-07-25 — not just designed above.** Quiet window confirmed twice (a clean
`ps aux`, then independently corroborated by the FL 2023 backfill's own completion note); created
`cherry-pick-line` from `ddp/phase1-bill-provenance`'s real tip (`b1a87966` — the production
checkout's own local ref for that branch had drifted 3 commits stale, so the branch was cut from
the fork's remote ref instead, not the local one); updated `apply-local-patches.sh` to the
range-pick form and **actually ran it** — all 7 commits applied cleanly onto a freshly rebuilt
`local-patches`, including the S3 Glacier commit; deleted `phase1-bill-provenance` everywhere
(local + `ddp` fork). **One correction to the snippet above, found only by running it for real:**
`git 2.50.1` has no `--skip-empty` flag — the working equivalent is `--empty=drop`
(`git cherry-pick --empty=drop $(git merge-base main cherry-pick-line)..cherry-pick-line`). This
doesn't remove the need for C's periodic rebase — `cherry-pick-line` itself still needs rebasing
onto a moving `main` on the same monthly-or-opportunistic cadence — it only removed the per-commit
script-editing step, which is now gone for good (the old `cherry_pick()` helper function was
deleted from the script too, since nothing calls it anymore).

---

## 6. Implementation Order

1. ~~**H**~~ — **Done 2026-07-25.** `cherry-pick-line` created, script switched to the range-based
   pick (using `--empty=drop`, not `--skip-empty` as originally written — see §5.H), `phase1-bill-provenance` deleted. The bill-provenance deploy this was blocking is itself now live in production.
2. **D** — one-line addition to `apply-local-patches.sh` (push `ddp main`), ships independently, no risk
3. **E** — delete the already-stale `fix/fl-floor-vote-source-url` branch (local + `origin`) now, as cleanup
4. **G** — clarify the script's header comment while D/H are already touching the file
5. **B** — first upstream-merge attempt for `openstates-scrapers`, scoped to DDP's tracked jurisdictions; treat as a trial run to learn actual conflict cost before committing to "monthly" as the right cadence
6. **C** — rebase `ddp-patches` (and `cherry-pick-line`, once H exists) onto fresh `main` once B has established the merge is safe
7. **A** — write up the branch-model note in each repo's README once the process in B/C has actually been run once and proven out

---

## 7. Open Questions

- Is monthly the right cadence for B, or should it be tied to backfill/session-start events
  instead (FL's session opens ~November — natural checkpoint)?
- Should the upstream merge in B be a required gate before *any* historical backfill? **Moot for
  2023 regular specifically — it already ran and finished 2026-07-25 05:24 EDT (1,828 bills, 2,601
  vote events, 0 errors) without B ever having been done.** Worth deciding for the *next* backfill,
  not this one — and worth noting the 2023 data now sitting in the replica was scraped by code that
  may still be missing whatever upstream fixes have landed in the 22,098-commit gap, same risk
  class as the FL floor-vote bug this plan already documents.
- Does anyone besides this Mac need `ddp/main` (core) to be current — e.g., would a second
  engineer cloning the fork expect it to be usable standalone? If not, D may be lower priority
  than it looks.
