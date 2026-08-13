# Architecture Assessment: OPEN-61 — Verify and configure `eligible_for_scorecard` rules for Utah

## Architectural Question

This ticket's phase 1 (the only phase this repo can do) is a verification task, not a build task:
what is the right, evidence-grade method to confirm — or refute — that the Virginia-shaped
`eligible_for_scorecard` tally regex and tag rules (`BROKER-47`) hold for Utah broadly, beyond the
single `HB247` concurrence case already covered by `UtHb247ConcurrenceTest`? The real architectural
decision is **methodology**, not code: how to query, sample, and categorize real Utah action data
so phase 2 (`ddp-broker-py`) gets a handoff artifact it can safely implement a migration from,
without re-deriving the evidence itself.

This is not a greenfield question. Two sibling tickets already answered the identical question for
two other jurisdictions this month — **OPEN-60** (US Congress) and **OPEN-64** (Virginia) — using
the same repo, the same replica, the same `Motion.eligible_for_scorecard` mechanism, and the same
notes-doc handoff shape. The live results split cleanly: US Congress's defaults were **actively
wrong** (0/4,897 tally matches), Virginia's were **correct but needed a `requires_pattern` gate**
for one ambiguous tag. Utah is closer to Virginia's shape (`HB247`'s tally already matched, and it's
a real concurrence vote), but "closer" is exactly the assumption this ticket exists to test, not
assume.

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Data source | Django ORM models (`openstates-core/openstates/data/models/bill.py`) over Postgres | `BillAction` → `opencivicdata_billaction` (482,212 rows prod-wide) |
| DB access | Direct `psycopg2` against `DATABASE_URL` (`activate.sh:8`) | `postgresql://openstates:openstates_dev@localhost:5433/openstates` — the real replica, port `5433` |
| Known footgun | `postgres` MCP tool | Defaults to the `cams` DB (port 5432-shaped, different service) — **wrong DB** unless explicitly pointed at the replica connection string above; both OPEN-60 and `bill-actions-persisted-verification` notes flag this explicitly |
| Handoff artifact format | Markdown notes doc, repo `notes/` dir | Established, repeated format: Context → Method → Result (numbered per AC) → Conclusion w/ recommended config → References |
| Target repo for phase 2 | `ddp-broker-py`, `common/models/JurisdictionEligibilityConfig.py` / `JurisdictionEligibilityRule.py`, migration + tests | Not reachable from this checkout — confirmed no `JurisdictionEligibilityConfig`/`eligible_for_scorecard`/`tally_pattern` references exist anywhere in this repo |
| Prior art (this repo) | `notes/open-60-us-congress-eligibility-verification-20260812.md`, `notes/open-64-virginia-eligibility-breadth-verification-20260812.md` | Same ticket family, same author-side methodology, both merged |

## Approaches Evaluated

### Approach A: Replicate the OPEN-60/OPEN-64 methodology exactly, scoped to Utah

**How it works:** Connect directly to the production replica via `psycopg2` using `DATABASE_URL`
(read-only queries only). Join `opencivicdata_billaction` → `opencivicdata_bill` →
`opencivicdata_legislativesession` → `opencivicdata_jurisdiction` filtered to Utah. Run the same
three-part investigation OPEN-60/64 ran: (1) classification breakdown across **all** Utah sessions
found locally — not just the one `HB247` lived in — since `ut-2025s2-tier2-500-bill-random-sample`
and `ut-2026-tier2-500-bill-random-sample` already confirm Utah has at least two distinct sessions
persisted (`2025S2`, a 5-bill special session, and `2026`, 496+ bills); (2) run the global tally
regex against every `passage`-classified (and any amendment/concurrence-tagged) action and
categorize non-matches by hand-sampling, exactly as OPEN-64 did for VA's 6,302 non-matches; (3)
specifically pull every action sharing `HB247`'s tag(s) and check for same-chamber floor-amendment
votes mixed in with cross-chamber concurrence votes, the Virginia `amendment-passage`/SB783 shape.
Write the notes doc in the exact format of `bill-actions-persisted-verification-20260811.md`.

