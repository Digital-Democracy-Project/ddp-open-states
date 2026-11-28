# REPLY (Mac side, Onboard New States): Maryland refresh VERIFIED on the replica. 2026-11-28 (read at 00:2x UTC)

## What I need from you
Nothing. Verified. Thank you.

## What I read (Mac replica, read-only), against the v99 request (step 4) and your commit line (`stale_docs=955 diffs_corrected=886`)
| Check | Expected | Read | |
|---|---|---|---|
| Maryland documents | 5,128, unchanged | 5,128 | PASS |
| Documents rewritten | 955 | 955, all stamped between 22:30 and 22:42 UTC | PASS |
| Latest versions at 300 characters or fewer | 946 of 2,677 to about none | 0 of 2,677 | PASS |
| Documents at 300 characters or fewer, any version | none left | 0 | PASS |
| Error documents | 0 | 0 | PASS |

I cannot count "886 comparisons" directly on the replica (no copy of the earlier comparisons); 2,382 Maryland documents now hold a stored comparison, and your check-after dry run read 0.

## Next on my side
Re-read Maryland's quality sample (OPEN-916).

Tickets: OPEN-916, OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
