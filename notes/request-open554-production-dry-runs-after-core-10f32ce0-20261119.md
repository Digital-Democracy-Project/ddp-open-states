# REQUEST (OPEN-554, read only): the two per-state dry runs on production data once core 10f32ce0 is live. 2026-11-19 (Mac side, State Specific Handling)

**Not a GO.** This adds a step after `eed0ebf` step 2, the api-v3 and ddp-sync rebuilds at core `10f32ce0`. Ramon decided it on 2026-11-19 (OPEN-554, Jira comment 21612): run the ticket's two read-only checks on production data.

## Why
OPEN-554 moved each state's text clean-up, reader choice and version rules into `openstates/ddp_states/<state>.py`. It was meant to change no behaviour, and the Mac comparison found no difference (OPEN-554 ticket and core #133). These two dry runs prove the same thing on the real stored data.

## When
* After `eed0ebf` step 2: api-v3 rebuilt at `10f32ce08088e544e88d54ec64aa325aea80756f` and the drift check exiting 0.
* Run each state **not while that state is scraping or archiving**. The rest is your judgment of load; there is no time window.

## How (the same way as the New Mexico dry run in `checkpoint-api-v3-core-c983ae68-and-nm-dry-run-20261119.md`)
* Host venv (Python 3.13) with a throwaway openstates-core worktree at **`10f32ce0`**. Confirm `openstates/ddp_states/` exists in it.
* **Read only. No `--commit` anywhere.**

For each of the 17 jurisdictions in `jurisdictions.yaml` (al, az, fl, ga, la, ma, mi, nc, ne, nm, nv, or, pa, us, ut, va, wa; use the code earlier runs used for Congress):

1. `os-text-extract recompute-diff-order <st> --dry-run --list <dir>/<st>-recompute-10f32ce0.csv`
   * **Expected:** `corrected=0 nulled=0`, and the `is_bill_version` and `diff_baseline_id` lines show `changed=0`.
2. `os-text-extract refresh-extraction <st> --dry-run`
   * **Expected:** 0 stale documents, 0 diffs that would change.
   * **This one is heavy:** it re-reads every archived document's stored bytes (local copy first, then the bill archive in S3), one bill at a time. Run one state at a time.

## If a state does not show 0
* A non-zero result can predate OPEN-554: a rule merged earlier whose recompute was never committed for that state.
* So run **the same command at core `c983ae68`** (the core before OPEN-554) in a second throwaway worktree, and compare:
  * for step 1, the `--list` file's md5 and the summary lines;
  * for step 2, the counts.
* **Identical at both cores:** the difference is not from OPEN-554. Record it and go on. It is a separate item for Ramon, not part of this ticket.
* **Different:** stop. That is an OPEN-554 regression. Report the state, both outputs and the list files, and do not run any `--commit`.

## Checkpoint wanted
* A table: state, the step 1 summary lines and list md5, the step 2 counts, and the `c983ae68` comparison where one was needed.
* Elapsed time per state for step 2.
* Anything that errored.

## Not authorized
* Any `--commit`, any write to RDS or S3.
* Anything outside these two read-only commands.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
