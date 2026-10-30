# Architecture Assessment: OPEN-261 — Add a probe/QA gate for unresolved voter attribution (voter_name set, voter_id NULL)

## Architectural Question

How should the "does a `personvote` row's `voter_name` actually resolve to a `voter_id`" check
be implemented and wired into both `verify-jurisdiction`'s gate table and `quality_check.py`'s
Tier 2 sign-off bar, given that the ticket's own AC text ("gates A-H become A-I") is now stale —
**gate letter I is already taken**.

## A finding that changes the plan before any approach can be evaluated

OPEN-261 was filed 2026-09-09 against the 2026-08-27 addendum, when `verify-jurisdiction` had
gates A-H. Since then, **OPEN-397 shipped gate I** (`run_gate_i` / `verify-jurisdiction:683-770`,
`GATE_ORDER = {"A": 0, ..., "I": 8}` at `verify-jurisdiction:129`): *"no vote `dedupe_key` repeats
across the sessions sampled."* That gate is read-only, DB-optional, and already covers this
ticket's own "related, worth carrying into the same gate design" aside about OPEN-179's
duplicate-roll-call parsing — not by coincidence; OPEN-397 is the uniqueness assertion this
ticket's description asked for, already built under a different ticket number.

Consequence: **the new gate this ticket wants cannot be gate I.** It must be the next free slot,
**gate J**. This doesn't change what to build — the single query the plan specifies is unaffected
— but it does mean the ticket's acceptance criteria and the plan's own §4.4 table text (`gates
A-H become A-I`) need the letter corrected to J when this ships, and the PR description should
say so explicitly rather than silently relabeling. Flagging this now so it isn't rediscovered
mid-implementation as a naming collision.

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Probe | `verify-jurisdiction` (72KB, single-file Python 3 script, no package) | Gates A-I today; stdlib + `psycopg2` + the scraper toolchain's own imports (`openstates.fulltext`, etc.) |
| QA gate | `quality_check.py` (77KB, single-file Python 3 script) | `--coverage`/`--tier2` CLI; `psycopg2` direct SQL against the OpenStates replica; no ORM |
| DB | PostgreSQL, OpenCivicData schema (`opencivicdata_personvote`, `opencivicdata_voteevent`, `opencivicdata_bill`, `opencivicdata_legislativesession`, `opencivicdata_jurisdiction`) | Raw SQL throughout both tools, no Django ORM despite the `opencivicdata_*` table names (these are `pupa`/OCD tables imported by `os-update`, read directly) |
| Shared code between the two tools | **None** — no `lib/*.py` module either imports | Existing precedent is deliberate small duplication across them (see `verify-jurisdiction:89-93`'s explicit comment: "deliberately duplicated here... rather than shelled out to, matching this repo's existing precedent for a byte-for-byte-intentional small duplication") |
| Tests | `test_verify_jurisdiction.py` (54KB), `test_quality_check.py` (46KB) | Per-gate/per-check unit tests already follow a `run_gate_x()` / `compare_bills()`-style seam |
| Report format | Markdown to `notes/<st>-onboarding-probe-<date>.md` (probe); stdout + `logs/quality-check/*.log` tee (QA gate) | Both already have a "top N offenders" precedent to follow (gate I's `details.append(f"repeated key {key!r} on {where}")`, Tier 1's `breakdown_by_prefix(missing)`) |

## Approaches Evaluated

### Approach A: One SQL query, duplicated in both tools (gate J in the probe, a new line in `run_coverage_check`)

**How it works:** Add a small, self-contained function to each file — `run_gate_j(conn, st, session, active_sessions)` in `verify-jurisdiction`, and a `check_voter_resolution(report, conn, jurisdiction, session)` call inside `run_coverage_check` in `quality_check.py`. Both run the same shape of query:

```sql
SELECT pv.voter_name, COUNT(*)
FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent ve ON ve.vote_event_id = pv.vote_event_id  -- adjust join per actual FK name
JOIN opencivicdata_bill b ON b.id = ve.bill_id
JOIN opencivicdata_legislativesession ls ON ls.id = b.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id = ls.jurisdiction_id
WHERE j.id LIKE %s AND ls.identifier = %s
  AND pv.voter_name IS NOT NULL AND pv.voter_id IS NULL
GROUP BY pv.voter_name
ORDER BY COUNT(*) DESC
```
(the `jurisdiction_code == "us"` exact-match vs `LIKE` split already exists as a pattern to copy verbatim — `count_shared_date_signature`, `fetch_all_local_identifiers`, `sample_bills` all do this same branch).

In `verify-jurisdiction`, gate J samples the probed session plus up to `MAX_EXTRA_SESSIONS` others — reusing gate I's own `active_sessions[:MAX_EXTRA_SESSIONS]` pattern exactly, since the ticket's "sampled sessions" language matches gate I's multi-session sampling, not a single-session query. In `quality_check.py`, it runs once for the single `(jurisdiction, session)` pair `--coverage` already takes — `quality_check.py --coverage xx <session>` is explicitly one session at a time by design (`args.coverage` is `nargs=2`), so there's no "sample of sessions" to do there; the plan's Stage 3 text itself only ever invokes it per-session.

**Pros:**
- Zero new shared-module coupling. Preserves `verify-jurisdiction`'s existing, load-bearing property of being runnable as an isolated Fargate task (`--fargate`) with no dependency beyond the scraper toolchain — it already duplicates a regex rather than import from `import-summary.sh` for exactly this reason.
- Matches the exact per-tool seam each file already has: a `run_gate_x()` function dropped into `verify-jurisdiction`'s existing gate list; a `report.record(PASS/FAIL, ...)` call dropped into `run_coverage_check` next to the Tier 1/Tier 2 lines it's supposed to sit beside.
- Small (~20-30 line) query, trivially testable with the same fixture-DB pattern `test_verify_jurisdiction.py`/`test_quality_check.py` already use per gate.
- The probe's version can be verified read-only against an **already-onboarded** state's existing data (FL/MI) with zero scraping — just point `DATABASE_URL` at a replica that already has FL/MI's history and run `verify-jurisdiction fl`. This directly satisfies AC #4 without needing a live scrape.

**Cons:**
- Two copies of near-identical SQL to keep in sync if the schema ever changes (the FK name above needs confirming against the real `opencivicdata_personvote` schema before either copy is written). Low risk in practice — this repo already tolerates several near-identical `personvote` queries across the nine `fix-open*.py` backfill scripts plus `quality_check.py`'s own `count_shared_date_signature`, so this is the established cost structure, not a new one.

### Approach B: Extract a shared `lib/voter_resolution.py` module, imported by both tools

**How it works:** Factor the query + top-N formatting into one function in a new shared module; both `verify-jurisdiction` and `quality_check.py` import it.

**Pros:** Single source of truth; a schema change only needs one edit.

**Cons:**
- Breaks an explicit, documented repo convention. `verify-jurisdiction`'s own docstring (line 89-93) states the opposite choice was made deliberately for a comparable case ("rather than shelled out to, matching this repo's existing precedent for a byte-for-byte-intentional small duplication — api-v3's copy of version_ordering.py is the same call"). Introducing the first cross-script Python import between these two tools is a bigger, precedent-setting architectural change than this ticket's one-query scope justifies.
- Actively works against `verify-jurisdiction`'s Fargate-isolation design goal (`--fargate` runs the probe on a cloud IP as a near-standalone task; the module header's whole "Safety" section is about minimizing what the probe depends on and touches). A new local import adds a packaging/path dependency for a container image that currently needs none.
- `lib/` today holds exactly one file, a shell script (`lib/slack-alert.sh`) — there's no existing Python package structure to extend, no `__init__.py`, no install step. Standing one up is disproportionate to a ~20-line query.
- No testing or maintainability benefit large enough to offset the above, given the query is small and the duplication precedent already exists.

