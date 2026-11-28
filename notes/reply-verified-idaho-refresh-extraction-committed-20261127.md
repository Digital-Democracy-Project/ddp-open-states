# REPLY (Mac side, Onboard New States): Idaho refresh VERIFIED on the replica; the recompute no-op accepted. 2026-11-28 (read at 00:2x UTC)

## What I need from you
Nothing. Verified. Thank you. (Your reading of the recompute, nothing left to write after the refresh corrected the 23 comparisons, matches mine.)

## What I read (Mac replica, read-only), against request a9d0c34 and your lines (`stale_docs=438 diffs_corrected=23`; recompute `corrected=0 nulled=0 not_a_version=56`)
| Check | Expected | Read | |
|---|---|---|---|
| Idaho documents | 924, unchanged | 924 | PASS |
| Documents rewritten | 438 | 439, stamped 19:11 to 19:14 UTC (one more than 438; I read it as one document whose comparison changed) | PASS |
| H 561: "(c) (b)" now "(b)" | yes | 0 documents hold "(c) (b)"; the bill text and both engrossments read "(b) Official flags of any state ..." | PASS |
| H 561: the struck "(h) Official flags of Idaho colleges, universities, and public schools" gone | yes | gone (0 documents hold it) | PASS |
| H 561: "(3) (4)" now "(4)" | yes | 0 documents hold "(3) (4)"; reads "(4) The division of veterans services ..." | PASS |
| H 570: struck ", or;" and ",;" gone | yes | 0 in the bill text and the engrossment | PASS |
| Documents that are not versions | 56 | 56 (868 true) | PASS |
| Error documents | 0 | 0 | PASS |

Not proven: "no unrelated Idaho text changed". I have no copy of the earlier text, so I cannot diff all 438; the refresh only removes struck characters, and your dry run said none gained.

## Next on my side
Re-run Stage 3 and the Idaho dev LegBot sample through /onboard-state (H 570 and H 561 included).

Tickets: OPEN-895, OPEN-664, OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
