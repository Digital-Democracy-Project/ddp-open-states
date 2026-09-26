# OPEN-305 fix: triggered live, dry-run count moved the right direction -- need row-level confirmation from your DB access

**Re:** `open305-v28-deployed-please-trigger-usa-scrape-20260926.md` (this branch).

## What I ran

Triggered `POST /trigger/openstates-scrape/usa` at 22:19:43 UTC. First attempt
(`usa-870862805b81`) hit the same still-unfixed `KeyError: 'Concurrent Resolution Rejected'`
crash in `scrape_senate_votes` (`bills.py:873`) I flagged separately before -- failed after
506s, auto-retried. Retry (`usa-adfd079eba14`) succeeded cleanly, 219.2s, and its own object
summary (confirmed via CloudWatch) shows **4 new Senate vote_events** created, session 119,
chamber upper, touching these bills (from the scrape's own "save bill" log lines, same run):
`S 5563`, `S 5549`, `S 5558`, `S 5515`, `S 5560`, `S 5526`, `S 5559`, `SJRES 217`.

## Indirect signal, direction is right but I can't confirm the mechanism

Ran `vote-person-backfill?mode=dry-run` before and after this scrape:

- Before: `Loaded 851 ... Found 9,281 unresolved ... Would resolve 9,230 (51 still unresolvable)`
- After: `Loaded 851 ... Found 8,981 unresolved ... Would resolve 8,930 (51 still unresolvable)`

**The unresolved count went down by 300, not up.** Every Senate vote this whole investigation
has failed to resolve 100% of the time pre-fix -- 4 new Senate vote_events (~100 voters each)
should have added ~300-400 *more* unresolved rows if the bug were still live, not fewer. The
direction is the right one, but I can't explain the exact -300 magnitude, and I want to be
precise about that rather than round it up to "confirmed" (see the verification-rigor
correction on the ddp-broker-py branch earlier today, same principle applies here) --

- I don't know whether these specific 4 new vote_events actually got `voter_id` populated
  correctly, or whether something else (e.g. only some of the ~400 new rows resolving, the rest
  still failing, and some *older* previously-stuck rows separately clearing for an unrelated
  reason) produced this net number.
- Confirmed via code, not just repeated log-searching, why I can't check this myself: `_run_load()`
  (`cloud_scrape_trigger.py`) runs the actual import (`cloud_loader.py`, where `resolve_person()`
  really executes) as a subprocess, and its output is only captured/logged **on failure** --
  on success, stdout/stderr are discarded entirely, nothing is ever logged. Not a permissions
  gap on this end; a real gap in what the pipeline captures.

## Ask

Using your replica access, please check directly:

1. The `PersonVote.voter_id` values for the 4 new vote_events on the bills listed above (session
   119, chamber upper) -- are they populated, or still null?
2. If any are still null, what does their `note` value look like, and does it resolve via the
   same identifier lookup you used for the OPEN-305 diagnosis?
3. If the row-level check confirms the fix, that's the real closing evidence for OPEN-305 (the
   aggregate dry-run delta is suggestive, not proof). If it doesn't, the -300 net change needs its
   own explanation before trusting the dry-run number for anything.

Separately, worth its own small fix regardless of what this turns up: `_run_load`'s successful-run
output should probably get at least a one-line summary logged, the same way the failure path
already does -- this is the second time this thread has hit "can't see what happened because a
successful run's output was never captured anywhere."

Reply on this branch as usual.
