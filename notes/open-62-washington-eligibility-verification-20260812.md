# OPEN-62: Washington `eligible_for_scorecard` verification — Virginia-shaped defaults don't fit, and here's what the real data looks like

## Context

`Motion.eligible_for_scorecard` (ddp-broker-py, BROKER-47) is computed from a global tally-pattern
regex and a set of `DEFINITE_YES`/`DEFINITE_NO` action-classification tags that were only ever
confirmed against Virginia's own action text. Washington currently falls back to those
Virginia-shaped defaults, unverified. This is phase 1 of OPEN-62 (research, in `ddp-open-states`)
— the handoff artifact for phase 2 (config/migration/tests, in `ddp-broker-py` PR #295,
`fix/BROKER-47-agent`).

Four things were asked, all against real replica data, no invented examples:
1. Sample `opencivicdata_billaction` rows for Washington, grouped by classification, including at
   least one real bill's full action list.
2. Whether the global tally-pattern regex actually matches Washington's real vote-tally text.
3. Whether Washington still has zero `amendment-passage`-tagged actions, and if so how
   cross-chamber concurrence votes are tagged instead.
4. Write it up so phase 2 has real bill IDs and real action text to implement against. Also:
   sanity-check the SB6002 same-date duplicate-motion reconcile flakiness noted during BROKER-47
   verification (2026-08-11), while sampling WA action data — flagged as likely a data-sync timing
   artifact, not confirmed as an eligibility-rule issue.

## Method

Queried the production OpenStates Postgres replica directly —
`postgresql://openstates:openstates_dev@localhost:5433/openstates` (the real replica; **not** the
`cams` DB the `postgres` MCP tool defaults to, and not this checkout's separate `openstates_dev`
DB — same caveat as `notes/bill-actions-persisted-verification-20260811.md`,
`notes/open-60-us-congress-eligibility-verification-20260812.md`, and
`notes/open-64-virginia-eligibility-breadth-verification-20260812.md`). Jurisdiction filter:
`opencivicdata_jurisdiction.name = 'Washington'` (`ocd-jurisdiction/country:us/state:wa/government`)
— one clean match, no ambiguity with a same-named federal entity the way "United States" had.

All numbers below are live counts as of 2026-08-12, via `psycopg2` against `opencivicdata_billaction`
joined through `opencivicdata_bill` → `opencivicdata_legislativesession` → `opencivicdata_jurisdiction`.

## Result

### 1. Classification breakdown (35,871 total WA billaction rows)

| classification | count |
|---|---|
| `[]` (untagged) | 11,873 |
| `reading-1` | 4,201 |
| `reading-3` | 3,497 |
| `committee-passage-unfavorable` | 2,432 |
| `referral-committee` | 2,385 |
| `reading-2` | 1,944 |
| `passage` | 1,938 |
| `substitution` | 1,861 |
| `committee-passage-favorable` | 1,718 |
| `became-law` | 1,380 |
| `filing` | 1,085 |
| `executive-receipt` | 691 |
| `executive-signature` | 674 |
| `introduction` | 117 |
| `amendment-failure` | 38 |
| `passage, reading-3` (compound) | 20 |
| `executive-veto-line-item` | 16 |
| `executive-veto` | 1 |

No `amendment-passage` tag anywhere in the list — confirms the ticket's premise still holds as of
2026-08-12. Also notably absent: any generic `failure` tag, and any `committee-passage` (non-
favorable/unfavorable) tag — WA's committee outcomes are always disambiguated into
favorable/unfavorable at the tag level, unlike VA's undifferentiated `committee-passage`.

### 2. One real bill's full action list — HB 1376, 2025-2026 session

`ocd-bill/b5e70e75-14e3-44f8-8bdd-e97e33a2fea8`. Chosen because it shows the full concurrence +
final-passage shape described in §4 below, plus committee passage, in one bill:

