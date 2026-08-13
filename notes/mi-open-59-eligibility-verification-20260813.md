# OPEN-59: Michigan `eligible_for_scorecard` verification — `amendment-passage` is single-purpose, the global tally regex is a 0% miss, and 6 real cross-chamber concurrence votes hide untagged

## Context

`Motion.eligible_for_scorecard` (ddp-broker-py, BROKER-47) is computed from a global tally-pattern
regex and a set of `DEFINITE_YES`/`DEFINITE_NO` action-classification tags that were only ever
confirmed against Virginia's own action text. Michigan currently falls back to those Virginia-shaped
defaults, unverified. This is phase 1 of OPEN-59 (research, in `ddp-open-states`) — the handoff
artifact for phase 2 (config/migration/tests, in `ddp-broker-py` PR #295, branch
`fix/BROKER-47-agent`), following the same two-repo split and methodology already run for OPEN-60
(US Congress), OPEN-57 (Arizona), OPEN-58 (Florida), OPEN-61 (Utah), OPEN-62 (Washington), and
OPEN-64 (Virginia breadth).

Four things were asked, all against real replica data, no invented examples:
1. Sample `opencivicdata_billaction` rows for Michigan, grouped by classification, including at
   least one real bill's full action list.
2. Whether the global tally-pattern regex actually matches Michigan's real vote-tally text for its
   real passage votes.
3. Whether Michigan's `amendment-passage` tag (previously sampled 2026-08-11, 15 instances, all
   reading literally "AMENDMENT(S) ADOPTED" with no vote tally) holds up broadly, and whether any
   other Michigan tag means more than one thing depending on context, the way Virginia's
   `amendment-passage` covers both a real cross-chamber concurrence vote and a same-chamber floor
   amendment that must never score.
4. Write it up so phase 2 has real bill IDs and real action text to implement against.

**A note on the ticket's own citation:** no notes doc dated 2026-08-11 documenting the prior
`amendment-passage` finding exists anywhere in this repo's `notes/` directory or git history
(checked directly — `grep -rn "AMENDMENT(S) ADOPTED"` and `git log --all --oneline | grep -i
"michigan\|OPEN-59"` both came back empty prior to this doc). Rather than either refusing to proceed
or blindly trusting an unsourced claim, the claim was independently re-verified against live data
below (§3) — it checks out exactly as stated — and this doc is now the actual supporting record for
it, which the earlier claim lacked.

## Method

Queried the production OpenStates Postgres replica directly —
`postgresql://openstates:openstates_dev@localhost:5433/openstates` (the real replica; **not** the
`cams` DB the `postgres` MCP tool defaults to, and not this checkout's separate `openstates_dev`
DB — same caveat as `notes/bill-actions-persisted-verification-20260811.md` and every sibling doc in
this family). `DATABASE_URL` was exported by sourcing `activate.sh` directly (unpiped) and verified
with `echo $DATABASE_URL` before any query ran.

Jurisdiction filter: confirmed `SELECT id, name, classification FROM opencivicdata_jurisdiction
WHERE name ILIKE '%michigan%'` returns exactly one row —
`ocd-jurisdiction/country:us/state:mi/government` — no municipal-jurisdiction collision (the trap
OPEN-58/Florida hit with 70+ `place:*` jurisdictions).

All numbers below are live counts as of 2026-08-13, via `psycopg2` against `opencivicdata_billaction`
joined through `opencivicdata_bill` → `opencivicdata_legislativesession` → `opencivicdata_jurisdiction`.

## Result

### 1. Classification breakdown (25,324 total MI billaction rows, one persisted session, `2025-2026`, 3,910 bills)

| classification | count |
|---|---|
| *(untagged, `classification = []`)* | 8,091 |
| referral-committee | 4,951 |
| introduction | 4,284 |
| reading-1 | 2,608 |
| passage | 1,989 |
| committee-passage | 1,882 |
| reading-2 | 654 |
| reading-3 | 614 |
| executive-signature | 95 |
| executive-receipt | 95 |
| amendment-failure | 46 |
| **amendment-passage** | **15** |

