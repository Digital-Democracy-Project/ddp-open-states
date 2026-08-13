# OPEN-58: Florida `eligible_for_scorecard` verification — the tally regex is a 0% miss, and FL's cross-chamber concurrence carries no tally at all

## Context

`Motion.eligible_for_scorecard` (ddp-broker-py, BROKER-47) is computed from a global tally-pattern
regex and a set of `DEFINITE_YES`/`DEFINITE_NO` action-classification tags that were only ever
confirmed against Virginia's own action text. Florida currently falls back to those Virginia-shaped
defaults, unverified. This is phase 1 of OPEN-58 (research, in `ddp-open-states`) — the handoff
artifact for phase 2 (config/migration/tests, in `ddp-broker-py` PR #295), following the same
two-repo split and methodology already run for OPEN-60 (US Congress) and OPEN-64 (VA breadth).

Four things were asked, all against real replica data, no invented examples:
1. Sample `opencivicdata_billaction` rows for Florida, grouped by classification, including at
   least one real bill's full action list.
2. Whether the global tally-pattern regex actually matches Florida's real vote-tally text.
3. Whether Florida still has zero `amendment-passage`-tagged actions, and if so how cross-chamber
   concurrence votes are tagged instead.
4. Write it up so phase 2 has real bill IDs and real action text to implement against.

## Method

Queried the production OpenStates Postgres replica directly —
`postgresql://openstates:openstates_dev@localhost:5433/openstates` (the real replica; **not** the
`cams` DB the `postgres` MCP tool defaults to, and not this checkout's separate `openstates_dev`
DB — same caveat as `notes/bill-actions-persisted-verification-20260811.md`, OPEN-60, and OPEN-64).
Jurisdiction filter: `opencivicdata_jurisdiction.id = 'ocd-jurisdiction/country:us/state:fl/government'`
(the FL **state** jurisdiction — there are 70+ FL municipal jurisdictions in this same table with
`place:*` IDs that a loose `name ILIKE 'florida'` or `id ILIKE '%state:fl%'` match would incorrectly
include; confirmed live by first running the naive query and getting an arbitrary municipal match
(`place:palm_coast`) before correcting to the exact state-government ID from `quality_check.py`'s
`OCD_TO_CODE`).

All numbers below are live counts as of 2026-08-12, via `psycopg2` against `opencivicdata_billaction`
joined through `opencivicdata_bill` → `opencivicdata_legislativesession` → `opencivicdata_jurisdiction`.

## Result

### 1. Classification breakdown (116,925 total FL billaction rows)

| classification | count |
|---|---|
| referral-committee | 16,277 |
| filing | 13,578 |
| committee-passage-favorable | 6,652 |
| reading-1 | 6,251 |
| failure | 4,902 |
| reading-2 | 3,845 |
| reading-3 | 3,845 |
| introduction | 3,767 |
| passage | 3,570 |
| deferral | 3,119 |
| enrolled | 2,284 |
| withdrawal | 2,256 |
| executive-receipt | 1,186 |
| executive-signature | 1,131 |
| executive-veto | 61 |
| *(untagged, `classification = []`)* | 48,049 |

That's the **complete** set of distinct tags Florida uses. Two things worth flagging immediately,
both load-bearing for the rest of this doc:

- **No `committee-passage` tag** — only `committee-passage-favorable`. Unlike VA (which has both, and
  where the plain `committee-passage` tag is what conference-report-agreement rows get mis-tagged
  as), FL's committee vocabulary is simpler.
- **No `amendment-passage` tag at all** — confirmed absent from the complete list, matching the
  ticket's 2026-08-11 note.

### 2. One real bill's full action list — HB 1537, 2023 Regular Session

`ocd-bill/3e96dece-4116-45ea-a663-2e38eb14ac1a` — chosen because it hits nearly every classification
tag FL uses in one bill: three subcommittee/committee `committee-passage-favorable` votes, three
real floor `passage` votes with real tallies, untagged concurrence-amendment actions, `enrolled`,
`executive-receipt`, `executive-signature`. Became Ch. 2023-39.

| order | date | description | classification |
|---|---|---|---|
| 0 | 2023-03-06 | Filed | `[filing]` |
| 1 | 2023-03-07 | 1st Reading (Original Filed Version) | `[filing, reading-1]` |
| 2 | 2023-03-09 | Referred to Education Quality Subcommittee | `[referral-committee]` |
| 3 | 2023-03-09 | Referred to PreK-12 Appropriations Subcommittee | `[referral-committee]` |
| 4 | 2023-03-09 | Referred to Education & Employment Committee | `[referral-committee]` |
| 5 | 2023-03-09 | Now in Education Quality Subcommittee | `[]` |
| 6 | 2023-03-13 | Added to Education Quality Subcommittee agenda | `[]` |
| 7 | 2023-03-20 | PCS added to Education Quality Subcommittee agenda | `[]` |
| 8 | 2023-03-22 | Favorable with CS by Education Quality Subcommittee | `[committee-passage-favorable]` |
| 9 | 2023-03-23 | Reported out of Education Quality Subcommittee | `[]` |
| 10 | 2023-03-23 | Laid on Table under Rule 7.18(a) | `[deferral]` |
| 11 | 2023-03-23 | CS Filed | `[filing]` |
| 12 | 2023-03-23 | 1st Reading (Committee Substitute 1) | `[reading-1]` |
| 13 | 2023-03-24 | Original reference removed: PreK-12 Appropriations Subcommittee | `[]` |
| 14 | 2023-03-24 | Referred to Appropriations Committee | `[referral-committee]` |
| 15 | 2023-03-24 | Referred to Education & Employment Committee | `[referral-committee]` |
| 16 | 2023-03-24 | Now in Appropriations Committee | `[]` |
| 17 | 2023-04-10 | Added to Appropriations Committee agenda | `[]` |
| 18 | 2023-04-12 | Favorable with CS by Appropriations Committee | `[committee-passage-favorable]` |
| 19 | 2023-04-12 | Reported out of Appropriations Committee | `[]` |
| 20 | 2023-04-13 | Laid on Table under Rule 7.18(a) | `[deferral]` |
| 21 | 2023-04-13 | CS Filed | `[filing]` |
| 22 | 2023-04-13 | Referred to Education & Employment Committee | `[referral-committee]` |
| 23 | 2023-04-13 | Now in Education & Employment Committee | `[]` |
| 24 | 2023-04-13 | 1st Reading (Committee Substitute 2) | `[reading-1]` |
| 25 | 2023-04-17 | Added to Education & Employment Committee agenda | `[]` |
| 26 | 2023-04-19 | Favorable with CS by Education & Employment Committee | `[committee-passage-favorable]` |
| 27 | 2023-04-20 | Reported out of Education & Employment Committee | `[]` |
| 28 | 2023-04-20 | Laid on Table under Rule 7.18(a) | `[deferral]` |
| 29 | 2023-04-20 | CS Filed | `[filing]` |
| 30 | 2023-04-20 | Bill referred to House Calendar | `[]` |
| 31 | 2023-04-20 | Bill added to Special Order Calendar (4/25/2023) | `[]` |
| 32 | 2023-04-20 | 1st Reading (Committee Substitute 3) | `[reading-1]` |
| 33 | 2023-04-25 | Read 2nd time | `[reading-2]` |
| 34 | 2023-04-25 | Amendment 926917 adopted | `[]` |
| 35 | 2023-04-25 | Amendment 384447 not allowed for consideration | `[]` |
| 36 | 2023-04-25 | Amendment 301481 adopted | `[]` |
| 37 | 2023-04-25 | Placed on 3rd reading | `[reading-3]` |
| 38 | 2023-04-25 | Added to Third Reading Calendar | `[]` |
| 39 | 2023-04-26 | Read 3rd time | `[reading-3]` |
| 40 | 2023-04-26 | **CS passed as amended; YEAS 115, NAYS 0** | `[passage]` |
| 41 | 2023-04-26 | In Messages | `[]` |
| 42 | 2023-04-26 | Referred to Fiscal Policy | `[referral-committee]` |
| 43 | 2023-04-26 | Received | `[enrolled]` |
| 44 | 2023-05-02 | Withdrawn from Fiscal Policy | `[withdrawal]` |
| 45 | 2023-05-02 | Placed on Calendar, on 2nd reading | `[]` |
| 46 | 2023-05-02 | Substituted for CS/CS/SB 1430 | `[]` |
| 47 | 2023-05-02 | Read 2nd time | `[reading-2]` |
| 48 | 2023-05-02 | Amendment(s) adopted (648866, 774200, 797990, 864902) | `[]` |
| 49 | 2023-05-02 | Read 3rd time | `[reading-3]` |
| 50 | 2023-05-02 | **CS passed as amended; YEAS 40 NAYS 0** | `[passage]` |
| 51 | 2023-05-02 | In Messages | `[]` |
| 52 | 2023-05-02 | Added to Senate Message List | `[]` |
| 53 | 2023-05-03 | Amendment 797990 Concur | `[]` |
| 54 | 2023-05-03 | Amendment 864902 Concur | `[]` |
| 55 | 2023-05-03 | Amendment 774200 Concur | `[]` |
| 56 | 2023-05-03 | Amendment 648866 Concur | `[]` |
| 57 | 2023-05-03 | **CS passed as amended; YEAS 112, NAYS 3** | `[passage]` |
| 58 | 2023-05-03 | Ordered engrossed, then enrolled | `[enrolled]` |
| 59 | 2023-05-08 | Signed by Officers and presented to Governor | `[executive-receipt]` |
| 60 | 2023-05-09 | Approved by Governor | `[executive-signature]` |
| 61 | 2023-05-10 | Chapter No. 2023-39; companion bill(s) passed, see HB 891 (Ch. 2023-66), CS/CS/SB 240 (Ch. 2023-81) | `[]` |
| 62 | 2023-05-10 | Chapter No. 2023-39; companion bill(s) passed, see HB 891 (Ch. 2023-66), CS/CS/SB 240 (Ch. 2023-81) | `[]` |

This is the complete, unabridged action list for this bill — all 63 rows, order 0 through 62.

Note the four "Amendment NNNNNN Concur" rows at order 53–56 immediately before the real final
`passage` vote — this is FL's cross-chamber concurrence shape, and it carries `classification = []`,
the same as every other concurrence action sampled (§4).

### 3. Does the global tally-pattern regex match Florida's real vote text?

The global regex is:

```
\(\s*\d+\s*-\s*Y\s+\d+\s*-\s*N(?:\s+\d+\s*-\s*A)?\s*\)
```

i.e. it expects Virginia-shaped text like `(96-Y 0-N)` — parenthesized, with literal `Y`/`N`/`A`
letters after each number.

Tested against all **3,570** `passage`-classified FL rows: **0 matches.**

Florida's real recorded-vote text never uses parentheses or `Y`/`N`/`A` letter suffixes. The actual
format, seen in effectively every real FL floor-vote action:

```
CS passed; YEAS 116, NAYS 0
Passed as amended; YEAS 27 NAYS 10
CS passed as amended; YEAS 64, NAYS 48
Passed as amended by Conference Committee Report; YEAS 35 NAYS 0
```

So, like US Congress (OPEN-60), the VA-shaped regex is a complete miss for Florida — it would never
fire on any bill.

**Recommended FL-specific `tally_pattern`:**

```
YEAS\s*\d+\s*,?\s*NAYS\s*\d+
```

(case-insensitive). Tested against the same 3,570 real `passage` rows: **3,223 match (90.3%)**.
All **347 non-matches**, without exception, are `"Adopted"` or `"Adopted by Publication"` —
resolution-passage language for FL's memorializing/simple resolutions, which pass by voice/consent
and carry no tally to extract at all (the same "legitimate no-tally noise" shape OPEN-60 found for
Congress's voice votes and OPEN-64 found for VA's ceremonial signings). Zero non-matches were an
unexplained format gap. The `\s*` (rather than `\s+`) spacing is deliberate: a small number of real
rows have irregular spacing around the comma/number (`"YEAS 113 , NAYS 0"`, `"YEAS112 , NAYS 0"`) —
an initial `\s+`-based draft of this pattern missed those 3 rows; `\s*` throughout catches them
without loosening the pattern enough to false-positive on anything else in the 3,570-row test set.

### 4. `amendment-passage` — still zero, and concurrence carries no tally at all

**Confirmed still zero** `amendment-passage`-tagged rows for Florida as of 2026-08-12 (absent from
the complete classification list in §1).

Searched for concurrence-shaped language across **all** FL classifications, not a guessed subset:
326 actions contain "concur", 54 contain "recede" (some overlap; 361 distinct rows contain either).
**100% have `classification = []`** — same "no classification-tag path" finding as OPEN-60 found for
US Congress. Real examples:

- `"Concurred in 2 amendment(s) (147775, 206225)"` — SB 7028
- `"Amendment 285882 Concur"` — HB 1545
- `"Refused to concur, requested House to recede"` — SB 1594
- `"Amendment 689718 Refuse to Concur"` — SB 994

**Unlike both VA and US Congress, none of these 361 rows carry any numeric vote tally at all** —
checked explicitly for `"YEAS"` co-occurring with "concur"/"recede" text: **0 of 361.** VA's
concurrence text embeds a tally directly (`"Senate amendment(s) agreed to by House (61-Y 35-N 0-A)"`)
and Congress's does too (`"...concurred...by Yea-Nay Vote. 91 - 3."`); Florida's concurrence actions
are pure procedural motion-outcome text — an amendment ID in parentheses, not a vote count. This
means **no tally-pattern-based rule is possible for FL concurrence at all** — the only usable signal
is the directional language itself:

- Affirmative: `"Concur"` / `"Concurred in..."` (without "Refus...")
- Negative: `"Refused to concur..."` / `"Amendment NNNNNN Refuse to Concur"`

This is a genuinely different rule *shape* than VA's `amendment-passage` + `requires_pattern` gate
(tag + tally) or Congress's recommended concur rule (text keyword + tally) — for Florida it would
have to be text-direction-only, with no tally to corroborate it. Whether that's precise enough to
trust for scorecard eligibility (a pure keyword match, no numeric corroboration) is a phase 2 design
decision, not something this research can resolve — flagging it as the open question, not making the
call.

**Real worked example — SB 994, 2025 Regular Session**
(`ocd-bill/fd712fb4-b184-4e55-bee8-97eeaba7e588`, enacted Ch. 2025-104):

| order | date | description | classification |
|---|---|---|---|
| 35 | 2025-05-01 | Amendment 689718 Refuse to Concur | `[]` |
| 36 | 2025-05-01 | Refused to concur, requested Senate to recede | `[]` |
| 38 | 2025-05-02 | Receded from amendment(s) to House amendment(s) (689718) | `[]` |
| 39 | 2025-05-02 | **Passed as amended; YEAS 33 NAYS 0** | `[passage]` |

A clean, real "refuse → recede → real final vote" cycle — the refusal never gets its own tally; the
tally only shows up on the passage vote that resolves it.

### 5. `failure` — confirmed 100% procedural death, never a recorded no-vote

Sampled and then exhaustively checked FL's `failure`-tagged rows (4,902 total): **100% match
`"Died..."`** (`"Died in [Committee]"`, `"Died in returning Messages"`, `"Died, introduction
refused"`, `"Died pending reference review..."`). **Zero** of the 4,902 contain `"YEAS"` or
`"failed"` — i.e. **not one `failure`-tagged action in Florida represents an actual recorded no-vote.**
It's exclusively procedural: a bill ran out of time in committee, or a cross-chamber disagreement
was never resolved before session end.

**This is the concrete risk to flag for phase 2**, analogous to OPEN-64's SB783 ambiguity: if the
existing global `DEFINITE_NO` tag set (VA-shaped, not yet inspected in this workspace since it lives
in `ddp-broker-py`) includes anything that would key off Florida's `failure` classification, that
would misrepresent a bill that never received a floor vote as though legislators voted it down.

**Real worked example — HB 1609, 2025 Regular Session**
(`ocd-bill/bc49bc3f-2f5a-4b8a-bfc6-436f033f7840`):

| order | date | description | classification |
|---|---|---|---|
| 47 | 2025-05-01 | **CS passed as amended; YEAS 111, NAYS 1** | `[passage]` |
| 51 | 2025-05-02 | **CS passed as amended; YEAS 26 NAYS 10** | `[passage]` |
| 54 | 2025-05-02 | Amendment 159170 Refuse to Concur | `[]` |
| 55 | 2025-05-02 | Refused to concur, requested Senate to recede | `[]` |
| 57 | 2025-05-02 | Refused to recede from amendment(s) to House amendment(s) (159170) | `[]` |
| 58 | 2025-05-02 | Insist House to concur | `[]` |
| 60 | 2025-05-03 | Indefinitely postponed and withdrawn from consideration | `[withdrawal]` |
| 61 | 2025-06-16 | **Died in returning Messages** | `[failure]` |

Both chambers passed real, tallied versions of this bill (111-1 and 26-10), but the chambers never
reconciled their amendments and the bill died procedurally — `failure` here reflects a stalemate,
not a rejection. `HB 6011` (2026 session, `ocd-bill/0bfb4da8-8474-49fe-a1ee-20bf4ca0cd03`) shows the
identical shape: real passage votes (115-0, 36-0), a refused concurrence, and `"Died in returning
Messages"` — confirming this is a recurring FL pattern, not a one-off.

### 6. `committee-passage-favorable` — no ambiguity found

Sampled 20 real rows: most are plain (`"Favorable by Judiciary Committee"`, no tally), a meaningful
minority carry a real committee-level tally in the same `YEAS`/`NAYS` shape as floor passage
(`"Favorable by Banking and Insurance; YEAS 9 NAYS 0"`, `"Favorable by- Fiscal Policy; YEAS 17 NAYS
0"`). No VA-shaped double-meaning (like SB783's `amendment-passage` covering two different real
things) found in this tag for Florida.

## Conclusion — recommended `tally_pattern` / rules for phase 2

1. **Override `tally_pattern` for FL** (iso2 `"FL"`): the VA-shaped regex is a proven 0% match (not
   "unverified" — actively confirmed non-functional, same as Congress). Recommended replacement:
   ```
   YEAS\s*\d+\s*,?\s*NAYS\s*\d+
   ```
   90.3% match rate against real `passage` rows (3,223/3,570); all 347 non-matches are legitimate
   voice/publication-consent resolution language with no tally to extract.
2. **Do not add a classification-tag-based rule keyed on `amendment-passage`** — it doesn't exist for
   FL. If a concurrence-eligibility rule is wanted at all, it has to be **text-direction-only**
   (`"Concur"`/`"Concurred"` without `"Refus"` → affirmative, `"Refused to concur"`/`"Refuse to
   Concur"` → negative) — FL's concurrence actions carry zero tally text (0/361), unlike both VA and
   US Congress. This is a real design choice for phase 2, not a default this doc can hand over
   pre-decided.
3. **Do not treat `failure` as a `DEFINITE_NO`-eligible classification tag for FL.** Confirmed 100%
   (4,902/4,902) procedural-death text, never a recorded floor no-vote. `HB 1609` and `HB 6011` are
   real, cited examples of bills with real passage tallies in both chambers that still end up
   `failure`-tagged after an unresolved concurrence fight.
4. **No FL-specific gate needed for `committee-passage-favorable`** — sampled clean, no ambiguity
   found comparable to VA's conference-report/committee-passage overlap.

Bills to cite in phase 2's regression test (real, verified, from this doc):
- **HB 1537**, 2023 Regular Session (`ocd-bill/3e96dece-4116-45ea-a663-2e38eb14ac1a`) — full
  lifecycle bill: 3 committee `committee-passage-favorable` votes, 3 real floor `passage` votes
  (115-0, 40-0, 112-3), 4 untagged concurrence actions immediately preceding the final vote, enacted
  Ch. 2023-39.
- **SB 994**, 2025 Regular Session (`ocd-bill/fd712fb4-b184-4e55-bee8-97eeaba7e588`) — real
  "Refuse to Concur" → "recede" → real final passage (33-0) cycle, enacted Ch. 2025-104. Good
  DEFINITE_YES-shaped concurrence-resolution case with a real tally on the resolving vote.
- **HB 1609**, 2025 Regular Session (`ocd-bill/bc49bc3f-2f5a-4b8a-bfc6-436f033f7840`) — real House
  (111-1) and Senate (26-10) passage votes, unresolved concurrence, `failure`-tagged
  `"Died in returning Messages"` with no recorded no-vote anywhere — the concrete proof that
  `failure` must not be treated as `DEFINITE_NO` for FL.

## References

- Production DB: `opencivicdata_billaction` / `opencivicdata_bill` / `opencivicdata_legislativesession`
  / `opencivicdata_jurisdiction` (`postgresql://openstates:openstates_dev@localhost:5433/openstates`),
  jurisdiction `ocd-jurisdiction/country:us/state:fl/government`
- `notes/bill-actions-persisted-verification-20260811.md` — precedent for this doc's format and for
  the DB-connection caveat (real replica vs. `cams` vs. this checkout's `openstates_dev`)
- `notes/open-60-us-congress-eligibility-verification-20260812.md` — sibling phase-1 doc; same
  "no classification-tag path for concurrence" finding recurs here, but FL additionally has zero
  tally text on those actions where Congress had some
- `notes/open-64-virginia-eligibility-breadth-verification-20260812.md` — sibling breadth-check doc;
  this doc's `failure`-tag finding is the FL-specific analogue of OPEN-64's SB783 `amendment-passage`
  ambiguity
- `OPEN-58-architecture-assessment-20260812.md` — confirms this workspace has no `ddp-broker-py`
  checkout; phase 2 (migration/tests) is explicitly out of scope here (see below)
- `quality_check.py` — source of the FL jurisdiction ID convention (`OCD_TO_CODE`) used to avoid the
  70+ FL municipal-jurisdiction false-match trap
- Ticket: OPEN-58 (phase 1 of 2; phase 2 is ddp-broker-py PR #295, `fix/BROKER-47-agent`,
  `apps/ddp-broker/common/models/JurisdictionEligibilityConfig.py` /
  `JurisdictionEligibilityRule.py`)

## Phase 2 scope note

This workspace (`ddp-open-states`) has no `ddp-broker-py` checkout — confirmed directly (only other,
unrelated CodeBot workspace clones and the human's own `~/Developer/repos/ddp-broker-py` dev checkout
exist elsewhere on this machine; neither is this ticket's workspace, per `project-config.md`'s
`repo.path` discipline). Phase 2 — the `JurisdictionEligibilityConfig`/`JurisdictionEligibilityRule`
migration for FL, the bill-specific regression test using HB 1537/SB 994/HB 1609 above, setting
`verified=True` with `verified_notes` citing this doc, and the before/after `validate_scorecards`/
`reconcile_scorecards --FL` run — requires a `ddp-broker-py` session and is out of scope for this
workspace. This doc is the complete handoff artifact for that follow-up session, the same way
OPEN-60's and OPEN-64's notes already fed real, merged `ddp-broker-py` config.
