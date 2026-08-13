# OPEN-65: Does Arizona need a fallback-only fix, or a non-text vote-evidence mechanism?

## Context

OPEN-57's phase 1 (PR #113, merged) found that Arizona's `billaction.description` and
`voteevent.motion_text` never contain a digit anywhere — 0 of 14,404 and 0 of 3,460 rows,
full-table, not a sample. No `tally_pattern` regex, however tuned, can ever match. Every Arizona
motion is already permanently `UNCLEAR` in `ddp-broker-py` and already falls back to the votes
feed's own raw `own_passage_flag` (`opencivicdata_voteevent.motion_classification` containing
`'passage'`, informally, since there's no literal DB column of that name — confirmed below, no such
column exists anywhere in this schema).

This ticket is pure research (`ddp-open-states`, replica read-only) answering whether that fallback
is trustworthy enough to leave alone, or whether a structural fix (votecount-based, Path 2; or a
same-day/adjacent-day amendment-passage pattern, Path 3) is worth designing instead. No
`ddp-broker-py` code or config change is proposed here.

## Method

Queried the production OpenStates Postgres replica directly —
`postgresql://openstates:openstates_dev@localhost:5433/openstates` (the real replica; **not** the
`cams` DB the `postgres` MCP tool defaults to, same caveat as every prior phase-1 doc in this
repo). Jurisdiction filter: `opencivicdata_jurisdiction.name = 'Arizona'`
(`ocd-jurisdiction/country:us/state:az/government`). All counts below are full-population queries
via `psycopg2`, not samples, except where explicitly noted as a stratified sample (Path 1, item 1).
All numbers are live as of 2026-08-12.

