# Architecture Assessment: OPEN-465 — Manifest-derived test assertions; retire the old nightly runner

## Architectural Question

Two independent cleanups, bundled because the survey (ddp-infra PR #347, rows B15/B17) filed
them together: **(1)** how should `test_check_jurisdiction_drift.py` and
`test_validate_jurisdictions.py` assert "the real manifest looks right" without re-breaking every
time a state is added, while still catching a genuinely broken validator rule; and **(2)** what is
the correct way to retire the old nightly runner, given it carries two stale per-jurisdiction lists
(no NC in its people-refresh loop; fixed FL/MA sessions) and nothing schedules it?

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Manifest | `jurisdictions.yaml` (10 entries today: us, fl, wa, va, mi, ut, az, ma, nc, al) | Single source of truth since OPEN-221/OPEN-318; this repo's own scripts derive from it (OPEN-327) |
| Schema validator | `validate_jurisdictions.py` + `test_validate_jurisdictions.py` (pytest) | Pure-Python, no DB/network. CI-gated via `.github/workflows/validate-jurisdictions.yml` |
| Drift checker | `check-jurisdiction-drift.py` + `test_check_jurisdiction_drift.py` (pytest) | Compares this repo's (now-derived) lists and, optionally, `ddp-sync`'s `sync_schedule.yaml` against the manifest's projected sets |
| Retired runner | the old nightly runner (this repo) | Confirmed dead in production twice over: `PRIMITIVES.md` ("scheduling moved to `ddp-sync`'s APScheduler on 2026-06-22") and `PLAN-coverage-completeness-check.md` §11/§12 ("the old nightly runner is no longer the production scheduler… dead code as far as the real weekly schedule is concerned"). `ddp-sync`'s own `sync_schedule.yaml` says outright it replaces the ad-hoc old-nightly-runner launchd job (paraphrased; ddp-sync's own comment names the retired script directly). |
| CI | `.github/workflows/validate-jurisdictions.yml` | Runs both test files on every PR that touches the manifest or validator/drift code; does not reference the retired runner |

## What's actually broken, verified directly

- **`test_check_jurisdiction_drift.py:267`** (`test_the_real_manifest_enrolls_every_archived_jurisdiction_somewhere_visible`):
  ```python
  assert {"us", "fl", "wa", "va", "mi", "ut", "az", "ma", "nc", "al"} == set(codes)
  ```
  `codes` comes from `--matrix`'s output, which is `project()`'d over every key in the real,
  loaded manifest. The test's own docstring says what it actually wants to guarantee: *"the
  matrix… must cover every manifest entry."* The literal is today's accidental snapshot of that
  set, not the property.

- **`test_validate_jurisdictions.py:460`** (`test_in_the_real_manifest_every_scheduled_state_is_live_or_paused_and_enabled`):
  ```python
  scheduled = {code for code, e in data.items() if e["archive"]["scheduled"]}
  assert scheduled == {"us", "fl", "wa", "va", "mi", "ut", "az", "ma", "nc", "al"}
  for code in scheduled:
      assert data[code]["status"] in ("live", "paused") and data[code]["archive"]["enabled"] is True
  ```
  The `for` loop is the real assertion and is already manifest-size-independent. The preceding
  equality line is the only part that pins the literal set, and it is redundant with it.

- **Two nearby tests already do this correctly and need no change** —
  `test_real_manifest_covers_the_eight_tracked_jurisdictions` (`test_validate_jurisdictions.py:225`)
  uses `<=` (subset) against the original eight, explicitly documented as "the manifest is allowed
  to grow beyond them." `test_matrix_lists_every_jurisdiction_and_feature`
  (`test_check_jurisdiction_drift.py:243`) asserts an exact 4-code set, but against a **synthetic
  fixture world** it constructs itself, not the real 10-entry manifest — adding a real state does
  not touch it. These two are the existing in-repo precedent for "derive or scope, don't pin the
  real file's literal size."

