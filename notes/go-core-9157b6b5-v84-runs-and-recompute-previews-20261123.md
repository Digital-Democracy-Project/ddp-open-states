# GO (Ramon, 2026-11-23, in the Onboard New States session, pop-ups): core rebuild at `9157b6b5`, then v84; four runs on v84; Kentucky and Oklahoma recompute **previews only**. 2026-11-23 (Mac side, Onboard New States)

**Ramon's answers, word for word (his choices in my session's pop-ups):**
1. "Go: core rebuild, then v84": the core rebuild, then he builds v84.
2. "Go: all four on v84": Idaho's 2026 re-import, Maryland's first scrape again, Iowa 2025, and Montana's 2027 re-import.
3. "Preview both now; save after I see numbers": Kentucky and Oklahoma recompute **dry runs only**. Each commit holds until he has seen the numbers and gives a second go.

Each request below stands as written, with its gates and pass/fail checks. This note only gives the go for the steps named.

## 1. Core rebuild at `9157b6b5` (`ce0bf8b` step 1)
* Rebuild EC2 api-v3 and EC2 ddp-sync (at `85c8888`) with `DDP_CORE_SHA=9157b6b563b9fbca71a081ada4c00c18878d9edb`. The Mac api-v3 is Ramon's or mine.
* Post the in-flight list before restarting ddp-sync. Do it at a quiet moment, never 02:15–04:45 UTC. Re-trigger what a restart cuts, as listed in `692a2ba`.
* Then `check-core-pin-drift.py --image-core 9157b6b5…` exits 0.

## 2. Image v84
Ramon builds it at scrapers main `2c29d8a1` or later, with core `9157b6b5`. I'll post its revision; the runs below need that revision or later.

## 3. Four runs on v84, one heavy load at a time
| Run | Request | Trigger |
|---|---|---|
| Idaho 2026 re-import | `7788700` / `c77027a` step 3 (people already loaded: 17/5) | `…/id?full=true&sessions=2026` |
| Maryland first scrape again | ddp-sync `2672ac8` part 3 (OPEN-799 fix) | `…/md` |
| Iowa 2025 | ddp-sync `aa0bf45` / `12be6e8` (OPEN-797 fix) | `…/ia?sessions=2025` |
| Montana 2027 re-import | `ce0bf8b` step 3 | `…/mt?full=true&sessions=2027` |

Report each against its request's pass/fail lines.

## 4. Recompute dry runs only
* **Kentucky:** `recompute-diff-order ky`, dry run, at core `9157b6b5` (it contains `42b48982`). Per `22d7100` step 4: expect `corrected` 760–860, `set` 620–680, 0 nulled or cleared.
* **Oklahoma:** `recompute-diff-order ok`, dry run, at core `9157b6b5`, **after the Oklahoma re-import from `8108de3` has loaded and been verified.** I'll post its expected range first.
* **Both commits hold** until Ramon gives a second go after seeing the numbers.

## Not authorized
* Either recompute commit.
* Any other state.
* A second run of any of the four.
* Any manifest, schedule, routing or LegBot change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
