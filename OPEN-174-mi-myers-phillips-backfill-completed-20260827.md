# MI Myers-Phillips voter backfill: record of what ran, 2026-08-27

Record of the OPEN-174 backfill against the DDP OpenStates replica's
`opencivicdata_personvote` table, run for real on 2026-08-27. Companion to
`vote-misattribution-backfills-completed-20260819.md`, which covers a different
defect class: those rows pointed at the **wrong** person, these pointed at
**nobody**.

**PR:** [#183](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/183) (merged)
**Script:** `fix-open174-mi-myers-phillips-voter-backfill.py`

## What was wrong

The Michigan House journal writes Rep. Tonya Myers Phillips as **Myers-Phillips**.
The `openstates/people` roster records her as `Tonya Phillips` / `family_name:
Phillips`, having dropped the "Myers". `resolve_person()` matches a bare journal
name against `name`, `other_names` and `family_name` only, so it matched nothing
and every vote she cast imported with `voter_id = NULL` — **680 rows between
2025-01-08 and 2026-07-03**, the largest unmatched name in Michigan.

Her own roster record carries the correction in three independent places: her
legislative email (`tonyamyersphillips@house.mi.gov`), her photo filename
(`Tonya_Myers_Phillips_*.png`), and every Ballotpedia / Wikipedia / House
Democrats URL under `sources`. An existing `other_names` entry already read
`T.M. Phillips` — the roster half-knowing the middle name it dropped.

## Why the data needed a backfill at all

`voter_id` is resolved at **vote-import** time, so correcting the roster does not
reach in and repair rows already stored. Re-importing would, and the importer is
safe for it (`PersonVote` sits on `_update_related()`'s wipe-and-recreate path, so
a re-import replaces rather than merges) — but `run-scrape.sh`'s `do_scrape()`
wipes `$SCRAPED_DATA_DIR/$STATE` at the start of every run, so only the most
recent run's bills are on disk. Covering eighteen months would have meant a full
~3,800-request, 7–8 hour Michigan re-scrape against the fleet's most WAF-sensitive
site, for a column whose correct value was already known and unambiguous.

## Result

| Change | Rows |
|---|---|
| `Myers-Phillips`, NULL → `ocd-person/787d9bda-d4dd-47fe-aaf0-348c505211e4` | **677** |
| Left NULL deliberately (surplus duplicates, see below) | 3 |

| Verification | Before | After |
|---|---|---|
| `Myers-Phillips` rows unresolved | 680 | **3** |
| Distinct people her rows point at | 0 | **1** |
| Michigan unresolved `personvote` rows overall | 1,427 | **747** |
| Michigan `personvote` rows total | 91,524 | **91,524** |
| Roll calls counting her twice | 0 | **0** |

## How the script decided, per row

Modelled on `fix-open116-blank-voter-id-same-surname-backfill.py` rather than a
new shape. For every affected row it re-derives from `opencivicdata_membership`
directly who held a Michigan **lower**-chamber seat under `family_name = Phillips`
**on that vote's own date** — not "currently", not `resolve_person()`'s
`current_role` tie-break — requires exactly one candidate, and requires that
candidate to be the identity OPEN-174 verified. All 680 rows passed across 109
distinct dates: zero ambiguous, zero resolving to anyone unexpected.

Measured before the run, and the reason no row was expected to be ambiguous: she
is the **only** Michigan legislator in any chamber whose name or family name
contains "Phillips" or "Myers", all 680 rows are lower-chamber rows, and every
vote date falls inside her open-ended term starting 2025-01-01.

## The mistake, and the correction

**The first production run created a defect it then had to undo, and the guard in
the merged script exists because of it — not as precaution.**

Three vote events dated 2026-07-03 each carried **two identical blank
`Myers-Phillips` rows**. Both were NULL, so nothing double-counted her. Filling
both made each roll call count her twice.

`DUPLICATE_CHECK_SQL` could not catch this, and the reason generalises: it asks
whether a row for this person *already* exists, which is false for **both**
members of a blank pair. The batch has to remember what it has queued within the
run, which the script now does (`queued`, a set of `(vote_event_id, person_id)`).

The three surplus rows were reverted to NULL within minutes, keeping exactly one
resolved row per roll call. Re-running the script is now a clean no-op that
reports those three as would-duplicate:

```
Found 3 blank-voter_id rows named 'Myers-Phillips' in MI lower.
  fillable                 : 0
  would duplicate a voter   : 3
```

## What this surfaced: OPEN-179

Investigating those three roll calls found a pre-existing defect the backfill
made visible rather than caused. They are **parsed twice** — ~214 voter rows for
~107 distinct people each — and **13 of the duplicate pairs disagree on how the
person voted**, so the replica holds two contradictory answers with nothing
marking either as suspect.

Ruled out before filing: nothing was absorbed from a neighbouring roll call (the
sequence runs #288 → #327 with no gaps and every neighbour holds normal counts),
and no two source documents were merged (all three cite exactly one source,
`2026-HJ-07-03-056.htm`). The doubling happens inside the parse of a single
journal page, and the second pass is not a copy of the first — distinct-voter
counts reach 115 and 109 against a 110-seat chamber.

Same journal page and date as OPEN-174 §5's merged-surname defect
(`Theis Victory`, `Bellino Bumstead`). Filed as **OPEN-179**, whose first
criterion is whether those are one bug or two.

## Reverting

The 680 affected row ids were captured before the write. Revert is:

```sql
UPDATE opencivicdata_personvote SET voter_id = NULL WHERE id IN (…);
```

## What this did *not* fix

The **broker** holds its own `common_vote` rows and has not re-synced, so
`report_unmatched_voters --jurisdiction MI` still reports 32 motions / 30 short
by exactly one. That is the two-layer distinction OPEN-174 turned on, not a
failure of the backfill.

It does, though, unblock the broker without waiting for upstream.
`_process_bill_votes()` falls back to a UUID lookup when the name match fails,
but only `if not representative_record and vote_data.voter` — and before this
backfill `voter` was null, so the fallback could never fire. It can now, and the
row it finds is the right one: broker `Representative` 1704 already carries
`openstates_id = 787d9bda-d4dd-47fe-aaf0-348c505211e4`, unique-indexed, so it
resolves to the existing seat rather than creating the second record OPEN-174
forbids.

So the remaining broker work is a **re-sync of the affected Michigan bills**, not
a roster change. (Caveat: the checkout names that column `primary_openstates_id`
while the running database has `openstates_id` — code and deployed image differ.
The dedupe mechanism holds either way, but confirm against what is deployed.)

The durable fix is still upstream: **[openstates/people#4036](https://github.com/openstates/people/pull/4036)**,
open at the time of writing. It is now the durability fix rather than the repair.