### Approach C: Build the check only in `quality_check.py`, skip the `verify-jurisdiction` gate

**How it works:** Treat Stage 3 (QA baseline) as the only place this matters, since a brand-new candidate state has no vote history yet at probe time — the gate would mostly report "no data" at Stage 0 anyway.

**Pros:** Less code; avoids the gate-letter question entirely.

**Cons:**
- **Directly fails AC #1**, which explicitly requires `verify-jurisdiction` to gain this gate. Not a real option, but worth stating why the ticket insists on both: the probe is re-runnable read-only against an *already-onboarded* state's existing data (that's exactly AC #4's verification path), so the gate isn't useless at probe time — it's a second, independent checkpoint, the same layered design the plan already uses everywhere else (Tier 1 coverage is checked at both Stage 0's structural gates and Stage 3's QA sweep; gate H's `BillVersionLink` check and Stage 3's extractor-success threshold are the same relationship). Dropping the probe side would leave this as the only data-quality class covered at just one of the two stages, an inconsistency a future gate audit would flag.

## Tradeoff Matrix

| Dimension | A: duplicate query, gate J | B: shared `lib/` module | C: QA-gate only |
|-----------|---|---|---|
| Complexity | Low | Medium (new package layout) | Low |
| Time to implement | ~0.5-1 day | ~1.5-2 days | ~0.5 day |
| Maintainability | Good (matches existing per-tool seams) | Good in theory, but fights existing isolation design | N/A — fails AC #1 |
| Scalability | Fine — bounded sample at probe, single-session query at QA gate | Same | N/A |
| Security posture | No change (read-only SQL, parameterized) | Same | Same |
| Testing ease | High — same per-gate fixture pattern both test files already use | High, plus a new module's own test file | High |
| Reversibility | High (two local edits) | Lower (introduces a new import graph to later unwind) | N/A |
| Alignment with codebase | High — follows the documented duplication precedent exactly | Low — reverses a stated design decision | Fails an explicit AC |