- **References to the retired runner**, by file:
  - Functional/living-doc references that assume the script is still a thing to restore state to:
    `RUNBOOK.md:1275` ("Then restore `va` to the old nightly runner"), `PRIMITIVES.md:31,35,55,946`
    (pipeline diagram, scheduling note, logging-convention list, OPEN-318 drift-check note),
    `check-jurisdiction-drift.py:31` (docstring listing it as deliberately-not-compared).
  - Historical, dated investigation logs that quote the script as it existed on the day they were
    written: `OPEN-40-architecture-assessment-20260808.md`, `OPEN-42-architecture-assessment-20260808.md`,
    `PLAN-coverage-completeness-check.md` §10-12, `notes/scraper-status-and-pydantic-break-20260713.md`.
    `run-archive.sh:23` is the same kind of thing in miniature — a one-line historical note about
    which scripts already resolved `SCRIPT_DIR` a certain way, not a functional dependency.
  - `.github/workflows/` and `test-manifest-derived-lists.sh`: **no references** (confirmed by
    grep) — nothing in CI or the OPEN-327 test suite depends on the file existing.

## Approaches Evaluated — test assertions

### Approach A: Derive the expected set from the manifest at test time
Replace the hardcoded literal with `set(data.keys())` (drift test) and drop the redundant
equality line, keeping the `for` loop (validator test).
**Pros:** Matches the ticket's first stated option exactly; smallest possible diff; the drift
test's assertion becomes a direct re-statement of its own docstring.
**Cons:** `set(codes) == set(data.keys())` is close to tautological — `matrix()` iterates
`for code, entry in manifest.items()` with no filtering, so this mostly guards against someone
*adding* a filter to `matrix()` later, not against today's real failure mode (an added state
breaking the test). Still correct, just not by itself a strong regression guard.

### Approach B: Move to a synthetic fixture, like the neighboring tests already do
Drop the real-manifest dependency entirely for these two assertions; assert the property against
a small hand-built fixture (as `test_matrix_lists_every_jurisdiction_and_feature` already does).
**Pros:** Maximum isolation from the real file's size; most consistent with the file's own
existing pattern for "the matrix must be complete."
**Cons:** Both current tests are explicitly titled `test_the_real_manifest_…` / `test_in_the_real_manifest_…`
— their point is to catch real-world drift (a bad edit to the actual `jurisdictions.yaml`), not
just to exercise the code path. Moving them to a fixture would quietly remove that live-manifest
coverage; nothing else in the suite re-asserts "the matrix covers every row of the *real* file"
or "every *real* scheduled state has valid status/enabled."

### Approach C: Derive, and add a floor (subset) check against accidental removal
Same as A, plus borrow the existing `<=` convention from
`test_real_manifest_covers_the_eight_tracked_jurisdictions` to assert the floor of **originally
unpaused/non-pilot codes** (`{"us","fl","wa","va","mi","ut","az","ma"}`) is still a subset of the
derived set — not an exact-equality snapshot, so adding a 9th/10th/11th state never breaks it, but
accidentally deleting one of the original eight's manifest entries, or flipping one of their
`archive.scheduled` flags off, does.
**Pros:** Satisfies the ticket's optional ask ("keep a test that fails when a code is removed
unintentionally if that matters") using a pattern the file already trusts elsewhere, rather than
inventing a new one. Keeps the real-manifest live-drift coverage Approach B would drop.
**Cons:** One more line per test than Approach A; requires picking which codes belong in the
floor (straightforward here — same eight as the existing precedent, deliberately excluding `nc`
(recently-promoted pilot) and `al` (paused) since their state is more likely to legitimately
change).

## Tradeoff Matrix

