# REPLY (nothing to start before Ramon's go): **Nevada's re-import (Part 4) is verified on the Mac replica, and its recompute numbers are measured.** Read at 22:26 UTC, ahead of your note (Nevada session 84 loaded 22:16:47). 2026-11-25 ~22:45 UTC (Mac side, Onboard New States)

**Not a GO.**

## Nevada, `nv?full=true&sessions=2025Special36,84` (v95)
| Pass line (bundle Part 4) | Replica |
|---|---|
| sponsors 0 unmatched of 27 | **0 of 27** |
| versions named `^Amendment` 0 | **0** |
| documents named `^Amendment` 26 | **26** |
| `2025Special36` 431 actions | **431** |
| no action text with a line break | **0** |
| AB 4, AB 5, SB 10 read as fail | **AB 4 (upper) fail, AB 5 (upper) fail, SB 10 (lower) fail** |
| versions 237 | **262** (72 in `2025Special36`, 190 in session 84): **not equal, and I think it is growth, not a fault:** session 84 is the 2027 session in pre-filing and has more bills each week (190 now); the amendment rule is what matters, and it holds. I could not reproduce the 237 baseline, so I call this "plausible, not proven" |
Verified, with that one number flagged. (Alabama's load has not landed yet.)

## Nevada's recompute: what your dry run should read (measured today in the v95 image, read-only)
`recompute-diff-order nv --dry-run`: 217 bills, **corrected 32, nulled 26**, `is_bill_version` changed **26** (`not_a_version` 26), baselines **set 22 / changed 10 / cleared 26**, **58 documents**: exactly the numbers in the bundle (OPEN-849). Commit only on Ramon's second go, `--list` kept for the undo, backup of the stored comparisons first (as you did for the others); then a second dry run reading 0.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
