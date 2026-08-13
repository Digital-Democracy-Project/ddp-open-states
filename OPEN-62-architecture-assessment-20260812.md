# Architecture Assessment: OPEN-62 — Verify and configure `eligible_for_scorecard` rules for Washington

## Architectural Question

`Motion.eligible_for_scorecard` (ddp-broker-py, BROKER-47) resolves each bill action to
`DEFINITE_YES` / `DEFINITE_NO` / `UNCLEAR` using a global `tally_pattern` regex plus a per-tag rule
table, both only ever confirmed against Virginia's text. Two prior tickets (OPEN-60 for US
Congress, OPEN-64 for VA breadth) already established the concrete pattern for this class of work:
query the replica directly, confirm or refute the regex and tag assumptions against real WA text,
and hand a `JurisdictionEligibilityConfig`/`JurisdictionEligibilityRule` recommendation to phase 2.
The architectural question this ticket actually turns on is narrower than "how do we verify this" —
that method is already settled precedent — it's:

**Given WA's real data, does the existing config shape (global defaults + a per-jurisdiction
`tally_pattern` override + optional `JurisdictionEligibilityRule` rows for tag-specific gates) fit
Washington, or does Washington need a structurally new kind of rule the way Congress did (a
text-pattern rule for an untagged action type with no classification to key off)?**