**Pros:**
- Directly reuses a methodology validated twice this month on the identical mechanism, by the same
  team, with two different outcomes (one confirmed-broken, one confirmed-correct-with-a-gate) —
  proof the method actually surfaces both false positives and false negatives, not just one.
- No new tooling, no new DB connection pattern, no new risk surface. Read-only, already-scoped.
- The notes-doc format is now a de facto interface contract phase 2 already knows how to consume
  (OPEN-64's migration was written directly from OPEN-60/64-shaped docs).
- Naturally satisfies the AC requiring "several real bills' full action lists" and "grouped by
  classification" — that's exactly OPEN-60 §1/§2's structure.

**Cons:**
- Utah's total action volume is far smaller than VA's or Congress's (2 known sessions vs. VA's much
  larger multi-year corpus), so "broad" sampling here means "all of it," not a statistical sample —
  worth stating plainly in the notes doc rather than implying a larger-scale sweep than the data
  supports.

**Standards alignment:** Principle of least privilege (read-only queries against a replica, never a
write path); reproducibility/evidentiary rigor (real bill IDs, real action text, no invented
examples — the explicit bar OPEN-60 and OPEN-64 both held themselves to).

### Approach B: Query via the public `v3.openstates.org` API instead of the DB replica

**How it works:** Use `OPENSTATES_API_KEY` (already used by `quality_check.py`) to pull Utah bills
and their `actions[]` from the public API, replicating the classification/tally analysis over JSON
responses instead of SQL rows.

**Pros:** No DB credentials needed; matches what an external consumer of OpenStates data would see.

**Cons:**
- `bill-actions-persisted-verification-20260811.md` already confirmed local DB rows match the public
  API exactly, field-for-field — so this approach produces the same answer at strictly worse cost:
  API rate limits (30k req/day tier, shared with other jobs), pagination overhead, and no ability to
  do the DB-side `GROUP BY classification` aggregation in one query the way Approach A can.
- The ticket's own AC explicitly says "directly from the OpenStates replica
  (`opencivicdata_billaction`)" — this approach doesn't satisfy the AC as written.

**Standards alignment:** None gained over Approach A; violates "cite the AC as written" and adds
avoidable external dependency (12-Factor: prefer the most direct backing service, not a network
hop through a rate-limited proxy of the same data).

### Approach C: Use the `postgres` MCP tool for the queries

**How it works:** Use the connected `postgres` MCP tool instead of a standalone script.

**Pros:** No script-writing overhead; interactive.

**Cons:** Confirmed, named footgun in two prior notes docs in this exact repo — the MCP tool
defaults to the `cams` database, not the OpenStates replica on port 5433. Using it without
explicitly overriding the target risks silently querying the wrong database and producing a notes
doc with false findings (e.g. "Utah has 0 rows" because `cams` has no OpenStates schema at all).
Even with an override, it offers no benefit over a direct `psycopg2` script for this read-only,
scripted, multi-query analysis.

**Standards alignment:** Fails "verify before assuming" (efficiency.md) — this exact assumption
already burned a prior investigation in this repo.

## Tradeoff Matrix

| Dimension | A: Direct replica query (OPEN-60/64 method) | B: Public API | C: `postgres` MCP tool |
|-----------|---|---|---|
| Complexity | Low | Medium (pagination, rate limits) | Low, but hides a real footgun |
| Time to implement | Fast (proven script pattern) | Slower (network, pagination) | Fast, but risk of silent wrong-DB result |
| Correctness risk | Low | Low (matches DB per prior verification) | High unless target DB explicitly overridden |
| Satisfies AC as written | Yes (explicitly requires the replica table) | No | Technically yes, if overridden |
| Reusability for phase 2 handoff | High — matches OPEN-60/64's proven handoff shape | Low — different evidence shape | Same as A if used correctly |
| Alignment with codebase precedent | Exact match (2 recent sibling tickets) | None | Explicitly warned against twice already |

