# OPEN-70: US Congress's 13x jump in "wrong vote scored" (456 → 6,045) — root-caused, not stale

## Context

A full, unfiltered rebuild of the local broker database — fresh `pg_dump` from production, every
migration applied, a system-wide `backfill_eligible_for_scorecard` (no jurisdiction filter, 815
tracked bills), every scorecard rebuilt — moved `validate_scorecards` check #9 ("scored votes that
are not up-or-down votes") for US Congress from a number that had held steady at **456** across
every earlier verification in this project (OPEN-60, Virginia, Florida, Washington, Michigan, Utah)
to **6,045**, a 13x jump, with the real Congress `Motion` row count unchanged (785, both before and
after). The ticket asks a binary question: was 456 simply stale (Congress's motions hadn't been
mass-recomputed under current code since OPEN-60), making 6,045 the true number now — or is this a
genuine new defect?

Same repo-boundary fact as `OPEN-57`/`OPEN-58`/`OPEN-59`/`OPEN-61`/`OPEN-62`/`OPEN-65`/`OPEN-67`:
`Motion.eligible_for_scorecard`, `motion_eligibility.py`, and `JurisdictionEligibilityConfig` all
live in `ddp-broker-py`, which has no checkout anywhere in this workspace. What's answerable from
here — and is exactly `OPEN-60`'s own precedent (the original Congress `tally_pattern`/
disambiguation work this investigation is checking) — is querying the real OpenStates replica
directly for the underlying `opencivicdata_billaction` rows behind the ticket's cited examples and
a systemic sample of the same two text shapes, independent of anything broker's DB has cached.

## Method

Queried the production OpenStates Postgres replica directly (`source activate.sh`, then
`psycopg2` against `DATABASE_URL` — confirmed `postgresql://openstates:openstates_dev@localhost:5433/openstates`,
**not** the `postgres` MCP tool, which defaults to the unrelated `cams` DB, and not this checkout's
separate local `openstates_dev` DB — same footgun called out in every sibling doc in this family).
Jurisdiction filter: `opencivicdata_jurisdiction.name = 'United States'`. Two sessions persisted
locally: 118th Congress (67,867 action rows) and 119th (56,348) — **124,215 total US billaction
rows, 56,562 (45.5%) entirely untagged (`classification = '{}'`)**.

Four steps, each independently re-run against live data (not taken on faith from any prior
research artifact):

1. Pull the full action history for the ticket's two cited bills (HR3943, HJRES98) and
   ground-truth them directly.
2. Confirm the systemic untagged-action scale (total rows, untagged fraction, per-pattern counts).
3. For sub-pattern A ("bill has no up-or-down vote"), find the full population of bills matching
   the cited text shape and check what fraction have zero real vote anywhere in their history.
4. For sub-pattern B ("wrong motion picked — bill HAS an up-or-down vote"), find the full
   population of bills with the cited text shape and check what fraction have a real vote
   *somewhere* in their history, distinct from the flagged action.

## Result

### 1. HR3943 — sub-pattern A's cited example, ground-truthed

