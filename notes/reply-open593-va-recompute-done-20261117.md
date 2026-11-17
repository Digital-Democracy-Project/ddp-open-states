# Reply to 1fc0d674 step 6: Virginia recompute (OPEN-593) committed, run before the 03:00 US run on the user's word

Written 02:49 UTC (date -u at write time). From the production EC2 host.

## Order
The GO says step 6 comes after the 03:00 US run, not before. The user asked for it now ("can we do the Virginia recompute now while we wait on the USA scraper run?"), so I ran it at 02:42-02:49 UTC. The US run had not started. WA (wa-4af1a468d4b1) had finished at about 02:37.

## Gates (core 44c3b8dc, revision 65, throwaway worktree on PYTHONPATH)
- Export of Virginia's stored comparisons: 25,607 rows, md5 0460d951c9c267093ffb53c05a64974f, mode 600, /home/bitnami/ops/step-us-flip-20261117/va-593-before.csv.
- Dry run 02:42:17-02:45:03: 4,413 bills checked, unchanged 20,844, corrected 4,763 (inside 4,600-4,950, same as the Mac replica), nulled 0, 0 errors; is_bill_version changed 0, not_a_version 1,828; diff_baseline_id changed 5,016, cleared 0.
- Commit 02:45:34-02:48:27, exit 0: same numbers (corrected 4,763, nulled 0, baseline changed 5,016). Change list va-593-commit.csv, 5,016 rows.
- Second dry run 02:48:27-02:49:19: corrected 0, nulled 0, unchanged 25,607, changed 0, cleared 0.

## One difference from the GO's command
The GO says `--commit --expect <count>`. The tool refuses: "--expect goes with --baseline-only" (it stopped at argument parsing at 02:45:18, nothing written). I committed without `--expect`; the dry run three minutes earlier was the only count guard. Please fix the GO text for next time.

Not done: the broker's refresh_bill_version_order (waits for BROKER-489), no other state touched. Step 7 (ga/nv/or) still needs the user's go.
