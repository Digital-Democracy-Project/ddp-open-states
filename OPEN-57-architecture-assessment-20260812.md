# Architecture Assessment: OPEN-57 — Verify and configure `eligible_for_scorecard` rules for Arizona

## Architectural Question

The ticket's premise, inherited from BROKER-47, is that Arizona is "unverified" against
Virginia-shaped `tally_pattern`/`DEFINITE_YES`/`DEFINITE_NO` defaults and that the fix is the same
shape as OPEN-60's US Congress work: sample the data, check whether the existing regex matches,
patch it if not, ship a `JurisdictionEligibilityConfig` migration. Live queries against the real
replica (below) show that premise doesn't quite hold for Arizona, in a way that changes what phase 1
should recommend and what phase 2 needs to build:

**Arizona never embeds a vote tally in text at all — not in `billaction.description`, not in
`voteevent.motion_text` — across all 14,404 rows, zero exceptions.** This is a different failure mode
than US Congress (OPEN-60: text has digits, wrong format — `221 - 203` vs `(96-Y 0-N)`, so a
tuned regex fixes it) and than Virginia (whose format the defaults were built against). For Arizona,
no regex, however tuned, can extract a tally that was never serialized into text in the first place.
The real question isn't "what regex fits Arizona's text" — it's **whether phase 2's eligibility
mechanism can pull structured vote counts from `opencivicdata_votecount` instead of parsing text**,
and if not, whether Arizona should be documented as structurally unscoreable via the current
mechanism rather than patched with a regex that will always no-op.

Separately, real data shows Arizona's `amendment-passage` tag (`DPA`/`DPA/SE`) is **not** a single
clean "bare committee shorthand, never scores" case the way the ticket's premise assumes — it
covers at least two distinct procedural moments, one of which sits immediately adjacent to a real,
recorded chamber-passage vote (evidence in §3 below). That's the same *shape* of problem
`JurisdictionEligibilityRule.requires_pattern` exists to solve for Virginia's `amendment-passage`
overload, not a case where "verified=True, empty ruleset" is obviously safe.

## Tech Stack Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Data source | PostgreSQL (OpenStates replica) | `postgresql://openstates:openstates_dev@localhost:5433/openstates` — **not** the `cams` DB the `postgres` MCP tool defaults to, and not this checkout's separate `openstates_dev` DB (same caveat documented in `notes/bill-actions-persisted-verification-20260811.md` and `notes/open-60-us-congress-eligibility-verification-20260812.md`) |
| Query access | `psycopg2` direct connection | Read-only queries in this session; consistent with prior phase-1 notes docs' method |
| Schema (this repo) | `openstates-core` Django models → `opencivicdata_billaction`, `opencivicdata_voteevent`, `opencivicdata_votecount`, `opencivicdata_personvote` | `voteevent.bill_action_id` exists as a column but is **unpopulated globally** (0/31,874 rows across all jurisdictions, not an AZ-specific gap) — cannot be used to join actions to votes; date+bill_id (+organization_id) is the only workable join key found |
| Consumer (out of reach) | `ddp-broker-py`, `Motion.eligible_for_scorecard`, `JurisdictionEligibilityConfig`/`Rule` | Not present in this workspace (confirmed: no `ddp-broker-py` checkout under this CodeBot workspace's tree — other paths matching that name on this machine belong to unrelated, isolated sessions and are out of scope per this repo's `repo.path` discipline). The exact interaction between `tally_pattern` and the `DEFINITE_YES`/`DEFINITE_NO` tag sets is not visible from here — same limitation OPEN-60's notes doc flagged for the cloture special-case shape |
| Precedent | `notes/open-60-us-congress-eligibility-verification-20260812.md`, `notes/bill-actions-persisted-verification-20260811.md` | Establish both the DB-connection caveat and the notes-doc format phase 1's actual deliverable must follow |

## Diagnosis (evidence, not hypothesis)

All queries below ran directly against the live replica, jurisdiction filter
`opencivicdata_jurisdiction.name = 'Arizona'` (`ocd-jurisdiction/country:us/state:az/government`),
2,190 bills, 14,404 billaction rows, sessions `49th-1st-regular` through `57th-2nd-regular`.

### 1. Classification breakdown (14,404 total AZ billaction rows)

