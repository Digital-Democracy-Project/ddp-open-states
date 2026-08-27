# OPEN-175 — FL: the decision on the 182 duplicate tally-only motions

**2026-08-26.** A decision memo. Nothing was deleted, nothing was written to the broker database,
and no live requests were made.

**Recommendation: do not delete. Re-sync instead, and fix the voter resolution first.**

The case rests on two things the ticket did not have: **its central factual claim about
`eligible_for_scorecard` is wrong for 71 of the 223 rows**, and **the 41 "residuals" are not a
separate mystery but duplicates whose twin is short exactly one voter** — a live defect that will
move rows between the two cohorts once fixed. Deciding now means deciding twice.

---

## What reproduces, and what does not

Every headline number in OPEN-171/OPEN-175 reproduces exactly. I re-derived the predicate from
`remediate_duplicate_tally_motions.py` itself rather than trusting the summary:

| measure | ticket | measured |
|---|---|---|
| FL motions carrying a YEAS/NAYS tally in their own text | 223 | **223** |
| ...with zero attached votes | 223 | **223** |
| ...with a same-bill, same-date, exact-tally twin | 182 | **182** |
| residuals | 41 | **41** |
| voice-vote stand-ins | 152 | **152** |

One thing does not reproduce, and it is the load-bearing claim of the correction section.

---

## Correction: they are not all `eligible_for_scorecard = false`

> *"All 223 zero-voter tally motions carry `eligible_for_scorecard = false`. Not null — false."*

Measured:

| `eligible_for_scorecard` | `is_voice_vote` | `is_passage` | count |
|---|---|---|---|
| **false** | true | true | **152** |
| **NULL** | false | true | **71** |

**71 of the 223 are NULL.** The distinction matters exactly as much as the ticket says it does,
because it says so while getting it the wrong way round: the argument was that both scorecard
builders "resolve the scored motion through that field", so all 223 are excluded *by
construction*. For 71 of them, the field carries no verdict to resolve.

### Are the 71 nevertheless excluded? Yes — but not by that field

`scorecard_views_v2._is_really_eligible()` is deliberately **not** a bare
`filter(eligible_for_scorecard=True)`; its own docstring explains that such a filter would wrongly
treat NULL as ineligible. So NULL falls through to a fallback:

```python
if motion.eligible_for_scorecard is not None:
    return motion.eligible_for_scorecard
if not _is_passage_motion(motion):
    return False
return _recorded_vote_count(motion) > 0
```

All 71 are `is_passage = True`, so they clear the first gate. They are excluded **only** by the
final line — having zero recorded votes.

So the ticket's conclusion survives — nothing reaches a scorecard — but the reason is different
for a third of the rows.

**Stated precisely, and no more strongly than the evidence allows:** those 71 are excluded solely
by the zero-recorded-votes condition, having already passed the `is_passage` gate. That guard was
added for an unrelated purpose (a VA documentation motion carrying `is_passage=True` with no real
vote, 2026-08-10) and its own comment describes it as narrowing "the degraded fallback path".

What that does **not** establish: that these rows are at any real risk of being scored. The guard
is deliberate, current production behaviour, and nothing suggests it is going away. Nor have I
shown what a scorecard would do with an eligible motion that has zero voters, so "one guard away"
describes the distance, not a likelihood.

The honest weight of it is this: the ticket rests its "inert data" verdict on a property (`false`)
that a third of the rows do not have, and their actual exclusion depends on a line written for a
different problem. That is a reason to give them an explicit verdict. It is not, on its own, a
reason to delete them.

---

## How the cohorts actually overlap

Everything below turns on this, and the totals alone hide it:

| | `eligible=false` (all voice votes) | `eligible=NULL` (all non-voice) | total |
|---|---|---|---|
| **182 with an exact same-date twin** — what the command deletes | 147 | **35** | 182 |
| **41 residuals** — what it leaves behind | 5 | **36** | 41 |
| total | 152 | 71 | 223 |

So the deletion would remove 35 of the 71 verdict-less rows by removing the rows, and leave the
other **36** — which are precisely the ones that need something else done to them.

## The finding that reframes it: the 41 residuals are one dropped voter away