## Recommendation: Approach A — duplicate the query, land it as gate **J**

**Why this approach:**
- It is the only approach that satisfies all four ACs without introducing a new architectural element (a shared module) that the codebase has already explicitly declined to use for a structurally identical problem. "Follow existing patterns" here isn't a generic preference — `verify-jurisdiction`'s own docstring names the precedent and the reason (Fargate isolation) in the code itself.
- **Standards alignment:** this is a data-integrity assertion added at the boundary where the pipeline's output is consumed (the scorecard), which is the correct place per the plan's own stated principle carried over from OPEN-50 — *"a gate must assert the collected data actually resolved, not merely that it arrived."* It's also consistent with the principle of least surprise for the next person reading either file: the check lives exactly where its siblings (Tier 1 coverage, gate I's uniqueness check) already live, using the same `GateResult`/`report.record()` vocabulary, not a new abstraction to learn.

**Why not the alternatives:**
- B is architecturally heavier than the problem (one query) warrants, and it's not neutral — it actively undermines a documented isolation property (`--fargate` probes running with minimal local dependencies) for a repo that has exactly one precedent of shared `lib/` code (a shell script, not Python).
- C fails an explicit acceptance criterion and would leave this gate's two-stage coverage inconsistent with every other check class in the plan.

**Design details carried into the recommendation (not a separate decision, since the plan already settles them):**
- **Gate letter:** J, not I — `GATE_ORDER` gains `"J": 9`; the module docstring's gate table and `PLAN-push-button-onboarding.md` §4.4's own table both need the correction from "A-H become A-I" to "A-I become A-J" when this merges.
- **Blocking vs. advisory at the probe:** advisory, following gates E/F/G's precedent, not a dedicated `classify_probe()` branch like A/D/H. Reasoning: the probe's bounded dry-scrape sample (default 20 bills, capped at `DEFAULT_MAX_OBJECTS=300` objects) is too small to be a statistically meaningful voter-resolution rate for a brand-new candidate state, and AC #3's blocking requirement is explicitly scoped to "Stage 3 (QA baseline)" — i.e., `quality_check.py`, not the probe — so this isn't a weakening, it's matching what the AC text itself asks for.
- **Blocking at Stage 3:** in `quality_check.py`, follow the Tier 1 coverage convention exactly — `report.record(FAIL, ...)` whenever *any* unresolved row exists (not a hard-coded 95% cutoff in code), always printing the resolved/unresolved counts, percentage, and top-offending-names breakdown. This matches how Tier 1 coverage already works (FAIL on any real gap; the 95% language is the human sign-off bar applied when reading the numbers, documented exactly this way in the plan's own 2026-09-01 NC entry: "611/72,058 personvote rows unresolved (0.85%)... clearing the 95% bar... Remainder itemized, not hand-waved"). Auto-passing at an arbitrary percentage in code would also risk silently clearing FL/MI's own known-bad data if a sampled session happened to dilute the concentration — AC #4 wants the gate to *flag* the known-bad rows, which a FAIL-on-any-unresolved rule guarantees by construction; a numeric auto-pass threshold does not.
- **Top offending names:** `GROUP BY voter_name ORDER BY COUNT(*) DESC LIMIT 10`, printed into gate J's `details` list (mirrors gate I's `for key, where in sorted(collisions.items())[:10]`) and into the QA gate's report line (mirrors Tier 1's `breakdown_by_prefix(missing)`).
- **AC #4 verification path:** run `verify-jurisdiction fl` (or `mi`) with `DATABASE_URL` pointed at a replica that already holds that state's real scrape history — no new scraping needed, gate J's query runs read-only against existing `opencivicdata_personvote` rows exactly as `quality_check.py --coverage fl <session>` already does for Tier 1/2. OPEN-178 (FL, 3,369 rows across 43 names, 94% in five) and OPEN-174 (MI, 1,427 across 154 names) are both already-quantified, named ground truth to assert the gate reproduces.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| The two SQL copies drift as the schema changes | Low | Low | Same cost profile as the nine existing `fix-open*.py` scripts' independent `personvote` queries; not a new risk class |
| Exact FK column name between `opencivicdata_voteevent` and `opencivicdata_personvote` isn't `vote_event_id` as sketched above | Medium (sketch, not verified against the live schema) | Low — caught immediately by running against any dev DB | Confirm the real column name from `count_shared_date_signature`'s working query (`quality_check.py:899`) before writing gate J's version, copy the join verbatim |
| A reviewer re-reads the ticket's "A-H become A-I" text literally and ships a second gate I, silently overwriting OPEN-397's dedupe-collision gate | Medium — this is exactly the kind of literal-instruction-following failure this repo's own `CLAUDE.md` warns about elsewhere | High if it happens | State the J relabeling explicitly in the PR description and in `PLAN-push-button-onboarding.md`'s next dated entry, not just in code |
| Advisory classification at the probe reads as "this ticket's gate doesn't really gate anything" | Low | Medium (optics) | Document in the PR and in §4.4's table update that the blocking enforcement point is Stage 3 by AC #3's own wording, and the probe's role is early signal on states that already have data to query |