## Recommendation: Approach A — direct replica query, OPEN-60/64 methodology, scoped to all Utah sessions

**Why this approach:**
- It is the only approach that satisfies the AC's literal requirement to query
  `opencivicdata_billaction` directly, grouped by classification, across multiple real bills.
- It reuses a methodology already validated twice this sprint on the exact same mechanism
  (`Motion.eligible_for_scorecard`), producing two different, correct outcomes — strong evidence
  the method itself (not just luck) surfaces both "defaults are wrong" (US) and "defaults are right
  but need a narrow gate" (VA) cases. Utah could land in either bucket, or a third ("defaults are
  right, no gate needed") — the method doesn't presuppose the answer.
- Per `reuse-before-reinvent.md`, this is precisely the case for checking existing
  patterns/conventions before building something new: the notes-doc format and query approach are
  an established convention in this repo, not something to reinvent per-ticket.

**Why not the alternatives:**
- Approach B is strictly dominated — same underlying data (already proven identical to the DB),
  higher cost, and doesn't satisfy the AC as literally written.
- Approach C has a concrete, previously-realized failure mode in this exact codebase (wrong default
  DB) with no compensating benefit for a scripted, multi-step analysis.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Utah's total action volume is small, making "broad" sampling read as thin compared to VA/US's docs | Certain (structural) | Low — doesn't undermine validity, just needs framing | State explicitly in the notes doc that all known Utah sessions were covered, not a subsample, if that's what the data supports |
| A same-chamber floor-amendment tag ambiguity exists for Utah (VA's `amendment-passage`/SB783 shape) but is missed because only `HB247`'s own tag is checked, not all actions sharing that tag jurisdiction-wide | Medium | High — would ship a regression-test-covered but production-incorrect config | Explicitly pull every action sharing HB247's classification tag(s) across all Utah bills, not just re-confirm HB247 itself (this is AC #3, called out directly in the ticket) |
| Connecting to the wrong DB (the `cams`/MCP footgun) | Low, now that it's flagged twice in this doc and two prior notes | High if it happens | Use `activate.sh`'s `DATABASE_URL` directly via `psycopg2`; do not use the `postgres` MCP tool for this ticket |

**Prerequisites:** None. `DATABASE_URL` is already exported by `activate.sh`; the query pattern is
directly copyable from OPEN-60/64's method sections.

**Tech debt created:** None. Phase 1 is read-only research producing a single notes doc; no code
changes land in this repo. (Phase 2's migration, tests, and config land in `ddp-broker-py` and are
out of this repo's scope entirely.)

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | N/A | Read-only research against an internal replica, no user input, no write path |
| Least privilege | Addressed | Read-only queries only; no `postgres` MCP tool (which risks touching the wrong DB, not a privilege issue but a correctness one) |
| Reproducibility / evidentiary rigor | Addressed | Real bill IDs, real action text, sample sizes and categorization shown, matching OPEN-60/64's bar |
| Reuse before reinvent | Addressed | Directly reuses the OPEN-60/64 methodology and notes-doc format rather than inventing a new one |
| Multi-tenancy | N/A | Not a multi-tenant application concern; jurisdiction filtering is a query predicate, not a tenancy boundary |
| Idempotent migrations | N/A here | This repo does no migration work; phase 2's migration idempotency is `ddp-broker-py`'s concern |

## Next Step

Run `/plan-ticket` (or proceed directly to execution, since the method is fully specified and
low-risk) to run the Utah queries and produce
`notes/ut-open-61-eligibility-verification-<date>.md` in the OPEN-60/64 format, then hand off to
phase 2 in `ddp-broker-py`.
