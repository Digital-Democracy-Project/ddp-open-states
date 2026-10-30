# Stage 3 structural gates — cross-state sweep and calibrated ceilings, OPEN-445, 2026-10-30

Full `--structural` sweep of all 9 tracked jurisdictions (`jurisdictions.yaml` `status: live` set:
us, fl, wa, va, mi, ut, az, ma, nc), run against the production-mirrored local DB
(`postgresql://openstates:openstates_dev@localhost:5433/openstates`) on 2026-10-30, immediately
after implementing the four gates. This is the in-repo equivalent of the ticket's "floors ...
written in the plan's section 4.5" deliverable — **PLAN-push-button-onboarding.md is not in this
repo** (confirmed during planning: it lives in a different repo this workspace has no access to).
Whoever next has access to that repo should transcribe the table and ceilings below into its
section 4.5; this note is not a substitute for that document, only the source data for it.

```bash
for st in us fl wa va mi ut az ma nc; do
  python3 quality_check.py --structural "$st"
done
```

Full raw output: `logs/quality-check/open445-structural-sweep-20261030.log` (this checkout).

## Results

| Jurisdiction | People loaded | Sessions w/ votes | Vote-key collision | Version-stage: no-stage share | Votes unresolved | Sponsorships unresolved |
|---|---|---|---|---|---|---|
| US | 725 | 0 | n/a (0 sessions) | 1,157/44,707 (2.59%) | 23,047/536,482 (4.30%) | 19,235/416,351 (4.62%) |
| FL | 539 | 0 | n/a (0 sessions) | 0/13,492 (0.00%) | 3,369/325,234 (1.04%) | 549/20,468 (2.68%) |
| WA | 348 | 0 | n/a (0 sessions) | 0/5,701 (0.00%) | 673/171,556 (0.39%) | 870/28,165 (3.09%) |
| VA | 356 | 2 | none | 18/12,253 (0.15%) | **35,240/452,159 (7.79%)** | **1,799/18,616 (9.66%)** |
| MI | 451 | 0 | n/a (0 sessions) | 433/7,883 (5.49%) | 903/93,259 (0.97%) | 5/41,369 (0.01%) |
| UT | 271 | 0 | n/a (0 sessions) | 1/5,147 (0.02%) | 0/93,865 (0.00%) | 45/1,774 (2.54%) |
| AZ | 351 | 1 | n/a (1 session) | 40/4,744 (0.84%) | 277/75,720 (0.37%) | 1/8,075 (0.01%) |
| MA | 415 | 1 | n/a (1 session) | 0/11,694 (0.00%) | **7,194/44,804 (16.06%)** | 582/37,657 (1.55%) |
| NC (test subject) | 508 | 1 | n/a (1 session) | 250/6,191 (4.04%) | 611/72,058 (0.85%) | 898/26,095 (3.44%) |

Bold = exceeds the ceiling derived below.

