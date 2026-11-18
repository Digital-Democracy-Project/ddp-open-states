# Status on da02e435f (OPEN-390): 625 rows rejected, ten-bill test run, STOPPED before the batches (one bill got no row; the real scale is far smaller)

Written 01:04 UTC 11-18 (date -u at write time). From the production EC2 host. User's words in session: pop-up answer "Yes, reject 625 and start the test".

## Steps 1 and 2 (read only, backup)
- Of the 923 existing NC bill_changelog rows, **625 sit on a comparison that differs between your 11-16 export (nc_before.csv, md5 572f4b66dbcea3b201ed80092cef07f0, 6,207 rows) and RDS today** (limit 633; 0 unmatched, 0 ambiguous). By version note: Edition 1 x 5, Edition 2 x 293, Edition 3 x 164, Edition 4 x 79, Edition 5 x 39, Edition 6 x 11, Edition 7 x 2, Edition 8 x 2, and the rest Ratified. Three example bills are in the list; the first is bill 5349f129-130a-42ed-b870-eca225a7c9e1 (Edition 5, 2 and 3).
- Backup of all 923 rows' review fields (id, status, review_status, reviewed_by, reviewed_at): /home/bitnami/ops/step-open390-20261117/nc-changelog-review-fields-before.csv (mode 600). The 625 ids: reject-list.csv in the same directory.

## Step 3: the rejection (00:44:34 to 00:44:40 UTC)
Exactly the 625 listed rows set to review_status rejected, one by one with .save() (reviewed_by left empty), after checking each id's bill, session and version note against the list (**0 mismatches**). Nothing deleted. NC changelog rows now: 625 rejected, 298 approved, 923 total.

## The scale is not what the request says
On RDS today NC has **6,207 documents, of which only 930 carry a comparison, in 475 bills** (not 3,550 comparisons in 2,336 bills). 135 of those 475 bills already have only approved changelogs. So the candidates (a comparison and either no row or only rejected rows) are **340 bills: 339 with a rejected row and 1 with no row** (SB1041). The remaining work is about 330 bills, not 3,250. Your Mac-replica figure of 3,550 comparisons does not match production RDS; please check what it counted.

## Step 4, the ten-bill test (Mac ddp-sync trigger, NC 2025, bill_changelog only, org research and concept statements off, retry_failed false, background true)
- Test set: 10 bills: HB308, SB664, SB115, HB268, HB576, HB23, SB205, SB77, SB599 (all with a rejected row; versions Edition 2 to 6 and Ratified; 3 had Ratified comparisons) plus SB1041 (the one bill with no row). I could not include Session Law comparisons: none exists in NC's candidates.
- Dry run 00:45:54: HTTP 202 accepted (run legbot-session-3b1e66405e44). Real call 00:48:25: HTTP 202 accepted, **run legbot-session-e158b829f81e**.
- Result by 01:02:42: all **26 changelog rows of the nine rejected bills are complete and approved again** (the rows overwrote in place), 0 empty and 0 raw {'...'} objects across all 26. About 14 minutes for 26 rows. POST /api/bill-artifacts/ in the last 8 minutes: 14 x 200.
- **I read the nine against their comparisons and they are right in substance** (HB308's added offences, SB664's removals, SB115's appointments, HB268, HB576 read in full against its whole diff, HB23, SB205, SB77, SB599). I read the opening of each changelog (up to about 900 characters); I did not read every row, and I did not read the other 17 rows.
- **SB1041 got no changelog row at all**, and it is not failed: no bill_changelog row exists for it. Its broker versions are Filed, Edition 1 to 4, Ratified and SL 2026-40, with two A1 amendment papers unplaced; the comparison that exists on RDS is on Ratified. I do not know why no row was created. That is **1 of 10 bills (10 percent) not generated, above your 5 percent stop line**.

## Stopped here
No batch has been run. I will not run the remaining ~330 bills until you say, because of SB1041 and the corrected scale. If the SB1041 gap is a pipeline quirk, tell me; if it is the SL 2026-40 version (enacted, ordinal 6) being treated as the latest one without a comparison, the same thing may happen to other bills and I would rather know first. The way back for any row is the backup CSV, only on Ramon's say-so.
