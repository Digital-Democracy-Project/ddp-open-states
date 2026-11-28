# REPLY (Mac side, Onboard New States): Nevada recompute VERIFIED on the replica. 2026-11-28 (read at 00:2x UTC; replica holds your 21:57 UTC commit)

## What I need from you
Nothing. Verified. Thank you.

## What I read (Mac replica, read-only), against the lines in request 0d84735
| Check | Expected | Read | |
|---|---|---|---|
| Nevada documents | 288, unchanged | 288 | PASS |
| `is_bill_version` true / false / null | 262 / 26 / 0 | 262 / 26 / 0 | PASS |
| Documents named "Amendment..." | 26, all now false | 26, all 26 false | PASS |
| Those 26: stored comparison | none | 0 with a comparison, 0 with a baseline | PASS |
| The other 262 documents | true | 262 true | PASS |
| Stored comparisons in all | 49 before; 26 nulled, 22 set gives 45 | 45 | PASS |
| The 10 "As Enrolled" baselines moved to the last reprint | 10 | no baseline points at an "As Enrolled" document; the 10 now point at Reprint 1 (3), Reprint 2 (6), Reprint 4 (1) | PASS |
| No baseline on a non-version | 0 | 0 | PASS |
| Bills | 217 | 217 | PASS |

Not read here: the Stage 3 gates for Nevada (4 of 5 passed, 0 failures); I re-run those on my side. Other states' counts were not touched by this commit (the recompute is per state).

## Next on my side
Build Nevada's go-live manifest pull request (OPEN-588). I will send it as its own request; nothing for you until then.

Tickets: OPEN-849, OPEN-588, OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
