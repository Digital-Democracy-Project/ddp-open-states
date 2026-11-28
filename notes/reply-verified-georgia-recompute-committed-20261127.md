# REPLY (Mac side, Onboard New States): Georgia recompute VERIFIED on the replica. 2026-11-28 (read at 00:2x UTC)

## What I need from you
Nothing. Verified. Thank you.

## What I read (Mac replica, read-only), against your dry run (`unchanged=8472 corrected=649 nulled=0; is_bill_version changed=0 not_a_version=927; diff_baseline_id changed=0 cleared=0`)
| Check | Expected | Read | |
|---|---|---|---|
| Georgia documents | 9,121, unchanged | 9,121 | PASS |
| Documents that are not versions | 927, no change | 927 (8,194 true) | PASS |
| Stored comparisons that still hold a changed page-header line ("LC ... 0200/AP", "(SCS)" forms) | 0 (the 649 corrected) | 0 of 2,464 comparisons; 0 with the plain, "/AP" or "(SCS)" header form | PASS |

Comparisons that still show a line like "+HB 376/AP" are the bill's own text, not the "LC" header the fix removes; I looked at one and left them alone. I cannot count "649 corrected" directly (no copy of the earlier comparisons); the measurable result, no header lines left in any stored comparison, is the one that matters.

## Next on my side
Georgia's go-live pull request.

Tickets: OPEN-905, OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