| Dimension | A: derive only | B: synthetic fixture | C: derive + floor |
|-----------|-----------------|----------------------|--------------------|
| Complexity | Low | Low | Low |
| Time to implement | Minutes | Minutes | Minutes |
| Catches "state added" false-red | Yes | Yes | Yes |
| Catches "state/flag accidentally removed" | No (weak) | No | Yes |
| Consistent with existing in-file precedent | Partial | Yes (matrix test) | Yes (subset test) |
| Preserves real-manifest drift coverage | Yes | No | Yes |
| Mutation-check (AC #3) unaffected | Yes — untouched parametrized tests already cover validator rules | Yes | Yes |

## Recommendation: Approach C (derive from the manifest, plus a floor check)

**Why this approach:**
- It is literally the ticket's own fallback clause ("or assert properties of every entry") plus
  its explicit optional ask, applied with a pattern **already proven in this same file** two
  tests away (`test_real_manifest_covers_the_eight_tracked_jurisdictions`'s `<=` subset check),
  rather than a new convention. Fit-with-codebase is the strongest signal here: this repo already
  solved "the manifest grows, don't pin the whole set" once, just not in these two spots.
- Satisfies the general **testing principle of testing behavior/invariants, not incidental
  state** (avoiding the "fragile/change-detector test" antipattern — a test that must be edited
  in lockstep with every unrelated production change is providing negative signal, not coverage).
- **AC #3 (mutation check) is unaffected either way**: the validator's actual rule enforcement
  (`archive.scheduled` requires `enabled` + `status` in `{live, paused}`) is covered by the
  existing synthetic, non-manifest-size-dependent parametrized tests
  (`test_a_state_before_live_cannot_be_on_the_recurring_archive_schedule`,
  `test_scheduled_requires_enabled`, etc., `test_validate_jurisdictions.py:409-453`) and by
  `assert errors == []` against the real file (`load_and_validate` already runs `validate()`).
  Neither of the two edited tests is where that guarantee lives; C just stops them from being
  *additionally, redundantly* pinned to today's exact code count without losing their live-drift
  purpose.

**Why not the alternatives:** Approach A alone is correct but weaker than what the ticket's
"if that matters" clause is asking for, for zero extra cost — there's no reason not to add the
floor. Approach B throws away real-manifest coverage these two tests are the *only* place
providing (the matrix fixture test two tests above it already covers the synthetic-fixture case;
duplicating that purpose here while losing the real-file check is a net loss of coverage).

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Floor set drifts out of sync if `nc`/`al` graduate to "always expected" | Low | Low | Comment the floor as "the original eight, OPEN-318"; revisit if/when `nc` fully soaks (already tracked separately, OPEN-417/418) |
| Someone reads "derive from the manifest" as license to also loosen `test_real_manifest_matches_known_live_config_values` or `test_real_manifest_covers_the_eight_tracked_jurisdictions` | Low | Low | Out of scope — those two already derive/scope correctly; PR should touch only the two named tests |

**Prerequisites:** None — both files already import what's needed (`load_and_validate`,
`DEFAULT_MANIFEST_PATH`) in the surrounding real-manifest tests.

**Tech debt created:** None. If anything this removes a (small) existing piece of debt — two
assertions that silently encoded "today's manifest has exactly these codes" as if it were a
schema invariant.

## Approaches Evaluated — retiring the old nightly runner

### Approach A: Delete the file; update living references; leave historical logs alone
Delete the old nightly runner. Fix the handful of references in files that are still active
guidance (`RUNBOOK.md:1275`, `PRIMITIVES.md:31,35,55,946`, `check-jurisdiction-drift.py:31`'s
docstring) so they describe the real driver (`ddp-sync`'s `sync_schedule.yaml` /
`run_secondary_scrapes_job()`) instead of a file that no longer exists. Leave the dated
investigation documents (`OPEN-40`/`OPEN-42` architecture assessments, `PLAN-coverage-completeness-check.md`,
the `notes/` file, `run-archive.sh:23`'s one-line historical comment) untouched, matching this
repo's own existing convention of not rewriting frozen point-in-time records
(`RUNBOOK.md:799`: "kept for historical record").
**Pros:** Matches the ticket's stated preference exactly; removes two stale lists (missing NC,
fixed FL/MA sessions) by removing the thing that carries them, rather than fixing lists nobody
runs; smallest action that actually closes the gap (a file that "does nothing live and is skipped
for a new state if run by hand" has negative value — it's an attractive nuisance for exactly the
"run it by hand" scenario the ticket describes).
**Cons:** The PR's grep-for-references check will still show historical-log hits; needs a
one-line note in the PR description explaining those are intentionally untouched, or review will
read it as an incomplete cleanup.

### Approach B: Convert its lists to derive from the manifest (OPEN-327-style), keep the file
Wire the old nightly runner through `jurisdiction-field.sh` like `activate.sh`/`run-people-refresh.sh`
already do, so it can no longer drift, and keep it as a manual-run fallback.
**Pros:** A human could still run a full manual sweep from this repo alone without `ddp-sync`.
**Cons:** Investing OPEN-327 engineering effort in a script that two independent documents
(`PRIMITIVES.md`, `PLAN-coverage-completeness-check.md` §11/12) already confirm nothing
schedules and whose own fix (`a139ca2`, the `session=194th` change) "never had a chance to run in
production" is effort spent maintaining a parallel, never-executed copy of logic that already
lives correctly in `ddp-sync` — the exact duplicate-source-of-truth problem OPEN-318/OPEN-327
exist to eliminate. If a human genuinely needs an ad-hoc full-fleet run, `run-scrape.sh <state>`
(the real entrypoint, still fully supported) already works per-jurisdiction; nothing is lost by
not having a looped wrapper around it that nobody maintains.

## Tradeoff Matrix

| Dimension | A: delete | B: convert & keep |
|-----------|-----------|--------------------|
| Complexity | Low | Low-Medium |
| Time to implement | Minutes | ~Same effort as A plus wiring + a test |
| Maintainability | Removes a maintenance burden | Adds one more script to keep derived-and-tested forever, for a path nobody uses |
| Reversibility | Fully reversible (git history) | N/A |
| Alignment with codebase direction | Matches OPEN-327's stated end-state ("don't add new schedule logic here") | Fights it |
| Closes the ticket's stated gap | Yes | Yes, differently |

## Recommendation: Approach A (delete)

**Why this approach:** The ticket itself states a preference for delete, and the evidence
fully supports it — this is not a judgment call, it's confirmed dead code with two independent
written confirmations in the repo's own docs, consistent with **DRY** (one production scheduler,
not two parallel copies of "which states, which sessions") and with **12-Factor's "one codebase,
one config"** spirit applied to scheduling (the schedule belongs in `ddp-sync`'s
`sync_schedule.yaml`, not duplicated here).

