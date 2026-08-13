# OPEN-57: Arizona `eligible_for_scorecard` verification — the Virginia-shaped defaults don't fit, and here's what the real data looks like

## Context

`Motion.eligible_for_scorecard` (`ddp-broker-py`, BROKER-47) is computed from a global tally-pattern
regex and a set of `DEFINITE_YES`/`DEFINITE_NO` action-classification tags that were only ever
confirmed against Virginia's own action text. Arizona currently falls back to those Virginia-shaped
defaults, unverified. This is phase 1 of OPEN-57 (research, in `ddp-open-states`) — the handoff
artifact for phase 2 (config/migration/tests, in `ddp-broker-py` PR #295), same pattern as OPEN-60's
US Congress verification.

Four things were asked, all against real replica data, no invented examples:
1. Sample `opencivicdata_billaction` rows for Arizona, grouped by classification, including one real
   bill's full action list.
2. Whether the global tally-pattern regex actually matches Arizona's real vote-tally text.
3. Whether Arizona's `amendment-passage`-tagged actions are bare committee-report shorthand
   (`DPA`/`DPA/SE`) with no vote tally in the text, broadly — not just in a sample.
4. Whether Arizona has any tag that means more than one thing depending on context, the way
   Virginia's `amendment-passage` does.

**Note on the ticket's citation:** the ticket asserts a specific prior finding — "Arizona's own
`amendment-passage`-tagged actions were already found (2026-08-11) to be bare committee-report
shorthand." No notes doc dated 2026-08-11 documenting this exists anywhere in this repo's `notes/`
directory or git history as of this session. The underlying claim turns out to be true (confirmed
below, against all 1,286 rows, not a sample) — but it's independently re-verified here against live
data, not re-cited from a document that doesn't actually exist in this repo.

## Method

Queried the production OpenStates Postgres replica directly —
`postgresql://openstates:openstates_dev@localhost:5433/openstates` (the real replica; **not** the
`cams` DB the `postgres` MCP tool defaults to, and not this checkout's separate `openstates_dev`
DB — same caveat as `notes/bill-actions-persisted-verification-20260811.md` and
`notes/open-60-us-congress-eligibility-verification-20260812.md`). Jurisdiction filter:
`opencivicdata_jurisdiction.name = 'Arizona'` (`ocd-jurisdiction/country:us/state:az/government`).

All numbers below are live counts as of 2026-08-12, via `psycopg2` against `opencivicdata_billaction`
joined through `opencivicdata_bill` → `opencivicdata_legislativesession` → `opencivicdata_jurisdiction`,
and cross-checked against `opencivicdata_voteevent` / `opencivicdata_votecount` joined by `bill_id` +
date (`opencivicdata_voteevent.bill_action_id` exists as a column but is unpopulated globally — 0
rows across all jurisdictions — so it cannot be used as a join key; same finding as OPEN-60).

## Result

### 1. Classification breakdown (14,404 total AZ billaction rows, 2,190 bills, sessions `49th
Legislature, 1st Regular Session (2009)` through `57th Legislature - Second Regular Session`)

| classification | count |
|---|---|
| reading-1 | 3,063 |
| reading-2 | 2,891 |
| *(untagged, `classification = {}`)* | 1,868 |
| passage, reading-3 | 1,385 |
| amendment-passage | 1,286 |
| committee-passage | 1,273 |
| passage | 563 |
| informal-passage | 517 |
| executive-receipt | 456 |
| filing | 392 |
| executive-signature | 244 |
| executive-veto | 151 |
| withdrawal | 140 |
| failure, reading-3 | 107 |
| failure | 68 |

(`passage` totals 1,948 across the `passage`-alone and `passage, reading-3` rows combined; `failure`
totals 175 across `failure`-alone and `failure, reading-3`.)

Unlike US Congress's sparse vocabulary (OPEN-60: 11 tags, no `amendment-passage` at all), Arizona's
tag set is rich, closer to Virginia's shape — which makes the "just fall back to VA defaults"
instinct more plausible on the surface than it was for Congress. The text-format finding in §2/§3
below is why that instinct still doesn't hold.

### 2. One real bill's full action list — HB 2197, 57th Legislature - Second Regular Session

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

Companion vote events for the same bill (`opencivicdata_voteevent`, joined by `bill_id` — no
`bill_action_id` link available), with their real structured tallies from `opencivicdata_votecount`:

| date | motion_text | motion_classification | result | yes | no | not voting |
|---|---|---|---|---|---|---|
| 2026-02-24 | do pass amended | `[committee-passage]` | fail | 0 | 0 | 0 |
| 2026-02-25 | failed to pass | `[passage]` | fail | 26 | 28 | 6 |
| 2026-02-26 | Passed | `[passage]` | pass | 0 | 0 | 0 |
| 2026-03-16 | failed to pass | `[passage]` | fail | 15 | 36 | 8 |

(The 2026-02-24 and 2026-02-26 vote events have all-zero `votecount` rows in the replica — the
tally simply wasn't captured for those two, not a data-quality finding this ticket needs to resolve.
Flagging it because it's real and visible in this table, not glossing over it.)

Every description in this bill's entire action list is terse shorthand — `DPA`, `FAILED`, `PASSED`
— with no numeric content anywhere. This is not specific to this bill; see §3.

### 3. Does the global tally-pattern regex match Arizona's real vote-tally text?

The global regex (de-escaped, same correction OPEN-60 applied to the ticket's markdown-mangled
form):

```
\(\s*\d+\s*-\s*Y\s+\d+\s*-\s*N(?:\s+\d+\s*-\s*A)?\s*\)
```

i.e. Virginia-shaped `(96-Y 0-N)`.

Tested against all 563 rows tagged exactly `classification = ['passage']`: **0 matches**, and all
563 read the identical string `"PASSED"`. Same result as US Congress (OPEN-60: also 0 matches) — but
the reason is different and more fundamental. Congress's text at least contains digits, in the wrong
format (`"221 - 203"`); Arizona's contains **no digits at all**, checked across the whole table, not
a sample:

```sql
SELECT count(*) FROM opencivicdata_billaction ba ... WHERE j.name = 'Arizona' AND ba.description ~ '[0-9]'
```

**Result: 0 of 14,404 rows.** No Arizona `billaction.description`, of any classification, in any
session back to the 49th Legislature (2009), has ever contained a digit. Same check against
`opencivicdata_voteevent.motion_text` for all 3,460 AZ vote events: **0 of 3,460 contain a digit.**
The distinct values that exist are exactly: `Passed`, `do pass`, `do pass amended`, `failed to pass`,
`retained`, `Retained on the Calendar` — all pure prose, zero numerics.

**This means the tally-pattern regex mechanism cannot ever produce a match for Arizona, regardless
of what pattern phase 2 writes.** It's not a wrong-format problem (fixable, as Congress's was, with
a better regex) — it's a wrong-field problem. The real numeric tally exists, but only in
`opencivicdata_votecount`, keyed by `vote_event_id`, with `option`/`value` pairs (`yes`/`no`/`not
voting`/`absent`/`excused`/`other`) — confirmed above for HB 2197's own vote events. Total AZ
`votecount` rows: 20,760, of which 4,633 have a nonzero `value`.

### 4. Does `amendment-passage` mean more than one thing depending on context?

Yes — confirmed with real data. Grouped all 1,286 `amendment-passage` (`DPA`: 1,167 rows, `DPA/SE`:
119 rows) billaction rows by whether a same-day `opencivicdata_voteevent` exists for the same bill,
and what that vote's own classification is:

| same-day vote-event match | count | share |
|---|---|---|
| same-day vote tagged `committee-passage` only | 451 | 35% |
| same-day votes tagged **both** `committee-passage` and `passage` | 299 | 23% |
| no same-day vote event captured at all | 536 | 42% |

The "both" row is the important one. Real example — **HB 2082, 57th Legislature - Second Regular
Session** (`ocd-bill/22fee663-a76a-425e-ae7d-ec9b34a18554`), full lifecycle:

| order | date | description | classification |
|---|---|---|---|
| 3 | 2026-01-22 | DP | `[committee-passage]` |
| 5 | 2026-02-24 | DPA | `[amendment-passage]` |
| 6 | 2026-02-25 | PASSED | `[passage, reading-3]` |
| 10 | 2026-03-11 | DPA | `[amendment-passage]` |
| 11 | 2026-05-18 | DPA | `[amendment-passage]` |
| 12 | 2026-05-18 | PASSED | `[passage, reading-3]` |
| 14–15 | 2026-06-02 | PASSED, PASSED | `[passage]`, `[passage]` |

Vote events for the same bill:

| date | motion_text | classification | result | organization |
|---|---|---|---|---|
| 2026-02-24 | do pass amended | `[committee-passage]` | fail | House |
| 2026-02-25 | Passed | `[passage]` | pass | House |
| 2026-05-18 | do pass amended | `[committee-passage]` | fail | Senate |
| 2026-05-18 | Passed | `[passage]` | pass | Senate |
| 2026-06-02 | Passed | `[passage]` | pass | House |
| 2026-06-02 | Passed | `[passage]` | pass | Senate |

Order 5's `DPA` (House) lands one day before order 6's floor `PASSED` — a House committee-of-the-
whole "do pass amended" report immediately preceding the real recorded floor passage vote. Order
11's `DPA` (Senate) is on the **identical calendar day** as order 12's `PASSED`/`passage` vote — the
committee "do pass amended" report and the floor passage vote landed the same day. Order 10's
earlier `DPA` (also Senate, standing-committee stage, no same-day vote event) is the "clean"
committee-shorthand case the ticket's premise describes — the same pattern HB 2197's order 3 (a lone
`DPA` on 2026-02-09 with no same-day vote at all) also shows.

So the same tag/text (`DPA`, classification `amendment-passage`) covers at least two distinct
procedural moments in Arizona's process: a standing-committee report with no adjacent vote (536 +
part of the 451 cases), and a floor-stage report landing the same day as, or the day before, the
bill's actual chamber-passage vote (299 + part of the 451 committee-passage-only cases, like HB
2197's order 4, which precedes order 5's `FAILED` by one day). **Collapsing this into a single rule
— either "always exclude `amendment-passage`" or "always include it" — will be wrong for one of the
two cases.** This is the same shape of problem `JurisdictionEligibilityRule.requires_pattern` was
built to solve for Virginia's `amendment-passage` (cross-chamber concurrence vs. same-chamber floor
amendment); Arizona needs an analogous disambiguation, not a verified-empty ruleset.

## Conclusion — recommended `tally_pattern` / rules for phase 2

For the phase 2 `JurisdictionEligibilityConfig`/`JurisdictionEligibilityRule` migration (Arizona,
iso2 `"AZ"`), the data supports:

1. **No `tally_pattern` override can fix Arizona** — unlike Congress (OPEN-60: wrong format, fixable
   with a tuned regex), Arizona's text contains zero digits anywhere, in any classification, checked
   across the entire 14,404-row table and all 3,460 vote events, not a sample. Whatever mechanism
   `Motion.eligible_for_scorecard` uses to extract vote-count evidence for Arizona today, it cannot
   be a text-pattern regex against `billaction.description` or `voteevent.motion_text` — there is
   nothing in either field for any regex to match. If `Motion` is built from `opencivicdata_votecount`
   directly (structured `yes`/`no`/`not voting` values, confirmed real and nonzero for AZ — e.g. HB
   2197's 2026-02-25 vote: yes 26/no 28/not voting 6), Arizona may need **no** `tally_pattern`
   override at all, because the failure mode that override exists to fix (embedded-but-malformatted
   text tallies) was never the path Arizona's real numeric data flows through. If `tally_pattern` is
   instead the *sole* source of vote-count truth with no `votecount` fallback, that's a real,
   pre-existing gap for Arizona (not created by this ticket) that phase 2 needs to close
   structurally — this can only be confirmed by reading `Motion`'s construction path in
   `ddp-broker-py`, which is out of reach from this repo.
2. **`amendment-passage` needs a `requires_pattern`-shaped disambiguation rule, not a blanket
   include/exclude** — confirmed via real same-day-vote analysis: 536/1,286 (42%) are clean
   standing-committee shorthand with no adjacent vote (safe to exclude), but 299/1,286 (23%) land on
   the identical calendar day as a real floor `passage` vote, and another share of the 451
   committee-passage-only bucket lands one day before a floor vote (HB 2197's order 4 → order 6, HB
   2082's order 5 → order 6). Recommend a rule keyed on same-day-or-next-day-adjacent
   `committee-passage`+`passage` vote-event pairing for the same bill, mirroring the shape of
   Virginia's `amendment-passage` disambiguation rule (reuse that structure; adapt the matching
   condition to AZ's same-day/adjacent-day pattern rather than VA's cross-chamber-concurrence
   pattern).
3. **`DEFINITE_YES`/`DEFINITE_NO` tag membership for the unambiguous tags checked here is
   consistent with the tag names** — `passage` rows read `"PASSED"` uniformly (563/563), `failure`
   rows read `"FAILED"` uniformly, `committee-passage` rows read `"DP"` uniformly (1,273/1,273),
   `informal-passage` rows read `"DP"` uniformly (517/517). No text-content surprises in these tags
   beyond the missing-tally finding in (1) above — the classification vocabulary itself appears
   reliable for AZ, unlike the concern that motivated checking in the first place.

Bills to cite in phase 2's regression test (real, verified, from this doc):
- **HB 2197**, 57th Legislature - Second Regular Session
  (`ocd-bill/7e4eec7d-e20a-4927-b062-d9cd8822cf6e`) — clean standing-committee `DPA` (order 3, no
  same-day vote) alongside an adjacent-day `DPA`→floor-vote case (order 4 → order 5/6), plus a real
  structured `votecount` tally (2026-02-25 failed-to-pass vote: yes 26/no 28/not voting 6; 2026-03-16
  failed-to-pass vote: yes 15/no 36/not voting 8).
- **HB 2082**, 57th Legislature - Second Regular Session
  (`ocd-bill/22fee663-a76a-425e-ae7d-ec9b34a18554`) — same-calendar-day `DPA`+floor-`passage`-vote
  case (order 11/12, Senate, 2026-05-18) and adjacent-day case (order 5/6, House), covering both
  ambiguous `amendment-passage` shapes in one bill's real lifecycle.

## References

- Production DB: `opencivicdata_billaction` / `opencivicdata_bill` / `opencivicdata_legislativesession`
  / `opencivicdata_jurisdiction` / `opencivicdata_voteevent` / `opencivicdata_votecount`
  (`postgresql://openstates:openstates_dev@localhost:5433/openstates`)
- `notes/bill-actions-persisted-verification-20260811.md`,
  `notes/open-60-us-congress-eligibility-verification-20260812.md` — precedent for this doc's format
  and the DB-connection caveat (real replica vs. `cams` vs. this checkout's `openstates_dev`)
- Ticket: OPEN-57 (phase 1 of 2; phase 2 is `ddp-broker-py` PR #295, `fix/BROKER-47-agent`,
  `apps/ddp-broker/common/models/JurisdictionEligibilityConfig.py` /
  `JurisdictionEligibilityRule.py`)
- `OPEN-57-architecture-assessment-20260812.md` — earlier architectural pass in this workspace that
  first surfaced the votecount-vs-text-regex structural finding and the `amendment-passage`
  ambiguity; this doc independently re-ran and confirms its queries, with one correction: that
  assessment's cited HB 2197 votecount tally (yes 15/no 36/not voting 8) actually belongs to the
  2026-03-16 vote, not the 2026-02-25 vote as stated there — the 2026-02-25 vote's real tally is
  yes 26/no 28/not voting 6 (both corrected above in §2).