The ticket asks for "a decision on the 41 residuals — vote-bearing siblings but no exact
same-date tally match, possibly the same off-by-one class as OPEN-94."

**That guess is exactly right, and it is now measured.** Of the 41:

| | count | shape |
|---|---|---|
| not voice votes, `eligible` NULL | **36** | a same-date sibling exists, tally differs |
| voice votes, `eligible` false | 3 | a same-date sibling exists |
| voice votes, `eligible` false | 2 | no same-date vote-bearing sibling at all |

For all **36**, comparing the motion's own tally text against its nearest same-date sibling's
attached votes:

| sibling short by | motions |
|---|---|
| exactly 1 yes | **34** |
| exactly 1 no | **2** |
| anything else | **0** |

**Thirty-six for thirty-six, off by exactly one.** These are not near-misses of an imprecise
predicate. They are duplicates whose twin is short a single voter — which is precisely the
OPEN-94 / OPEN-174 defect, in Florida rather than Michigan. Florida carries **3,369** unresolved
person-vote rows across 43 distinct names, led by `Valdés` (914), `Cassel` (914), `Garcia` (469)
and `Rayner-Goolsby` (466) — diacritics and hyphenated surnames, the same family of failure as
Michigan's `Myers-Phillips` and `O’Neal`.

**A correction to an earlier draft of this memo.** It argued that deleting the 182 would destroy
the evidence the residuals carry. That is wrong, and the cross-tab above shows why: the 41
residuals are by definition the rows *without* an exact twin, so the command does not touch them.
They would survive the deletion intact. The argument was reviewed, and it did not hold.

What the finding actually changes is subtler, and it is about sequencing rather than evidence.

**The 182/41 partition is not a stable property of the data.** It is a snapshot of which rows
currently have an exact-tally twin — and "exact" is measured against sibling votes that are
missing a voter. Repair Florida's voter resolution and 36 of the 41 residuals gain their missing
vote, their sibling's tally becomes exact, and they *become* deletable by the same predicate.

That turns one decision into two if taken in the wrong order:

- **Delete now** → 182 rows go, 41 remain, 36 of them still verdict-less. Then fix the voter
  resolution, watch 36 rows become exact twins, and hold the same conversation again about them.
- **Fix first** → the population settles at ~218 exact twins and ~5 genuine residuals, and one
  decision covers all of it.

Neither order loses evidence. The second is simply one decision instead of two, taken on a
population that has stopped moving.

---

## The rest of the "for deleting" case, checked

