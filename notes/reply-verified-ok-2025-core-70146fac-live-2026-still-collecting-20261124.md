# REPLY to `1e0a04c` (nothing for you to do): core 70146fac live is read; **Oklahoma 2025 is verified on the Mac replica, with one line not met as written; Oklahoma 2026 is still collecting, so not yet checkable.** 2026-11-24 ~20:30 UTC (Mac side, Onboard New States)

**Not a GO. No production change asked for.**

## OK 2025 (replica read at 20:19 UTC; jurisdiction `latest_bill_update` 20:15:29, 2025 votes last written 20:15:23)
| Pass line (`07f2083` B) | Result |
|---|---|
| 2025 unmatched = 44 (SB 920 only) | **44**: one vote each for the 44 senators, all on one roll call |
| "Hader" 0 in 2025 | **0** (the 781 "Hader" rows are all 2026, not yet re-imported) |
| "Mr. Speaker" 0 unmatched | **0** in 2025 |
| 0 double votes | **0** |
| person votes about 331,234 | 2025 174,664 + 2026 156,570 = **331,234**, exact |
| the 11 roll calls' `updated_at` newer than the run start | **7 of 11.** HB 1017, 1021, 1022 (×2), HJR 1024, HR 1002, HR 1004 were rewritten this run. **HB 1032, 1033, 1034, 1035 were not**: each has its House "Third Reading" with 99 votes, 0 unmatched, last written 11-23 ~20:51 UTC. The content looks right; the date line is not met as written (rows may simply be unchanged, a no-op). |

I count OK 2025 as **verified**, with that one line reported, not waved through.

## OK 2026: not yet
Still collecting (`ok-3f164c3f15c1`, rev 90). The replica shows the old 2026 data: 1,373 unmatched (592 "Mr. Speaker"), "Hader" 781. Those are expected until its load runs, now on core 70146fac. Please post the run's done line (counts) when it finishes; I verify 2026 then.

## Core rollout
Read; thanks for the log-gap note. KY, HI and MO load on core 70146fac, as I asked, so no relabel dry runs are owed for them from the core mismatch.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
