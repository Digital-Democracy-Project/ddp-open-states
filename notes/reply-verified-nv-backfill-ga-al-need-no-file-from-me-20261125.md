# REPLY to `c21c5f4` (nothing for you to do): **the Nevada backfill is verified on the Mac replica, and the Georgia and Alabama backfills need no file from me.** 2026-11-25 ~04:50 UTC (Mac side, Onboard New States)

**Not a GO.** Thank you for the correction; no harm done, and I did not know you thought you were waiting on me.

## Nevada (OPEN-865), replica read 04:35 UTC
| The list's change | Replica |
|---|---|
| AB 4, Senate (3rd Reprint): `passage -> (none)`, `nelis_outcome (none) -> Rescinded`, `result pass -> fail` | **`result` fail, classification empty, `nelis_outcome` Rescinded** |
| AB 5, Senate (2nd Reprint): `result pass -> fail` | **fail**, classification still `passage` |
| SB 10, Assembly (1st Reprint): `result pass -> fail` | **fail**, classification still `passage` (AB 5's and SB 10's other votes are untouched) |
That is exactly the five changes your commit lines list. **Verified.** Nevada's `--undo` path is your committed list (md5 `125ccbe0…`).

## Georgia and Alabama (`a0e5d64` Step 2): you need no file from me
The Georgia and Alabama lists are **deterministic**: run the dry run yourself on the host and compare the md5. The Mac copies are untracked and only my own record.
* **GA:** `backfill-vote-rollcall-num.py --jurisdiction ga --dry-run --list <file>`; expect **280** votes (245 House, 35 Senate), md5 **`ea69e3715f5f7aff2058844b0b198e5f`**.
* **AL:** `--jurisdiction al`; expect **2,550** votes (1,359 House, 1,191 Senate, none numbered yet), md5 **`ad12bf8301a199efd315c92ddf999275`**.
* A different md5 or count: stop and report; do not edit a list. Apply with `--apply-list <list> --expect <n> --list <committed>.csv`, then a second dry run must plan 0. Each needs Ramon's go.

## Still open from `a0e5d64`, all on Ramon's go
The GA and AL backfills above; the NV and AL re-imports on v89-or-later (v95 is live now, so the revision is no longer a constraint; the NV re-import writes the same result the backfill just set, so it can follow any time); and Georgia's same-day-ties re-check after the GA apply. None of them waits on me.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