That's the complete set of distinct tags Michigan uses (sum of the table above = 25,324, matching
the total row count exactly; confirmed zero rows carry more than one classification tag). This is
Michigan's complete local corpus — one session, not a subsample, the same framing OPEN-61 (Utah) used
for its own thinner corpus.

### 2. One real bill's full action list — SB 878, 2025–2026 session

`ocd-bill/3f025cc5-541e-4432-a3ad-0e2b1ba52c69` — chosen because it hits the `amendment-failure` →
`amendment-passage` → `passage` sequence back-to-back on the same day, the exact shape needed to
confirm `amendment-passage` never doubles as a real vote itself.

| order | date | description | classification | acting org |
|---|---|---|---|---|
| 0 | 2026-03-18 | INTRODUCED BY SENATOR SARAH ANTHONY | `[introduction]` | Senate |
| 1 | 2026-03-18 | RULES SUSPENDED | `[]` | Senate |
| 2 | 2026-03-18 | REFERRED TO COMMITTEE OF THE WHOLE | `[referral-committee]` | Senate |
| 3 | 2026-04-14 | REASSIGNED TO COMMITTEE ON APPROPRIATIONS | `[]` | Senate |
| 4 | 2026-04-28 | DISCHARGE COMMITTEE APPROVED | `[]` | Senate |
| 5 | 2026-04-28 | PLACED ON ORDER OF GENERAL ORDERS | `[]` | Senate |
| 6 | 2026-04-28 | RULES SUSPENDED FOR IMMEDIATE CONSIDERATION | `[]` | Senate |
| 7 | 2026-04-29 | REPORTED BY COMMITTEE OF THE WHOLE FAVORABLY WITH SUBSTITUTE (S-1) | `[committee-passage]` | Senate |
| 8 | 2026-04-29 | SUBSTITUTE (S-1) CONCURRED IN | `[]` | Senate |
| 9 | 2026-04-29 | PLACED ON ORDER OF THIRD READING WITH SUBSTITUTE (S-1) | `[]` | Senate |
| 10 | 2026-04-29 | RULES SUSPENDED | `[]` | Senate |
| 11 | 2026-04-29 | PLACED ON IMMEDIATE PASSAGE | `[]` | Senate |
| 12 | 2026-04-29 | **AMENDMENT(S) DEFEATED** | `[amendment-failure]` | Senate |
| 13 | 2026-04-29 | **AMENDMENT(S) ADOPTED** | `[amendment-passage]` | Senate |
| 14 | 2026-04-29 | **PASSED ROLL CALL # 78 YEAS 19 NAYS 18 EXCUSED 0 NOT VOTING 0** | `[passage]` | Senate |
| 15 | 2026-04-30 | received on 04/30/2026 | `[introduction]` | House |
| 16 | 2026-04-30 | read a first time | `[reading-1]` | House |
| 17 | 2026-04-30 | referred to Committee on Appropriations | `[referral-committee]` | House |

This is the complete, unabridged action list — all 18 rows, order 0 through 17. Order 12→13→14 is
the exact shape: a failed amendment, an adopted amendment, then the chamber's own real floor vote
immediately after — `amendment-passage` here is a same-chamber procedural marker, never a vote in
itself.

### 3. `amendment-passage`/`amendment-failure` breadth — confirmed single-purpose, never dual-meaning

**All 15 `amendment-passage` rows**, across 15 distinct bills (HB 4135, HB 4420, SB 23, SB 3, SB 462,
SB 463, SB 465, SB 466, SB 483, SB 532, SB 596, SB 599, SB 700, SB 723, SB 878), read the identical
literal string `"AMENDMENT(S) ADOPTED"` — zero variation. **100% (15/15) have `acting_org` = Senate**,
including for the two House-originated bills (HB 4135, HB 4420) — confirming this tag fires only when
the Senate adopts a floor amendment on a bill currently in its own possession, never as a
cross-chamber concurrence marker. This independently reproduces and confirms the ticket's own
2026-08-11 citation.

**All 46 `amendment-failure` rows** are equally clean: 100% read the identical literal string
`"AMENDMENT(S) DEFEATED"`, 100% `acting_org` = Senate, same same-chamber shape, no ambiguity.

