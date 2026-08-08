# Architecture Assessment: OPEN-41 — finish verifying the 540-bill FL WAF vote-gap re-scrape (steps 4–6)

## Architectural Question

Steps 1–3 (regenerate the 540-bill list, capture the BEFORE baseline of 75 House vote events,
clear the cutoff, launch the full re-scrape) are done and are pure data-collection/scraper-trigger
work. Steps 4–6 are pure **verification** work — no feature code to write, no schema to touch. The
real architectural question is not "how do we build this" but:

**How do steps 4–6 get executed so that "ran against prod's replica, not dev" is a verifiable,
recorded fact rather than a repeat of the same unverified assumption §8.1a's own open question
already flagged once — given `quality_check.py`'s environment selection today is entirely ambient
(shell-exported env vars + one hardcoded URL), with no built-in signal of which environment it
actually hit?**

A secondary, blocking question: Step 4 requires an AFTER count "across the 540-bill list," but
that list is not a file in this repo — it was generated as part of Steps 1–3, and its current
location/form needs to be established before a like-for-like comparison against the BEFORE
baseline (75) is even possible.

## Tech Stack Context

| Layer | Technology | Notes |
|---|---|---|
| Verification tool | `quality_check.py` (repo root, `--tier2`/`--coverage` modes) | Single-file CLI, `psycopg2` (raw SQL) + `requests`; `fl` is already in `JURISDICTIONS` (line 42) and already has known-good invocations (`--tier2 fl 2026 --tier2-limit 250 --tier2-random`, used for OPEN-27) |
| DB selection | `DATABASE_URL` env var, default `postgresql://openstates:openstates_dev@localhost:5433/openstates` (`quality_check.py:36-39`) | Resolved **entirely from the invoking shell's environment** at run time — the script itself never checks or reports which database it actually connected to |
| Local API selection | `LOCAL_API = "http://localhost:8002"` (`quality_check.py:34`, hardcoded, not env-driven) | Confirmed live on this host: `docker ps` shows `ddp-openstates-api-1` bound to `0.0.0.0:8002` — this is **always prod's api-v3**, regardless of which `DATABASE_URL` is exported |
| Prod DB | `ddp-openstates-postgres-1` container, port `:5433`, database name **`openstates`** | Confirmed running (`docker ps`, "Up 9 days (healthy)") |
| Dev DB | **Same container, same port `:5433`**, database name `openstates_dev` (`RUNBOOK.md:270-274`) | Selected only by which `activate.sh` (prod) vs `activate-dev.sh` (dev) was last sourced in the current shell — there is no separate host/port to distinguish them |
| Environment selector | `source activate.sh` (prod checkout `~/Developer/repos/ddp-open-states`) vs `source activate-dev.sh` (dev checkout `~/Developer/repos/ddp-open-states-dev`) | Purely a matter of which shell session last sourced which file — a stale/leaked `DATABASE_URL` from an earlier session survives a `cd` between checkouts |
| Gate this unblocks | `DDP_OPENSTATES_JURISDICTIONS` env var in prod `ddp-broker-py` (`RUNBOOK.md:1113-1118`) | Currently routes only validated jurisdictions (e.g. `UT,MI`) through the replica; adding `FL` is a live-traffic config change gated on this ticket |

**Key fact driving the design:** the dev/prod split for the database is *only* a database name on
an otherwise-identical connection string, on the same container and port. That is precisely the
shape of mistake §8.1a's open question is worried about: two DB configs that look and feel like
"the same command, safely re-run" but silently diverge based on invisible shell state — exactly the
anti-pattern 12-Factor's config discipline (Factor III) warns about when a single config *shape*
resolves differently depending on ambient, non-explicit state.

## Approaches Evaluated

### Approach A: Manual discipline only — `cd` to the prod checkout, `source activate.sh`, eyeball `$DATABASE_URL`, run the checks

**How it works:** Standing in `~/Developer/repos/ddp-open-states` (never `-dev`), re-source
`activate.sh`, manually confirm the printed/echoed `DATABASE_URL` contains `/openstates` (not
`/openstates_dev`), then run the Step 4 SQL, Step 5 spot-diffs, and Step 6
`quality_check.py --tier2 fl <session>` sweep.

