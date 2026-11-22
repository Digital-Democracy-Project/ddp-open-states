# REQUEST (dry run only, not a GO for any write): US Congress votes with no person attached, `backfill-vote-person-resolution.py` dry run (OPEN-611). 2026-11-22 (Mac side, State Specific Handling)

**Ramon, 2026-11-22: "Yes, request test runs".** This covers the **dry run only**. The commit (`mode=commit`) needs his separate go, after he has reviewed the list. **Do not run `mode=commit`.**

## Why
* A stored vote with no person behind it drops silently out of that legislator's page and scorecard.
* The US blanks are votes imported before their member's id reached our people data: the 14 senators elected in 2024, plus Wahab, Blair and Waltz.
* The backfill fills them from the member id the vote already carries. It is an identifier lookup only, never a name match, and it touches only blank rows.
* **Count:** 217 on 11-17. The Mac replica reads **15** today (`--dry-run`: "Would resolve 15 records (0 still unresolvable)"). Most were filled by the 11-22 US re-import (`256541d`).

## The dry run (SYNC-74's trigger)
```
POST /ddp-sync/v1/trigger/vote-person-backfill?mode=dry-run
```
* **Answer:** 202, with `"mode": "dry-run"` and a `run_id`.
* **Report from the job's log:**
  * the run id;
  * the "Would resolve N records (M still unresolvable)" line;
  * every row it would fill: vote, roll call, date, bill, the person it resolves to. This is the "which votes start counting" list for Ramon.

## Scorecard checks to send with the list (read only, on the production broker)
* `validate_scorecards --jurisdiction US --all`, and `validate_scorecards --bills --all`.
* `reconcile_scorecards --jurisdiction US`.
* These are the "before" values; the same checks run again after any commit.
* The Mac side checks a sample of the list against the House and Senate roll calls and assembles the review for Ramon.

## Not authorized
`mode=commit`; any other script or state; any broker change.

Tickets: OPEN-611, SYNC-74. Plan: PLAN-state-specific-handling §8 (scorecard gate).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
