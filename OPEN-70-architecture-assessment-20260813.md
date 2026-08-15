# Architecture Assessment: OPEN-70 — US Congress's 13x jump in "wrong vote scored" (456 → 6,045)

## Architectural Question

Is the jump from 456 to 6,045 in `validate_scorecards` check #9 for US Congress a genuine new
defect in the current matching/disambiguation logic, or was 456 simply a stale number from a dev
DB where Congress's `Motion.eligible_for_scorecard` values had never been recomputed end-to-end
under current code? The ticket frames this as binary — either close with "456 was stale" or
root-cause a bug. **This assessment's diagnosis finds the honest answer is neither cleanly**:
6,045 is not "reality" either. Direct sampling against real replica data shows a reproducible,
systemic pattern of genuinely wrong matches, not merely a first-time-computed-correctly number.

## Tech Stack / Investigation Context

| Layer | What it is | Relevant to this ticket |
|---|---|---|
| `ddp-open-states` (this repo) | DDP's local shadow OpenStates pipeline; real production Postgres replica at `postgresql://openstates:openstates_dev@localhost:5433/openstates` | Repo root only; this is where the diagnosis below was run |
| `ddp-broker-py` | **Not present in this repo/workspace** — separate service | `Motion.eligible_for_scorecard`, `motion_eligibility.py`, `JurisdictionEligibilityConfig`, `manage.py backfill_eligible_for_scorecard`/`validate_scorecards`, and the `feature/BROKER-47-eligible-for-scorecard-wip` branch all live here — none of it is reachable from this checkout |

**Same repo-boundary finding as `OPEN-67-architecture-assessment-20260813.md`**: this ticket's AC
literally asks to "compare against `Motion.eligible_for_scorecard`" and sample `validate_scorecards`
output — both are `ddp-broker-py`-side artifacts. Per `project-config.md`'s `repo.path` rule, this
workspace has no `ddp-broker-py` checkout, and that absence is itself the finding to report, not
something to route around by looking for a stray broker checkout elsewhere on the machine.

What **is** answerable from here, and is exactly the precedent `notes/open-60-us-congress-eligibility-verification-20260812.md`
(OPEN-60, the original Congress fix this ticket is checking) already established: query the real
OpenStates replica directly for the underlying `opencivicdata_billaction` rows behind the two
example bills the ticket cites (HR3943, HJRES98) and a broader sample of the same two text
patterns, and determine — independent of anything broker's DB has cached — whether a real
up-or-down vote exists on each bill and whether it's the kind of row a text-pattern-based
disambiguator plausibly would or wouldn't select correctly.

## Diagnosis (evidence, not hypothesis)