**Pros:** Zero code changes; fastest path; matches how every quality-check invocation in this
repo's history (OPEN-27, the Tier 2 250-bill sweeps) has been run so far.

**Cons:** This is exactly the procedure that produced the unresolved doubt in §8.1a's open
question in the first place — "whatever validation... may have actually run against the local Mac
Studio dev stack" describes a human who *did* believe they were following this same discipline.
Repeating the identical unverified procedure and asserting "this time it's really prod" is not
evidence; it's the same claim a second time. Nothing about this run would be distinguishable from a
mistaken one after the fact — the PLAN doc update in AC #4 would have nothing harder than an
assertion to record.

### Approach B: Add a minimal, explicit environment-assertion step (query `SELECT current_database()`, capture it as recorded evidence) before and inside the verification runs — no changes to `quality_check.py` itself

**How it works:**
- Before Steps 4–6, run `psql`/`docker exec ddp-openstates-postgres-1 psql -U openstates -c
  "SELECT current_database();"` using the exact `DATABASE_URL` about to be used, and paste the
  literal output (`openstates`, not `openstates_dev`) into the note/PLAN update as evidence.
- For Step 6, since `quality_check.py` never prints which DB/API it hit, wrap the invocation:
  `echo "DATABASE_URL=$DATABASE_URL"` immediately before running it, and include that line (with
  the database name, not credentials) in the captured log alongside the sweep's pass/fail output.
- Because `LOCAL_API` is hardcoded to `localhost:8002` (always prod's api-v3 container per the
  `docker ps` check above), there is no equivalent ambiguity to resolve on the API side — only the
  DB side needs the explicit check.

**Pros:** Directly closes the exact gap the ticket's own AC #3 caveat calls out, with real recorded
evidence, not a stronger assertion of the same care that already once produced ambiguity. No code
changes — pure procedure, so it ships at zero engineering cost and zero regression risk. Reusable
as boilerplate for the next environment-sensitive verification (this is a recurring failure mode
per §8.1a, not a one-off).

**Cons:** Still relies on a human/agent remembering to run the extra query every time — it upgrades
"trust" to "verify," but doesn't make the tool itself refuse to proceed on the wrong database.

### Approach C: Add a permanent preflight guard to `quality_check.py` itself (refuse to run, or print a loud banner, unless `current_database()` matches an expected prod value)

**How it works:** At the top of `main()`, after opening the `psycopg2` connection, run `SELECT
current_database()` and compare against an expected value (a new `--allow-dev` opt-out flag for
legitimate dev-checkout use, defaulting to requiring `openstates`). Fail fast with a clear error if
it doesn't match, per the fail-safe-defaults principle (secure/safe design: ambiguous or
unrecognized environment state should hard-stop, not silently proceed).

**Pros:** Makes the guarantee structural instead of procedural — closes the gap for every future
invocation, not just this ticket's.