| order | date | description | classification |
|---|---|---|---|
| 25 | 2026-03-24 | Effective date 6/11/2026. | `[became-law]` |
| 24 | 2026-03-24 | Chapter 191, 2026 Laws. | `[became-law]` |
| 23 | 2026-03-24 | Governor signed. | `[executive-signature]` |
| 22 | 2026-03-12 | Delivered to Governor. | `[executive-receipt]` |
| 21 | 2026-03-12 | President signed. | `[passage]` |
| 20 | 2026-03-12 | Speaker signed. | `[passage]` |
| 19 | 2026-03-12 | **Passed final passage; yeas, 96; nays, 0; absent, 0; excused, 2.** | `[passage]` |
| 18 | 2026-03-12 | House concurred in Senate amendments. | `[]` |
| 17 | 2026-03-06 | Third reading, passed; yeas, 48; nays, 0; absent, 0; excused, 1. | `[reading-3]` |
| 16 | 2026-03-06 | Rules suspended.  Placed on Third Reading. | `[reading-3]` |
| 15 | 2026-03-06 | Committee amendment(s) adopted with no other amendments. | `[]` |
| 14 | 2026-03-03 | Placed on second reading by Rules Committee. | `[reading-2]` |
| 13 | 2026-03-02 | Passed to Rules Committee for second reading. | `[]` |
| 12 | 2026-03-02 | WM - Majority; do pass with amendment(s). | `[committee-passage-favorable]` |
| 11 | 2026-03-02 | Executive action taken in the Senate Committee on Ways & Means at 10:30 AM. | `[]` |
| 10 | 2026-01-27 | Public hearing in the Senate Committee on Ways & Means at 4:00 PM. | `[]` |
| 9 | 2026-01-16 | First reading, referred to Ways & Means. | `[reading-1]` |
| 8 | 2026-01-15 | Third reading, passed; yeas, 97; nays, 0; absent, 0; excused, 1. | `[reading-3]` |
| 7 | 2026-01-15 | Rules suspended.  Placed on Third Reading. | `[reading-3]` |
| 6 | 2026-01-13 | Rules Committee relieved of further consideration.  Placed on second reading. | `[reading-2]` |
| 5 | 2026-01-12 | By resolution, reintroduced and retained in present status. | `[]` |
| 4 | 2025-02-28 | Referred to Rules 2 Review. | `[referral-committee]` |
| 3 | 2025-02-26 | FIN - Majority; do pass. | `[committee-passage-favorable]` |
| 2 | 2025-02-26 | Executive action taken in the House Committee on Finance at 8:00 AM. | `[]` |
| 1 | 2025-02-18 | Public hearing in the House Committee on Finance at 8:00 AM. | `[]` |
| 0 | 2025-01-17 | First reading, referred to Finance. | `[reading-1]` |

The bill originated in House, passed 97-0 (order 8), was amended in Senate, passed Senate 48-0
(order 17), then House concurred in the Senate amendments (order 18, untagged) and immediately
— same date — recorded a full up-or-down floor vote on final passage, 96-0 (order 19, tagged
`passage`). This concurrence-then-final-passage shape is the key structural finding; see §4.

### 3. Does the global tally-pattern regex match Washington's real vote-tally text?

The global regex is:

```
\(\s*\d+\s*-\s*Y\s+\d+\s*-\s*N(?:\s+\d+\s*-\s*A)?\s*\)
```

i.e. it expects Virginia-shaped text like `(96-Y 0-N)` — parenthesized, with literal `Y`/`N`/`A`
letters after each number.

Tested against all **1,938** `passage`-classified WA rows: **0 matches.** Same complete miss as US
Congress (OPEN-60) — WA's real tally text never uses `Y`/`N`/`A` letter suffixes and is never
parenthesized. Washington's actual format:

```
Passed final passage; yeas, 96; nays, 0; absent, 0; excused, 2.
Third reading, passed; yeas, 97; nays, 0; absent, 0; excused, 1.
```

Breaking down the 1,938 `passage` rows by shape:

| shape | count |
|---|---|
| VA-shaped regex (`\(\d+-Y \d+-N...\)`) | **0** |
| `"Passed final passage; yeas, N; nays, N; absent, N; excused, N."` | 298 |
| `"Speaker signed." / "President signed."` (ceremonial, no tally) | 1,419 |
| `"Adopted." / "Third reading, adopted."` (resolutions, voice vote/UC, no tally) | 221 |

