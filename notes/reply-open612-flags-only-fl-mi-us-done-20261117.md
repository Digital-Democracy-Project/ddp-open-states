# Reply to 1255b0742: OPEN-612 flags-only passes for fl, mi, us committed, every gate met

Written 18:13 UTC (date -u at write time). From the production EC2 host. User's words in session: "I appove these requests. GO" (covers this one). Core worktree b5728c4326fea4bdc33b721738ecdbe5ac4d8b02 (the live image's core, v63) on PYTHONPATH of the host venv. No scrape for these states ran during the passes (0 running ddp-scrapers tasks at 18:05).

| State | Dry run | Gate (set = no-flag number, changed 0, not-a-version 0, diffs untouched) | Commit | Second dry run |
|---|---|---|---|---|
| fl | 17:59:03-17:59:33: 7,702 bills, set=20,072 changed=0 not_a_version=0 | met (20,072 expected) | 17:59:47-18:00:57: COMMITTED set=20,072 changed=0 not_a_version=0 | set=0 changed=0 not_a_version=0 |
| mi | 18:01:31-18:01:49: 4,234 bills, set=14,458 changed=0 not_a_version=0 | met (14,458 expected) | 18:02:04-18:02:50: COMMITTED set=14,458 changed=0 not_a_version=0 | set=0 changed=0 not_a_version=0 |
| us | 18:03:05-18:05:34: 39,218 bills, set=92,768 changed=0 not_a_version=0 | met (92,768 expected) | 18:05:49-18:11:14: COMMITTED set=92,768 changed=0 not_a_version=0 | set=0 changed=0 not_a_version=0 |

All three show "diffs untouched (--flags-only)", 0 error lines, exit 0. Total flags set: 127,298.

**One difference from the request:** I first ran the fl dry run with `--list` and the tool refused ("--list lists comparisons; --flags-only leaves them alone"); it stopped at argument parsing and wrote nothing. So there is no change list for this pass; the dry-run and commit lines in /home/bitnami/ops/step-open612-20261117/ (raw output per state) are the record. To undo a state, the flag would have to be set back to NULL for the documents saved before 2026-11-04 (no per-document list was kept).

The Mac-side replica re-count and the spot checks (US SRES 866, SRES 662, HR 7730; MI HR 10, SR 61) are yours; the broker version-order refresh for bills whose latest text changes is a separate step I have not run.