This matters architecturally because the three jurisdictions verified so far (VA, US, WA) have
turned out to need three different shapes of fix — VA needed a `requires_pattern` gate on an
existing tag, Congress needed a wholly new text-pattern rule for an untagged vote type, and (per
this ticket's findings) WA needs neither — only a `tally_pattern` override. Getting this
classification right prevents phase 2 from either under-building (missing a real gap) or
over-building (adding a rule for a distinction WA's own data doesn't make).

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Data source | PostgreSQL (OpenStates replica) | `opencivicdata_billaction` / `_bill` / `_legislativesession` / `_jurisdiction`, dedicated instance at `localhost:5433`, read-only from this repo |
| Query method | `psycopg2` direct connection | Established primitive (`quality_check.py`, `audit-motion-texts.py`, `backfill-motion-classification.py`); not the `postgres` MCP tool, which defaults to a different DB (`cams`) |
| Config target (phase 2, different repo) | Django ORM, `ddp-broker-py` | `JurisdictionEligibilityConfig` / `JurisdictionEligibilityRule` models, not accessible from this workspace |
| Handoff artifact | Markdown notes doc | `notes/open-62-washington-eligibility-verification-20260812.md`, same format as the two prior sibling tickets |

## Evidence Gathered (this assessment, live against the replica, 2026-08-12)

Full detail and every query is in `notes/open-62-washington-eligibility-verification-20260812.md`;
summarized here because it's what the recommendation below depends on:

1. **Classification breakdown** — 35,871 WA `billaction` rows across 18 distinct tags. No
   `amendment-passage` tag exists (confirms the ticket's premise still holds). No undifferentiated
   `committee-passage` either — WA always tags favorable/unfavorable directly.
2. **Global `tally_pattern` regex — 0/1,938 match** against `passage`-classified rows. Same total
   miss as Congress (OPEN-60), for a different reason: WA's real format is
   `"yeas, N; nays, N; absent, N; excused, N."` — no parentheses, no `Y`/`N`/`A` letter suffixes.
   A corrected pattern (`yeas,\s*(\d+);\s*nays,\s*(\d+);\s*absent,\s*(\d+);\s*excused,\s*(\d+)`)
   was tested against all 2,026 real tally-bearing rows and matched **100%**, resolving to exactly
   two literal templates — an unusually clean result compared to VA's and Congress's noisier mix.
3. **`amendment-passage` — confirmed still zero.** Cross-chamber concurrence (312 real actions,
   100% untagged `classification = []`) does **not** need its own rule: verified across 5 real
   bills that the concurring chamber immediately records a same-date, `passage`-tagged, fully
   tallied final vote on the amended bill. The default tag-based mapping already reaches that
   action once `tally_pattern` is fixed — no gate, no new tag rule.
4. **A real, recurring same-date duplicate-tally pattern** (`"Vote on final passage/third reading
   will be reconsidered"`) — 18 real bills, more frequent than VA's single confirmed case (HB1212,
   OPEN-64). Not a new gap: the existing nearest-in-time candidate/action matching fix (already
   proven to generalize once, VA → Congress) is expected to cover it; flagged for phase 2's test
   coverage rather than a new rule.
5. **SB6002's reported reconcile flakiness does not reproduce** against current replica data — no
   duplicate-motion pattern found in its action history, consistent with the ticket's own hedge
   that it was a transient data-sync artifact, not an eligibility-rule defect.

## Approaches Evaluated

The decision that matters here isn't the query methodology (settled by precedent) — it's **what
shape of config change phase 2 should make**, given what WA's data actually shows.

### Approach A: `tally_pattern` override only, no `JurisdictionEligibilityRule` rows

WA gets a `JurisdictionEligibilityConfig` row (iso2 `"WA"`) with an overridden `tally_pattern` and
an empty rule set, `verified=True`, `verified_notes` citing HB1376/HB2156/SB6002 and this doc.

**Pros:**
- Directly matches what the evidence shows: no tag-level ambiguity exists in WA's data the way
  `amendment-passage` created for VA (SB783) or the missing-tag problem created for Congress.
- Smallest possible change — lowest risk of introducing a rule that doesn't correspond to a real
  distinction in the data (over-fitting the config to a hypothetical, not a confirmed gap).
- Consistent with the ticket's own instruction: "If Washington's defaults already fit with no
  override needed, create the config row with verified=True and an empty rules set... don't skip
  this step just because nothing needs overriding" — this is exactly that case, except one field
  (`tally_pattern`) does need overriding.

**Cons:**
- Depends on the same-date-reconsideration pattern (§5 above) genuinely being covered by the
  existing nearest-in-time matching mechanism, which lives in `ddp-broker-py` and isn't visible
  from this repo — phase 2 needs to confirm this rather than assume it from this doc alone.

### Approach B: `tally_pattern` override + an explicit concurrence rule (mirroring VA's `requires_pattern` gate)

Add a `JurisdictionEligibilityRule` for the `passage` tag or a synthetic concurrence-adjacent tag,
gating on proximity to a `"concurred in"` action, mirroring VA's `amendment-passage`
`requires_pattern` gate.

**Pros:** would generalize the same shape of fix already applied for VA, keeping the three
jurisdictions' configs structurally similar.

**Cons:** **Not supported by the evidence.** VA needed a gate because its `amendment-passage` tag
is genuinely ambiguous — it covers both a real cross-chamber vote and a same-chamber floor
amendment that must never score (SB783). WA has no such ambiguity: the concurrence action itself is
never tagged at all, and the action that *is* tagged (`passage`) is never ambiguous — it's always
the final floor vote, with a clean, unambiguous tally format. Adding a gate here would be solving a
problem WA's data doesn't have, adding rule-table complexity and review burden for no behavioral
benefit — a violation of the "verified, not guessed" spirit the ticket exists to enforce in the
first place.

### Approach C: Leave Washington on the Virginia-shaped global defaults, unverified

Do nothing — this is the status quo the ticket exists to close out.

**Pros:** none beyond zero effort.

**Cons:** **Actively wrong, confirmed by evidence, not just "unverified."** The global
`tally_pattern` has a proven 0/1,938 match rate against WA's real `passage` actions — every single
WA floor vote currently fails to produce tally evidence under the defaults. This isn't a
theoretical risk; it's a confirmed, total functional gap identical in shape to what OPEN-60 found
for Congress.

## Tradeoff Matrix

| Dimension | A: `tally_pattern`-only override | B: override + concurrence gate | C: leave on defaults |
|-----------|-----------|-----------|-----------|
| Complexity | Low | Medium | None |
| Time to implement | Low | Medium | Zero |
| Maintainability | High — one field, matches real data | Lower — rule exists with no real case exercising its distinction | N/A |
| Correctness (vs. verified data) | Matches all findings | Adds an untested, unmotivated distinction | Confirmed broken (0% tally match) |
| Scalability (to future jurisdictions) | Good — mirrors "override only what's proven wrong" discipline established by VA/Congress | Risks over-fitting future configs to patterns copied from VA without verification | N/A |
| Testing ease | Straightforward — one regex test + concurrence/reconsideration regression bills | Harder — must justify and test a gate with no confirmed failure mode to catch | N/A |
| Reversibility | Fully reversible (config row, migration) | Fully reversible, but adds dead-weight surface area | N/A |
| Alignment w/ codebase precedent | Matches VA's *and* Congress's actual precedent: override only what's proven wrong | Matches VA's precedent superficially, ignores that VA's gate was evidence-driven, not template-driven | Contradicts the whole point of BROKER-47/OPEN-60/62/64 |

## Recommendation: Approach A — `tally_pattern` override only, empty rule set otherwise

**Why this approach:**

- **Evidence-driven, not template-driven.** The whole reason this class of ticket exists is that
  VA-shaped defaults were silently applied to every jurisdiction without verification. Approach B
  would repeat exactly that mistake in miniature — copying VA's `requires_pattern` gate pattern to
  WA because it's the shape "concurrence-related tickets" have produced twice before, not because
  WA's data shows the same ambiguity. The evidence in `notes/open-62-washington-eligibility-
  verification-20260812.md` §4 is unambiguous: 5/5 real bills show concurrence resolving into a
  clean, unambiguous, already-tagged final vote.
- **Follows OWASP-adjacent least-privilege-of-change principle applied to config surface area.**
  Every additional `JurisdictionEligibilityRule` is a piece of scoring logic that must be
  maintained, reasoned about, and kept correct as data drifts — adding one with no confirmed
  failure mode to catch is pure liability, not defense-in-depth (there's no adversarial input model
  here where an unnecessary check helps; it's a deterministic classification pipeline over trusted,
  already-validated internal data).
- **Matches this ticket's own explicit instruction** for the "defaults already fit" case — the only
  difference is that here, "defaults" minus the WA-specific `tally_pattern` fit, not defaults
  wholesale, since the regex is confirmed broken.

**Why not the alternatives:**

- **Approach B** fails on its own merits once WA's evidence is in hand — VA's gate was justified by
  a bill (SB783) with a genuine text-level ambiguity in the same tag; WA has produced no analogous
  bill despite sampling across 5 concurrence-bearing bills specifically chosen to surface exactly
  that kind of ambiguity if it existed.
- **Approach C** is simply confirmed wrong — this isn't a judgment call, it's a 0/1,938 measured
  match rate.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| The same-date reconsideration pattern (18 real WA bills) isn't actually covered by the existing nearest-in-time matching fix | Low — the fix is described as jurisdiction-agnostic in OPEN-60/64 | Medium — would silently misattribute one of two real tallies on ~18 bills | Phase 2's regression test should explicitly include HB 2156 (or another reconsideration bill), not just a clean concurrence bill like HB 1376 |
| A WA tally format variant exists outside the `passage`/`reading-3` sample checked here (e.g. in a different session range) | Low — 2,026/2,026 matched with only 2 literal templates found, a very clean result | Low-medium | If phase 2's `validate_scorecards --all` run surfaces new WA `UNCLEAR` motions post-deploy at a materially different rate than pre-deploy, that's a fast, cheap signal to re-open verification |
| `committee-passage-favorable`/`unfavorable` handling in ddp-broker-py's actual rule engine turns out to depend on `tally_pattern` in a way not visible from this repo | Low | Low — these tags carry no tally text in WA regardless, so no pattern change WA introduces should affect them | Phase 2 should confirm from the actual rule-engine code, not just this doc, since ddp-broker-py internals aren't visible here |

**Prerequisites:**

- None beyond phase 2 access to `ddp-broker-py` (already scoped there per the ticket: PR #295,
  `fix/BROKER-47-agent`).

**Tech debt created:** None. This closes out WA's share of the unverified-defaults debt BROKER-47
originally created; it doesn't introduce new debt.

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | N/A | Read-only replica queries against trusted internal data; no user input, no injection surface (parameterized queries used throughout) |
| SOLID principles | Addressed | Approach A keeps `JurisdictionEligibilityConfig` doing one thing (jurisdiction-specific override) without accreting rule logic that duplicates or second-guesses the classification pipeline |
| 12-Factor | N/A | Not a service-config change; a data-driven correctness fix |
| Accessibility | N/A | No UI surface |
| Multi-tenancy | N/A | Single-tenant internal scoring pipeline; jurisdiction scoping (`iso2`) is the existing, correct isolation mechanism and this change doesn't alter it |
| Idempotent migrations | Addressed (phase 2) | Phase 2's migration should follow the same idempotent-insert shape as migration `0052` (VA) — out of scope for this repo, but the precedent is directly reusable |
| Minimize unverified/over-fit rule surface (project-specific standard, established by this ticket family) | Addressed | Approach A explicitly rejects adding a rule not backed by confirmed ambiguity in real data — the core discipline BROKER-47/OPEN-60/62/64 exists to enforce |

## Next Step

Phase 1 (this repo) is complete: `notes/open-62-washington-eligibility-verification-20260812.md`
has the queries, real bill IDs, and the recommended `tally_pattern` plus the "no rule needed for
concurrence" finding, ready for phase 2 to implement directly. Phase 2 (migration, tests,
`verified=True`, `validate_scorecards`/`reconcile_scorecards` before/after) is `ddp-broker-py` work
and out of reach from this workspace — hand this assessment and the notes doc to whoever picks up
PR #295, `fix/BROKER-47-agent`, ddp-broker-py, `apps/ddp-broker/common/models/
JurisdictionEligibilityConfig.py` / `JurisdictionEligibilityRule.py`.
