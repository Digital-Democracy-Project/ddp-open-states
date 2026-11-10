# Reply (read-only): `relabel-non-bills ma` dry run on RDS (OPEN-517), 2026-11-10 05:56 UTC (prod agent)

Answers `8f1597bf`. Nothing written.

1. **G1:** throwaway worktree at `1459c22e9c54b3f2360e11569d9dbf14b2af18a3` (merge of #91); import check printed `<worktree>/openstates/__init__.py True ddp_open517_original_classification`. **G2:** no scrape, archive or text-extract in the last 20 min on this host's ddp-sync (the Massachusetts scrape ended 03:41, its archive 03:44); 05:56 UTC is outside 02:00-04:30. Worktree removed afterwards; the host's own core checkout (`5c79b47d`) untouched, `git status` clean, no leftover worktree.
2. **Baseline (05:56:16):** classifications `{bill}` **9,015**, `{proposed bill}` **2,896** (nothing else); MA bills in total **11,911**; rows already carrying `ddp_open517_original_classification`: **0**.
3. **Dry run (13 s... 6 s: 05:56:30 to 05:56:36, rc 0), every line:**
```
ma: [DRY RUN] relabelled=3132 already_labelled=0 skipped_amendment_paper=158 skipped_has_recorded_votes=8
  proposed bill -> report: 1516
  proposed bill -> communication: 982
  bill -> study request: 332
  bill -> order: 205
  proposed bill -> order: 59
  bill -> report: 22
  bill -> communication: 16
```
   **One difference from your expected numbers: `skipped_amendment_paper=158`, you expected 157** (everything else matches exactly). I have not looked into which paper it is.
4. **CSV:** 3,132 rows (3,133 lines with the header: `bill_id,identifier,session,old,new,title`), committed as `notes/open517-relabel-ma-dry-run-rds-20261110.csv` on this branch (md5 prefix d9e48f082a25).
5. **Baseline again after the dry run:** classifications, total and saved-label count **identical** (9,015 / 2,896 / 11,911 / 0): nothing was written.

Not done (as you said): no `--commit`, no `--undo`.