**"They will otherwise be re-reported forever."** True, and it already cost one wrong ticket. But
`report_unmatched_voters` (PR #350) now reports zero-voter motions separately from tally
mismatches, specifically so this cannot be misread again — the ticket says so itself. The
recurring cost is largely already paid down.

**"They double-count if anything ever tallies motions per bill without filtering on
eligibility."** True and unchanged. But this is an argument for giving all 223 an explicit
verdict, which is what the re-sync below does, not specifically for deleting them.

**One fact neither column mentions: all 223 are frozen.**

```
eligible   count   first_created   last_created   first_updated   last_updated
false        152      2026-03-05     2026-04-30      2026-03-05      2026-04-30
NULL          71      2026-04-30     2026-04-30      2026-04-30      2026-04-30
```

Nothing has touched any of them since **2026-04-30**. They are not being re-minted on every sync;
they are stale rows from before `eligible_for_scorecard` was computed at ingestion (BROKER-47).
That is why 71 have no verdict — not because the computation returns None for them, but because
it has never run on them.

This matters because it makes the non-destructive option actually work.

---

## Why the third option is the right one

The ticket raises BROKER-86's `_retire_superseded_motions` (PR #349) and sets it aside: *"It does
not currently cover these rows: it excludes `is_voice_vote=True` motions, which 152 of the 223
are."*

True — and the complement is the point. **The 152 it excludes are exactly the 152 that already
carry an explicit `false`.** The rows still lacking a verdict are the 71, and every one of them
is `is_voice_vote = False` — precisely the class `_retire_superseded_motions` does cover:

```python
superseded = (
    Motion.objects.filter(bill=bill_record)
    .exclude(openstates_id__in=comparable_ids)
    .exclude(eligible_for_scorecard=False)
    .exclude(is_voice_vote=True)
)
retired = superseded.update(eligible_for_scorecard=False)
```

So the non-destructive path needs no extension at all. A sync of the affected Florida bills should
either re-produce these motions as candidates and give them a real computed verdict, or not
produce them — in which case they are retired to `eligible_for_scorecard = False` automatically,
by the code path that already runs on every sync.

**What I verified and what I did not.** I verified that the predicate *applies* to all 71 rows:
they are non-voice, not already false, and therefore not excluded by either `.exclude()` clause. I
did **not** verify that a sync run will actually reach these particular historical bills — that
depends on which bills a sync pass visits, which I have not traced. So this is the right mechanism
rather than a guaranteed outcome, and step 3 below should be checked by measurement rather than
assumed. If a re-sync turns out not to revisit them, that is worth knowing on its own: it would
mean stale motions can sit indefinitely with no verdict, which is a more general problem than
these 71 rows.

That path resolves the verdict question without an irreversible one-off deletion, and it matches
the standing preference against correcting production data with commands that delete rows.

---

## Recommendation

1. **Do not run `remediate_duplicate_tally_motions --apply`.** Not because the command is unsafe
   — it is careful, and I reviewed it: dry-run by default, refuses `--apply` without a
   jurisdiction, re-derives its predicate inside the transaction under `select_for_update()`,
   hard-asserts against deleting any motion with votes, prints every deleted id, and caps a
   runaway match. The objection is to deleting these rows at all, right now.

2. **Fix Florida's voter resolution first** (the OPEN-174 defect in FL guise). If the 36
   residuals' siblings gain their missing voter, those 36 become exact-tally twins and stop being
   residuals — the population resolves itself rather than being cut down to a remainder.

3. **Then re-sync the affected Florida bills** and let `_retire_superseded_motions` give the 71
   an explicit verdict.

4. **Then re-measure**, and only consider deletion for whatever is still unexplained. On this
   evidence that should be at most the 5 voice-vote residuals, and 2 of those have no same-date
   sibling at all — which is a different question again, and a small one.

### The durable policy this implies, stated plainly

**Retirement is the intended end state, not a step on the way to deletion.** A motion marked
`eligible_for_scorecard = False` is excluded everywhere that matters, keeps its lineage, and costs
a row. Once all 223 carry an explicit verdict there is no remaining harm to fix, so deletion would
be tidying rather than correcting.

The exception worth naming in advance, so this is not reopened from scratch: delete only a row
that is **both** provably redundant **and** actively misleading somewhere the verdict does not
reach. Nothing in this population currently meets that bar.

### What to check after each step, per cohort

Aggregate totals will hide partial processing here, so check the cohorts rather than the headline:

- **After the voter fix:** the 36 off-by-one residuals should have moved into the exact-twin set.
  Expect roughly `218 twins / 5 residuals`, not merely "fewer residuals".
- **After the re-sync:** all **71** previously-NULL rows should carry an explicit `true` or
  `false` — checked as a count of NULLs going to zero, split by whether the row was one of the 35
  inside the 182 or one of the 36 residuals, since those reach the retirement path by different
  routes.
- **Throughout:** the count of FL motions with a tally in their text and zero attached votes
  should not *rise*. If it does, something is re-minting them and the staleness finding above is
  wrong.

**If you want them gone anyway**, the command is sound and the case for it is real. The cost is
not lost evidence — the 41 residuals survive it — but a second conversation later, when the voter
fix turns 36 of them into exact twins and the same question comes back for them.

## Review responses

**Acted on, and it was a real error.** The reviewer pointed out that the 41 residuals are by
definition outside the 182, so deleting the 182 cannot erase them — which was the central claim of
the first draft. It was wrong. The section is rewritten: the argument is now about sequencing (one
decision on a settled population rather than two on a moving one), and the memo says plainly that
neither order loses evidence. The cross-tab that makes the overlap visible is new, and it is the
thing whose absence let the mistake through.

Also narrowed the "one guard away" claim to what the code actually shows, added the durable-policy
statement (retirement is the end state, not a stage before deletion), added cohort-specific
acceptance checks, and marked the re-sync's reach as verified-in-principle but not traced.

**Considered and not acted on.** *"Justify whether the exact 182 must wait for the voter fix at
all."* They need not, and the memo no longer implies a hard dependency — the sequencing argument
is about avoiding a repeat decision, not a blocker. Splitting them into two independently-decided
cohorts would be defensible; it just costs the thing the sequencing buys.

---

## Reproducing any of this

The full predicate, as SQL rather than through the management command (read-only, and it does not
require the broker container):

```sql
WITH fl AS (
  SELECT m.id, m.bill_id, m.text, m.is_voice_vote, m.is_passage, m.eligible_for_scorecard,
         (m.date AT TIME ZONE 'UTC')::date AS d
  FROM common_motion m
  JOIN common_bill b ON m.bill_id = b.id
  JOIN common_legislativesession ls ON b.session_id = ls.id
  JOIN common_jurisdiction j ON ls.jurisdiction_id = j.id
  WHERE j.iso2 = 'FL'
), counts AS (
  SELECT motion_id,
         sum(CASE WHEN lower(choice) IN ('yes','yea','y','1','aye') THEN 1 ELSE 0 END) AS yes,
         sum(CASE WHEN lower(choice) IN ('no','nay','n','0')        THEN 1 ELSE 0 END) AS no,
         count(*) AS total
  FROM common_vote GROUP BY 1
), zero_tallied AS (
  SELECT fl.*,
         (substring(fl.text from '(?i)YEAS?\s+(\d+)\s*[,;]?\s*NAYS?\s+\d+'))::int AS t_yes,
         (substring(fl.text from '(?i)YEAS?\s+\d+\s*[,;]?\s*NAYS?\s+(\d+)'))::int AS t_no
  FROM fl LEFT JOIN counts c ON c.motion_id = fl.id
  WHERE fl.text ~* 'YEAS?\s+\d+\s*[,;]?\s*NAYS?\s+\d+' AND COALESCE(c.total, 0) = 0
)
SELECT count(*) AS total,
       count(*) FILTER (WHERE EXISTS (
         SELECT 1 FROM fl o JOIN counts c2 ON c2.motion_id = o.id
         WHERE o.bill_id = zero_tallied.bill_id AND o.d = zero_tallied.d
           AND o.id <> zero_tallied.id
           AND c2.yes = zero_tallied.t_yes AND c2.no = zero_tallied.t_no)) AS deletable,
       count(*) FILTER (WHERE eligible_for_scorecard IS NULL) AS no_verdict
FROM zero_tallied;
```

Expected: `223 | 182 | 71`.

The regex is copied from `_TALLY_RE` in the management command and the yes/no spellings from its
`_YES`/`_NO` sets, so this selects the same rows the command would.

---

## Acceptance criteria

- [x] **A decision recorded, with the reason** — do not delete; re-sync. Reasons above.
- [ ] **If deleting: run the command and keep the audit trail** — not done, deliberately.
- [x] **The remaining count explained rather than merely smaller** — this is why the
      recommendation is sequenced fix → re-sync → re-measure, rather than delete → re-measure.
- [x] **A decision on the 41 residuals** — 36 are off-by-one duplicates caused by a dropped
      voter (measured, 36/36), 3 are voice votes with a same-date sibling, 2 are voice votes with
      none. They should be left in place until the voter-resolution defect is fixed, at which
      point 36 of them should resolve themselves.

---

## Reference

- **OPEN-171** — root cause and tooling, closed
- **OPEN-174** — the same dropped-voter defect in Michigan; the FL residuals are its local form
- **OPEN-95** — a second pending deletion of the same kind (53 Utah rows), also awaiting a call
- `ddp-broker-py` PR #348 — `remediate_duplicate_tally_motions`
- `ddp-broker-py` PR #349 — BROKER-86's `_retire_superseded_motions`, the option recommended here
- `apps/ddp-broker/scorecard/scorecard_views_v2.py` — `_is_really_eligible()` and the NULL fallback