The 221 no-tally `"Adopted."` rows are exclusively resolutions (`HR`/`SR`/`SCR` identifiers, spot
checked: HR 4696, HR 4694, SCR 8403, SR 8614, etc.) — the same class of legitimate
no-recorded-tally noise VA's `"Signed by Speaker"` and Congress's voice-vote rows represent; not a
gap, and correctly left `UNCLEAR` regardless of pattern.

**Recommended WA `tally_pattern`:**

```
yeas,\s*(\d+);\s*nays,\s*(\d+);\s*absent,\s*(\d+);\s*excused,\s*(\d+)
```

Tested against every `passage`- or `reading-3`-classified row containing "yeas" (2,026 rows total,
spanning both chamber-of-origin passage votes tagged `reading-3` and post-concurrence final-passage
votes tagged `passage`): **2,026/2,026 (100%) match**, resolving to exactly two literal templates
with digits substituted (`"Passed final passage; yeas, N; nays, N; absent, N; excused, N."` and
`"Third reading, passed; yeas, N; nays, N; absent, N; excused, N."`) — no other tally-text shape
exists in WA's real data. This is a clean, unambiguous format, unlike VA/Congress's noisier mix.

### 4. `amendment-passage` — still zero, and how concurrence is actually tagged

**Confirmed still zero** `amendment-passage`-tagged rows for Washington as of 2026-08-12 (absent
from the classification table in §1).

Searched all actions containing "concur" (case-insensitive) in `description`, any classification:

| description shape | count | classification |
|---|---|---|
| `"House concurred in Senate amendments."` | 154 | `[]` |
| `"Senate concurred in House amendments."` | 141 | `[]` |
| `"House refuses to concur in Senate amendments. Asks Senate to recede from amendments."` | 8 | `[]` |
| `"Senate refuses to concur in House amendments. Asks House for conference thereon."` | 3 | `[]` |
| `"Senate refuses to concur in House amendments. Asks House to recede from amendments."` | 3 | `[]` |
| `"Senate refuses to concur in the House amendments."` | 2 | `[]` |
| `"House refuses to concur in the Senate amendments."` | 1 | `[]` |

**100% of concurrence actions (312/312) carry `classification = []`** — same untagged shape as US
Congress's concurrence votes (OPEN-60). Unlike Congress, though, the concurrence action itself
never carries a numeric tally.

**The key difference from both VA and Congress:** pulled the full action list for 5 real bills with
a concurrence action (HB 1376, SB 6347, SB 6260, SB 6355, HB 2034) and found the same structure in
all 5, 100% consistent:

1. `"[Chamber] concurred in [other chamber] amendments."` — untagged, no tally.
2. **Same date, immediately following** — `"Passed final passage; yeas, N; nays, N; absent, N;
   excused, N."`, tagged `passage`, carrying the real up-or-down floor vote on the bill as amended.
3. Same date — `"Speaker signed." / "President signed."`, tagged `passage`, ceremonial, no tally.