**Prerequisites:**
- Confirm the exact `opencivicdata_personvote` ↔ `opencivicdata_voteevent` FK column name against a real dev DB before writing either query (five minutes with `\d opencivicdata_personvote` or by reading `count_shared_date_signature`'s working version).
- Decide and record the gate-letter correction (J) in the same PR that implements it, and carry it into `PLAN-push-button-onboarding.md`'s next dated addendum per this plan's own convention of dating every substantive change.

**Tech debt created:** None beyond the pre-existing, already-accepted cost of near-duplicate `personvote` SQL across this repo's standalone scripts (same cost class as the current nine `fix-open*.py` files).

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | Addressed | Parameterized queries throughout (`%s` placeholders, matching every existing query in both files) — no string-built SQL |
| SOLID principles | Addressed | Single Responsibility: one function per gate/check, consistent with every existing `run_gate_x()` / `compare_*()` function in both files |
| 12-Factor | N/A | Both tools already read `DATABASE_URL`/`OPENSTATES_API_KEY` from the environment; this change adds no new config surface |
| Accessibility | N/A | CLI/markdown output only |
| Multi-tenancy | N/A | Single-tenant internal tooling, jurisdiction-scoped by design (`WHERE j.id LIKE %s` already enforces this everywhere) |
| Idempotent migrations | N/A | No schema migration — this is a read-only query against existing columns |
| Read-only safety (this repo's own bar, see `verify-jurisdiction`'s "Safety" section) | Addressed | Gate J never writes; it only reads `opencivicdata_personvote`, matching the probe's documented read-only guarantee |

## Next Step
Run `/plan-ticket` to turn this into a concrete task list (exact SQL, the `GATE_ORDER`/docstring/§4.4-table edits, the `report.record()` call site inside `run_coverage_check`, and the FL/MI verification run) and then `/implement-ticket`.