"Sessions w/ votes = 0" means the gate is not applicable (every jurisdiction's own vote-key
uniqueness check requires at least 2 sessions with votes loaded to have anything to compare) —
most tracked jurisdictions currently have only their most recent session's votes imported, not a
backlog of multiple sessions with votes simultaneously present. This is expected, not a defect;
the gate activates automatically once a second session's votes are loaded for a given jurisdiction
(as NC's history shows for `2025`/`2025E1` — see below).

## Derivation of the two numeric ceilings

Both the ticket text and the approved implementation plan require ceilings "derived from measured
data, not invented," with **NC excluded from deriving its own bar** (NC is the test subject). The
same reasoning is applied to **VA and MA**: both measured well outside every other jurisdiction's
range on attribution resolution, with no prior ticket (unlike NC's OPEN-233/234) explaining why.
Treating their numbers as acceptable baseline would mean the first real run of this gate quietly
ratifies two previously-invisible data-quality gaps instead of surfacing them — exactly the
failure mode this ticket exists to close. They are therefore **findings this sweep produced**, not
inputs to the ceiling.

**`ATTRIBUTION_UNRESOLVED_CEILING = 0.047`** (quality_check.py) — the maximum measured unresolved
share among the 6 jurisdictions not flagged above (us, fl, wa, mi, ut, az), across both votes and
sponsorships: US sponsorships at 4.6199...%, rounded up to the next thousandth for a stable
constant. No additional margin was applied beyond that rounding. This also validates the
95%-resolved convention already on record from NC's own first baseline
(`notes/nc-tier2-250-bill-baseline-sweep-20260831.md`) — a 5%-ish ceiling was already in informal
use, and the real cross-state data independently lands in the same place.

**`VERSION_STAGE_UNKNOWN_CEILING = 0.055`** (quality_check.py) — the maximum measured no-stage
share among the 8 jurisdictions other than NC: MI at 5.4928...%, rounded up to the next
thousandth. No additional margin applied.

## NC before/after (the ticket's own motivating comparison)

| | 2026-09-01 (people not loaded, per `notes/nc-tier2-250-bill-baseline-sweep-20260831.md`) | Today (2026-10-30, measured live) |
|---|---|---|
| People loaded | 0 | 508 |
| Votes unresolved | 72,058/72,058 (100%) | 611/72,058 (0.85%) |
| Sponsorships unresolved | 26,095/26,095 (100%) | 898/26,095 (3.44%) |
| Version-stage no-stage share | 3,800/6,191 (61.4%) — OPEN-366, since fixed | 250/6,191 (4.04%) |

NC's version-stage number dropped from 61.4% to 4.04% between the ticket being filed and this
sweep running — **OPEN-366 (status: Done) already fixed the specific gap the ticket cites.** The
ticket's "NC had 3,800 of 6,191" is accurate as the historical finding that motivated this work,
not as what Stage 3 measures today. The historical 100%/100%/0-people state is reproduced as a
fixture in `test_quality_check.py` (`test_nc_2026_09_01_people_not_loaded_fails_people_and_attribution_gates`)
since no live DB snapshot from 2026-09-01 exists to query directly; the numbers in that fixture are
exactly the ones this note's "2026-09-01" column repeats, which are themselves copied from the
already-published NC baseline note above, not invented for this ticket.

## New findings this sweep produced (not NC, not previously ticketed)

- **VA**: 7.79% of votes and 9.66% of sponsorships unresolved — both exceed the calibrated
  ceiling. No existing ticket explains this (unlike NC's OPEN-233/234). **Recommend filing a
  `quality-regression` ticket for VA's attribution resolution**, following the same AC shape as
  OPEN-233/234, before VA's next Stage 3 run (which will now fail on this).
- **MA**: 16.06% of votes unresolved — exceeds the ceiling (sponsorships pass at 1.55%). **Recommend
  filing a `quality-regression` ticket for MA's vote attribution** specifically.

Filing those two tickets was treated as outside this implementation's authority to do
unilaterally (a visible, hard-to-reverse action on tickets this work didn't previously own) and is
flagged here for the ticket owner to confirm, rather than done silently.

## Scope decisions carried into the code (see quality_check.py and RUNBOOK.md for the enforcement)

- Gate 1 (attribution resolution) is implemented in full here (`qa_primitives.attribution_resolution_rates`)
  rather than stubbed out, even though the ticket description says "this is OPEN-261, do not
  duplicate it" — OPEN-261 remains open with no implementation anywhere in this repo, and this
  ticket's own AC requires a working, numeric gate end-to-end. OPEN-261 should import this
  function rather than duplicate it; see the function's own docstring.
- "Files a `quality-regression` ticket" is implemented as the existing report-and-human/agent-files-it
  pattern (a blocking `FAIL` plus a printed recommendation), not literal Jira API code — no Jira
  client exists anywhere in this repo, and `verify-jurisdiction`'s own identically-shaped failure
  path (probe fails → a human/agent files a ticket) is the only precedent for this shape.
- "Sends the state back to Stage 1" does not write to `jurisdictions.yaml`'s `status` field — that
  enum has no Stage 1 value, and a script flipping it automatically risks overwriting a deliberate
  human override (NC's own `status: live`, OPEN-417).
- Gate 4's "again... before routing" checkpoint has no entry point in this repo; the replica
  routing decision is `ddp-broker-py`'s concern (BROKER-302). This gate's Stage 3 run is the
  "again" re-assertion within `ddp-open-states`' own pipeline stage only.