Examples (all same-date pairs, chamber concurring → chamber's own final-passage tally):

- HB 1376, 2026-03-12: `"House concurred in Senate amendments."` → `"Passed final passage; yeas,
  96; nays, 0; absent, 0; excused, 2."`
- SB 6347, 2026-03-12: `"Senate concurred in House amendments."` → `"Passed final passage; yeas,
  39; nays, 10; absent, 0; excused, 0."`
- SB 6260, 2026-03-12: `"Senate concurred in House amendments."` → `"Passed final passage; yeas,
  26; nays, 23; absent, 0; excused, 0."`
- SB 6355, 2026-03-12: `"Senate concurred in House amendments."` → `"Passed final passage; yeas,
  32; nays, 17; absent, 0; excused, 0."`
- HB 2034, 2026-03-12: `"House concurred in Senate amendments."` → `"Passed final passage; yeas,
  50; nays, 46; absent, 0; excused, 2."`

**Answer: Washington does not need a jurisdiction-specific rule for cross-chamber concurrence.**
The real, scoreable vote on the amended bill is fully captured by the existing `passage`
classification tag — WA's process re-runs a full floor vote immediately after concurrence, and that
vote gets tagged `passage` like any other final-passage vote, not `amendment-passage` or anything
else. Once `tally_pattern` is corrected (§3), the default `passage`-tag → `DEFINITE_YES/NO` mapping
already reaches the right action with no new rule required — a materially different answer than VA
(which needed a `requires_pattern` gate on `amendment-passage` for OPEN-64/SB783) or Congress (which
needs a genuinely new text-pattern rule because its concurrence vote is never re-tagged at all).

### 5. Same-date duplicate-tally pattern — confirmed present in WA, more common than in VA

Checked for bills with more than one tallied action of the *same* classification on the *same*
date — the shape OPEN-60 (US SJRes11-adjacent) and OPEN-64 (VA HB1212) already found and whose fix
(nearest-in-time candidate/action matching, not date-only) is expected to generalize.

**`passage`-classification duplicates:** exactly one bill, **HB 2156** (2026-03-11):

| order | date | description | classification |
|---|---|---|---|
| 25 | 2026-03-11 | Passed final passage; yeas, 54; nays, 41; absent, 0; excused, 3. | `[passage]` |
| 24 | 2026-03-11 | Vote on final passage will be reconsidered. | `[]` |
| 23 | 2026-03-11 | Passed final passage; yeas, 54; nays, 33; absent, 8; excused, 3. | `[passage]` |
| 22 | 2026-03-11 | House concurred in Senate amendments. | `[]` |

Two genuinely different real tallies (33-yea-then-41-yea) on the same date, separated by an
explicit `"Vote on final passage will be reconsidered."` action — a real reconsideration, not a
duplicate-row data artifact.

**`reading-3`-classification duplicates:** the same reconsideration shape recurs on **17 more real
bills** (HB 1023, HB 1131, HB 1244, HB 1355, HB 1390, HB 1688, HB 1795, HB 2020, HB 2040, HB 2317,
HB 2575, HB 2650, SB 5079, SB 5143, SB 5357, SB 5459, SB 5752) — e.g. HB 1023 on 2025-03-07:
`"Third reading, passed; yeas, 96; nays, 1..."` → `"Vote on third reading will be reconsidered."`
→ `"Third reading, passed; yeas, 97; nays, 0..."`.

This is a **real and recurring** pattern for Washington — 18 bills total, more than the single VA
case (HB1212) OPEN-64 confirmed. It's not a new gap: the existing nearest-in-time candidate/action
matching fix (already generalized once, from VA to US Congress in OPEN-60/64) is expected to handle
it the same way, since the mechanism doesn't depend on jurisdiction-specific text. Flagging as
validated-relevant, not unhandled — but worth phase 2 confirming its regression coverage explicitly
exercises a reconsideration case, since WA hits it often enough that it isn't a rare edge case here.

### 6. SB 6002 — the reported reconcile flakiness does not reproduce

The ticket description flagged SB6002 as having shown "a same-date duplicate-motion reconcile
flakiness during BROKER-47 verification (2026-08-11)," hedged as "likely a live data-sync timing
artifact, not confirmed as an eligibility-rule issue." Pulled SB 6002's full action list
(`ocd-bill/d15c7f64-3669-41e6-8110-3c7fb3279553`) directly:

- No same-date duplicate `passage` or `reading-3` action exists in the current replica snapshot.
  Single clean sequence: House passage (2026-02-04, `reading-3`, 40-9) → Senate amendment →
  concurrence (2026-03-10, untagged) → single final-passage tally same date (`passage`, 39-10) →
  signatures → law.
- No `"will be reconsidered"` action anywhere in its history, unlike the 18 bills in §5.

This confirms the ticket's own hedge: as of 2026-08-12, SB6002 shows no duplicate-motion pattern in
the replica at all — consistent with a transient data-sync timing artifact during BROKER-47's
2026-08-11 verification window, not a defect in WA's eligibility rules or tagging. No action needed
here beyond this confirmation; out of scope per the ticket's own framing.

## Conclusion — recommended `JurisdictionEligibilityConfig` for phase 2

For the phase 2 migration (WA, iso2 `"WA"`), the data supports:

1. **Override `tally_pattern`** for WA: the VA-shaped regex is a proven 0% match (0/1,938
   `passage` rows), same complete miss as Congress. Replacement:
   `yeas,\s*(\d+);\s*nays,\s*(\d+);\s*absent,\s*(\d+);\s*excused,\s*(\d+)` — confirmed 100%
   (2,026/2,026) against every real tally-bearing `passage`/`reading-3` row, two clean literal
   templates, no other format variant found.
2. **No `JurisdictionEligibilityRule` override needed for concurrence.** Unlike VA
   (`amendment-passage` `requires_pattern` gate) and Congress (a wholly new text-pattern rule), WA's
   cross-chamber concurrence resolves into a same-date `passage`-tagged final vote that the default
   tag-based mapping already reaches once `tally_pattern` is fixed. Confirmed across 5 real bills
   (HB 1376, SB 6347, SB 6260, SB 6355, HB 2034), 100% consistent.
3. **No new rule needed for `committee-passage-favorable`/`committee-passage-unfavorable`** — these
   never carry tally text in WA (they're pure disposition tags: `"Majority; do pass."` /
   `"Minority; do not pass."`), so their existing classification-only handling (independent of
   `tally_pattern`) is unaffected either way; nothing found here that changes their treatment.
4. **The same-date-duplicate-tally / reconsideration pattern is real and more common in WA than in
   VA** (18 bills vs. VA's 1) — not a new gap, since the existing nearest-in-time matching fix is
   jurisdiction-agnostic, but recommend phase 2's regression test explicitly exercise it (HB 2156 is
   the cleanest real example, at the `passage` classification itself).

Bills to cite in phase 2's regression test (real, verified, from this doc):
- **HB 1376**, 2025-2026 session (`ocd-bill/b5e70e75-14e3-44f8-8bdd-e97e33a2fea8`) — the canonical
  concurrence → same-date final-passage shape, 96-0, no reconsideration noise. Best candidate for a
  `WaHb1376ConcurrenceTest`-style baseline test (mirroring `UtHb247ConcurrenceTest`).
- **HB 2156**, 2025-2026 session (`ocd-bill/df54826a-6a06-421a-94af-96b36f79205c`) — the
  reconsideration/duplicate-tally case (54-33-then-54-41 on the same date), best candidate for a
  `WaHb2156ReconsiderationTest`-style regression covering the nearest-in-time matching path.
- **SB 6002**, 2025-2026 session (`ocd-bill/d15c7f64-3669-41e6-8110-3c7fb3279553`) — cited only to
  document that the reported reconcile flakiness does not reproduce against current replica data;
  not itself proposed as a regression-test fixture.

## References

- Production DB: `opencivicdata_billaction` / `opencivicdata_bill` / `opencivicdata_legislativesession`
  / `opencivicdata_jurisdiction` (`postgresql://openstates:openstates_dev@localhost:5433/openstates`)
- `notes/bill-actions-persisted-verification-20260811.md` — precedent for this doc's format and for
  the DB-connection caveat (real replica vs. `cams` vs. this checkout's `openstates_dev`)
- `notes/open-60-us-congress-eligibility-verification-20260812.md` — sibling ticket; same repo
  split, same tally-pattern-miss finding shape, source of the nearest-in-time matching fix this doc
  confirms also covers WA's (more frequent) same-date reconsideration pattern
- `notes/open-64-virginia-eligibility-breadth-verification-20260812.md` — sibling ticket; same
  breadth-verification method, source of the `amendment-passage` `requires_pattern` precedent this
  doc found WA does not need an equivalent of
- Ticket: OPEN-62 (phase 1 of 2; phase 2 is ddp-broker-py PR #295, `fix/BROKER-47-agent`,
  `apps/ddp-broker/common/models/JurisdictionEligibilityConfig.py` /
  `JurisdictionEligibilityRule.py`)