| classification | count |
|---|---|
| reading-1 | 3,063 |
| reading-2 | 2,891 |
| passage | 1,948 |
| reading-3 | 1,492 |
| amendment-passage | 1,286 |
| committee-passage | 1,273 |
| informal-passage | 517 |
| executive-receipt | 456 |
| filing | 392 |
| executive-signature | 244 |
| failure | 175 |
| executive-veto | 151 |
| withdrawal | 140 |
| *(untagged, `classification = {}`)* | 1,868 |

Unlike US Congress's sparse vocabulary (OPEN-60: 11 tags, no `amendment-passage` at all), Arizona's
tag set is rich, closer to Virginia's shape — which makes the "just fall back to VA defaults"
instinct more plausible on the surface than it was for Congress. The text-format finding below is
why that instinct still doesn't hold.

### 2. One real bill's full action list — HB 2197, 57th-2nd-regular

`ocd-bill/7e4eec7d-e20a-4927-b062-d9cd8822cf6e` — "unlawful camping; stock; wildlife; access":

| order | date | description | classification |
|---|---|---|---|
| 0 | 2026-01-09 | Prefiled. | `[filing]` |
| 1 | 2026-01-13 | House First Reading. | `[reading-1]` |
| 2 | 2026-01-14 | House Second Reading | `[reading-2]` |
| 3 | 2026-02-09 | DPA | `[amendment-passage]` |
| 4 | 2026-02-24 | DPA | `[amendment-passage]` |
| 5 | 2026-02-25 | FAILED | `[failure, reading-3]` |
| 6 | 2026-02-26 | PASSED | `[passage]` |
| 7 | 2026-03-16 | FAILED | `[failure, reading-3]` |

Companion vote events for the same bill (`opencivicdata_voteevent`, joined by `bill_id`, no
`bill_action_id` link available):

| date | motion_text | motion_classification | result |
|---|---|---|---|
| 2026-02-24 | do pass amended | `[committee-passage]` | fail |
| 2026-02-25 | failed to pass | `[passage]` | fail |
| 2026-02-26 | Passed | `[passage]` | pass |
| 2026-03-16 | failed to pass | `[passage]` | fail |

Every description in this bill's entire action list is terse shorthand — `DPA`, `FAILED`, `PASSED`
— with no numeric content anywhere. This is not specific to this bill; see §3.

### 3. Does the global tally-pattern regex match Arizona's real vote-tally text?

The global regex (de-escaped, same correction OPEN-60 applied to the ticket's markdown-mangled
form):

```
\(\s*\d+\s*-\s*Y\s+\d+\s*-\s*N(?:\s+\d+\s*-\s*A)?\s*\)
```

i.e. Virginia-shaped `(96-Y 0-N)`.

Tested against all 1,948 `passage`-classified AZ rows: **0 matches** — same result as US Congress.
But the reason is different and more fundamental. Congress's text at least contains numbers in the
wrong format (`"221 - 203"`); Arizona's does not contain numbers **at all**:

- All 1,948 `passage` rows: 100% read exactly `"PASSED"`.
- All 1,492 `reading-3` rows: 100% read `"PASSED"` (1,385) or `"FAILED"` (107).
- All 1,273 `committee-passage` rows: 100% read exactly `"DP"`.
- All 517 `informal-passage` rows: 100% read exactly `"DP"`.
- All 175 `failure` rows: 100% read exactly `"FAILED"`.
- All 1,286 `amendment-passage` rows: 100% read `"DPA"` (1,167) or `"DPA/SE"` (119) — confirms the
  ticket's cited 2026-08-11 finding, verified here directly against all 1,286 rows, not a sample.
  (Note: no notes doc dated 2026-08-11 documenting this exists anywhere in this repo's `notes/` or
  git history as of this session — the underlying claim checks out against live data, but phase 1's
  actual notes doc should not cite a prior document that doesn't exist.)

**Checked across the entire AZ billaction table, not just `passage`/`amendment-passage`:**

```sql
SELECT count(*) FROM opencivicdata_billaction ba ... WHERE j.name = 'Arizona' AND ba.description ~ '[0-9]'
```

**Result: 0 of 14,404 rows.** No Arizona billaction description, of any classification, in any
session back to `49th-1st-regular`, has ever contained a digit. Same result for
`opencivicdata_voteevent.motion_text` (0 of the AZ-linked vote events contain a digit; distinct
values are things like `"Passed"`, `"do pass amended"`, `"failed to pass"`, `"do pass"`).

**This means the tally-pattern regex mechanism cannot ever produce a match for Arizona, regardless
of what pattern phase 2 writes.** It's not a wrong-format problem (fixable, as Congress's was, with
a better regex) — it's a wrong-field problem. Whatever numeric tally exists for an Arizona vote
lives somewhere else entirely:

