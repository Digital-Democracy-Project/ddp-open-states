# OPEN-60: US Congress `eligible_for_scorecard` verification — the Virginia-shaped defaults don't fit, and here's what the real data looks like

## Context

`Motion.eligible_for_scorecard` (ddp-broker-py, BROKER-47) is computed from a global tally-pattern
regex and a set of `DEFINITE_YES`/`DEFINITE_NO` action-classification tags that were only ever
confirmed against Virginia's own action text. US Congress currently falls back to those
Virginia-shaped defaults, unverified. This is phase 1 of OPEN-60 (research, in `ddp-open-states`)
— the handoff artifact for phase 2 (config/migration/tests, in `ddp-broker-py` PR #295).

Four things were asked, all against real replica data, no invented examples:
1. Sample `opencivicdata_billaction` rows for US federal bills, grouped by classification.
2. Whether the global tally-pattern regex actually matches Congress's real vote-tally text.
3. Whether US Congress still has zero `amendment-passage`-tagged actions, and if so how
   cross-chamber concurrence and cloture votes are tagged instead.
4. Write it up so phase 2 has real bill IDs and real action text to implement against.

## Method

Queried the production OpenStates Postgres replica directly —
`postgresql://openstates:openstates_dev@localhost:5433/openstates` (the real replica; **not** the
`cams` DB the `postgres` MCP tool defaults to, and not this checkout's separate `openstates_dev`
DB — same caveat as `notes/bill-actions-persisted-verification-20260811.md`). Jurisdiction filter:
`opencivicdata_jurisdiction.name = 'United States'` (`ocd-jurisdiction/country:us/government`).

All numbers below are live counts as of 2026-08-12, via `psycopg2` against `opencivicdata_billaction`
joined through `opencivicdata_bill` → `opencivicdata_legislativesession` → `opencivicdata_jurisdiction`.

## Result

### 1. Classification breakdown (124,204 total US billaction rows)

| classification | count |
|---|---|
| introduction | 35,817 |
| referral-committee | 25,148 |
| passage | 4,897 |
| receipt | 503 |
| executive-receipt | 393 |
| became-law | 379 |
| executive-signature | 376 |
| reading-2 | 120 |
| reading-1 | 32 |
| executive-veto | 15 |
| veto-override-failure | 5 |

That's the **complete** set of distinct tags US Congress uses — no `amendment-passage`, no
`committee-passage`, no generic `failure`. Compare to Virginia's much richer tag vocabulary (the
current defaults' source of truth) — Congress relies heavily on free-text description rather than
classification tags for anything beyond introduction/referral/passage/executive action.

### 2. One real bill's full action list — S.J.Res. 11, 118th Congress

`ocd-bill/228eb616-da39-4ab2-9970-3ed8c7813e0f` — "A joint resolution providing for congressional
disapproval ... of the rule submitted by the Environmental Protection Agency relating to 'Control
of Air Pollution From New Motor Vehicles: Heavy-Duty Engine and Vehicle Standards'." Chosen because
it's a real bill that passed both chambers, was vetoed, and had a failed override — hitting most of
the classification tags in one bill:

| order | date | description | classification |
|---|---|---|---|
| 23 | 2023-02-09 | Introduced in Senate | `[introduction]` |
| 22 | 2023-02-09 | Read twice and referred to the Committee on Environment and Public Works. | `[]` |
| 21 | 2023-04-26 | Senate Committee on Environment and Public Works discharged by Unanimous Consent. | `[]` |
| 20 | 2023-04-26 | Passed/agreed to in Senate: Passed Senate without amendment by Yea-Nay Vote. **50 - 49**. Record Vote Number: 98. | `[passage]` |
| 19 | 2023-04-26 | Passed Senate without amendment by Yea-Nay Vote. **50 - 49**. Record Vote Number: 98. (consideration: CR S1360, S1363-1365; text: CR S1365) | `[]` |
| 18 | 2023-04-27 | Received in the House. | `[receipt]` |
| 17 | 2023-04-27 | Held at the desk. | `[]` |
| 16 | 2023-05-23 | Rules Committee Resolution H. Res. 429 Reported to House. ... | `[]` |
| 15 | 2023-05-23 | Considered under the provisions of rule H. Res. 429. | `[]` |
| 14 | 2023-05-23 | Rule provides for consideration of H.R. 467, S.J. Res. 11 and H.J. Res. 45. ... | `[]` |
| 13 | 2023-05-23 | DEBATE - The House proceeded with one hour of debate on S.J. Res. 11. | `[]` |
| 12 | 2023-05-23 | The previous question was ordered pursuant to the rule. | `[]` |
| 11 | 2023-05-23 | POSTPONED PROCEEDINGS - ... by voice vote announced the ayes had prevailed. Mr. Pallone demanded the yeas and nays ... | `[]` |
| 10 | 2023-05-23 | Considered as unfinished business. | `[]` |
| 9 | 2023-05-23 | Passed/agreed to in House: On passage Passed by the Yeas and Nays: **221 - 203** (Roll no. 232). (text: CR H2523) | `[passage]` |
| 8 | 2023-05-23 | On passage Passed by the Yeas and Nays: **221 - 203** (Roll no. 232). (text: CR H2523) | `[]` |
| 7 | 2023-05-23 | Motion to reconsider laid on the table Agreed to without objection. | `[]` |
| 6 | 2023-06-07 | Presented to President. | `[executive-receipt]` |
| 5 | 2023-06-14 | Vetoed by President. | `[executive-veto]` |
| 4 | 2023-06-14 | Veto message received in Senate. Ordered held at the desk. (text: CR S2089-2090) | `[]` |
| 3 | 2023-06-21 | Veto Message considered in Senate. | `[]` |
| 2 | 2023-06-21 | Failed of passage in Senate over veto: Failed of passage in Senate over veto by Yea-Nay Vote. **50 - 50**. Record Vote Number: 167. | `[]` |
| 1 | 2023-06-21 | Failed of passage in Senate over veto by Yea-Nay Vote. **50 - 50**. Record Vote Number: 167. | `[veto-override-failure]` |
| 0 | 2023-06-22 | Message on Senate action sent to the House. | `[]` |

Two things worth flagging beyond the ticket's specific questions, both visible in this one bill:

- **Every real recorded vote appears twice** in the table — once with the real classification tag
  (order 20, 9, 1) and once immediately adjacent with `classification = []` (order 19, 8, 2). This
  is consistent with the separately-tracked "`is_passage` is `False` on ~60% of US federal motions"
  issue noted in the ticket (it's the builder-side match-up between `Motion` and the *tagged* action
  row, not the untagged duplicate, that's presumably going wrong) — flagging as context, not
  re-litigating it; that issue is explicitly out of scope here.
- The failed veto-override (`50 - 50`, i.e. did **not** get the 2/3 needed) is correctly tagged
  `veto-override-failure` and not `passage` — a real `DEFINITE_NO`-shaped signal that classification
  tagging *does* capture correctly for Congress, at least for this action type.

### 3. Does the global tally-pattern regex match Congress's real vote text?

The global regex (as given in the ticket, corrected from its escaped form) is:

```
\(\s*\d+\s*-\s*Y\s+\d+\s*-\s*N(?:\s+\d+\s*-\s*A)?\s*\)
```

i.e. it expects Virginia-shaped text like `(96-Y 0-N)` — parenthesized, with literal `Y`/`N`/`A`
letters after each number.

Tested against all **4,897** `passage`-classified US rows: **0 matches.**

Congress's real recorded-vote text never uses `Y`/`N`/`A` letter suffixes. The actual formats seen:

- `"Passed by the Yeas and Nays: 221 - 203 (Roll no. 232)"`
- `"Passed Senate without amendment by Yea-Nay Vote. 50 - 49. Record Vote Number: 98."`
- `"Agreed to by the Yeas and Nays: (2/3 required): 409 - 0, 1 Present (Roll no. 393)."`

Breaking down all 4,897 `passage` rows:

| pattern | count |
|---|---|
| VA-shaped regex (`\(\d+-Y \d+-N...\)`) | **0** |
| bare numeric tally (`\d+ *- *\d+`, no letters) | 1,297 |
| voice vote / unanimous consent (no recorded tally at all) | 3,600 |

So even independent of the separate `is_passage`-reliability issue, **the tally regex itself is a
complete miss for Congress** — it would never fire, on any bill, ever. Whatever mechanism currently
extracts vote-count evidence for US Congress motions today is not this regex; it's presumably
falling through to whatever the fallback path does when the regex fails to match. Of the 4,897
`passage` rows, only 1,297 (26%) have any recorded numeric tally at all to extract — the rest are
voice votes/unanimous consent with no tally text to find.

### 4. `amendment-passage` tagging, and how concurrence/cloture votes are actually tagged

**Confirmed still zero** `amendment-passage`-tagged rows for US Congress as of 2026-08-12 (see the
classification table in §1 — it's not in the list at all).

Cloture is already handled as a special case elsewhere (`UsSenateClotureTest`), so the open question
was specifically: how are cross-chamber **concurrence** votes tagged? Checked both:

- All **282** actions containing "cloture" (case-insensitive) in `description`: **100% have
  `classification = []`.** Not one is tagged `passage`, `amendment-passage`, or anything else.
- All **114** actions containing "concur" in `description`: **100% have `classification = []`** too.

Real examples, all `classification = []`:

- `"Senate concurred in the House amendment to S. 2073 with an amendment (SA 3021) by Yea-Nay Vote.
  91 - 3. Record Vote Number: 221."` — S 2073 (`ocd-bill/67ca2da3-9c3d-4793-ae9e-9b0dd165e226`,
  118th Congress)
- `"Motion by Senator Schmitt to concur in the House amendment to the Senate amendment to H.R. 2882
  with an amendment (SA 1795) was not agreed to by Yea-Nay Vote. 47 - 51. Record Vote Number: 109."`
- `"Motion by Senator Hagerty to concur in the House amendment to the Senate amendment to H.R. 4366
  with an amendment (SA 1634) was not agreed to by Yea-Nay Vote. 45 - 51. Record Vote Number: 83."`
- `"Cloture on the motion to concur in the House amendment to S. 1071 invoked in Senate by Yea-Nay
  Vote. 76 - 20. Record Vote Number: 647."`

**Answer: there is no classification-tag path for concurrence votes to go through at all** — unlike
the veto-override case in §2, which at least gets a real tag. Congress's concurrence votes carry a
real recorded tally and unambiguous directional language ("concurred" / "was ... agreed to" / "was
not agreed to") but zero structured signal. Any Congress-specific rule for these has to be
text-pattern-based against `description`, the same shape as the existing cloture special-case — not
classification-based, because there is no classification to key off.

## Conclusion — recommended `tally_pattern` / rules for phase 2

For the phase 2 `JurisdictionEligibilityConfig`/`JurisdictionEligibilityRule` migration (US, iso2
`"US"`), the data supports:

1. **Override `tally_pattern`** for US: the VA-shaped regex is a proven 0% match (not just
   "unverified" — actively confirmed non-functional). A Congress-shaped replacement needs to match
   bare `NNN - NNN` with no letter suffix, e.g. something like
   `\b(\d{1,3})\s*-\s*(\d{1,3})\b` scoped to phrases containing "Yea(s)", "Nay(s)", "Roll no.", or
   "Record Vote Number" to avoid false-positives on bill numbers / date ranges / CR page citations
   elsewhere in the same description string (several examples above have `CR S1360, S1363-1365`
   style citations in the same sentence).
2. **`veto-override-failure` is safe to treat as `DEFINITE_NO`** — it's a real, correctly-applied
   tag, confirmed via S.J.Res. 11's 50-50 override failure.
3. **Concurrence and cloture both need a text-pattern rule, not a classification-tag rule** —
   `classification` is `[]` for 100% of both (114/114 and 282/282 sampled). Recommend a rule keyed
   on description text containing "concur" + a recorded-vote phrase ("Yea-Nay Vote", "Yeas and
   Nays") + the numeric tally pattern from (1), mirroring however the existing cloture special-case
   is implemented in ddp-broker-py (not visible from this repo — phase 2 should reuse that shape).
4. **Do not treat `passage` classification alone as sufficient signal for a recorded vote** — 3,600
   of 4,897 (74%) `passage` rows are voice-vote/unanimous-consent with no tally to extract at all;
   this is expected and correct (no vote breakdown exists for those), not a bug, but phase 2's rule
   should not assume every `passage` row has a matching tally.

Bills to cite in phase 2's regression test (real, verified, from this doc):
- **S.J.Res. 11**, 118th Congress (`ocd-bill/228eb616-da39-4ab2-9970-3ed8c7813e0f`) — House passage
  221-203, Senate passage 50-49, failed veto-override 50-50.
- **S 2073**, 118th Congress (`ocd-bill/67ca2da3-9c3d-4793-ae9e-9b0dd165e226`) — Senate concurrence
  vote, 91-3, `classification = []`.

## References

- Production DB: `opencivicdata_billaction` / `opencivicdata_bill` / `opencivicdata_legislativesession`
  / `opencivicdata_jurisdiction` (`postgresql://openstates:openstates_dev@localhost:5433/openstates`)
- `notes/bill-actions-persisted-verification-20260811.md` — precedent for this doc's format and for
  the DB-connection caveat (real replica vs. `cams` vs. this checkout's `openstates_dev`)
- Ticket: OPEN-60 (phase 1 of 2; phase 2 is ddp-broker-py PR #295, `fix/BROKER-47-agent`,
  `apps/ddp-broker/common/models/JurisdictionEligibilityConfig.py` /
  `JurisdictionEligibilityRule.py`)
- Related, out of scope here: the separate `is_passage`-reliability builder-side issue (already
  addressed in `fix/BROKER-47-agent`) — §2's duplicate-row observation is context for that issue,
  not a re-investigation of it.
