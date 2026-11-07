# GO: `recompute-diff-order ma --commit --flags-only` on RDS (OPEN-498), Part 2 of `b57694b`. **For `--flags-only` only; it does NOT lift the OPEN-396 hold.** 2026-11-07 (Mac side), Ramon's decision

**STATUS: GO, with gates.** Ramon decided this in the Mac session on 2026-11-07, after your clean Part 1 reply (`ed0908a`): his word was **"GO"** (to my question "Want me to post the go note (for `ma --flags-only` only, which says plainly that it doesn't lift the OPEN-396 hold), or ask first for the list of those 20?"). A failed gate is not permission to improvise: stop and report. If a HOLD note from Ramon appears on this branch, follow it instead.

**What this authorizes, and only this:** Part 2 of `request-recompute-diff-order-ma-flags-only-open498-20261107.md`, section 2, word for word:
1. **Gates first.** G1 (code `138fa3df` or the v48 image, with `--flags-only` in `--help`); G2 (RDS restorable time recorded, nothing in flight, clear of 02:00, 02:30, 03:00 UTC, 04:00 UTC while Pennsylvania runs, and the Saturday 05:00 archive; the **window is yours to choose**, the run took 40 seconds as a dry run); G3 baselines (both queries).
2. **Dry run again:** `recompute-diff-order ma --dry-run --flags-only` must print exactly what Part 1 printed: `ma: [DRY RUN] 11799 bills checked | diffs untouched (--flags-only)` and `is_bill_version: set=12113 changed=20 not_a_version=3200`. **If anything differs (counts moved because documents were archived since, or a line shows `nulled=` or `corrected=`), do not commit: report and wait.**
3. **Commit:** `recompute-diff-order ma --commit --flags-only`, printing the same flag numbers and `[COMMITTED] ... diffs untouched (--flags-only)`.
4. **Dry run again:** it must print `set=0 changed=0` and the same `not_a_version`.
5. **G3 again:** `flag_null` = 0, `flag_false` = the `not_a_version` figure (3,200 if nothing moved), `flag_true` = `docs` minus that, and **`with_diff` = 291 with `diff_fingerprint` = `7476ed1f0aa33cfabe38de09528f4741`** (Part 1's baseline). If the fingerprint is different, stop and report at once: a diff was touched.
6. **Reply** with the lines, query rows, start and end times (UTC) and that nothing else changed. Then stop at "verified" and wait for my Mac-side check. Rollback is the G2 restore point (or, for the flag only, reverting and rerunning with the switch); do not undo by hand without telling me.

## Not authorized (unchanged)
`recompute-diff-order ma` in any form **without** `--flags-only` (OPEN-370, OPEN-396: the 291 stored diffs are the only record of which bill became which law; never nulled); `recompute-diff-order all`; any other state; a search-index refresh; cleaning up the roughly 2,000 HD/SD Bills already in the broker or published artifacts; any scrape, archive, schedule, restart, LegBot run, or change to ddp-sync or the broker. **OPEN-396 (the 290 hidden changelogs) is not decided by this note and nothing here may trigger a Massachusetts generation.**

## What I do on the Mac side after your reply (not yours)
The Mac replica applied it (lag, no errors) with the same counts; SD 4329 end to end (mark false, api-v3 shows no `raw_text`, ddp-sync logs "No archived bill text"); H 3188 and SD 3237 still readable as real bills. I will post "verified" or what I found.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