`opencivicdata_votecount` stores real, structured, nonzero tallies (4,633 nonzero rows for AZ),
keyed by `vote_event_id`, with `option`/`value` pairs (`yes`/`no`/`not voting`/etc.) — e.g. the
2026-02-25 "failed to pass" vote on HB 2197 above: `yes: 15, no: 36, not voting: 8`. This is the
real vote-count data Arizona has; it is structured, not embedded in any text field a regex could
ever reach.

### 4. Does `amendment-passage` mean more than one thing depending on context?

Yes — confirmed with real data, and it's not the same overload shape as Virginia's, but it's the
same *class* of problem. Grouped all 1,286 `amendment-passage` (`DPA`/`DPA/SE`) billaction rows by
whether a same-day `opencivicdata_voteevent` exists for the same bill, and what that vote's own
classification is:

| same-day vote-event match | count | share |
|---|---|---|
| same-day vote tagged `committee-passage` only | 451 | 35% |
| same-day votes tagged **both** `committee-passage` and `passage` | 299 | 23% |
| no same-day vote event captured at all | 536 | 42% |

The "both" row is the important one. Real example — **HB 2082, 57th-2nd-regular**
(`ocd-bill/22fee663-a76a-425e-ae7d-ec9b34a18554`), full lifecycle:

| order | date | description | classification |
|---|---|---|---|
| 3 | 2026-01-22 | DP | `[committee-passage]` |
| 5 | 2026-02-24 | DPA | `[amendment-passage]` |
| 6 | 2026-02-25 | PASSED | `[passage, reading-3]` |
| 10 | 2026-03-11 | DPA | `[amendment-passage]` |
| 11 | 2026-05-18 | DPA | `[amendment-passage]` |
| 12 | 2026-05-18 | PASSED | `[passage, reading-3]` |
| 14–15 | 2026-06-02 | PASSED, PASSED | `[passage]`, `[passage]` |

Order 5's `DPA` (House) sits one day before order 6's floor `PASSED` — a same-day-adjacent House
committee-of-the-whole "do pass amended" report immediately preceding the real recorded floor
passage vote. Order 11's `DPA` (Senate) is same-day with both a `committee-passage`-classified vote
event (`do pass amended`, org = Senate) and order 12's `PASSED`/`passage` vote (`Passed`, org =
Senate) — the DPA report and the floor passage vote landed on the identical calendar day. Order
10's earlier `DPA` (also Senate, standing committee stage, no same-day vote event at all) is the
"clean" committee-shorthand case the ticket's premise describes.

So the same tag/text (`DPA`, classification `amendment-passage`) is used for at least two distinct
procedural moments in Arizona's process — a standing-committee report with no adjacent vote (536 +
part of the 451 cases), and a floor-stage report landing the same day as, or the day before, the
bill's actual chamber-passage vote (299 + part of the 451 "committee-passage-only" cases, like HB
2197's order 4 above, which precedes order 6's `FAILED` by one day). **Collapsing this into a single
rule — either "always exclude `amendment-passage`" or "always include it" — will be wrong for one of
the two cases.** This is the same shape of problem
`JurisdictionEligibilityRule.requires_pattern` was built to solve for Virginia's `amendment-passage`
(cross-chamber concurrence vs. same-chamber floor amendment); Arizona needs an analogous
disambiguation, not a verified-empty ruleset.

## Approaches Evaluated

### Approach A: Patch `tally_pattern` with an Arizona-shaped regex (mirror OPEN-60's Congress fix)

**How it works:** Write a new regex tuned to whatever numeric shape Arizona's text uses, the same
move that fixed Congress (bare `NNN - NNN` scoped to vote-language keywords).

**Pros:** Matches the established precedent exactly; phase 2 already has a working pattern to copy.

**Cons:** Provably cannot work. §3 confirms zero digits exist in Arizona's action or vote-motion
text, in any classification, ever — there is nothing for any regex to match. Shipping this wastes
phase 2 effort on a mechanism guaranteed to no-op silently (regex-doesn't-match is not usually a
loud failure), which is worse than doing nothing, because it looks fixed in review.

**Standards alignment:** None — this approach ignores the evidence rather than acting on it.

### Approach B: Leave Arizona on VA defaults, `verified=True`, empty ruleset, documented as "DPA never carries a tally so it naturally excludes itself"

