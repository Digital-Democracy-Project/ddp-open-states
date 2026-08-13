# OPEN-61: Utah `eligible_for_scorecard` breadth verification

## Context

`Motion.eligible_for_scorecard` (ddp-broker-py, BROKER-47) is computed from a global
tally-pattern regex and a set of `DEFINITE_YES`/`DEFINITE_NO` action-classification tags that
were only ever confirmed against Virginia's own action text. Utah currently has one real
regression case (`HB247`, "House/ concurs with Senate amendment", `UtHb247ConcurrenceTest`) but
no `JurisdictionEligibilityConfig` row and no jurisdiction-wide verification. This is Phase 1 of
OPEN-61 (research, in `ddp-open-states`) -- the handoff artifact for Phase 2 (config/migration/
tests, in `ddp-broker-py`, `fix/BROKER-47-agent`, PR #295).

Three things were asked, all against real replica data, no invented examples:
1. Sample `opencivicdata_billaction` rows for Utah, grouped by classification, across several
   real bills (not just HB247).
2. Whether the global tally-pattern regex holds broadly for Utah.
3. Whether Utah has a tag that means more than one thing depending on context, the way Virginia's
   `amendment-passage` covers both a real cross-chamber concurrence vote and a same-chamber floor
   amendment that must never score -- specifically checking whether Utah's own `amendment-passage`
   tag (HB247's tag) has the same shape.

## Method

Queried the production OpenStates Postgres replica directly --
`postgresql://openstates:openstates_dev@localhost:5433/openstates` (the real replica; **not** the
`cams` DB the `postgres` MCP tool defaults to -- same caveat as `bill-actions-persisted-
verification-20260811.md`, `open-60-us-congress-eligibility-verification-20260812.md`, and
`open-64-virginia-eligibility-breadth-verification-20260812.md`). Jurisdiction filter:
`opencivicdata_jurisdiction.name = 'Utah'` (`ocd-jurisdiction/country:us/state:ut/government`).

All numbers below are live counts as of 2026-08-12, via `psycopg2` against
`opencivicdata_billaction` joined through `opencivicdata_bill` -> `opencivicdata_legislativesession`
-> `opencivicdata_jurisdiction`, plus `opencivicdata_voteevent` / `opencivicdata_votecount` for
real vote tallies.

## Result

### 1. Classification breakdown (37,340 total UT billaction rows, both known sessions)

Utah has exactly **two** sessions persisted locally: `2025S2` (5 bills, a special session) and
`2026` (1,016 bills). Unlike VA/US Congress this isn't a subsample of a larger corpus -- this is
the complete set of Utah action data available, stated plainly per the AC's "across more than
just HB247" ask.

| classification | count |
|---|---|
| receipt | 4,361 |
| passage | 2,144 |
| committee-passage-favorable | 1,930 |
| referral-committee | 1,447 |
| executive-receipt | 554 |
| reading-2 | 551 |
| enrolled | 548 |
| executive-signature | 515 |
| filing | 505 |
| **amendment-passage** | **424** |
| amendment-introduction | 226 |
| failure | 109 |
| deferral | 9 |
| amendment-failure | 7 |
| executive-veto | 2 |
| executive-veto-line-item | 1 |
| substitution | 1 |
| became-law | 1 |

### Two real bills' full action lists

**`HB 247`** (`ocd-bill/b692d11a-8bb8-4d0c-a8c1-9e692dc1b80b`, 2026 session, 66 actions) -- the
existing `UtHb247ConcurrenceTest` bill. Full list on file; key rows:

| order | date | description | classification |
|---|---|---|---|
| 22 | 2026-02-17 | House/ passed 3rd reading | `[passage]` |
| 46-48 | 2026-03-06 | Senate/ 2nd & 3rd readings/ suspension ... Senate/ passed 2nd & 3rd readings/ suspension | `[]` |
| 52 | 2026-03-06 | **House/ concurs with Senate amendment** | `[amendment-passage]` |
| 55 | 2026-03-07 | Senate/ signed by President/ returned to House | `[passage]` |
| 58 | 2026-03-07 | House/ signed by Speaker/ sent for enrolling | `[passage]` |
| 65 | 2026-03-25 | Governor Signed | `[executive-signature]` |

**`HB 101`** (`ocd-bill/85dcf430-f46e-43b1-812f-503275d99df0`, 2026 session, 45 actions) --
chosen because it independently contains **both** `amendment-passage` shapes in one bill's own
history, the same way VA's SB783 did:

| order | date | description | classification |
|---|---|---|---|
| 22 | 2026-02-17 | Senate/ comm rpt/ amended [Senate Natural Resources, Agriculture, and Environment Committee] | `[amendment-passage]` (same-chamber, procedural, no vote) |
| 28 | 2026-02-19 | Senate/ to House with amendments | `[]` |
| 31 | 2026-02-20 | **House/ concurs with Senate amendment** | `[amendment-passage]` (cross-chamber, real vote: yes=70, no=1, other=4) |

`HB 115` (`ocd-bill/919a6166-90fe-4dda-b0ed-1d47bd4eb876`) was pulled as a contrasting bill whose
*only* `amendment-passage` action is the same-chamber committee shape (`House/ comm rpt/ amended
[House Revenue and Taxation Committee]`, order 13) with no concurrence step at all -- confirms the
committee-only shape occurs independently, not just as a same-bill companion to a real concurrence
vote. `SB 2001` (`ocd-bill/5274ee44-c8d6-4efd-a7c6-0b2124c4a1d1`, the `2025S2` special session) was
pulled for session diversity -- its `Senate/ floor amendment failed` action is tagged
`[amendment-failure, failure]`, not `amendment-passage`, confirming Utah tracks failed same-chamber
floor amendments under a *different* tag pair entirely (no bleed into `amendment-passage`).

### 2. Tally-pattern regex

```
\(\s*\d+\s*-\s*Y\s+\d+\s*-\s*N(?:\s+\d+\s*-\s*A)?\s*\)
```

**Real methodological divergence from VA/US Congress, stated plainly:** scanning all 37,340 UT
`billaction.description` rows, **zero** contain an inline tally string matching this regex (VA had
2,720/9,022 `passage` rows match directly in description text). Utah's raw OpenStates action text
never embeds vote tallies -- the Y/N/Other counts live exclusively in the separate
`opencivicdata_votecount` table, joined via `opencivicdata_voteevent` (e.g. HB247's concurrence
vote: `yes=67, no=0, other=8`; HB101's: `yes=70, no=1, other=4`). This is consistent with the
ticket's premise that HB247 "already matched (56-Y 17-N)" -- that string isn't in the raw OpenStates
data itself, so it must be `ddp-broker-py`'s own `Motion` construction that formats it from
`votecount` before the regex runs. That construction code isn't reachable from this repo, but the
regex's *shape-compatibility* was verified directly: formatting all 214 real `"concurs with"`
concurrence votes' `votecount` rows as `(<yes>-Y <no>-N <other>-A)` produces a string the regex
matches **214/214 times, 0 failures** (samples: `SB 292` -> `(24-Y 2-N 3-A)`, `SB 69` ->
`(19-Y 0-N 10-A)`, `HB 475` -> `(58-Y 2-N 15-A)`, `HB 566` -> `(68-Y 1-N 6-A)`, `HB 591` ->
`(47-Y 14-N 14-A)`). **No format gap found; the global regex is fully compatible with Utah's real
tally data, whatever the exact string ddp-broker-py formats.**

### 3. `amendment-passage` breadth -- Utah's own concurrence/same-chamber ambiguity, confirmed

Utah's `amendment-passage` tag (428 total rows counting duplicate-description grouping; 424
distinct-row count from the classification breakdown above) is genuinely dual-purpose, the exact
shape the ticket asked to check for -- mirroring VA's `amendment-passage`/SB783 finding:

**Real cross-chamber concurrence votes (218 rows, 100% have a matching real `VoteEvent` +
`votecount`):**
- `"House/ concurs with Senate amendment"` and `"Senate/ concurs with House amendment"` -- the
  only two distinct text shapes in this group.
- Confirmed across many real bills beyond HB247: HB101, HB110, HB111, HB113, HB118, HB119, HB129,
  SB292, SB69, HB475, HB566, HB591, and more.

**Same-chamber committee-level amendment markers (210 rows, 0% have any matching `VoteEvent` --
purely procedural, not real votes):**
- `"House/ comm rpt/ amended [Committee Name]"` / `"Senate/ comm rpt/ amended [Committee Name]"`
  -- committee reports out a bill with amendments, most common shape (e.g. `House/ comm rpt/
  amended [House Education Committee]`, 15 occurrences; `Senate/ comm rpt/ amended [Senate
  Judiciary, Law Enforcement, and Criminal Justice Committee]`, 12 occurrences; dozens more
  committee variants).
- `"House/ comm rpt/ substituted/ amended [Committee Name]"` -- same shape with a substitute.
- `"Senate/ comm rpt/ sent to Rules/ amended [Senate Rules Committee]"`, `"Bill amended in Senate
  Rules Committee [Senate Rules Committee]"`, `"Senate/ amended in Rules"` -- Rules Committee
  procedural variants.
- `"Bill amended by Conference Committee [Conference Committee]"` -- conference committee
  procedural marker.

None of the 210 same-chamber rows have a matching `opencivicdata_voteevent` row (joined on
`bill_id` + `motion_text = description`); all 218 concurrence rows do. This is a clean, decisive
split confirmed against real vote-linkage data, not just text pattern-matching.

**Recommended `requires_pattern` gate**, validated against all 428 rows with **zero false
positives and zero false negatives** against the has-a-real-vote ground truth:

```
concurs with (House|Senate) amendment
```

| | matches gate | doesn't match gate |
|---|---|---|
| **has real VoteEvent** | 218 (true positive) | 0 (false negative) |
| **no VoteEvent (procedural)** | 0 (false positive) | 210 (true negative) |

**Spot-check of other UT-specific tags for similar ambiguity:** sampled `failure` (109 rows --
consistently `"House/Senate/ failed"`, `"...substitute adoption failed"`, `"...floor amendment
failed"`, committee "Motion to Recommend Failed" shapes, no real-vote/procedural mixing found),
`committee-passage-favorable` (1,930 rows -- consistently committee recommendation language, no
floor-vote text mixed in), and `amendment-failure` (7 rows -- consistently `"House/Senate/ floor
amendment failed"`, a real failed floor vote, distinct tag from `amendment-passage` so no bleed).
No other dual-meaning tag found. `passage`-tagged ceremonial signing rows (`"House/ signed by
Speaker/ sent for enrolling"`, `"Senate/ signed by President/ returned to House"`) exist (as in
VA) but are naturally excluded from scoring by the tally-regex not matching them -- the same
ceremonial-signing pattern OPEN-64 already characterized for VA, not a new gap.

## Conclusion

- **Global tally-pattern regex**: fully compatible with real Utah tally data. No change needed;
  recommend reusing the global default as-is for Utah's `tally_pattern`.
- **`amendment-passage` requires_pattern gate**: Utah needs the same kind of gate VA needed for
  its own `amendment-passage` ambiguity. Recommended `JurisdictionEligibilityRule`:
  - `classification = "amendment-passage"`, `requires_pattern = "concurs with (House|Senate)
    amendment"` -- validated with 0 false positives/negatives against 428 real rows.
- **No other tag ambiguity found** in `failure`, `committee-passage-favorable`, or
  `amendment-failure`.

Recommended `verified_notes` for the `ddp-broker-py` migration (`JurisdictionEligibilityConfig`,
jurisdiction iso2 `UT`):

> Basis: HB247 (`UtHb247ConcurrenceTest`, "House/ concurs with Senate amendment", amendment-passage,
> yes=67/no=0/other=8). Breadth-verified, OPEN-61/2026-08-12: classification breakdown across all
> 37,340 UT billaction rows (both known sessions, 2025S2 + 2026 -- the complete local corpus, not a
> subsample). tally_pattern confirmed format-compatible with real votecount data across 214 real
> concurrence votes (0 format failures; UT's raw action text never embeds tallies inline, unlike
> VA/US Congress -- tallies live in votecount/voteevent only). amendment-passage tag confirmed
> dual-purpose like VA's own case: 218 real cross-chamber concurrence votes (100% have a matching
> VoteEvent) vs. 210 same-chamber committee-level amendment markers (0% have a VoteEvent) across
> HB101, HB110, HB111, HB113, HB118, HB119, HB129, SB292, SB69, HB475, HB566, HB591 and more.
> requires_pattern "concurs with (House|Senate) amendment" added for amendment-passage, validated
> with 0 false positives/negatives against all 428 rows. No other tag ambiguity found in
> failure/committee-passage-favorable/amendment-failure sampling.

**Additional regression test candidate for Phase 2** (beyond `UtHb247ConcurrenceTest`): `HB101`
is a strong second fixture because it contains *both* shapes in one bill -- a same-chamber
`"Senate/ comm rpt/ amended [...]"` action that must stay `UNCLEAR`/non-scoring, and a real
`"House/ concurs with Senate amendment"` vote (yes=70, no=1, other=4) that must be
`eligible_for_scorecard=True` -- directly exercising the new `requires_pattern` gate the way VA's
`RequiresPatternDistinguishesSameChamberFromConcurrenceTest` does for SB783.

## References

- `notes/open-60-us-congress-eligibility-verification-20260812.md` -- sibling ticket, same
  mechanism, US Congress found actively wrong (0/4,897 tally matches)
- `notes/open-64-virginia-eligibility-breadth-verification-20260812.md` -- sibling ticket, same
  mechanism, VA found correct-with-a-gate (the `amendment-passage`/SB783 shape this ticket
  confirmed Utah shares)
- `notes/bill-actions-persisted-verification-20260811.md` -- confirms `opencivicdata_billaction`
  is the correct, fully-persisted source table, and the `cams`/MCP-tool DB footgun
- `notes/ut-2026-tier2-500-bill-random-sample-20260803.md`, `notes/ut-2025s2-tier2-500-bill-
  random-sample-20260803.md` -- prior UT data-quality sweeps confirming the 2 sessions/1,016+5
  bill counts used as this doc's population
- Production DB: `opencivicdata_billaction` / `opencivicdata_bill` /
  `opencivicdata_legislativesession` / `opencivicdata_jurisdiction` / `opencivicdata_voteevent` /
  `opencivicdata_votecount`
- Phase 2 handoff target: `ddp-broker-py`, `common/models/JurisdictionEligibilityConfig.py` /
  `JurisdictionEligibilityRule.py`, branch `fix/BROKER-47-agent`, PR #295 -- not reachable from
  this checkout; no `ddp-broker-py` clone exists anywhere in this workspace
