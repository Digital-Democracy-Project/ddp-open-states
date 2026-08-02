# PLAN: Managing the OpenStates Forks

**Status:** DRAFT — analysis complete 2026-07-24, no implementation started yet.

**Goal:** `openstates-core` and `openstates-scrapers` are formal GitHub forks
(`Digital-Democracy-Project/openstates-core`, `Digital-Democracy-Project/openstates-scrapers`)
rather than local-patch-only checkouts (scrapers went formal 2026-07-17, core went formal
2026-07-19). **`people` joined them 2026-07-27** (`Digital-Democracy-Project/people`, created to
open openstates/people#3902 — Susan Valdés's missing 2022-2024 FL House term). **`api-v3` joined
2026-07-29** (`Digital-Democracy-Project/api-v3`, created for OPEN-12) — it doesn't fit the model
below at all yet; see §1a. Forking solved "how do we ship our own fixes," but nothing was ever set
up to answer "how do we keep receiving *upstream's* fixes." This plan documents the current state,
the gap, and a concrete process to close it.

---

## 1. Current State — What Each Fork Actually Is

All three repos live at `~/Developer/repos/ddp-open-states/<repo>` (`openstates-core` and
`openstates-scrapers` are installed editable into the shared `.venv`, see
`project-pydantic-people-fix` memory; `people` is data-only, read via `OS_PEOPLE_DIRECTORY`).
`openstates-core`/`openstates-scrapers` have a nightly refresh step in `apply-local-patches.sh`
(run via `ddp-sync`'s `openstates_patch_refresh` cron, 01:00 UTC); `people` has its own weekly
step (`run-people-refresh.sh`, Sundays). All three use **different fork models**:

| | `openstates-core` | `openstates-scrapers` | `people` |
|---|---|---|---|
| Local remotes | `origin` = public `openstates/openstates-core`; `ddp` = fork | `origin` = fork `Digital-Democracy-Project/openstates-scrapers`; `upstream` = public `openstates/openstates-scrapers` | `origin` = public `openstates/people`; `ddp` = fork |
| Fork model | Cherry-pick: nightly script rebuilds a throwaway `local-patches` branch from fresh public `main` + a short cherry-pick list | Formal: fixes land on the fork's own `main` via branch + PR, normal git history | Cherry-pick-adjacent: `main` mirrors public upstream exactly (weekly `git pull --ff-only` in `run-people-refresh.sh`, no explicit remote → follows `origin`); the `ddp` fork only ever holds short-lived fix branches for open upstream PRs, never becomes the source `main` pulls from |
| DDP's own diff surface | 1 commit (`d6653a5`, read `CACHE_DIR`/`SCRAPED_DATA_DIR` from env) | 24 commits (see §3), all scoped to specific state scraper files — WAF session fix, vote-count reconciliation, dedup, incremental `start=` filtering, motion classification, etc. | 1 commit so far (`8b864d85`, Valdés's missing term), on branch `fix/valdes-missing-2022-2024-term` — not on `main` |
| What the sync step does | `git checkout main && git pull origin main` (pulls **public** upstream directly into local `main`) → `git branch -D local-patches` → recreate from `main` → cherry-pick `d6653a5` | `git checkout main && git pull origin main` (pulls the **fork's own** `main` — never touches `upstream`) | `git pull --ff-only` against `origin` (public) — the real production-critical step, since a weekly cron reads this checkout directly for role/tenure data |
| Net effect | Local working tree is fresh every night, straight from public upstream | Local working tree just re-syncs to whatever's already on the DDP fork — upstream is never consulted | Local working tree is fresh every week, straight from public upstream; the fork is purely a staging area for contributing fixes back, never a data source |

**Why `people` follows the `core` model, not the `scrapers` model:** `people` backs a live
weekly cron (`run-people-refresh.sh` → `os-people to-database`) that real production reads from
(this Mac's local `api-v3`, WireGuard-tunneled to `ddp-api` for FL/WA/MI/AZ/VA/UT/US — see
`RUNBOOK.md` → "api.digitaldemocracyproject.org proxy"). Repointing `origin` at our fork would
introduce exactly the fork-drift risk this plan already documents for `openstates-core`
(§3 below) — the automated weekly pull would silently stop getting fresh community data the
moment anyone forgets to sync the fork's `main`. Keeping `origin` on public upstream means the
weekly refresh is always current by construction; `ddp` exists solely so a local fix (like
`8b864d85`) has somewhere to be pushed from and a PR opened against upstream, exactly like
`ddp`/`cherry-pick-line` already does for `openstates-core`.

### `api-v3` — a fourth, differently-shaped fork (added 2026-07-29, deployed same day)

`Digital-Democracy-Project/api-v3` forked from `openstates/api-v3` on 2026-07-29, prompted by
OPEN-12 (`GET /jurisdictions/{iso2}?include=legislative_sessions` 500ing — see
`PLAN-open-states.md` Appendix D). **Remote convention: `origin` already points at the DDP fork**
(matching `openstates-scrapers`'s model, not `core`/`people`'s) — this was set up correctly at
fork-creation time, no separate `upstream`/`ddp` split was ever needed here.

Two patches merged the same day:
- **PR #1** — a one-sided `back_populates` fix on `Jurisdiction`/`LegislativeSession`/`DataExport`.
  Kept even though live testing showed it wasn't actually necessary for OPEN-12 — the
  table-creation fix in `start-os-api.sh` was sufficient on its own. Being kept as legitimate
  independent hygiene, not reverted.
- **PR #2** — OPEN-13, exposes archived full bill text (`raw_text`) on `BillDocumentLink` for
  single-bill detail queries. A real feature, not hygiene — reviewed diff-by-diff, its schema
  assumption (`ddp_bill_version_document`) verified against the actual production DB (unlike
  OPEN-12's wrong assumption), and its full test suite run in an isolated container (something the
  PR's own author couldn't do) — 100/100 pass, no regressions.

**Deployed 2026-07-29, later the same day:** repointed the local checkout
(`~/Developer/repos/ddp-open-states/api-v3`) with a plain `git pull` (already on the right remote),
rebuilt `ddp-openstates-api:local`, redeployed via `docker-compose -f deploy/docker-compose.ddp.yml
up -d --force-recreate api`. Both fixes confirmed live: OPEN-12 endpoint 200s in ~126ms, OPEN-13
`raw_text` confirmed present on a real archived FL bill. Backup image tagged
`ddp-openstates-api:pre-pr1-pr2-backup-20260729` for rollback.

**Real incident during this deploy, not this fork's fault:** the first redeploy attempt ran
`--force-recreate` with no service name, which also recreated the *shared* dedicated Postgres
(`ddp-openstates-postgres-1`, :5433) and killed two live scrapes (`va`, `ut`) mid-write. No bill/vote
data was lost; both had to be manually restarted. Full writeup in `RUNBOOK.md` → "Known gotchas" →
the `--force-recreate` entry — the lesson is general to this compose file, not specific to api-v3.

Still doesn't fit the table above — no `apply-local-patches.sh`-style refresh step or cron exists
for this fork yet, so future patches will need the same manual pull/rebuild/redeploy cycle until
one is built. Lower urgency than it looks, since deploys are infrequent so far, but worth the same
eventual treatment (§5.A documentation, a place in the upstream-sync cadence of §5.B–D) rather than
staying a one-off manual process indefinitely.

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

**2026-07-28 — this recommendation's premise has changed since it was written.** It was written
when DDP's own diff surface for `openstates-core` was one commit (`d6653a5`) — at that size, a
cherry-pick rebuild genuinely is cheaper than maintaining a real diverging fork. That's no longer
true: the bill-document-archive feature (Phase 1/2, `PLAN-bill-document-provenance.md`) alone is
8+ commits, plus 3 more from the same-day bot-block fix, all DDP-only and none upstreamable. And
the two-branch split (`main` = upstream mirror, `cherry-pick-line` = DDP's actual target) just
produced a real incident, not a hypothetical one: a merged PR against the "obviously correct"
branch (`main`) sat completely inert until the next deploy step happened to check for it (§4.4).
A model with one branch and one rule — "this fork's `main` is DDP's, PRs land there, pull public
upstream into it on a cadence" (exactly `openstates-scrapers`' already-working model) — has no
equivalent wrong-branch trap, because there's only one branch to target. Whether that tradeoff
is worth taking now is the open question added to §7, not resolved here.

---

## 3. The Gap: Nobody Merges Public Upstream Into Either Fork's `main`

### `openstates-scrapers` — the real, active gap

Checked 2026-07-24, and the raw number **re-verified and corrected 2026-07-25** after Ramon
questioned it (rightly): `git log main..upstream/main | wc -l` really does return **22,102**
(re-run 2026-07-25; was 22,098 the day before — the gap grows by a handful of commits daily,
consistent with the "11 since fork" figure below) — but that figure is **not** 22,000 commits of
recent upstream activity, and the plan's original framing here was misleading. Breaking the same
commit set down by year:

```
2009: 333    2015: 1331   2021: 1593
2010: 1781   2016: 606    2022: 1022
2011: 2706   2017: 1779   2023: 1333
2012: 2909   2018: 1105   2024: 906
2013: 1396   2019: 545    2025: 724
2014: 672    2020: 1033   2026: 328
```

This is essentially the public project's **entire commit history back to 2009**, not a burst of
recent activity. `git merge-base` does find a shared ancestor (`c999752`, 2026-06-30), but a large
share of upstream's deep history — old merge commits joining long-since-dead branches into `main`
over 17 years — isn't reachable from that ancestor along whatever line DDP's fork's `main`
actually follows. That's a quirk of how the fork's history was constructed, not evidence of a
firehose of new commits. **The actual, actionable numbers:** only **11** commits have landed on
public upstream `main` since DDP's fork was created (2026-07-17); counting only along the
mainline (`--first-parent`, ignoring those old side-branch merges) the gap is **28** commits —
much closer to DDP's own 30-commit diff than to 22,000. Every one of those real 11-28 commits is
still invisible to us unless independently rediscovered (as happened with the FL floor-vote bug —
see `project-fl-historical-backfill` memory) — the underlying risk this section exists to flag is
real, just not at the scale the raw `wc -l` number implied.

The good news, unchanged: DDP's own changes are a small, well-scoped diff (30 commits as of
2026-07-25, was 24 on 2026-07-24 — see `git merge-base main upstream/main` → `c999752`), almost
entirely confined to individual `scrapers/<state>/` files. That means a merge from upstream is
very unlikely to be an unmanageable conflict storm — but it has never been attempted, so the
actual conflict surface is unverified.

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
   behind upstream. The `openstates-scrapers` gap (a real but modest ~11-28 commits since the fork
   was created, see §3 — not the misleadingly large raw `git log main..upstream/main` count, which
   includes 17 years of unrelated history) was discovered only because this conversation happened
   to ask about it — it could just as easily have gone unnoticed indefinitely, and would only get
   harder to eyeball correctly over time without a tool that already knows to filter it this way.

4. **A PR merged to the wrong branch is silently inert — happened for real, 2026-07-28.** A
   bill-document-archive fix (bot-block/CAPTCHA detection, prompted by a live MI incident that
   day) was opened and merged as `openstates-core` PR #3 against the fork's `main` — the natural
   choice by analogy with `openstates-scrapers`' model, where fork-`main` *is* where fixes land.
   But `openstates-core`'s `main` is the public-upstream mirror (§1), not DDP's integration
   branch; only `cherry-pick-line` is. The merge succeeded, GitHub showed it as merged, and
   nothing errored — it just never reached production, because `apply-local-patches.sh` only ever
   cherry-picks from `cherry-pick-line`. Caught only because the very next step (rebuilding
   `local-patches` to deploy the fix) was checked against what actually landed, rather than
   trusted on the strength of "the PR says merged." Re-landed correctly as PR #4 against
   `cherry-pick-line`. **This is exactly the failure mode §2's "keep the script" recommendation
   assumed would be rare** (see the note appended to §2 below) — worth weighing directly against
   whichever option wins in the open question added to §7.

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
# scrapers: how far behind is our main? --first-parent, not a plain main..upstream/main count —
# the latter includes 17 years of unrelated upstream history not reachable from the shared
# merge-base along main's own line (found 2026-07-25: raw count reads ~22,000, real gap is ~28)
cd openstates-scrapers && git fetch upstream --quiet && \
  echo "scrapers behind upstream: $(git log --oneline --first-parent main..upstream/main | wc -l)"

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
  may still be missing whatever upstream fixes have landed in the real (much smaller than
  originally stated — see §3) commit gap, same risk class as the FL floor-vote bug this plan
  already documents.
- Does anyone besides this Mac need `ddp/main` (core) to be current — e.g., would a second
  engineer cloning the fork expect it to be usable standalone? If not, D may be lower priority
  than it looks.
- **Added 2026-07-28, prompted by the wrong-branch incident in §4.4: should `openstates-core`
  drop the cherry-pick-line model entirely and just become a clean fork like `openstates-scrapers`**
  — DDP's fixes land directly on the fork's own `main`, public upstream gets pulled in on a
  periodic (monthly, or whenever someone's already touching the repo) cadence, same as
  Recommendation B/C already propose for the other two repos? This would retire `cherry-pick-line`
  and the nightly `local-patches` rebuild outright, not just rename or document them (§2/§5.G).
  Argument for: removes the exact wrong-branch trap §4.4 hit for real, and the "cheap because it's
  one commit" premise that justified keeping cherry-picking (§2) no longer holds now that DDP's
  own diff surface has grown into a real feature (Phase 1/2 archive + this fix, 11+ commits).
  Argument against, not yet weighed: cherry-picking does force each DDP commit to individually
  prove it still applies cleanly against fresh upstream every rebuild — a clean fork with a
  monthly pull would instead risk a bigger, less frequent merge-conflict reckoning, batched up
  once a month instead of surfaced nightly. Whichever way this goes, resolve it the same time as
  H's original migration (§5.H, §6.1) — don't leave `openstates-core` on a third, in-between model.

  **Resolved 2026-08-01: yes, drop it.** Decided while landing OPEN-19 (the MI Barracuda-cookie
  fetcher) — same day this question predicted would happen ("resolve it the same time as H's
  original migration") arrived in practice: PR #6 needed the fork's own `main` to be current,
  and the cherry-pick-line rebuild had already been silently bypassed by the last three DDP
  fixes (PRs #3, #5, #6 all merged direct to fork `main`) before anyone noticed the docs hadn't
  caught up. `apply-local-patches.sh` rewritten to treat `openstates-core` identically to
  `openstates-scrapers` (plain `checkout main && pull origin main`); `cherry-pick-line`/
  `local-patches`/`ddp-patches` branches retired; remotes renamed to match `openstates-scrapers`'
  convention (`origin` = fork, `upstream` = real project — previously reversed for `core`, which
  was itself part of what made the 2026-07-26 wrong-branch-targeting incident easy to hit). On
  the unweighed argument against: accepted the batched-monthly-merge-conflict risk as the right
  trade — `openstates-core`'s fork was confirmed at zero commits behind real upstream at
  migration time (checked directly, not assumed), so there's no backlog to batch yet, and the
  same argument didn't stop `openstates-scrapers` from using this model successfully since
  2026-07-03. See `RUNBOOK.md`'s `apply-local-patches.sh` section for the full incident history
  kept as record, and `PRIMITIVES.md` for the current (single, unified) mechanism description.
- **Resolved 2026-07-29, same day as raised: PR #1 and #2 deployed** (§1a) — remote convention
  question turned out to already be settled (`origin` = fork, `scrapers`'s shape) at fork-creation
  time. **Still open:** no forcing function/cron exists for *future* patches on this fork the way
  `apply-local-patches.sh`/`run-people-refresh.sh` do for the other three — each new fix will need
  the same manual pull/rebuild/redeploy cycle until one is built. Worth revisiting once this fork
  sees enough patch volume to justify the automation cost.