**How it works:** Accept the ticket's framing that `amendment-passage` is safely nothing-to-do-here
shorthand and ship the minimal AC-satisfying config (a real config row, `verified=True`,
`verified_notes` citing the bills above, no rule overrides).

**Pros:** Fast, satisfies the letter of "config filled in or explicitly left empty with documented
reason." Correct for the narrow question "does `amendment-passage` itself carry a parseable
tally" — no, never, confirmed.

**Cons:** Answers a narrower question than the one that matters. It's not just
`amendment-passage` that carries no tally — it's every Arizona classification (`passage`,
`failure`, `committee-passage`, all of them). If `Motion.eligible_for_scorecard`'s
`DEFINITE_YES`/`DEFINITE_NO` tag membership is independent of `tally_pattern` (i.e., tag membership
alone is sufficient signal, regex is only used to extract vote counts for *display*, not
eligibility), this is fine. If `tally_pattern` matching is required as corroboration before a
`DEFINITE_YES`/`DEFINITE_NO` tag is trusted, "verified=True, empty ruleset" silently makes Arizona
score nothing, ever — a worse outcome than being unverified. This interaction is defined in
`ddp-broker-py`, which is not visible from this workspace; shipping this without confirming it is a
guess dressed up as verification. It also doesn't address the `amendment-passage` multi-meaning
finding in §4 at all.

**Standards alignment:** Satisfies documentation/traceability practice (a `verified_notes` field
naming real bills) but not correctness — false confidence is worse than the ticket's starting
"unverified" state if the interaction guess is wrong.

### Approach C (recommended): Report the structural finding, recommend a votecount-based path, and require `amendment-passage` disambiguation

**How it works:** Phase 1's notes doc documents, as fact, that (1) no text-based `tally_pattern` can
ever match Arizona regardless of shape — the numeric data was never serialized into text; (2) real
structured tallies exist in `opencivicdata_votecount`, joinable by `bill_id` + `start_date`
(`bill_action_id` is unusable — unpopulated globally, not an AZ gap); (3) `amendment-passage` is
multi-meaning in the same way VA's is, with real bill-cited evidence for both meanings. It hands
phase 2 an explicit decision point instead of a guessed answer: if `Motion` is already built from
`voteevent`/`votecount` data (not from `billaction.description` text — likely, since
`voteevent.motion_text` is the natural "motion" source), Arizona may need **no** `tally_pattern`
override at all, because the mechanism that override exists to fix (extracting embedded tallies from
text) was never the path Arizona's real numeric data flows through. If instead `tally_pattern` is
the *sole* source of vote-count truth with no `votecount` fallback, that's a real, pre-existing gap
for Arizona (not created by this ticket) that phase 2 needs to close structurally, not regex-patch.
Either way, `amendment-passage` gets a `requires_pattern`-shaped rule keyed on the same-day
`committee-passage`-vote-vs-`passage`-vote distinction in §4, not a blanket include/exclude.

**Pros:** Matches the actual evidence rather than the ticket's inherited assumption. Gives phase 2 a
decision it can act on regardless of which way `Motion`'s internals actually work (both branches are
covered). Directly answers all four of the ticket's phase-1 acceptance criteria with real,
broadly-checked (not sampled) data. Avoids shipping either a no-op regex (Approach A) or a
false-confidence empty ruleset that ignores the `amendment-passage` finding (Approach B).

**Cons:** More work for phase 1's actual notes doc (this assessment already did the core queries;
formalizing them into the notes-doc format and citing every classification exhaustively is
additional, but bounded, effort). Phase 2 has a genuine decision to make that phase 1 cannot resolve
from this repo alone — but naming that decision explicitly is more useful to phase 2 than guessing.

**Standards alignment:** Evidence-based verification (matches this repo's own established practice
in `notes/open-60-...` and `notes/bill-actions-persisted-verification-...`); least-surprise handoff
(phase 2 gets a real decision tree, not a black box); tenant/scope isolation (see Standards
Checklist).

## Tradeoff Matrix

| Dimension | A: Patch regex | B: Empty ruleset, verified=True | C: Report structural finding + decision point (recommended) |
|---|---|---|---|
| Complexity | Low | Low | Medium |
| Correctness vs. real data | Fails — 0 possible matches, provably | Partially right (DPA specifically) but guesses on the broader tag/regex interaction | High — matches every checked fact |
| Risk of false confidence | High (looks fixed, silently no-ops) | Medium–High (verified=True on an unverified interaction) | Low (defers the one genuinely unknowable piece explicitly) |
| Addresses §4 tag ambiguity | No | No | Yes |
| Alignment with OPEN-60 precedent | Superficial (same move, wrong fit) | N/A | Same rigor, different (correct) conclusion |
| Effort for phase 2 | Wasted | Low now, likely rework later | Slightly more upfront, less rework risk |