**A note on session coverage that affects Path 2 below:** `opencivicdata_legislativesession` lists
34 Arizona sessions back to `49th-1st-regular` (2009), but only **one** — `57th-2nd-regular`
(57th Legislature, Second Regular Session) — actually has any bills loaded in this replica (2,190
bills; every other listed session has 0). OPEN-57's own phase-1 doc states billaction rows span
"sessions `49th Legislature, 1st Regular Session (2009)` through `57th Legislature - Second Regular
Session`" — that claim does not hold against the current replica snapshot: all 14,404 billaction
rows and all 3,460 voteevent rows belong to the single `57th-2nd-regular` session. Flagging this
directly rather than re-citing the earlier doc's session range as if re-confirmed.

## Path 1 — Is Arizona's own vote-feed classification ("own_passage_flag") actually reliable?

### 1. Full-population check of all AZ `passage`-tagged vote events against the bill's own record

2,089 AZ `opencivicdata_voteevent` rows carry `motion_classification` exactly `['passage']` (the
ticket asked for 50+; a stratified sample of 62 was drawn first for manual inspection, then the
check was run against the full 2,089 population directly, since that's cheap and more conclusive).
For each, the same bill's `opencivicdata_billaction` row(s) on the **identical date** were checked
for a `passage`- or `failure`-classified action recording the real outcome:

| outcome | count | share |
|---|---|---|
| voteevent `result` agrees with the same-day billaction PASSED/FAILED record | 2,064 | 98.8% |
| voteevent `result` **contradicts** the same-day billaction record | 25 | 1.2% |
| no same-day passage/failure billaction found at all | 0 | 0% |

Every one of the 25 contradictions has the identical signature: `motion_text = 'failed to pass'`,
`result = 'pass'`, while the same-day `billaction.description` reads `FAILED`
(`classification = ['failure', 'reading-3']`). Real examples, with their actual structured
`votecount` tallies:

| bill | date | chamber | yes | no | not voting | billaction same day |
|---|---|---|---|---|---|---|
| HB 2457 | 2026-02-25 | House | 28 | 26 | 6 | FAILED |
| HB 2457 | 2026-06-10 | Senate | 15 | 14 | 1 | FAILED |
| HB 2095 | 2026-02-26 | House | 30 | 24 | 6 | FAILED |
| SB 1512 | 2026-06-11 | House | 29 | 24 | 7 | FAILED |
| SB 1152 | 2026-02-23 | Senate | 16 | 11 | 3 | FAILED |
| HB 2812 | 2026-04-09 | Senate | 15 | 11 | 4 | FAILED |
| (19 more, same signature) | | | | | | |

In every one of the 25, `yes > no` (a simple majority of votes cast), but the bill's own
authoritative record says the motion failed — consistent with Arizona requiring a majority (or, for
some bill types, a supermajority) **of the chamber's full membership**, not just of votes cast
(House: 28–30 yes out of 60 members falls short of the 31 needed; most Senate cases show 14–16 yes
out of 30, and even SB 1152's 16 yes — nominally a bare majority of 30 — still failed, suggesting a
supermajority requirement for that particular bill, not investigated further here). The votes
feed's own `result` field appears to run a naive `yes > no` check rather than checking against the
actual required threshold, producing a **confirmed, one-directional 1.2% false-positive rate**:
`own_passage_flag` says "passed" for 25 votes Arizona's own record says failed. The reverse never
happens — 0 of the 97 `result = 'fail'` rows contradict a same-day PASSED billaction.

**This is a real, not hypothetical, reliability gap in `own_passage_flag`** — but it is small (1.2%),
one-directional, and has a single, well-characterized signature (`motion_text = 'failed to pass'`
paired with `result = 'pass'`) that is itself trivially cross-checkable against the same-day
billaction record, which was 100% populated for every one of the 2,089 votes checked (no missing
billaction match at all).

### 2. Does the floor vote's own `motion_classification` reliably say `passage` independent of the amendment-passage billaction row?

Yes, cleanly. Across every AZ voteevent, `motion_classification` takes exactly one of three distinct
values — `['passage']` (2,089), `['committee-passage']` (1,266), or `[]` untagged (105) — **there is
no compound row that mixes `committee-passage` and `passage` in a single voteevent.** When a bill's
`amendment-passage` billaction lands the same day as a real floor passage vote, that floor vote is
always a *separate* voteevent row, independently and unambiguously self-tagged `['passage']` — it
never needs the billaction's `amendment-passage` tag to be identified; it's directly queryable via
`bill_id` + date on its own. Re-running OPEN-57's phase-1 split against the full 1,286
`amendment-passage` rows reproduces it exactly: 451 same-day-committee-only, 299 same-day-both, 536
no-same-day-vote-at-all.

One caveat that connects back to §1: **2 of those 299 "both" floor passage votes are themselves
among the 25 known false-positive `result` rows** (SB 1035, 2026-02-23; HB 2812, 2026-04-09). The
floor vote's *tag* is always unambiguous — but that doesn't make its `result` field immune to the
§1 bug. Tag identity and result correctness are separate axes; confirming the first doesn't confirm
the second.

### 3. Do the 536 no-same-day-vote amendment-passage rows ever get promoted by `own_passage_flag`?

No — confirmed two ways, full population, not sampled. First, by construction, none of those 536
rows have *any* same-day vote event at all (of any classification), so there's nothing to promote
them. Second, and more broadly, checked whether **any** AZ voteevent with clearly committee-stage
motion text (`motion_text IN ('do pass', 'do pass amended')`) ever carries `'passage'` in its own
`motion_classification`: **0 of 0** — this never happens anywhere in the dataset, not just within
the 536-row subset. The votes feed never self-tags a pure committee vote as a floor passage.

## Path 2 — Is `opencivicdata_votecount` a viable alternative signal, or is it too incomplete?

### 1–2. Completeness across all 2,089 `passage`-tagged vote events

| completeness | count | share |
|---|---|---|
| nonzero, real votecount breakdown | 1,664 | 79.7% |
| all-zero votecount rows present | 425 | 20.3% |
| no votecount rows at all | 0 | 0% |

Every `passage`-tagged vote has *some* votecount row set (never fully missing) — the gap is entirely
in the all-zero rows, i.e. the tally was never captured, not that the row is absent.

By chamber: House 863/1,118 nonzero (77.2%), Senate 801/971 nonzero (82.5%) — a modest, not dramatic,
~5-point gap.

By calendar month (the only correlation axis available — see the session-coverage note above; there
is no older-vs-recent-session comparison possible because only one session has data):

| month (2026) | nonzero / total | rate |
|---|---|---|
| January | 4/8 | 50% (small n) |
| February | 566/624 | 91% |
| March | 413/492 | 84% |
| April | 225/259 | 87% |
| May | 49/80 | 61% |
| June | 407/626 | 65% |

Completeness dips at the very start of the session (small sample) and, more importantly, **during
May–June — the session's highest-volume, end-of-session crunch period, when the largest share of
final floor passage votes actually happen** (626 of 2,089 total passage votes, 30%, fall in June
alone). This is the opposite of reassuring: the votecount gap is worst exactly when the most passage
votes are being decided.

### 3. Would a votecount-based mechanism just trade one reliability problem for another?

Largely yes. A ~20% incompleteness rate, concentrated in the highest-volume period of the year, means
a "does a real votecount exist" mechanism would need its own fallback for roughly 1 in 5 real passage
votes — and that 1-in-5 isn't evenly distributed, it's worse right when session-end floor activity
peaks. This doesn't make Path 2 impossible, but it means Path 2 alone would need a secondary fallback
of its own, not just a straight swap for `own_passage_flag`.

## Path 3 — Does the same-day/adjacent-day pattern generalize, or were HB 2082/HB 2197 lucky picks?

### 1. Broadened to all 1,286 `amendment-passage` rows, ±1 calendar day, chamber-checked

| pattern | count | share |
|---|---|---|
| same-day passage vote, same chamber as the DPA action | 299 | 23% |
| adjacent-day (±1 day, not same-day) passage vote, same chamber | 176 | 14% |
| no passage vote within ±1 day at all | 811 | 63% |
| same-day or adjacent-day passage vote, **different** chamber (coincidence candidate) | 0 | 0% |

**Zero cross-chamber coincidences found, in either window, across all 1,286 rows.** Every single
time the pattern fires (same-day or adjacent-day), the matched floor vote is in the *same* chamber
as the `amendment-passage` action itself — there is no case of a House DPA landing near a Senate
floor vote (or vice versa) by pure calendar coincidence. Where the pattern fires, it's real, not
noise. But it only fires for 475/1,286 (37%) of rows — the majority (811/1,286, 63%, up from the
536 "no same-day vote of any kind" figure once committee-only-same-day rows with no *adjacent*
passage vote are folded in) genuinely have no floor-passage signal nearby at all, consistent with
being pure standing-committee shorthand.

### 2. Does this pattern actually need an amendment-passage-specific rule, or is it moot?

Path 1, item 2 above already answers this: the floor `passage` vote is *always* independently and
unambiguously identifiable via its own `voteevent.motion_classification`, with no dependency on the
`amendment-passage` billaction tag at all. **If `Motion`'s construction in `ddp-broker-py` reads
`voteevent`/`votecount` data directly (rather than `billaction.classification` text), the
same-day/adjacent-day `amendment-passage` pattern is moot for the purpose of *finding* the real
floor vote** — you'd find it by its own tag regardless of what the committee-stage billaction stream
looks like. This is a real refinement of OPEN-57 phase 1's original recommendation, which
(hedging against not knowing `Motion`'s construction path) proposed building a VA-style
`requires_pattern` disambiguation rule for `amendment-passage` specifically. That hedge is no longer
the most promising path once Path 1's full-population tag-cleanliness result is in hand — though it
still cannot be fully confirmed without reading `ddp-broker-py`'s actual `Motion` construction code,
out of reach from this repo (same repo-boundary limitation OPEN-57 and OPEN-60 both flagged).

## Path 4 — Is this an Arizona-only shape, or does it affect other not-yet-verified jurisdictions?

Same "any digit anywhere" check, full population, run against Washington, Michigan, and Utah
(OPEN-59, OPEN-61, OPEN-62 — not yet verified):

| jurisdiction | billaction digit rate | voteevent motion_text digit rate |
|---|---|---|
| Arizona (OPEN-57, for comparison) | 0.0% (0/14,404) | 0.0% (0/3,460) |
| Washington | 38.4% (13,788/35,871) | 100.0% (2,302/2,302) |
| Michigan | 24.5% (6,211/25,324) | 100.0% (1,083/1,083) |
| Utah | 42.6% (15,912/37,340) | 84.6% (1,621/1,917) |

All three carry real embedded numeric tallies. Washington's `motion_text` always reads something
like `"Third reading, passed; yeas, 44; nays, 5; absent, 0; excused, 0."`; Michigan's reads
`"passed; given immediate effect Roll Call #22 Yeas 98 Nays 4 Excused 0 Not Voting 8"`; Utah's is
mostly digit-containing too (fiscal-note/bill-number references dominate the non-digit billaction
minority, e.g. `"LFA/ fiscal note sent to sponsor for SB0024"` actually *does* contain digits — the
15.4% digit-free `voteevent.motion_text` minority wasn't investigated further here since it's out of
this ticket's scope). **None of the three shows Arizona's "zero digits anywhere" shape.** This
remains, so far, an Arizona-specific structural anomaly among the jurisdictions checked to date —
not evidence of a broad multi-jurisdiction problem.

## Recommendation

**Arizona's `own_passage_flag` fallback is trustworthy enough to remain the primary signal — 98.8%
accurate against a full-population, not sampled, ground-truth check — but it has one real, small,
well-characterized bug worth closing cheaply, not a structural replacement.**

- The confirmed failure mode (§Path 1.1: `motion_text = 'failed to pass'` + `result = 'pass'`
  contradicting the same-day billaction record, 25/2,089 = 1.2%, one-directional) is fully and
  reliably catchable by cross-checking against the bill's own same-day `billaction` PASSED/FAILED
  classification — which was 100% populated for every vote checked. That's a small, targeted guard,
  not a new evidence mechanism.
- **Path 2 (votecount-based) is the less promising of the two structural paths.** Real votecount
  data is reasonably complete (79.7% nonzero) but the ~20% gap is concentrated in the session's
  highest-volume period (May–June, 30% of all passage votes), which is the worst possible place for
  a signal to go missing. Building a mechanism keyed on "does a real votecount exist" would need its
  own fallback for exactly the busiest stretch of the year.
- **Path 3 (amendment-passage same-day/adjacent-day pattern) is reliable where it fires (zero
  cross-chamber coincidences across all 1,286 rows) but is very likely moot as a *identification*
  mechanism**, because Path 1 already shows the floor passage vote is independently and unambiguously
  self-tagged via its own `voteevent.motion_classification` — no `amendment-passage`-specific rule is
  needed to find it, provided `Motion` is built from `voteevent` data rather than `billaction` text
  (unconfirmed from this repo; same `ddp-broker-py` boundary OPEN-57/OPEN-60 already flagged).
- **Path 4 shows this isn't (yet) a multi-state problem** — Washington, Michigan, and Utah all embed
  real digits pervasively in their vote-tally text, unlike Arizona. There's no evidence here that a
  general non-text mechanism needs to be built for jurisdictions beyond Arizona.

If any further investment is warranted beyond the cheap same-day billaction cross-check above, Path
3's underlying finding (chamber-consistent, zero-coincidence adjacency) is closer to being already
resolved/moot than Path 2's (which carries a real, timing-correlated 20% gap) — so of the two, **Path
3 is the more promising starting point**, though the evidence here suggests neither needs to be built
as originally scoped once the cheap billaction cross-check is in place.

## References

- OPEN-57 (Phase 1, done) — `ddp-open-states` PR #113,
  `notes/open-57-arizona-eligibility-verification-20260812.md`,
  `OPEN-57-architecture-assessment-20260812.md`
- OPEN-60 — `notes/open-60-us-congress-eligibility-verification-20260812.md` — precedent for "is the
  raw passage flag reliable" as its own research question
- `ddp-broker-py` `fetch/interfaces/OpenStates/motion_eligibility.py` — `_matched_actions()`,
  `_classify()`, `compute_eligibility()` (read-only reference; not modified by this ticket)
- Production DB: `opencivicdata_billaction` / `opencivicdata_bill` / `opencivicdata_legislativesession`
  / `opencivicdata_jurisdiction` / `opencivicdata_voteevent` / `opencivicdata_votecount` /
  `opencivicdata_organization` (`postgresql://openstates:openstates_dev@localhost:5433/openstates`)
- `OPEN-65-architecture-assessment-20260812.md` — companion architectural assessment for this ticket