**Cons:** Over-scoped for a verification-only ticket whose AC list is entirely about *running and
recording* Steps 4–6, not about hardening the tool; changes shared, actively-used production
tooling (`quality_check.py` is invoked by every jurisdiction's routine sweeps, not just FL) for a
gap this ticket only needs to close once; introduces a new flag/behavior that needs its own tests
and its own review cycle, delaying steps 4–6 behind unrelated tool work. This is legitimate Tier 1
tech debt worth tracking (see below), but bundling it into OPEN-41 conflates "verify this one
re-scrape" with "harden the shared tool," and risks the actual gate (routing FL to the replica)
slipping behind a scope-creep review.

## Tradeoff Matrix

| Dimension | A: manual discipline | B: explicit assertion + recorded evidence | C: permanent tool guard |
|---|---|---|---|
| Complexity | None | Trivial (one extra command) | Low-Med (new flag, new failure path, tests) |
| Time to implement | None | Minutes | Hours (code + tests + review) |
| Actually closes §8.1a's open question | No — repeats the same unverified pattern | Yes — produces recorded proof | Yes — structurally, going forward |
| Risk to shared/production tooling | None | None (read-only, no code change) | Some — touches code every jurisdiction's sweep depends on |
| Matches this ticket's AC scope (verify & record, not harden) | Under-delivers on AC #3's actual intent | Exact fit | Over-scoped |
| Reusable for future environment-sensitive checks | No | Yes, as documented practice | Yes, structurally, but not shipped by this ticket |

## Recommendation: Approach B

**Why this approach:**
- It is the literal fix for the literal gap AC #3 names: "run against prod's replica, not the dev
  stack." Recording `SELECT current_database()`'s actual output turns "we ran it against prod" from
  an assertion into an auditable fact attached to the PLAN doc update (AC #4) — which is exactly
  what's missing from every prior FL/AZ/VA/WA validation the open question is worried about.
- No code changes means zero blast radius: `quality_check.py` is shared, actively-scheduled
  production tooling (`RUNBOOK.md` references it across every jurisdiction's routine sweeps) —
  this ticket has no need to touch it to satisfy its own ACs, and touching shared tooling under
  time pressure to unblock a live-traffic gate (`DDP_OPENSTATES_JURISDICTIONS`) is exactly the kind
  of avoidable risk `tech-debt.md`'s Tier 3 guidance (don't let unrelated hardening block a gating
  fix) argues against.
- Matches `reuse-before-reinvent.md`: `quality_check.py --tier2 fl <session>` already exists and
  already ran successfully for FL (OPEN-27); Approach B reuses it completely unmodified and adds
  only a preceding verification step, rather than reinventing or extending the tool for a
  one-time need.

**Why not the alternatives:**
- **Not A** — it's not that manual discipline is inherently wrong, it's that this exact ticket
  exists *because* manual discipline alone already once produced an unresolved doubt. Repeating the
  identical procedure without adding any new evidence doesn't answer the open question; it just
  produces a second unverifiable claim.
- **Not C** — the hardening is real and worth doing, but it's a different ticket with a different
  blast radius (shared tooling every jurisdiction depends on) and a different owner of risk
  (introduces new code/tests to review) than "verify one already-completed re-scrape and update a
  doc." Bundling them risks the actual, time-sensitive gate (FL → `DDP_OPENSTATES_JURISDICTIONS`)
  slipping behind unrelated code review.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The 540-bill list from Steps 1–3 isn't found as a saved artifact (not committed to this repo, not present in this workspace) | High — confirmed: no matching file exists in this checkout (`find` for `540`/`vote-gap` returned nothing) | Blocks Step 4's exact "across the 540-bill list" comparison | Locate the list/query on the actual prod checkout where Steps 1–3 ran (likely a scratch file or an inline SQL predicate never saved), or reconstruct it deterministically: the 540 bills should be exactly "FL 2026 bills with a House committee vote event whose scrape timestamp falls in the pre-fix 2026-06-25/26 window" — re-deriving that WHERE clause and confirming it returns 540 rows again is itself a form of verification that the baseline was well-defined |
| `DATABASE_URL` in the current shell is stale from a prior session (exported once, never re-checked) | Medium — this is the literal failure mode the ticket exists to rule out | High — would silently validate against dev, exactly repeating the open question | Always re-`source activate.sh` immediately before Steps 4–6 in the same shell that runs them, then run the `SELECT current_database()` check from Approach B in that same shell before proceeding |
| CodeBot/automated sessions may not always have live Docker/DB access (this session does — `docker ps` shows the real prod containers reachable — but that isn't guaranteed for every workspace) | Unknown/session-dependent | High if steps 4-6 are attempted from a session without real DB/API access — results would be fabricated or the run would simply fail | Confirm `docker ps` shows `ddp-openstates-postgres-1` and `ddp-openstates-api-1` reachable as the very first action of implementation; if unreachable, this ticket's steps 4–6 must run as a human-interactive session on the Mac Studio itself (per this repo's own CLAUDE.md operating model), not from an isolated automated workspace — flag via `CODEBOT_QUESTION` rather than guessing |
| Step 6's "FL sweep" is read as needing a new capability (validating specifically the 540 previously-broken bills, not a generic sample) | Low — AC #6 says "quality_check.py FL sweep passes" with no mention of the bill list, unlike AC #4/#5 which explicitly name it | Medium if misread — would trigger unnecessary new-flag work | Read Step 6 as the existing, already-proven invocation (`--tier2 fl <session>`, as used for OPEN-27) — a general regression/quality gate for FL as a whole, distinct from Steps 4–5's list-specific checks; the 540-bill-specific comparison is fully covered by Steps 4 (count) and 5 (spot-diff) |

**Prerequisites:**
- Locate (or re-derive, per the mitigation above) the actual 540-bill list/query from Steps 1–3
  before Step 4 can produce a comparable AFTER count.
- Confirm the full re-scrape (started 2026-07-30, ~13–14h estimated) actually completed
  successfully rather than stalling or erroring partway — nothing in this workspace's `logs/`
  shows a completion marker for that run (expected: this is a fresh clone, not the host with the
  real logs), so this must be checked on the actual prod host/log location before trusting any
  AFTER count as final.
- Re-`source activate.sh` (never `activate-dev.sh`) in the shell that will run Steps 4–6, and
  verify `docker ps` shows the real `ddp-openstates-postgres-1`/`ddp-openstates-api-1` containers
  before starting.

**Tech debt created:** None by this ticket itself. Recommend filing Approach C (a permanent
`current_database()` preflight guard in `quality_check.py`) as a separate Tier 2 tech-debt ticket —
untracked today, now discovered and named here — since the underlying ambiguity (same
container/port, database-name-only environment split, zero tool-level self-reporting) will keep
producing this exact class of doubt for every future prod-vs-dev-sensitive verification, not just
FL's.

## Standards Checklist

| Standard | Status | Notes |
|---|---|---|
| 12-Factor App, Factor III (Config) | Addressed (finding, mitigated procedurally) | The dev/prod split violates the spirit of explicit, unambiguous config — same connection shape resolves to different backing stores based on invisible shell state; Approach B mitigates by making the resolved value explicit and recorded rather than assumed, Approach C (deferred) would fix it structurally |
| Fail-safe defaults (secure design principle) | Partially addressed, flagged for follow-up | `quality_check.py` currently has no fail-safe behavior for an unrecognized/wrong environment — it silently proceeds against whatever `DATABASE_URL` resolves to; not fixed by this ticket (see tech debt), but the recorded manual check in Approach B substitutes for it this one time |
| Reuse before reinvent (`reuse-before-reinvent.md`) | Addressed | Recommendation reuses `quality_check.py --tier2 fl <session>` completely unmodified (already proven for FL in OPEN-27) rather than adding a new bill-list-filtering flag or a parallel verification script |
| Tech debt tiering (`tech-debt.md`) | Addressed | The tool-hardening approach (C) is explicitly deferred and named as a Tier 2 ticket to file, not silently dropped or silently bundled in |
| Parameterized queries / OWASP A03:2021 Injection | N/A for this ticket | Step 4/5 are read-only ad hoc SQL against a known, fixed bill-ID set with no untrusted external input; still use `%s` placeholders if the 540-bill IDs are interpolated into a query rather than embedding them as raw string literals |
| Idempotent/reversible changes (`artifacts.md`) | Addressed | Every recommended action (SQL counts, spot-diffs, `quality_check.py` sweep, doc update) is read-only or additive-documentation; nothing here is destructive or hard to reverse |
| Multi-tenancy | N/A | Not a multi-tenant system |

## Next Step

No data model or cross-module design work is needed — this is a verification/ops ticket, not a
build. Recommend skipping `/design-feature` and going to `/plan-ticket` (or straight to
`/implement-ticket`) with this concrete shape already specified: locate/re-derive the 540-bill
list → confirm the re-scrape completed → re-source `activate.sh` and confirm `current_database()`
= `openstates` → run the Step 4 count query, Step 5 spot-diffs (2–3 bills against flhouse.gov
directly), and Step 6's `quality_check.py --tier2 fl <session>` sweep, all in that verified prod
shell → record all four pieces of evidence (BEFORE/AFTER counts, spot-diff results, sweep pass/
fail, and the `current_database()` proof) in the `ddp-infra/PLAN-open-states.md` §8.1a FL item.
File the `quality_check.py` preflight-guard hardening (Approach C) as a separate Tier 2 tech-debt
ticket rather than folding it into OPEN-41.
