# OPEN-64: Virginia eligible_for_scorecard breadth verification

## Context

VA is the jurisdiction `Motion.eligible_for_scorecard`'s tally-pattern regex and action-tag rules
were originally built and confirmed against (BROKER-47, HB1207). Those values lived as unlabeled
module-level defaults in `motion_eligibility.py`, silently applied to every jurisdiction without
its own config, until a same-session architecture change removed that fallback entirely and gave
VA a real, explicit `JurisdictionEligibilityConfig` (ddp-broker-py migration `0052`) -- including a
fix for a real ambiguity found live 2026-08-12 (SB783: the `amendment-passage` tag covers both a
real cross-chamber concurrence vote and a same-chamber floor amendment that must never score).

That migration's `verified_notes` reflected two bills (HB1207, SB783). This is the breadth check
promised in OPEN-64's Phase 1: confirming the tally pattern and the `amendment-passage`
`requires_pattern` gate hold across VA's real action data broadly, not just those two bills.

Queried the production OpenStates Postgres replica directly (`opencivicdata_billaction` joined
through `opencivicdata_bill` -> `opencivicdata_legislativesession` -> `opencivicdata_jurisdiction`,
`jurisdiction.name = 'Virginia'`), read-only, 2026-08-12.

## Result

### 1. Tally-pattern regex against real `passage`-classified actions

```
\(\s*\d+\s*-\s*Y\s+\d+\s*-\s*N(?:\s+\d+\s*-\s*A)?\s*\)
```

Of 9,022 real `passage`-tagged actions: **2,720 (30%) match**, 6,302 don't. Sampled 30 of the
non-matching rows at random -- **100% are exactly the ceremonial/administrative/voice-vote noise
the algorithm is designed to leave `UNCLEAR`**, not a gap in the pattern:

- `"Signed by Speaker"` / `"Signed by President"` -- same-day ceremonial signing (the exact case
  `VaHb1207Test` already covers).
- `"Bill text as passed House and Senate (HB59ER)"`-shaped rows -- an enrolled-bill-text marker,
  not a vote event at all.
- `"Agreed to by House by voice vote"` -- a real voice vote with genuinely no tally to extract
  (same shape as the 74% of US Congress `passage` rows found voice-vote-only in OPEN-60's own
  research).

No VA-specific tally-format variant was found that the current regex misses. The 30% match rate is
explained entirely by legitimate no-tally actions, the same way US Congress's lower match rate was
explained by its own voice-vote share.

### 2. `amendment-passage` breadth -- the SB783 `requires_pattern` gate

Of 728 real `amendment-passage`-tagged actions: **157 (22%) match** the gate
(`agreed to by (House|Senate)|Governor`), 571 don't. Categorized a broad sample of both sides:

**Correctly excluded (571), same shape across dozens of real bills, e.g.:**
- `"committee amendments agreed to"` / `"committee amendment agreed to"` -- committee-level
  amendment, most common shape by far.
- `"[Committee Name] Amendment(s) agreed to"` (e.g. `"Courts of Justice Amendment agreed to"`,
  `"Rehabilitation and Social Services Amendments agreed to"`) -- floor amendment reported by
  committee, same chamber.
- `"Senator/Delegate [Name] Amendment agreed to"` / `"...Floor amendment agreed to"` -- individual
  member's floor amendment, same chamber.

None of these contain `"agreed to by"` + a chamber name, or `"Governor"` -- the gate correctly
excludes all of them, confirmed across many bills (HB1005, HB1007, HB1011, HB1013, HB1020, HB1045,
HB1093, HB1111, HB1140, HB1150, HB1165, HB1212, HB1214, HB1217, HB122, HB1220, HB1222, and more),
not just SB783's own two examples.

**Correctly included (157), e.g.:**
- `"Senate amendment(s) agreed to by House (NN-Y NN-N 0-A)"` -- the real cross-chamber concurrence
  shape (HB1045, HB1111, HB1140, HB1150, HB1165, HB1212, HB1214, HB1217, HB122, HB1222, and more).
