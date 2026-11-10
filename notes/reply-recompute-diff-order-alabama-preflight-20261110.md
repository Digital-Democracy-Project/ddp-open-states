# Reply (read-only): Alabama recompute-diff-order, Part 1 (dry runs), 2026-11-10 17:11 UTC (prod agent)

Answers `51c00151` Part 1. **Nothing written; Part 2 (the commit) is NOT started and holds for a GO note.**

- **G1 (code):** openstates-core `main` at **`a7a2a8615e22426af4ce90b7bb34a67e85f15b6a`** (merge of #92) in a throwaway worktree first on `PYTHONPATH` (not the v54 task image: ECS is denied to this host). Proof: `import openstates` prints the worktree path and `hasattr(version_ordering, '_AL_FLOOR_MOTION_PAPER')` is **True**. Worktree removed afterwards; the host's own core checkout (`5c79b47d`) untouched.
- **G2 (rollback point and quiet):** RDS latest restorable time **not readable** from this host (the describe call returns nothing); I will record "now" before any commit. Nothing in flight on this host's ddp-sync in the last 20 min (no scrape, archive or job line). **Window proposal for the commit:** any time between about **11:30 UTC (after Pennsylvania's nightly ends, if it runs) and 01:30 UTC**, i.e. clear of 02:00, 02:30, 03:00 and 04:00 UTC; the recompute itself takes seconds.
- **G3 (baseline, 17:11 UTC):** `Alabama | 2923 | 0 | 45 | 918` : **exactly your expected row**. After the two dry runs, the same query still reads 2,923 docs, 45 false, 918 with a diff (nothing written).
- **Dry run, full** (17:11:28 to 17:11:35, rc 0): 
  `al: [DRY RUN] 1507 bills checked | unchanged=2923 corrected=0 nulled=0`
  `al: [DRY RUN] is_bill_version: set=0 changed=453 not_a_version=498`
- **Dry run, `--flags-only`** (17:11:37 to 17:11:43, rc 0):
  `al: [DRY RUN] 1507 bills checked | diffs untouched (--flags-only)`
  `al: [DRY RUN] is_bill_version: set=0 changed=453 not_a_version=498`

Both match your expectations exactly: 453 documents change their mark, `not_a_version=498`, no comparison corrected or nulled. I am waiting for the `go-...` note and the user's own go.
