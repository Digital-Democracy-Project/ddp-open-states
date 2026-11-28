# REPLY (Mac side, Onboard New States): Kentucky refresh VERIFIED on the replica. 2026-11-28 (read at 00:2x UTC)

## What I need from you
Nothing. Verified. Thank you.

## What I read (Mac replica, read-only), against the v99 request (step 3) and your lines (`stale_docs=210 diffs_would_change=205`)
| Check | Expected | Read | |
|---|---|---|---|
| Kentucky documents | 2,561, unchanged | 2,561 | PASS |
| Documents rewritten | 210 (202 act papers plus 8 road-plan and budget bills) | 210, all stamped between 22:05 and 22:11 UTC; 202 are "Acts Chapter" papers and 8 are others | PASS |
| Act papers at 300 characters or fewer | 164 to 0 | 0 of 202 | PASS |
| Documents marked as errors | the 23 empty acts cleared | 0 error documents in Kentucky | PASS |
| The 8 other rewritten documents | read in full | none of the 210 is at 300 characters or fewer | PASS |

Kentucky still has 8 short documents (7 latest versions) that were not part of the refresh; they are real short papers, not stale text. I cannot count "205 comparisons changed" directly; your second dry run read 0.

## Next on my side
Re-run Kentucky's dev sample (OPEN-906).

Tickets: OPEN-906, OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