## Recommendation: Approach C

**Why this approach:** It's the only one that doesn't contradict evidence gathered directly from the
same replica every prior phase-1 doc in this repo used, with the same rigor (exhaustive counts, not
samples, per AC #3's explicit "broadly, not just in the sample already checked"). It gives phase 2 —
which has visibility into `Motion`/`JurisdictionEligibilityRule` that this workspace does not — an
actionable decision instead of an assumption made from the wrong side of the repo boundary.

**Why not the alternatives:** Approach A is disproven by a direct, total-population query (0/14,404
digit-containing rows) — there's no version of "try a different regex" that survives that fact.
Approach B answers the ticket's literal question about `amendment-passage` correctly but silently
assumes an answer to a question (`tally_pattern`'s role in the eligibility decision) that isn't
visible from this repo, and it doesn't address the real `amendment-passage` multi-meaning finding at
all — shipping it "verified=True" would mean re-opening this exact ticket the first time an AZ
scorecard silently drops every vote, or scores a committee-noise DPA on the same day as a real
passage vote.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Phase 2 can't confirm the `Motion`/`votecount` design question from this repo alone | Certain (repo boundary) | Medium | Phase 1's notes doc states the decision tree explicitly (both branches), so phase 2 only needs to check its own code, not re-derive the finding |
| `amendment-passage` disambiguation rule is wrong in a way not caught by one bill's regression test | Medium | Medium | Cite both HB 2197 (clean committee case, no same-day vote) and HB 2082 (same-day committee+passage case) in phase 2's regression test, not just one bill |
| The "no digits anywhere" finding could go stale as new AZ sessions scrape in | Low | Low | The query is a `~ '[0-9]'` full-table scan, cheap to re-run; not a one-time sample |

**Prerequisites:** None blocking phase 1. Phase 2 needs to inspect `ddp-broker-py`'s actual
`Motion` construction path (out of reach here) before it can pick between the two Approach-C
branches.

**Tech debt created:** None from phase 1 itself. If phase 2 confirms the "no votecount fallback"
branch, that's pre-existing debt this ticket surfaces (Arizona presumably has never had a working
tally signal), not new debt created by this work.

## Standards Checklist

| Standard | Status | Notes |
|----------|--------|-------|
| OWASP Top 10 | N/A | Read-only research against an internal replica; no user input, no new external-facing surface |
| Parameterized queries (OWASP A03 Injection) | Addressed | All queries in this session and in `notes/open-60-...`/`notes/bill-actions-persisted-verification-...` use `psycopg2` parameter binding for classification filters, not string interpolation |
| Tenant/scope isolation (multi-jurisdiction analog) | Addressed | Ticket's out-of-scope explicitly limits changes to `iso2='AZ'`; every recommended rule in §4/Approach C is scoped to Arizona-specific evidence, not proposed as a global default change |
| Migration safety/idempotency (12-Factor config, applies to phase 2) | Flagged for phase 2 | Phase 2's `JurisdictionEligibilityConfig`/`Rule` data migration should be reversible and idempotent per this repo's usual Django-migration conventions — not verifiable from this repo since the models live in `ddp-broker-py` |
| Evidence-based documentation (this repo's own ADR-equivalent practice) | Addressed | Matches `notes/open-60-...`'s and `notes/bill-actions-persisted-verification-...`'s method: full-population queries against the real replica, real bill IDs, no invented examples |

## Next Step

Phase 1's actual deliverable — the `notes/open-57-arizona-eligibility-verification-<date>.md` doc —
can now be written up directly from this assessment's queries (they already satisfy all four
phase-1 acceptance criteria with exhaustive, not sampled, evidence). Recommend `/plan-ticket` to
formalize that write-up plus the handoff, rather than `/design-feature` — there's no new data model
or schema work on the `ddp-open-states` side, just documentation of an existing structural finding.
Phase 2 (the actual `JurisdictionEligibilityConfig`/`Rule` migration, regression test, and
`validate_scorecards`/`reconcile_scorecards` run) is out of reach from this workspace and belongs in
a separate `ddp-broker-py` session against `fix/BROKER-47-agent` (PR #295), using this doc plus
phase 1's notes doc as its handoff artifact.
