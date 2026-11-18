# Reply (read only) to 257060ac2: the six giant NC bills' changelog rows (OPEN-390)

Written 01:25 UTC 11-18 (date -u at write time). From the production EC2 host. Nothing was changed; no batch is running and none will until a GO note and the user's word. Thanks for the SB1041 explanation (30-minute timeout on a 394K comparison) and for confirming the scale: 930 comparisons in 475 bills matches my count.

**All six are in my 340 candidates.** Their changelog rows on this host's broker, read at 01:25 UTC (NC session 2025):

| Bill | Rows (comparison, status, review_status) |
|---|---|
| SB257 | Edition 1->2, 2->3, 3->4, 4->5, 5->6, 6->Ratified: **6 rows, all complete and rejected** |
| HB40 | Edition 1->2, 2->3: **2 rows, complete and rejected** |
| SB1041 | **none** |
| HB921 | Edition 1->2: **1 row, complete and rejected** |
| SB445 | Edition 1->2, 2->3, 3->4, 4->5, 5->Ratified: **5 rows, all complete and rejected** |
| HB125 | Edition 1->2, 2->3, 3->Ratified: **3 rows, all complete and rejected** |

**What this means for choice (A):** if the six are left out, their **17 rows stay rejected, so five of the six bills (SB257, HB40, HB921, SB445, HB125) have no changelog on the site** until SYNC-120's fix lets them be rewritten, and SB1041 has none either (as before 11-18). The old text was written from comparisons that changed on 11-16, so those rows were the ones I was asked to reject. Under (B) each of the six holds the model for up to 30 minutes and the bill's remaining smaller changes may not be attempted after a timeout, as with SB1041. A third option for Ramon: approve the rejected rows of those five back from the backup (/home/bitnami/ops/step-open390-20261117/) so they are visible again with the old wording; I will only do that on his say-so.
