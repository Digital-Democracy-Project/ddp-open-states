# Architecture Assessment: OPEN-445 — Stage 3 data-quality gates (structure, not just counts)

## Architectural Question

`quality_check.py`'s Stage 3 gate currently only compares *counts* (Tier 1 identifier diff, Tier 2
field diff) between local and live. NC passed 2,338/2,338 bills and 1,081/1,081 Tier 2 checks while
every vote and sponsorship was unresolved, because counts can't see an unresolved reference, a
cross-session key collision, or missing structural fields. The question is **not** whether to add
structural checks — the ticket already specifies four — it's **where each one's logic should live
given what already exists**, and **what "wire into Stage 3 so a failure blocks and files a ticket"
concretely means** in a codebase whose two related automations (the Stage 0 onboarding probe, and
`jurisdictions.yaml`'s own state machine) already answer parts of this differently than a literal
reading of the ticket implies.

## Tech Stack Context

| Layer | Technology | Notes |
|---|---|---|
| Stage 3 implementation | `quality_check.py` (repo root, ~1,900 lines) | Stdlib `argparse` + `psycopg2` + `requests`; no framework. `Report`/`PASS`/`FAIL`/`WARN`/`SKIP` is the one pass/fail contract already in use (`report.summary()` returns `failed == 0`; `WARN` never blocks, `FAIL` always does) |
| Stage 0 implementation | `verify-jurisdiction` (repo root, ~1,900 lines) | Separate script, same DB, **gate-lettered** (A–I) architecture with an explicit `GateResult(letter, blocking, status, summary, details)` and a blocking/advisory split baked into scoring |
| Shared data model | `openstates-core/openstates/data/models/*.py` (Django models, no live Django app — used as an ORM layer against the existing Postgres schema) | `PersonVote.voter_name` / `voter_id` (FK column), `BillSponsorship(RelatedEntityBase)`.`person_id`/`entity_type`, `VoteEvent.dedupe_key`, `BillVersion.note` |
| Stage ordering / state | `jurisdictions.yaml` (repo root) | Per-jurisdiction manifest; `status: probing \| live \| paused` (no "Stage 1" value exists); already the one place config like this belongs (`check-jurisdiction-drift.py` keeps every consumer in sync with it) |
| External plan doc | `PLAN-push-button-onboarding.md` | **Not present in this checkout** — lives in a different repo (referenced from `RUNBOOK.md`, `PRIMITIVES.md`, and several `notes/*.md` files, but the file itself isn't here). Section 4.5 (the attribution-resolution addendum) and the Stage 0–4 pipeline definition are both in it |
| Ticket filing | None in this repo | No Jira API code exists anywhere in `ddp-open-states`. Every precedent (`verify-jurisdiction`'s own recommendation text, `notes/*onboarding-probe*.md`) is "the script reports, a human/agent files the ticket by hand per RUNBOOK §5" |

**Nine tracked jurisdictions** currently have `status: live` or `probing` in the manifest: `us`,
`fl`, `wa`, `va`, `mi`, `ut`, `az`, `ma`, `nc` — this is the state set the ticket's "all other
tracked states" and "floors set from those numbers" refer to.

## Grounding: three primitives already exist that this ticket would otherwise duplicate

This is the load-bearing finding, so it goes before the approaches:

1. **Gate 2 (unique vote keys)** — `verify-jurisdiction` already has a Gate I
   (`run_gate_i`/`run_gate_i_from_dir`, OPEN-456/OPEN-397), whose verdict logic lives in
   `compare_vote_keys()` / `find_vote_key_collisions()`. It already implements exactly this rule —
   "fail when a `dedupe_key` repeats across sessions or bills for a jurisdiction with >1 active
   session" — and already cites OPEN-397 as its origin, same as this ticket's AC. **But it operates
   on sampled scraped JSON files** (`vote_event_*.json` from a bounded dry-scrape), because Stage 0
   runs before anything is imported. Stage 3 needs the same rule run as a real SQL query over
   already-imported production rows (`opencivicdata_voteevent`, scoped by jurisdiction, grouped on
   `dedupe_key` across all sessions/bills) — the rule and its wording should be lifted verbatim from
   PRIMITIVES.md's dedupe_key section and `compare_vote_keys()`'s docstring; the mechanism cannot be
   reused as-is because the data source is different (full table vs. sample files).

2. **Gate 3 (version stage coverage)** — "stage" is not a free-standing field to query; it's the
   output of `note_stage()` in `openstates-core/openstates/utils/version_ordering.py`, the single
   canonical, OPEN-91-audited classifier already depended on by `text_extract.py` and api-v3's
   bill-detail endpoint. "No stage" == `note_stage(version.note)[0] == STAGE_UNKNOWN`. Reinventing a
   second regex table in `quality_check.py` would create exactly the kind of drift PRIMITIVES.md
   warns against elsewhere ("two Dockerfiles claiming to mirror each other can still drift"). This
   gate should **import and call** `note_stage()`, not reimplement version-stage classification.

3. **Gate 4 (people loaded first)** — `verify-jurisdiction` already has `count_people_loaded(conn,
   st)`, added for OPEN-446, whose own docstring narrates this exact ticket's root cause ("Zero means
   no qualifying people are present... NC imported first and every vote and sponsorship stayed
   unresolved until the legislators were loaded"). It's a five-line query
   (`COUNT(DISTINCT person_id)` via `opencivicdata_membership` joined to
   `opencivicdata_organization` scoped by `jurisdiction_id`). Stage 3 should call this same function
   (move it to a shared module, or import it), not re-derive "people count for a jurisdiction" a
   second way.

Only **gate 1 (attribution resolution)** has no existing implementation — and the ticket's own
description says not to build it here: *"This is OPEN-261; do it there and link it here, do not
duplicate it."* That instruction directly conflicts with this ticket's own AC bullet list, which
opens with "Implement Attribution resolution gate..." as if it were in scope. See Approach
discussion below — this is a real scope decision, not a detail.

## Approaches Evaluated

### Approach A: Implement all four gates as new, self-contained logic inside `quality_check.py`

Write four new functions directly in `quality_check.py`, each with its own query, ignoring what
`verify-jurisdiction` and `version_ordering.py` already do, because the ticket says "wire into
`quality_check.py`."

**Pros:** Fastest to scope — no cross-file refactor, no shared-module extraction decision to make.
**Cons:** Duplicates gate 2's rule and gate 4's query in a second place with a second chance to drift
from OPEN-397/OPEN-446 (exactly the failure mode PRIMITIVES.md's "two Dockerfiles" lesson warns
about); reimplements version-stage classification a second time, risking a second, slightly
different definition of "no stage" than the one api-v3 actually serves; still implements gate 1,
directly contradicting the ticket's explicit "do not duplicate, that's OPEN-261" instruction.
**Standards alignment:** Violates DRY without a countervailing reason; no reuse of audited logic.

### Approach B: Extract the three existing primitives into a shared module; implement only gate 1 narrowly scoped out per the ticket's own instruction

Pull `count_people_loaded()` out of `verify-jurisdiction` and `note_stage()`'s STAGE_UNKNOWN check
(already importable — `version_ordering.py` is already a public module built for exactly this kind
of reuse, per its own docstring) into wherever `quality_check.py` can reach them; write gate 2 as a
new SQL-based function that implements the *same rule* as `compare_vote_keys()` but queries the
imported table directly (can't share code with the file-sample version, but should share the rule's
wording/tests); explicitly **do not implement gate 1** in this ticket — add a dependency link to
OPEN-261 and make Stage 3's attribution check a thin call-site that consumes whatever OPEN-261
exposes (a function, a query, or a CLI flag), landing as a no-op/TODO-with-tracking-ticket until
OPEN-261 ships.

**Pros:** No duplicated logic; each gate's rule has exactly one implementation audited once;
resolves the AC/description conflict by following the description (which is explicit and gives a
reason — "do not duplicate it") over the AC bullet (which doesn't explain why gate 1 is listed).
**Cons:** Requires a small refactor of `verify-jurisdiction` (extracting `count_people_loaded`) and
touches a file this ticket wasn't originally scoped to touch; gate 1 landing as a stub means part of
the ticket's own acceptance list ("gate 1 needs a stated threshold... run against NC today: each
gate passes or reports a known number") can't be satisfied end-to-end until OPEN-261 exists —
this needs to be flagged back to the ticket owner, not silently absorbed.
**Standards alignment:** DRY, single-responsibility (each gate's logic owned by the one place that
already has to get it right for other reasons), matches the repo's existing norm of extracting
shared logic into importable modules once two callers exist (`version_ordering.py` itself was
extracted from `text_extract.py` for exactly this reason, per OPEN-91).

### Approach C: Same as B, plus treat "file a ticket and send back to Stage 1" as a reporting-contract change, not new Jira-API code

Everything in B, plus: don't write Jira API calls inside `quality_check.py`. Instead, extend the
existing `Report`/exit-code contract (already the mechanism Tier 1/Tier 2 use to block Stage 3 —
`report.record(FAIL, ...)` → `summary()` returns `False` → non-zero exit) to also emit a structured,
machine-parseable failure record (e.g., a `--json` output mode, or a per-gate result in the existing
log file under `logs/quality-check/`) that names which gate failed, its measured number, and its
floor. The actual Jira ticket filing and jurisdiction-status rollback remain a human/agent action
reading that output — exactly the pattern `verify-jurisdiction` already uses today (it never files a
ticket itself; its recommendation text says "file templated tickets per RUNBOOK.md §5 Stage 1").
Floors live in `jurisdictions.yaml` per jurisdiction (or one global default with per-state
overrides), consistent with the existing manifest-is-config-of-record convention (OPEN-327: "a new
state only needs the entries below... `quality_check.py`'s sweep read the manifest").

**Pros:** Matches the one automation pattern that already exists for this exact "probe fails →
someone files a ticket → state goes back a stage" shape, so it doesn't need to invent conventions for
Jira credentials/retry/idempotency inside a QA script, and doesn't silently rewrite
`jurisdictions.yaml`'s `status` field — which matters because NC's `status: live` was itself a
deliberate human override of unmet soak criteria (OPEN-417, "a human call"); an automated script
flipping that value back on gate failure would be overriding a human decision with no human in the
loop, in the same file, for the opposite reason.
**Cons:** The ticket's literal text ("a failure files a `quality-regression` ticket") reads like it
wants code that calls Jira directly — this needs confirming with the ticket owner before committing
either way, since it changes whether this ticket needs Jira API credentials, a retry/idempotency
story, and a new dependency at all.
**Standards alignment:** Single Responsibility (detection vs. remediation-workflow stay separate
services); 12-Factor config (floors externalized to `jurisdictions.yaml`, not hardcoded); matches
OWASP's principle of least privilege — a read-only QA script doesn't need write credentials to Jira
if a human/agent step already has them.

## Tradeoff Matrix

| Dimension | A: self-contained in quality_check.py | B: extract + reuse, stub gate 1 | C: B + reporting-contract for ticket filing |
|---|---|---|---|
| Complexity | Low | Medium | Medium |
| Time to implement | Low | Medium | Medium |
| Maintainability | Low (2nd copy of 3 rules) | High | High |
| Scalability (new gates later) | Low | High | High |
| Security posture | N/A (no new surface) | N/A | Better (no new Jira credential path in a QA script) |
| Testing ease | Medium (all logic local) | High (reuses already-tested primitives) | High |
| Reversibility | Medium | High (pure extraction, additive) | High |
| Alignment with codebase | Low (contradicts "do not duplicate," ignores existing primitives) | High | Highest (matches existing probe-reports/human-files-ticket pattern) |

## Recommendation: Approach C

**Why this approach:** It resolves the two real tensions in this ticket — the AC-vs-description
conflict on gate 1, and the ambiguity in "wire into Stage 3 so a failure files a ticket" — by
following the codebase's own precedent rather than the most literal reading of the ticket prose.
`count_people_loaded()` and `note_stage()`/`STAGE_UNKNOWN` are not patterns to imitate, they are the
actual functions this ticket should call; gate 2's rule is lifted from `compare_vote_keys()` even
though its mechanism (file sample vs. DB query) can't be shared. This satisfies 12-Factor config
(floors as externalized, per-jurisdiction data in `jurisdictions.yaml`, not invented or hardcoded —
matching the AC's own "not invented" instruction for gate 1's floor) and avoids OWASP's broader
"insecure design" risk of giving a read-only diagnostic script a write credential to an external
issue tracker it doesn't strictly need.

**Why not the alternatives:** Approach A actively contradicts the ticket's own stated instruction
not to duplicate OPEN-261, and reintroduces the exact "two copies drift apart" failure mode this
repo has hit before (PRIMITIVES.md's version-ordering and Dockerfile lessons) for the two gates that
already have one correct implementation. Approach B is correct on gates 2–4 and the OPEN-261 scope
call but leaves "file a ticket" underspecified in a way that will cause rework if the ticket owner
actually wants literal Jira-API code — it should be raised as a question, not guessed either way.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Gate 1 lands as a stub, so this ticket's own AC ("run against NC today: gate 1 needs a stated threshold accounting for 611 unresolved rows") can't be fully closed until OPEN-261 ships | High (if OPEN-261 isn't already done) | Medium | Confirm OPEN-261's status before `/plan-ticket`; if not done, split OPEN-445's AC so the attribution-floor work is explicitly OPEN-261's deliverable and OPEN-445 only wires the call site |
| "Send the state back to Stage 1" has no corresponding value in `jurisdictions.yaml`'s `status` enum (`probing`/`live`/`paused`) | High | Medium | Either add a status value for this (schema change, needs its own design sign-off) or keep the rollback a human action triggered by reading the gate-failure report — recommend the latter per Approach C, but this is a decision for the ticket owner, not a default to assume silently |
| Gate 4's "before routing" checkpoint is a `ddp-broker-py`/`ddp-sync` concern (BROKER-302), not something `quality_check.py` can see or enforce | Medium | Medium | Scope OPEN-445's gate 4 to the "before first import" + Stage-3 re-check only; file a follow-up ticket for the replica-routing-side check in the owning repo rather than silently dropping it |
| Attribution gate 1's denominator for sponsorships is ambiguous — `BillSponsorship` covers both person and organization entities; counting org-type rows as "unresolved" would skew every state's measured floor | Medium | High (bad floor = every future state either fails spuriously or the gate is meaningless) | Flag explicitly to OPEN-261: denominator must be `entity_type = 'person'` rows only |

**Prerequisites:**
- Confirm OPEN-261's current status (done / in progress / not started) before planning gate 1's
  wiring — this assessment found no code for it anywhere in this repo.
- A decision from the ticket owner on literal Jira-API-in-`quality_check.py` vs. the existing
  report-and-a-human/agent-files-it pattern, since it changes the dependency and credential surface
  of this ticket materially.
- Access to (or numbers already computed for) all nine tracked jurisdictions, to set the three
  floors from measured rates rather than inventing them, per the ticket's own instruction.

**Tech debt created:** None if gate 2/3/4 genuinely reuse the existing primitives as recommended. If
Approach A is chosen instead under time pressure, it creates exactly the duplicated-logic debt this
assessment flags above.

## Standards Checklist

| Standard | Status | Notes |
|---|---|---|
| OWASP Top 10 | Addressed | A04:2021 Insecure Design — recommend not adding a Jira write-credential path to a read-only diagnostic script without a stated need; A09:2021 Security Logging — gate failures should log specifics (measured number, floor, jurisdiction) to the existing `logs/quality-check/` convention |
| DRY / single-responsibility | Addressed | Core of the recommendation — three of four gates reuse existing audited logic instead of reimplementing it |
| 12-Factor config | Addressed | Floors live in `jurisdictions.yaml`, matching the existing manifest-as-config-of-record convention, not hardcoded in Python or only in a Jira ticket |
| Migration safety | N/A | No schema changes — every field these gates read (`voter_id`, `dedupe_key`, `BillVersion.note`, `opencivicdata_membership`) already exists |
| Idempotency | Addressed | All four gates are read-only queries; re-running Stage 3 produces the same verdict given the same data, no side effects to guard |
| Multi-tenancy | N/A | Single-tenant internal data pipeline, no per-user/tenant isolation concern |

## Next Step

Run `/plan-ticket` — but first resolve the two flagged open questions (OPEN-261's status, and
whether ticket-filing should be literal Jira API code vs. the existing report-and-human-files-it
pattern), since the implementation plan's shape depends on both answers.