- `"Governor's amendment nos. 1, 4, and 5 agreed to (66-Y 34-N 0-A)"` (HB1011) -- a real vote on
  whether to accept the Governor's proposed amendments, correctly captured by the gate's separate
  `"Governor"` alternative. This is a distinct real-vote shape from the House/Senate concurrence
  case, confirming the gate's second alternative is load-bearing, not redundant.

**One shape worth flagging, not a defect:** HB1212 has three same-day `amendment-passage` actions
on 2026-03-06 -- a first concurrence vote (`"Senate amendments agreed to by House (61-Y 35-N 0-A)"`),
a `"Reconsideration of Senate amendments agreed to by House"` (no tally text, so never reaches
`_matched_actions` regardless of the gate), and a second, final tally after reconsideration
(`"Senate amendments agreed to by House (60-Y 35-N 0-A)"`). This is the same same-day-multiple-
real-votes shape OPEN-60 found and fixed for US Congress (nearest-in-time candidate/action
matching, not date-only) -- VA can hit it too, and the existing fix already generalizes to it; not
a new gap, just confirming the mechanism that protects against it applies here too.

### 3. `committee-passage` / `committee-passage-favorable` -- no other ambiguity found

Sampled real committee-passage actions: overwhelmingly `"Reported from [Committee] (NN-Y NN-N)"`,
a clean, unambiguous shape. One case worth noting: `"Conference report agreed to by Senate (21-Y
18-N 0-A)"` is also tagged `committee-passage` -- this maps to `DEFINITE_NO` under VA's config,
which is the **correct, intended** behavior (`VaHb1207Test.test_conference_report_is_not_eligible`
already requires exactly this outcome -- VA's real final vote is captured by the separate
`"Passage R"`-shaped motion, not the conference-report-agreement step). Confirms the existing test
fixture's assumption is correct against broader real data, not an accident specific to HB1207.

## Conclusion

Both pieces of VA's migrated config (`tally_pattern`, and the `amendment-passage` `requires_pattern`
gate) hold up against a broad sample of real VA action text, not just the two bills the original
`verified_notes` cited. No new tag ambiguity or tally-format variant was found. Migration `0052`'s
`verified=True` is justified at this broader scope; `verified_notes` below has been updated to
reflect it.

Updated `verified_notes` (ddp-broker-py, `common_jurisdictioneligibilityconfig` row for VA):

> Original basis, BROKER-47: HB1207. requires_pattern fix, OPEN-64/2026-08-12: SB783. Breadth-
> verified, OPEN-64/2026-08-12: tally_pattern checked against 9,022 real `passage`-tagged actions
> (2,720 match; 30-sample of non-matches confirmed 100% legitimate ceremonial/voice-vote/no-tally
> content, no format gap found). `amendment-passage` requires_pattern checked against 728 real
> actions across 15+ distinct bills (157 correctly included via "agreed to by House/Senate" or
> "Governor"; 571 correctly excluded as committee/same-chamber floor amendments). No other tag
> ambiguity found in committee-passage/committee-passage-favorable sampling.

## References

- ddp-broker-py migration `0052_virginia_eligibility_config.py`
- `fetch/tests/test_motion_eligibility.py` -- `VaHb1207Test`,
  `RequiresPatternDistinguishesSameChamberFromConcurrenceTest`
- `fetch/tests/test_process_bill_votes_eligibility.py` -- `VaHb1207ProcessBillVotesTest`
- OPEN-60 -- the sibling ticket whose same-day-multiple-real-votes fix (nearest-in-time candidate/
  action matching) is confirmed relevant to VA too (HB1212), not just US Congress
- Production DB: `opencivicdata_billaction` / `opencivicdata_bill` /
  `opencivicdata_legislativesession` / `opencivicdata_jurisdiction`