**Why not the alternative:** Approach B spends effort hardening a path that is, by the repo's own
written record, not just unscheduled today but actively mis-fixed in the past (the `session=194th`
fix that could never run) — a textbook case for deletion over continued investment, and directly
contrary to `PRIMITIVES.md`'s own instruction: "Don't add new schedule logic here — add a job to
`ddp-sync/config/sync_schedule.yaml` instead."

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Grep-for-references AC reads as failed because historical logs still mention the filename | Medium | Low | State explicitly in the PR description which hits are historical-record files and why they're intentionally unchanged, same convention as `RUNBOOK.md:799` |
| Someone actually does still run it by hand occasionally, unobserved | Low | Low | `run-scrape.sh <state> [session=X]` remains the fully-supported entrypoint; nothing it did is otherwise lost |

**Prerequisites:** None — confirm via grep (already done above) that no CI workflow or test
invokes the file before deleting.

**Tech debt created:** None; this removes tech debt (a second, stale, unscheduled copy of
per-jurisdiction lists).

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | N/A | No user input, auth, or external-facing surface in either change |
| DRY | Addressed | Both changes remove a duplicate source of truth (hardcoded test literal; hardcoded script lists) in favor of the existing manifest |
| 12-Factor (config) | Addressed | Scheduling stays owned by `ddp-sync`'s config, not re-duplicated here |
| Test-quality (avoid change-detector/fragile tests) | Addressed | Approach C for the tests specifically targets this smell |
| SOLID | N/A | No structural/class design involved |
| Accessibility / Multi-tenancy | N/A | Not applicable to this ticket |

## Next Step

This is small enough (two test edits + one file deletion + a handful of doc-line fixes) that
`/plan-ticket` can go straight to a task list without a `/design-feature` pass.