**Unlike Virginia's `amendment-passage` (BROKER-47/SB783, which covers both a real cross-chamber
concurrence vote and a same-chamber floor amendment and needed a `requires_pattern` gate to
distinguish them) or Utah's own dual-meaning tag, Michigan's `amendment-passage` and
`amendment-failure` are single-purpose** — always same-chamber, never a real vote, never carrying a
tally of their own. No gate is needed for these two tags; a corrected `tally_pattern` (§4, below)
already excludes them by simply never matching their tally-free text.

### 4. Global tally-pattern regex — confirmed 0% match on real passage votes

```
\(\s*\d+\s*-\s*Y\s+\d+\s*-\s*N(?:\s+\d+\s*-\s*A)?\s*\)
```

Tested against all **1,989** real `passage`-classified rows: **0 matches (0.0%).** Michigan's real
tally text is never parenthesized and never uses `Y`/`N`/`A` letter suffixes — the VA-shaped regex
would never fire on any Michigan bill, the same complete-miss failure mode OPEN-60 (US Congress) and
OPEN-58 (Florida) found for their own jurisdictions.

Real examples of Michigan's actual tally text (case varies — both mixed-case and all-caps forms
occur, seemingly by era/chamber):
- `"passed; given immediate effect Roll Call #156 Yeas 57 Nays 45 Excused 0 Not Voting 8"`
- `"PASSED ROLL CALL # 6 YEAS 34 NAYS 0 EXCUSED 3 NOT VOTING 0"`

**Recommended Michigan-specific `tally_pattern`:**

```
Roll Call\s*#\s*\d+\s+Yeas\s+\d+\s+Nays\s+\d+\s+Excused\s+\d+\s+Not Voting\s+\d+
```

(case-insensitive). Tested against the same 1,989 real `passage` rows: **1,021 match (51.3%)**. All
**968 non-matches** were categorized without exception into two legitimate, tally-free shapes — zero
were an unexplained format gap:

- **540 rows** — a same-bill, same-classification **duplicate cross-chamber transmittal notice**,
  e.g. `HB 4284` has its real tally at order 10 (`"passed; given immediate effect Roll Call #2 Yeas
  63 Nays 46 Excused 0 Not Voting 1"`) and then, at order 12, a second `passage`-tagged row from the
  other chamber reading only `"PASSED BY HOUSE WITH IMMEDIATE EFFECT"` — no tally of its own, the
  same "real vote recorded once, notification recorded again nearby with no numbers" shape OPEN-60
  found for Congress.
