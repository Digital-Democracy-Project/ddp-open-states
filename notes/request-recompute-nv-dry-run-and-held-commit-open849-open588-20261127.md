# REQUEST (not a GO): **Nevada's `recompute-diff-order nv`: dry run now, commit held until a go note. It is the last data step before Nevada's go-live pull request.** 2026-11-27 (Mac side, Onboard New States)

## What I need from you
1. **Prove the rule is present first.** Run from the image or a throwaway worktree of DDP openstates-core main at **`1e13837` or newer** (the commit v99 recorded; it contains core #164, OPEN-849, `openstates/ddp_states/nv.py`). Print that `nv.py` exists and report the commit. Stop if it is older.
2. **Gates before any write:** nothing in flight for NV (no ddp-sync NV job in the last 10 to 12 minutes; NV's weekly slot is Saturday 12:00 UTC, so not 11:50 to 14:00 UTC Saturday); not Sunday from 02:00 UTC; record "now" as the restore point.
3. **Baseline (read-only, Mac replica, for comparison):** NV documents 288; `is_bill_version` true 288, false 0; documents named `^Amendment` 26, all 26 still `is_bill_version` true, all 26 with a stored comparison (`diff_from_previous_version`) and a baseline; 49 NV documents have a stored comparison in all.
4. **Dry run:** `recompute-diff-order nv --dry-run`. Expected (your own measurement of 11-25, reply `36bcd77`): 217 bills, **corrected 32, nulled 26**, `is_bill_version` changed **26** (`not_a_version` 26), baselines **set 22 / changed 10 / cleared 26**, 58 documents. Report the exact lines. **Do not commit.**
5. **Commit part: HOLDS until a go note** from Ramon (his own words, in the note). Then: backup of the stored NV comparisons first, `--commit` with `--list` kept for the undo, then a second dry run that must read 0 changes. Post the lines.

## Not authorized
Any other state; `all`; a scrape or re-import; any manifest, routing, LegBot or scorecard switch; a ddp-sync restart; any commit before a go note.

## What I check on the Mac side afterwards
NV documents unchanged in number (288); the 26 `^Amendment` documents `is_bill_version` false with no stored comparison; the other 262 true; the 10 "As Enrolled" baselines moved to their last reprint; other states' counts unchanged; Stage 3 gates for NV still 4/5 passed (0 failures). Then I post `reply-verified-` and the go-live manifest PR can be built.

Tickets: OPEN-849 (core #164), OPEN-588 (Nevada go-live), OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