Queried the production OpenStates Postgres replica directly (`source activate.sh`, then `psycopg2`
against `DATABASE_URL` — **not** the `postgres` MCP tool, which defaults to the unrelated `cams` DB,
a footgun called out in every sibling doc in this family). Jurisdiction filter:
`opencivicdata_jurisdiction.name = 'United States'`. Two sessions persisted locally: 118th Congress
(19,315 bills' worth of actions) and 119th (18,350) — **124,215 total US billaction rows, 56,562
(45.5%) of them entirely untagged (`classification = []`)**. That untagged fraction is the
structural fact everything below traces back to.

### 1. HR3943 — the ticket's cited "no up-or-down vote" example

Full action history, `ocd-bill/ded09748-2c90-45ff-bad8-a128ca12dd6e` ("Servicemember Employment
Protection Act of 2023"):

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

**Ground truth: this bill never had a floor vote of any kind — it stalled at "placed on the
calendar."** The flagged action (order 2) is a committee markup vote on a substitute amendment,
not a chamber vote on the bill. If a Motion tied to this action is scored `eligible_for_scorecard`,
that is unambiguously wrong — there is no real up-or-down vote anywhere in this bill's history to
have scored instead.

### 2. HJRES98 — the ticket's cited "wrong motion picked" example

Full action history, `ocd-bill/91847d8e-76ff-4172-9193-f636a11a48f0` (NLRB joint-employer
disapproval resolution) — 35 actions, abridged to the relevant sequence:

| order | description | classification |
|---|---|---|
| 23 | POSTPONED PROCEEDINGS — conclusion of debate, voice vote ayes prevailed, yeas/nays demanded, **postponed** | `[]` |
| 21 | Passed/agreed to in House: On passage Passed by the Yeas and Nays: **206 - 177** (Roll no. 10). | `[passage]` |
| 17 | Passed/agreed to in Senate: Passed Senate without amendment by Yea-Nay Vote. **50 - 48**. | `[passage]` |
| 13 | Vetoed by President. | `[executive-veto]` |
| **6** | **POSTPONED PROCEEDINGS — conclusion of debate on veto message, "the vote must be taken by the yeas and nays," further proceedings postponed** | **`[]`** |
| **4** | **Failed of passage in House over veto ... Failed by the Yeas and Nays: (2/3 required): 214 - 191 (Roll no. 185).** | **`[]`** |

The bill's original passage (order 21, 206-177) is cleanly tagged `passage` — not the problem.
**The real gap is the veto-override vote**: order 4 is a genuine, countable, real up-or-down vote
(214-191, a recorded roll call) — and it carries **no classification tag at all**, unlike OPEN-60's
own S.J.Res. 11 example where the equivalent override failure was correctly tagged
`veto-override-failure`. It sits two actions after an untagged "POSTPONED PROCEEDINGS" narration
row (order 6) that mentions "yeas and nays" but contains **zero digits** — it only announces that a
recorded vote *will* happen later. **Both rows are untagged; only one contains an actual tally.**
This is exactly the shape a text-pattern matcher keying on procedural phrasing ("yeas and nays",
"postponed proceedings") without requiring the matched row to itself contain a numeric tally would
get wrong — it has two candidates immediately adjacent, one real, one a placeholder, with no
classification tag to disambiguate and no numeric-content check to fall back on.

### 3. Broader sample — is this systemic or two cherry-picked bills?

Counted untagged US rows matching each cited phrase:

| pattern | untagged (US) row count |
|---|---|
| `POSTPONED PROCEEDINGS` | 1,001 |
| `unanimous consent` (any) | 2,657 |
| `asked unanimous consent` | 176 |
| `by Voice Vote` | 2,215 |

These counts alone are the right order of magnitude to produce thousands of flagged motions, not
dozens.

**Sample A — 12 bills with an untagged "...Nature of a Sub[stitute]...by Voice Vote" committee
action** (HR3943's shape): 7 of 12 (HR 3173, HR 6292, HRES 81, HRES 1063, HR 4486, HR 6994,
HR 6531) have **zero** `passage`-classified action anywhere in their history — no floor vote ever
occurred, same as HR3943. The other 5 do have a real `passage` action elsewhere, so the committee
markup row isn't necessarily the one scored for those — but for the 7 with no real vote at all,
any Motion scored against that committee action is a confirmed false positive, structurally
identical to HR3943.

**Sample B — 10 bills with an untagged `POSTPONED PROCEEDINGS` action** (HJRES98's shape): in 7 of
10 (HR 6914, HCONRES 113, HRES 1115, HR 1449, HRES 1287, HRES 583, HR 5692, SJRES 31 — several
bills had more than one instance), a real, digit-bearing vote (`passage`-tagged, or an untagged
motion-to-recommit/previous-question tally) sits within 2–4 action-orders of the untagged
`POSTPONED PROCEEDINGS` narration, with no digits in the narration row itself. One bill (HR 4553)
shows a long committee-of-the-whole amendment sequence with 10 `POSTPONED PROCEEDINGS` rows across
many amendments, each debated and postponed separately, consistent with batched later voting
further away than a ±2 window captures — a harder disambiguation case, not a counterexample.

**Conclusion: this is systemic, not two hand-picked bad examples.** Both of the ticket's cited
bills are representative of a real, common shape in Congress's action stream: roughly half of all
US billaction rows carry no classification tag at all (56,562/124,215), and within that untagged
pool, procedural narration text ("postponed proceedings," "unanimous consent," "voice vote") sits
immediately adjacent to — and is textually similar to — the real vote-outcome text, whether or not
a real vote exists at all on that bill.

### On the ticket's own binary framing

The ticket asks to conclude either "456 was stale, 6,045 is correct" or "genuine bug." The
diagnosis above shows **6,045 is not simply "correct"** — a meaningful fraction of it (both
sub-patterns, confirmed on real, verified bill data, not invented examples) reflects real
mis-scoring. It's plausible **both things are true at once**: 456 likely *was* computed against a
long-lived dev DB where Congress's motions hadn't been mass-recomputed under current code since
OPEN-60 landed (the ticket's own framing), **and** the current code — even with OPEN-60's
tally-pattern/concurrence fix applied — still mis-scores a large fraction of Congress's untagged
procedural actions as if they were real votes. The first full, unfiltered backfill simply exposed
a pre-existing defect at real scale for the first time, rather than 6,045 representing 13x more
genuine bugs materializing from nowhere.

## Approaches Evaluated

### Approach A: Accept the ticket's binary framing at face value, sample a few motions "informally," and let the sample's outcome pick the label

**How it works:** Spot-check a handful of the 6,045 without a documented method, conclude whichever
way the sample leans.
**Pros:** Fast.
**Cons:** This is exactly the failure mode `OPEN-59-architecture-assessment-20260812.md` and
`OPEN-57-architecture-assessment-20260812.md` already had to correct for in this same ticket
family — an unsourced or under-evidenced claim ships as fact. It also can't produce the
bill-by-bill citations phase 2 needs to write a regression test, and it treats the ticket's
either/or framing as exhaustive when the evidence here shows it isn't.

### Approach B: Direct replica diagnosis against the two cited bills plus a broader systemic sample (what this assessment did)

**How it works:** Pull full action histories for the exact cited bills first (ground-truth the
ticket's own examples before generalizing), then quantify the two flagged text patterns across all
of US Congress and sample enough real bills from each to distinguish "isolated cherry-picked
examples" from "systemic shape." Exactly the method `OPEN-60`, `OPEN-59`, `OPEN-62`, `OPEN-64` all
used for the *original* Virginia-shaped-defaults problem — this ticket is checking whether that
fix, once actually run at scale, still has a gap of the same general kind (untagged procedural text
competing with real vote text).

**Pros:**
- Directly answers the ticket's real question with real bill IDs and action text, not invented
  examples — satisfies the AC's explicit "bill by bill" requirement.
- Reuses established, validated methodology and connection caveats from six prior sibling
  investigations rather than reinventing a diagnostic approach (`reuse-before-reinvent.md`).
- Distinguishes the two sub-patterns cleanly: "no real vote exists at all" (HR3943-shape, 7/12
  sampled) is a different bug surface from "a real vote exists but sits next to a textually similar
  placeholder" (HJRES98-shape, 7/10 sampled) — both need root-causing, but the fix for each is
  different (the first needs a positive check that a candidate action contains a real tally before
  treating it as scoreable at all; the second needs the disambiguator to prefer a numeric-bearing
  candidate over an adjacent non-numeric one, or to require classification-tag or numeric evidence
  before selecting a match).

**Cons:**
- Only two Congress sessions (118th, 119th) are persisted in this replica — narrower than
  Congress's full real history, though `RUNBOOK.md`'s own description of what production actually
  pulls doesn't suggest a materially different distribution of tagged-vs-untagged actions across
  older sessions. Flagging as a scope caveat, not a defect in the method (same posture OPEN-61 took
  for Utah's two-session corpus).
- Cannot literally execute `Motion.eligible_for_scorecard` or `validate_scorecards` from this repo
  — the conclusion about *which specific action* broker currently matches for each Motion is
  inferred from the shape of the underlying OpenStates data plus OPEN-60's documented rule set, not
  observed directly from broker's own matching code. This is the same limitation `OPEN-67` hit for
  the Utah chamber-swap investigation, stated plainly rather than glossed over.

**Standards alignment:** Reproducibility/evidentiary rigor and "verify before assuming"
(`efficiency.md`) — this session independently ground-truthed both of the ticket's own cited
examples before generalizing, rather than trusting the ticket's characterization on faith. Least
privilege — read-only queries against the replica only, no `postgres` MCP tool, no write path.

### Approach C: Treat this purely as a `ddp-broker-py`-side ticket and decline to investigate further from this repo

**How it works:** Report the repo-boundary gap (broker's DB/code isn't here) and stop, deferring
everything to whoever picks up `ddp-broker-py`.
**Pros:** Technically accurate about the boundary.
**Cons:** Under-delivers relative to what's actually answerable from here — OPEN-60/59/62/64 all
prove that a large, useful fraction of this exact investigation family can be done from
`ddp-open-states` alone, against real replica data, before any broker-side code is touched. Stopping
at "not my repo" here would repeat the exact under-delivery this ticket family's `PRIMITIVES.md`
cross-repo checklist (item 7) already warns against, and would leave the actual, sample-backed
finding (both example bills confirmed genuinely wrong, systemic scale confirmed) undocumented.

## Tradeoff Matrix

| Dimension | A: Informal sampling | B: Direct replica diagnosis (recommended) | C: Decline, defer entirely |
|---|---|---|---|
| Complexity | Low | Low–Medium | Lowest |
| Time to implement | Fastest | Fast (proven query pattern, already run) | Fastest |
| Evidentiary rigor | Low — no ground-truth citation | High — real bill IDs, full action histories, systemic counts | N/A — no evidence produced |
| Satisfies AC as written | Partially, unreliably | Yes, to the extent answerable without broker's own DB | No |
| Distinguishes sub-patterns | No | Yes — two structurally distinct failure modes identified | No |
| Alignment with codebase precedent | Repeats a mistake already corrected twice in this family | Exact match (OPEN-60/59/62/64 method) | Under-delivers relative to established precedent (OPEN-67 still investigated everything answerable) |

## Recommendation: Approach B — direct replica diagnosis, extended to a systemic sample, with the repo-boundary gap stated plainly

**Why this approach:**
- It's the only approach that actually grounds the ticket's own cited examples in real data before
  generalizing, and the only one that can distinguish "two cherry-picked bad examples" from "a
  systemic pattern" — which it does: 7/12 and 7/10 in the two samples respectively show the same
  structural shape as the ticket's own citations.
- It reuses this repo's own established, six-ticket-deep methodology (`reuse-before-reinvent.md`)
  rather than inventing a new diagnostic approach for what is, at its core, the same class of
  problem OPEN-60 already characterized once (Congress's action stream is untagged-text-heavy and
  a Virginia-tuned matcher doesn't generalize to it) — this ticket shows that even after OPEN-60's
  fix, the underlying untagged-text density still causes wrong matches, not because the *tally
  regex* is wrong again, but because the *disambiguation step that picks which row is "the" vote*
  doesn't require the row it picks to actually contain a tally.

**Why not the alternatives:**
- Approach A repeats a documented mistake (`OPEN-57`/`OPEN-59`) of shipping a conclusion without
  ground-truthing it against real data first.
- Approach C leaves real, answerable diagnostic work undone and under-delivers relative to what
  every sibling ticket in this family has already shown is achievable from this repo alone.

**Risks and mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Concluding "6,045 is correct" from this data alone, when the actual broker-side matched-action-per-Motion isn't directly observable from this repo | Real, inherent to the repo boundary | Medium — could overstate confidence in the exact per-Motion verdict | State plainly (as above) that the specific action broker currently matches per Motion is inferred from data shape + OPEN-60's documented rules, not observed directly; recommend phase 2 (in `ddp-broker-py`) confirm against the real `Motion` rows for the specific bills cited here |
| Treating HR3943/HJRES98 as fully representative without checking scale | Was live until the broader sample was run | High if unaddressed | Ran systemic counts (1,001/2,657/176/2,215 untagged rows matching the cited phrases) and two 10–12 bill samples confirming the same shape recurs, not isolated to the ticket's two picks |
| Missing that some "no passage action" bills might legitimately still be scoreable via a non-`passage` real-vote path (e.g. `veto-override-failure`, a Senate-only concurrence) | Low — checked full classification breakdown per sampled bill, not just presence/absence of `passage` | Medium | Classification breakdown was pulled per bill (not just a boolean), and HJRES98's own veto-override case (a real vote with no tag at all) is called out explicitly as the harder, non-`passage` case |

**Prerequisites:** `DATABASE_URL` exported via `source activate.sh` (unpiped, per the known footgun
in `OPEN-59-architecture-assessment-20260812.md`); confirmed pointing at the `:5433/openstates`
replica, not `cams` or this checkout's separate `openstates_dev` DB.

**Tech debt created:** None in this repo — this is read-only diagnostic work producing a
recommendation document. If the BROKER follow-up ticket proceeds, its own migration/rule work is
`ddp-broker-py`'s tech debt to track, not this repo's.

## Root-Cause Hypothesis for the BROKER Follow-up Ticket

Based on the diagnosis above, the recommended root-cause framing for a `ddp-broker-py`/BROKER
ticket (not created by this assessment — see Next Step) is:

**`motion_eligibility.py`'s action-matching/disambiguation step selects a candidate action for a
bill's up-or-down vote without requiring that candidate to (a) carry a real vote-outcome
classification tag, or (b) itself contain a countable numeric tally.** Congress's action stream is
45.5% untagged locally, and within that untagged pool, procedural narration text (`"POSTPONED
PROCEEDINGS..."`, `"...asked unanimous consent that..."`) is textually adjacent to, and shares
vote-related vocabulary with (`"yeas and nays"`, `"vote"`), the real tally text — but frequently
contains zero digits itself. Two concrete, distinct failure shapes, both confirmed on real,
verified bills:

1. **No real vote exists anywhere on the bill** (HR3943 and 7/12 sampled siblings) — the bill only
   ever had a committee-level markup/substitute "Voice Vote," never a floor vote — yet gets scored
   as if that committee action were a real up-or-down vote. Fix direction: a scoreable action must
   have either a real vote-outcome classification tag (`passage`, `veto-override-failure`, etc.) or
   contain an actual numeric tally matching the jurisdiction's `tally_pattern` — committee-level
   procedural actions with neither should never be eligible, regardless of keyword match.
2. **A real vote exists, but an adjacent untagged narration row gets matched instead** (HJRES98 and
   7/10 sampled siblings) — e.g., a real, digit-bearing `passage` vote or untagged-but-numeric
   veto-override tally sits within a few action-orders of a textually similar but digit-free
   "postponed proceedings" narration. Fix direction: when multiple untagged candidates match a
   jurisdiction's vote-related text pattern for the same bill, prefer the candidate that actually
   contains a numeric tally over one that doesn't, rather than matching on procedural phrasing
   alone (or nearest-in-time without a numeric-content check).

Regression-test bill candidates to hand off: **HR3943** (`ocd-bill/ded09748-2c90-45ff-bad8-a128ca12dd6e`,
no real vote anywhere — should never be eligible) and **HJRES98** (`ocd-bill/91847d8e-76ff-4172-9193-f636a11a48f0`,
real veto-override vote at 214-191, untagged, adjacent to a digit-free "postponed proceedings" row
— the correct match is the numeric row, order 4, not order 6).

## Standards Checklist

| Standard | Status | Notes |
|---|---|---|
| OWASP Top 10 | N/A | Read-only diagnostic queries against an internal replica; no user input, no write path |
| Least privilege | Addressed | Read-only `psycopg2` queries only; no `postgres` MCP tool (confirmed footgun in sibling docs); no broker DB credentials requested or used |
| Reproducibility / evidentiary rigor | Addressed | Real bill IDs, full action histories, and systemic counts shown for both sub-patterns, not just the ticket's two invented-sounding-but-real examples |
| Reuse before reinvent | Addressed | Directly reuses OPEN-60/59/62/64's replica-query methodology and notes-doc precedent rather than inventing a new diagnostic approach |
| Verify before assuming | Addressed | Independently ground-truthed both of the ticket's own cited bills against real data before generalizing to a broader sample or accepting the ticket's binary framing |
| Multi-tenancy | N/A | Not a multi-tenant application concern |
| Idempotent migrations | N/A here | No migration work happens in this repo; any `JurisdictionEligibilityConfig` rule change is `ddp-broker-py`'s migration to write |

## Next Step

1. Write up this diagnosis as `notes/open-70-us-congress-eligibility-verification-20260813.md` in
   this family's established format (Context → Method → Result → Conclusion), citing HR3943 and
   HJRES98 plus the broader samples above — mirroring `notes/open-60-us-congress-eligibility-verification-20260812.md`'s
   own handoff structure.
2. Open a BROKER Jira ticket (not done by this assessment — architecture-only per this skill's
   guardrails) using the Root-Cause Hypothesis section above as its description, scoped to
   `motion_eligibility.py`'s action-matching/disambiguation step, with HR3943/HJRES98 as regression
   fixtures. Confirm the exact title/description/labels with you before it's created, since creating
   a new tracked ticket is a visible, shared-system action.
3. This ticket (OPEN-70) should **not** close with "456 was stale, no code change needed" — the
   evidence contradicts that branch of the ticket's own acceptance criteria. Recommend closing
   OPEN-70 itself once the BROKER follow-up is filed and linked, per the ticket's own AC ("If
   root-cause is identified, open a BROKER follow-up ticket for the fix").
