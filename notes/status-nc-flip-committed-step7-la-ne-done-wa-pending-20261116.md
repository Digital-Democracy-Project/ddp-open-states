# Status: North Carolina flip COMMITTED (A.2); step 7 Louisiana and Nebraska DONE, Washington on its last steps; step 8 not started. 2026-11-16 05:08 UTC (prod agent)

Answers `a7748386` and `9963ec87`. User's words in session (pop-up, for A.2, because it was a new data change beyond the earlier release steps): **"Yes, commit it"** (after I showed the dry run and said it rewrites the stored action order of those bills). **A.3 (the label) is not done.**

## A. North Carolina
- **Core: `96445eb26d7d4c59c592dadc0261c47d985e6d46`** (the core in v60, in a throwaway worktree on `PYTHONPATH`, **host venv Python 3.9.2**), not core main (`e964183b` has PR #105, a stored-comparison change I did not want to run against production unreleased). Checkout `5f945b01` (nc `newest_first: true`), `--manifest /opt/ddp-open-states/jurisdictions.yaml`, no override. 0 NC ddp-sync activity, 0 running tasks.
- **Dry run 05:05:21-26:** `nc: [DRY RUN] reversed=2343 actions=20035`, `stored dates: newest_first=2327 same_day=16`. **Gate met** (2,320-2,360; no error); the same figures as your Mac replica.
- **Commit `--commit --expect 2343 --list ...` 05:06:46 to 05:07:13, exit 0:** `nc: [COMMITTED] reversed=2343 actions=20035`, same dates line, `latest action fields recomputed and changed: 2291`. **Second dry run: `reversed=0 actions=0 skipped_already_reversed=2343`.**
- **Change list (old and new order per bill, 2,343 rows):** `/home/bitnami/ops/step-nc-20261116/nc_flip_committed_list.csv`, plus the dry-run list and raw outputs in that folder. `--undo --commit` would work inside the hold; not used.
- **A.1 hold / A.4:** nothing scheduled runs NC before **Sunday 11-22 02:00 UTC** and I will not trigger it; no scheduled broker bill-event task exists, so nothing to re-bootstrap.
- **A.3 (label):** ddp-open-states #380 (nc `newest_first: false`) **is not merged** as far as I can see; I have not pulled or rolled anything out. **The label must follow the flip and NC must not scrape before both.** Tell me when #380 is merged and I will pull, run `rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync`, and check that `/ddp/enrollment` shows `newest_first` true for us only. Until then enrollment still says nc true while the stored order is now oldest first; nothing reads it for a scrape before 11-22, but the broker's stage check does read it, so please do not leave it long.

## Step 7 struck words (`9963ec87`), all on core `eec94082b`, host venv, each only on its gate
- **Louisiana: DONE.** Refresh commit 03:26-03:50: `diffs_corrected=980`, 0 skipped, 0 refused; follow-up dry run 0 stale; recompute dry and commit `corrected=0 nulled=0`; second dry run `corrected=0`. Export `la_diffs_before.csv` (10,468 rows, md5 `8306fd8bd07e41998e2b7c58761e5c69`).
- **Nebraska: DONE.** Refresh commit 04:16-04:26: `diffs_corrected=197`, 0 skipped, 0 refused; follow-up 0 stale; recompute `corrected=0 nulled=0`; second dry run 0. Export (3,383 rows, md5 `dd912a33f1d19c6223bf6af5b493b4c8`).
- **Washington: refresh COMMITTED, finishing.** Gate: stale 3,771 (range 3,566-3,787), 0 refused, 0 skipped. Commit 04:02-04:38: `diffs_corrected=1178`. Its follow-up dry run (must show 0 stale) was still running at 05:07, then the recompute (gate `nulled=0`). Export (11,636 rows, md5 `065bc0f8acc080d8395d498a56ae15aa`). Files are in `/home/bitnami/ops/step7-struck-20261116/`.
- **Step 8 (api-v3 #61): NOT started**, after Washington.

## B and C
- **B (Alabama version dates, OPEN-569):** after Alabama's Sunday 11-22 run on v60 has finished its import and archive; nothing to do now. The hold on `recompute-diff-order al` stands.
- **C, owed:** PA's first v60 nightly (04:00 UTC 11-17: the OPEN-574 export line, any "full walk" warning, mode, run time); SYNC-162's first LegBot trigger. **Context for the PA nightly:** this morning's 04:00 run failed on a stale S3 lock from yesterday's killed run (my report `921cfc1` on the ddp-sync branch); the lock has since expired, nothing has been retried, and I have not touched it.

## Separately (broker branch)
The broker deploy `c52e91d2` is live (`bdef7ef1`); the 05:00 scorecard chain started on it normally at 05:00:00 UTC.
