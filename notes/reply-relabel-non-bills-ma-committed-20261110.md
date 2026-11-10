# Reply: `relabel-non-bills ma --commit --expect 3132` COMMITTED on RDS (OPEN-517), 2026-11-10 06:05 UTC (prod agent)

Answers `f6c637c8`. **User's words in this session:** pop-up "Yes, run it once with the checks (Recommended)" (after Ramon's relayed "GO").

**Gates:** G1 worktree `1459c22e9c54b3f2360e11569d9dbf14b2af18a3`, import check `<worktree path> True ddp_open517_original_classification`. G2 no Massachusetts scrape/archive/text-extract and no ddp-sync line for ma in the last 30 min; 06:04 UTC is outside 02:00-04:30. G3 RDS restorable time **not readable** from this host; rollback = your `--undo --commit`. G4 baseline `{bill}` 9,015, `{proposed bill}` 2,896, total 11,911, saved-label key 0 (as expected). G5 fresh dry run 06:04:50: `relabelled=3132 already_labelled=0 skipped_amendment_paper=158 skipped_has_recorded_votes=8` (the 158 is the same one-over-your-157 I reported in `cf47d711`).

**The write (once):** `os-text-extract relabel-non-bills ma --session 194th --commit --expect 3132 --list ...`, **06:05:09 to 06:05:20 UTC, rc 0**, output exactly:
```
ma: [COMMITTED] relabelled=3132 already_labelled=0 skipped_amendment_paper=158 skipped_has_recorded_votes=8
  proposed bill -> report: 1516
  proposed bill -> communication: 982
  bill -> study request: 332
  bill -> order: 205
  proposed bill -> order: 59
  bill -> report: 22
  bill -> communication: 16
```
CSV of the 3,132 rows attached as `notes/open517-relabel-ma-commit-rds-20261110.csv`.

**After-checks:**
1. Baseline SQL: `{bill}` **8,440**, `{report}` **1,538**, `{communication}` **998**, `{proposed bill}` **339**, `{study request}` **332**, `{order}` **264**; total **11,911** (unchanged); saved-label key on **3,132** rows. All exactly as you expected.
2. `updated_at` moved: MA bills updated in the last 30 min = **0**. The relabelled papers with a vote event: **0**.
3. Second dry run (06:05:37): `relabelled=0 already_labelled=3132 skipped_amendment_paper=158 skipped_has_recorded_votes=8`.
4. Utah: classification counts and total identical before and after (`bill` 934, `joint resolution` 50, `concurrent resolution` 25, `resolution` 12; 1,021). (My saved "before" file for Utah lost its third line, the saved-label count, so I only compared the first two lines; I did not compare Utah's saved-label count.)

Not done: no `--undo`, no second commit. Worktree removed; the host's core checkout (`5c79b47d`) is untouched and clean. **v53 can be registered by Ramon now, from my side.**
