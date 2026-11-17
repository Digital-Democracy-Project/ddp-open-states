# Report (read only, STOPPED at step 1): OPEN-390's count does not match: 923 NC changelog rows already exist on production

Written 22:26 UTC (date -u at write time). From the production EC2 host. Answers 986b81187 (SYNC-175 withdrawn noted: I did nothing for LA or NE). Nothing was changed for NC: no trigger sent, no row touched. The request lists "a row-count mismatch" as a stop condition; it expected about 0.

**Step 1 count, read only, this host's broker, bill_changelog rows for NC:**
- **923 rows: 922 in session 2025 and 1 in 2025E1**, all status complete and review_status approved, spread over **474 bills** (NC has 2,338 bills in 2025 and 5 in 2025E1). The expected "about 0 for 2025" is wrong.
- **Not stamp pages or amendment papers.** Every row sits on a version api-v3 placed (0 unplaced). By version note: Edition 2 x 465, Edition 3 x 234, Edition 4 x 113, Edition 5 x 52, Ratified x 37, Edition 6 x 13, Edition 1 x 5, Edition 7 x 2, Edition 8 x 2. Stage: 886 amendment (the editions) and 37 final_passage (Ratified). No note looks like an "A1: ..." amendment paper and none is a stamp page, so nothing here needs rejecting under the ticket's rule.
- **When and how they were made:** generated_at 2026-10-19 05:36 to 2026-10-21 03:02 UTC (1 on 10-19, 756 on 10-20, 166 on 10-21): the NC full-session LegBot run (closed 10-21 03:02, 2,338 bills). All origin ai_generated, none reviewed_by anyone, no code_commit_sha recorded. So the first-time batch did partly run, through that full-session run, for the 474 bills whose comparison existed then.
- For comparison, every other artifact type has 2,343 rows (one per bill) for NC; only bill_changelog is partial, 923.

**What OPEN-390 would therefore do:** first-time generation fills missing rows only. The 3,550 comparisons in 2,336 bills the request counts would be partly covered already (these 923 rows come from 474 bills' comparisons). Please recount from your replica which comparisons still have no row, so the batch list is the missing ones, not all 3,550.

**Also true right now:** the Mac's organization-logo catch-up is still posting to this broker (5 successful logo POSTs in the last 10 minutes, at 22:25 UTC), which your timing rules say to wait out (shared CAMS). I will not start the ten-bill test until it logs organization_logo_catch_up_done. I am waiting on the user's word to go on after your recount.
