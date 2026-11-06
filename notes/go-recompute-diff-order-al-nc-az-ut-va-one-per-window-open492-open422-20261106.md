# GO: `recompute-diff-order --commit` for Alabama, North Carolina, Arizona, Utah and Virginia, **one state per window, in this order, each only after Mac-side verification of the one before** (OPEN-492, OPEN-422; Ramon: "go"). 2026-11-06

This is the GO note for Part 2 of `request-recompute-diff-order-va-ut-al-az-nc-open492-open422-20261106.md` (`7f1c286`), after your Part 1 reply `b8846e1`. Ramon's go was given in the Mac session after he read my summary of your preflight; **I read it as GO for all five states in the order you proposed (smallest first: Alabama, North Carolina, Arizona, Utah, Virginia), one per window, with my check between them, the same pattern as Nebraska then Louisiana.** If you read it differently, ask before committing.

**My independent check of your numbers (Mac replica, same classifier, read-only):** 53,027 documents in the five states, and the not-a-version counts match yours exactly (Alabama 45, North Carolina 54, Arizona 16, Utah 3,170, Virginia 1,828). Every one of those papers already has no stored comparison in all five states, so `nulled=0` is right (Utah included); `with_diff` stays at your baseline (AL 918, NC 3,557, AZ 4,328, UT 4,158, VA 14,927). `corrected=0` is the dry run's own answer; I cannot reproduce it on the Mac.

## What you may do, per state
1. **Gates right before each commit.** Read the RDS latest restorable time again; nothing in flight; no ddp-sync job in the last 10 minutes; a window clear of 02:00, 02:30, 03:00 UTC, Sunday, and **that state's own 05:00 UTC archive day** (yours: Mon fl+ut, Tue az, Wed wa+va, Thu mi+nc, Fri ma, Sat al). Your own go in your session is also needed, as you said.
2. The state's dry run must print **exactly your Part 1 lines** (`corrected=0 nulled=0`, the same `set=` and `not_a_version=`); if it differs even slightly, **do not commit; report and wait.**
3. `recompute-diff-order <st> --commit` printing the same numbers; then `--dry-run` again (must print `corrected=0 nulled=0` and `changed=0`); then the G3 query: **`flag_null` = 0, `flag_false` = the not-a-version count above, `with_diff` unchanged.** Report the lines, query row, start and end times (UTC) and that nothing else changed. Reply file per state: `reply-recompute-diff-order-<state>-committed-20261106.md` (the date you actually run it).
4. **Stop after each state** and wait for my "verified" line on this branch before the next one. If I do not post one, do not continue.

## Not authorized
Any other state; `recompute-diff-order all`; `ma --commit`; rejecting or changing any approved summary (Arizona's 17); a search refresh; any scrape, archive, schedule, restart, LegBot run, or change to ddp-sync or the broker; two states in one window.

## What I do on the Mac side
After each commit: worker running and lag, the same counts on the replica, no unmarked row in that state, then a "verified" note here. After Virginia: the 104-bill re-scan from OPEN-422 and the 22 SYNC-126 bills.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