`ocd-bill/ded09748-2c90-45ff-bad8-a128ca12dd6e` ("Servicemember Employment Protection Act of
2023"), all 10 actions:

| order | description | classification |
|---|---|---|
| 9 | Introduced in House | `[introduction]` |
| 8 | Referred to the House Committee on Veterans' Affairs. | `[referral-committee]` |
| 7 | Referred to the Subcommittee on Economic Opportunity. | `[]` |
| 6 | Subcommittee Hearings Held | `[]` |
| 5 | Forwarded by Subcommittee to Full Committee (Amended) by Voice Vote. | `[]` |
| 4 | Subcommittee Consideration and Mark-up Session Held | `[]` |
| 3 | Committee Consideration and Mark-up Session Held. | `[]` |
| **2** | **Ordered to be Reported in the Nature of a Substitute (Amended) by Voice Vote.** | **`[]`** |
| 1 | Reported (Amended) by the Committee on Veterans' Affairs. H. Rept. 118-241. | `[]` |
| 0 | Placed on the Union Calendar, Calendar No. 193. | `[]` |

**Confirmed: this bill never had a floor vote of any kind.** It stalled at "placed on the
calendar." The flagged action (order 2) is a committee markup vote on a substitute amendment, not
a chamber up-or-down vote. Any `Motion` scored `eligible_for_scorecard` against this action is
unambiguously wrong — there is no real vote anywhere in this bill's history to have scored
instead.

### 2. HJRES98 — sub-pattern B's cited example, ground-truthed

`ocd-bill/91847d8e-76ff-4172-9193-f636a11a48f0` (NLRB joint-employer disapproval resolution), 35
actions, relevant sequence:

| order | description | classification |
|---|---|---|
| 21 | Passed/agreed to in House: On passage Passed by the Yeas and Nays: **206 - 177** (Roll no. 10). | `[passage]` |
| 17 | Passed/agreed to in Senate: Passed Senate without amendment by Yea-Nay Vote. **50 - 48**. Record Vote Number: 122. | `[passage]` |
| 13 | Vetoed by President. | `[executive-veto]` |
| **6** | POSTPONED PROCEEDINGS — "...Under the Constitution, the vote must be taken by the yeas and nays. Further proceedings were postponed until a time to be announced." | **`[]`** |
| **4** | Failed of passage in House over veto ... Failed by the Yeas and Nays: (2/3 required): **214 - 191** (Roll no. 185). | **`[]`** |
| 3 | (duplicate of order 4's text, also untagged) | `[]` |

The bill's original passage (order 21) is cleanly tagged `passage` — not the problem. The real gap
is the veto-override vote: **order 4 is a genuine, countable, recorded roll call (214-191) and
carries no classification tag at all**, unlike OPEN-60's own S.J.Res. 11 example where the
equivalent override failure *was* correctly tagged `veto-override-failure`. It sits two actions
after an untagged "POSTPONED PROCEEDINGS" narration row (order 6) that mentions "yeas and nays" but
contains **zero digits** — it only announces that a recorded vote *will* happen later. Both rows
are untagged; only one (order 4) contains an actual tally. Confirmed exactly as cited.

### 3. Systemic scale — confirmed, not two cherry-picked bills

| pattern | untagged (US) row count |
|---|---|
| `POSTPONED PROCEEDINGS` | 1,001 |
| `unanimous consent` (any) | 2,657 |
| `asked unanimous consent` | 176 |
| `by Voice Vote` | 2,215 |

### 4. Sub-pattern A at full population scale (not a 12-bill sample)

Every distinct bill with an untagged `"...Nature of a Sub[stitute]...by Voice Vote"` action
(HR3943's shape): **147 bills**, spanning both House and Senate (e.g. `S 1153`, `S 1723`, `S 1838`
alongside House bills). **81/147 (55%) have zero `passage`-classified action anywhere in their
entire history** — a confirmed false positive if a `Motion` is scored against that committee
action, structurally identical to HR3943, at population scale rather than a small sample.

### 5. Sub-pattern B at full population scale (not a 10-bill sample)

Every distinct bill with an untagged `POSTPONED PROCEEDINGS` action (HJRES98's shape): **415
bills**, again spanning both chambers (e.g. `S 1071`, `S 1383`, `S 5`). **414/415 (>99%) have a
real numeric-tally vote *somewhere* in their full action history** — i.e., these are exactly the
"bill HAS an up-or-down vote" case the ticket describes: a real vote exists, but an untagged,
textually vote-adjacent placeholder competes with it. Additionally, **all 1,001** untagged
`POSTPONED PROCEEDINGS` row instances contain zero real vote-tally text themselves (100% placeholder
shape, confirmed with a `\d{1,3}\s*-\s*\d{1,3}` tally regex, not a blanket digit check — bill
numbers like "H.J. Res. 98" contain digits too and would otherwise produce false negatives). Of
those, 380/1,001 (38%) have the real tally within a tight ±5 action-order window (the easy,
nearby-match case like HJRES98 itself); the rest sit further away in longer action sequences
(harder disambiguation, e.g. batched committee-of-the-whole amendment sequences with many
`POSTPONED PROCEEDINGS` rows across separate amendments) but still resolve to a real vote
somewhere in the same bill's history.

## Conclusion — the ticket's own binary framing does not hold

**6,045 is not simply "the true number now that 456 was stale."** Both of the ticket's cited
examples are ground-truthed as genuinely wrong matches, and both sub-patterns are confirmed
systemic at full population scale (147 and 415 bills respectively, not isolated picks), across both
chambers. It's plausible **both things are true at once**: 456 likely *was* computed against a
long-lived dev DB where Congress's motions hadn't been mass-recomputed under current code since
OPEN-60 landed, **and** the current code — even with OPEN-60's tally-pattern/concurrence fix
applied — still mis-scores a large, real fraction of Congress's untagged procedural actions as if
they were genuine votes. The first full, unfiltered backfill exposed a pre-existing defect at real
scale for the first time; it did not manufacture 13x more genuine bugs from nothing.

Per the ticket's own acceptance criteria, this is **not** eligible to close under "456 was stale,
6,045 reflects reality, no code change needed." A real pattern of wrong answers was found and is
root-caused below.

## Root-Cause Hypothesis (for the BROKER follow-up)

`motion_eligibility.py`'s action-matching/disambiguation step selects a candidate action for a
bill's up-or-down vote without requiring that candidate to (a) carry a real vote-outcome
classification tag, or (b) itself contain a countable numeric tally. Congress's action stream is
45.5% untagged, and within that untagged pool, procedural narration text ("POSTPONED
PROCEEDINGS...", "...asked unanimous consent that...") is textually adjacent to, and shares
vote-related vocabulary with ("yeas and nays", "vote"), the real tally text — but frequently
contains zero digits itself. Two distinct, both-confirmed failure shapes:

1. **No real vote exists anywhere on the bill** (HR3943; 81/147 population-confirmed) — the bill
   only ever had a committee-level markup/substitute "Voice Vote," never a floor vote, yet gets
   scored as if that committee action were a real up-or-down vote. Fix direction: a scoreable
   action must have either a real vote-outcome classification tag (`passage`,
   `veto-override-failure`, etc.) or contain an actual numeric tally matching the jurisdiction's
   `tally_pattern` — committee-level procedural actions with neither should never be eligible,
   regardless of keyword match.
2. **A real vote exists, but an adjacent untagged narration row gets matched instead** (HJRES98;
   414/415 population-confirmed) — a real, digit-bearing vote sits within a few action-orders of a
   textually similar but digit-free "postponed proceedings" (or "unanimous consent") narration.
   Fix direction: when multiple untagged candidates match a jurisdiction's vote-related text
   pattern for the same bill, prefer the candidate that actually contains a numeric tally over one
   that doesn't, rather than matching on procedural phrasing alone or nearest-in-time without a
   numeric-content check.

Regression-test bill candidates: **HR3943** (`ocd-bill/ded09748-2c90-45ff-bad8-a128ca12dd6e`, no
real vote anywhere — should never be eligible) and **HJRES98**
(`ocd-bill/91847d8e-76ff-4172-9193-f636a11a48f0`, real veto-override vote at 214-191, untagged,
adjacent to a digit-free "postponed proceedings" row — the correct match is the numeric row, order
4, not order 6).

## Limitations

- Only two Congress sessions (118th, 119th) are persisted in this replica — narrower than
  Congress's full real history. No evidence suggests a materially different tagged/untagged
  distribution in older sessions, but this is a scope caveat, not a defect in the method (same
  posture OPEN-61 took for Utah's two-session corpus).
- The exact action `ddp-broker-py` currently matches per `Motion` is not directly observable from
  this repo — the conclusion is inferred from the shape of the underlying OpenStates data plus
  OPEN-60's documented rule set, not observed directly from broker's own matching code. This is the
  same limitation `OPEN-67` hit for the Utah chamber-swap investigation.
- Which specific legislators' scorecards are affected (the ticket cites Peltola/Begich/Sullivan and
  "every state's congressional delegation") is not independently re-verified here — it isn't
  resolvable from `opencivicdata_billaction` alone (that's a broker-side `Motion`-to-legislator
  join), but the scale confirmed here (147 + 415 bills, both chambers) is consistent with that
  breadth claim.

## References

- Production DB: `opencivicdata_billaction` / `opencivicdata_bill` / `opencivicdata_legislativesession`
  / `opencivicdata_jurisdiction` (`postgresql://openstates:openstates_dev@localhost:5433/openstates`)
- `OPEN-70-architecture-assessment-20260813.md` — the `/architect-ticket` pass that first ran this
  diagnosis; this note independently re-derives and, for the two sub-pattern samples, extends it
  from n=12/n=10 samples to full population counts (147 and 415 bills respectively)
- `notes/open-60-us-congress-eligibility-verification-20260812.md` — the original Congress
  `tally_pattern`/disambiguation research this investigation checks
- `notes/open-67-utah-chamber-swap-investigation-20260813.md` — precedent for this doc's format and
  for stating the repo-boundary limitation plainly
- Ticket: OPEN-70 (this investigation); follow-up: BROKER ticket (see Jira, linked via comment on
  OPEN-70) scoped to `motion_eligibility.py`'s action-matching/disambiguation step
