# status: Part 2 COMMITS DONE for OR, ID, GA, WY, MT, MO (core a7035d68); extra read-only runs; Part 4 progress; read ef0737b, caae1c1, ecaa7ea

Ramon's go in my session (pop-up ~22:00 UTC): all four groups of Part 2 (Oregon relabel + recompute; Idaho + Georgia recompute; Wyoming + Montana; Missouri recompute). Each commit: fresh dry run first, compared with the measured numbers (any difference would have been an abort; none occurred), **a backup of the stored comparisons (id, bill_id, is_bill_version, diff_baseline_id, diff text, updated_at) before each recompute** (ops/<st>-stored-comparisons-backup-20261125.csv, mode 600), the commit with its list, then a second dry run. Relabels used `--expect <n>` with the list; recompute has no --expect, so the match was enforced by my pre-check against your numbers.

| State and command | Committed | Second dry run |
|---|---|---|
| OR relabel | actions changed 337 (passage -> none 306; none -> passage 29; none -> failure 1; reading-3 -> reading-3, failure 1), list md5 5d3394d7554c4192e15f6eb416bc2dd5 | actions changed 0 (3,912 unchanged) |
| OR recompute | 304 bills, corrected 201, nulled 432, is_bill_version changed 433 / not_a_version 433, baselines changed 201 / cleared 432; 633 documents; backup 633 rows | corrected 0, nulled 0, flags changed 0 |
| ID recompute | 817 bills, corrected 50, nulled 56, flags 56; 106 documents; backup 106 | 0, 0, flags 0 |
| GA recompute | 176 bills, corrected 3, nulled 0, flags changed 0 (not_a_version 102 stored); 3 documents; backup 3 | 0, 0, flags 0 |
| WY recompute | 335 bills, corrected 88, nulled 841, flags 845, baselines changed 88 / cleared 841; 929 documents; backup 929 | 0, 0, flags changed 0 (845 stored) |
| MT relabel | actions changed 62 ((none) -> introduction), computed fields 0; list md5 e2cd918b9f791edf9e9f611574155002 | actions changed 0 (4,938 unchanged) |
| MT recompute | 241 bills, corrected 60, nulled 0, flags and baselines 0; 60 documents; backup 60 | 0, 0, flags 0 |
| MO recompute | 3,161 bills, corrected 461, nulled 598, flags changed 746 / not_a_version 756, baselines set 372 / changed 119 / cleared 598; 1,089 documents; backup 1,089 | corrected 0, nulled 0, flags changed 0 (756 stored) |
Committed lists (the `--undo` path for the relabels) are in ops/<st>-relabel-commit-20261125.csv and <st>-recompute-commit-20261125.csv. (The MO list file has 1,145 lines for 1,089 documents because some cells hold line breaks.)

## Extra read-only runs you asked for (the host's own read, nothing written)
HI recompute: 6,132 bills, unchanged 21,472, corrected 0, nulled 0, flags 0, baselines 0. MD recompute: 2,677 bills, unchanged 5,128, all 0. HI relabel: actions changed 0 (68,030 unchanged). RI relabel: 0 (14,325 unchanged). ND relabel: 0 (15,495 unchanged). All as you predicted.

## Part 4 (AL and NV, started 21:50:32) and the Arizona full load (21:37:04), all on ddp-scrapers:97 = v95
- NV: session 2025Special36 done (collection 21:55:36, load 21:55:46, 312.9 s); session 84 collecting. AL (2026rs) and AZ (57th-2nd-regular) collecting at 22:10; host load about 1.3. The AZ load-task capture is waiting for the load task to launch.

## Read, not started: Part 4b and the go-live request
- **Part 4b (ME, MD, MS second passes; caae1c1):** read. **Ramon has not given that go in my session**: I put it to him next. Not started.
- **ecaa7ea (go-live for HI, RI, ND, KY, #494):** read. It starts only after #494 is merged on origin/main and on Ramon's go naming it; I will first read the per-state diff and run the dry run. Not started.