- **428 rows** — voice-vote/consent resolution language containing `"ADOPTED"` with no numeric tally
  at all (Michigan's memorializing/simple-resolution passage path).

### 5. Real worked example of the duplicate-notification shape — HB 4284, 2025–2026 session

`ocd-bill/2ca433cd-e99f-4013-9aad-2c118df69028`:

| order | date | description | classification | acting org |
|---|---|---|---|---|
| 9 | 2026-01-14 | read a third time | `[reading-3]` | House |
| 10 | 2026-01-14 | **passed; given immediate effect Roll Call #2 Yeas 63 Nays 46 Excused 0 Not Voting 1** | `[passage]` | House |
| 11 | 2026-01-14 | transmitted | `[]` | House |
| 12 | 2026-01-21 | **PASSED BY HOUSE WITH IMMEDIATE EFFECT** | `[passage]` | Senate |
| 13 | 2026-01-21 | REFERRED TO COMMITTEE ON CIVIL RIGHTS, JUDICIARY, AND PUBLIC SAFETY | `[referral-committee]` | Senate |

Order 10 is the real House floor vote with a full tally; order 12 is the Senate's own
`passage`-classified notice that the bill arrived from the House, carrying no tally of its own. Both
share the `passage` classification, so any per-classification rule has to tolerate this — the MI
regex correctly leaves order 12 as `UNCLEAR` (no tally to extract) rather than misreading it.

### 6. New finding beyond the ticket's own ask — where Michigan's real cross-chamber concurrence votes actually live

Searched all `billaction` rows containing `"concur"` case-insensitively, across **all**
classifications, not just `amendment-passage`: **388 rows, 100% (388/388) carry `classification =
[]`** — untagged, the same shape Washington's and Congress's own concurrence votes have (OPEN-62,
OPEN-60).

Of those 388 untagged rows, the overwhelming majority (382, 98.5%) are voice-vote-style with no
numeric tally at all — e.g. `"SUBSTITUTE (S-1) CONCURRED IN"`, `"Senate substitute (S-3) concurred
in"`, `"recommendation concurred in"`. But **6 rows, across 5 distinct real bills, carry a real,
embedded roll-call tally directly in the untagged text**:

| bill | description |
|---|---|
| HB 4961 | `"Senate amendment(s) concurred in Roll Call #248 Yeas 102 Nays 7 Excused 0 Not Voting 1"` |
| SB 158 | `"HOUSE AMENDMENT(S) CONCURRED IN ROLL CALL # 364 YEAS 32 NAYS 3 EXCUSED 2 NOT VOTING 0"` |
| SB 240 | `"HOUSE AMENDMENT(S) CONCURRED IN ROLL CALL # 117 YEAS 36 NAYS 1 EXCUSED 1 NOT VOTING 0"` |
| SB 240 | `"HOUSE AMENDMENT(S) CONCURRED IN ROLL CALL # 116 YEAS 35 NAYS 1 EXCUSED 1 NOT VOTING 1"` |
| SB 241 | `"HOUSE AMENDMENT(S) CONCURRED IN ROLL CALL # 118 YEAS 36 NAYS 1 EXCUSED 1 NOT VOTING 0"` |
| SB 690 | `"HOUSE AMENDMENT(S) CONCURRED IN ROLL CALL # 365 YEAS 35 NAYS 0 EXCUSED 2 NOT VOTING 0"` |

**These 6 real, tallied cross-chamber votes are currently unreachable by any classification-tag-based
rule at all** — this is not a dual-meaning-tag problem (like VA/UT's `amendment-passage`) and not a
wrong-format problem (like `passage`'s own regex gap, §4) — it's a genuinely new-rule gap. The
existing MI-shaped `tally_pattern` regex from §4 *would* match this text if it were ever tested
against these rows (it matches on the `Roll Call # N Yeas N Nays N Excused N Not Voting N` shape
regardless of surrounding words), but nothing currently routes untagged rows through the tally check
at all. This is the same shape Congress needed a dedicated untagged-concurrence text-pattern rule for
(OPEN-60) — Michigan needs the analogous rule, keyed on `"concur"` in the description text (untagged)
combined with the tally regex from §4, rather than a classification tag.

### 7. `committee-passage` — sampled clean, no ambiguity found

Sampled 40 of 1,882 `committee-passage` rows at random plus an explicit scan of the full set for
"conference" language (Virginia's own committee-passage footgun, where conference-report-agreement
rows get mis-tagged as plain `committee-passage`): **zero** Michigan rows mention "conference" at
all, and **zero** carry any embedded vote tally. Every sampled row reads one of two clean shapes:
`"reported with recommendation [with/without] [substitute/amendment] (...)"` (House) or `"REPORTED
[BY COMMITTEE OF THE WHOLE] FAVORABLY [WITH/WITHOUT] ..."` (Senate) — purely procedural committee
disposition, never a recorded vote, never conflated with a floor or conference vote the way VA's
tag can be.

## Conclusion — recommended `tally_pattern` / rules for phase 2

1. **Override `tally_pattern` for MI** (iso2 `"MI"`): the VA-shaped regex is a proven 0% match (not
   "unverified" — actively confirmed non-functional). Recommended replacement:
   ```
   Roll Call\s*#\s*\d+\s+Yeas\s+\d+\s+Nays\s+\d+\s+Excused\s+\d+\s+Not Voting\s+\d+
   ```
   (case-insensitive). 51.3% match rate against real `passage` rows (1,021/1,989); all 968
   non-matches are legitimate duplicate-transmittal-notice or voice-vote/consent-resolution content,
   with zero unexplained gaps.
2. **No `JurisdictionEligibilityRule` needed for `amendment-passage`/`amendment-failure`** —
   confirmed single-purpose, always-same-chamber, never a real vote, across all 15 + 46 real rows.
   Safe to leave at defaults; the corrected `tally_pattern` above already excludes them by simply
   never matching their tally-free text (no `requires_pattern` gate needed, unlike VA's SB783 fix).
3. **A new rule is needed for the 6 untagged-but-tallied concurrence votes** (HB 4961, SB 158, SB
   240 ×2, SB 241, SB 690) — text-pattern-based (keyed on `"concur"` in the description, untagged
   `classification = []`), not classification-based, combined with the `tally_pattern` from
   recommendation 1. This is the same rule shape Congress's own untagged concurrence/cloture gap
   needed (OPEN-60); phase 2 should mirror however that rule ends up implemented.
4. **No ambiguity found in `committee-passage`** — sampled clean, no VA-style conference-report
   conflation.

Bills to cite in phase 2's regression test (real, verified, from this doc):
- **SB 878**, 2025–2026 session (`ocd-bill/3f025cc5-541e-4432-a3ad-0e2b1ba52c69`) — clean
  `amendment-failure` → `amendment-passage` → `passage` same-day sequence (order 12→13→14),
  confirming `amendment-passage` never scores as a real vote itself.
- **HB 4284**, 2025–2026 session (`ocd-bill/2ca433cd-e99f-4013-9aad-2c118df69028`) — real House
  floor vote with full tally (order 10, Roll Call #2, 63-46) followed by a same-classification,
  tally-free Senate transmittal notice (order 12) — the duplicate-notification shape a naive
  per-classification rule must tolerate.
- **HB 4961**, 2025–2026 session — the untagged-but-tallied concurrence gap: `"Senate amendment(s)
  concurred in Roll Call #248 Yeas 102 Nays 7 Excused 0 Not Voting 1"`, `classification = []`. Good
  DEFINITE_YES-shaped candidate for the new text-pattern rule recommendation 3 requires.

## Phase 2 scope note

This workspace (`ddp-open-states`) has no `ddp-broker-py` checkout — only unrelated CodeBot workspace
clones and the human's own separate dev checkouts exist elsewhere on this machine; neither is this
ticket's workspace, per `project-config.md`'s `repo.path` discipline. Phase 2 — the
`JurisdictionEligibilityConfig`/`JurisdictionEligibilityRule` migration for MI, the bill-specific
regression test using SB 878/HB 4284/HB 4961 above, setting `verified=True` with `verified_notes`
citing this doc, and the before/after `validate_scorecards`/`reconcile_scorecards --MI` run — requires
a `ddp-broker-py` session and is out of scope for this workspace. This doc is the complete handoff
artifact for that follow-up session, the same way OPEN-58's, OPEN-60's, and OPEN-64's notes already
fed real, merged `ddp-broker-py` config.

## References

- Production DB: `opencivicdata_billaction` / `opencivicdata_bill` / `opencivicdata_legislativesession`
  / `opencivicdata_jurisdiction` (`postgresql://openstates:openstates_dev@localhost:5433/openstates`),
  jurisdiction `ocd-jurisdiction/country:us/state:mi/government`
- `notes/bill-actions-persisted-verification-20260811.md` — precedent for this doc's format and for
  the DB-connection caveat (real replica vs. `cams` vs. this checkout's `openstates_dev`)
- `notes/open-60-us-congress-eligibility-verification-20260812.md` — sibling phase-1 doc; same
  "no classification-tag path for concurrence" finding recurs here
- `notes/fl-open-58-eligibility-verification-20260812.md` — sibling phase-1 doc; same tally-regex
  complete-miss and duplicate-notification-row shapes recur here
- `notes/open-64-virginia-eligibility-breadth-verification-20260812.md` — sibling breadth-check doc;
  this doc's `amendment-passage` finding is the inverse of OPEN-64's SB783 ambiguity (MI's tag is
  single-purpose where VA's is dual-meaning)
- `OPEN-59-architecture-assessment-20260812.md` — architecture assessment for this ticket; confirms
  this workspace has no `ddp-broker-py` checkout, and its Diagnosis section's live-query figures are
  independently reproduced exactly by this doc's own re-run queries
- Ticket: OPEN-59 (phase 1 of 2; phase 2 is ddp-broker-py PR #295, `fix/BROKER-47-agent`,
  `apps/ddp-broker/common/models/JurisdictionEligibilityConfig.py` /
  `JurisdictionEligibilityRule.py`)
