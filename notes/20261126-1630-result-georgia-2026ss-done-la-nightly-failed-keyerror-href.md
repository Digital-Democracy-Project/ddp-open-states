# Result 11-26 16:30 UTC: Georgia 2026_ss done; Louisiana's nightly FAILED (scraper KeyError); v97 rebuild prepared

## Georgia `ga?full=true&sessions=2026_ss` - DONE (05:29:23 trigger, 202)
* Collection 05:29 to 05:48; load 05:48:50 (cloud_scrape 1,166 s); archive 1,054 s; pipeline done 06:06:25, `failed=0`, `archived=True`, 2,222 s. Ran on the v96 image (it started before v97 was built).
* **Pass met:** the 35 "Jason T. Dickerson" person votes with no voter id are now **0**. Production `2026_ss`: 176 bills, 280 vote events, 45,780 person votes, 0 unmatched. `unmatched_voter_check` alerted false. (Same missing-marker warning as the other Fargate loads.)
* Georgia `2025_26` still reads 5,480 bills, 2,517 vote events, 279,904 person votes, 0 unmatched.

## Louisiana's 12:00 UTC nightly FAILED (needs your eyes; I did not retry)
* `la-9d7607a9285e`, started 12:00:00, collection failed 15:34:00 (12,840 s), container exit 1, `openstates_pipeline status=failed`, nothing loaded, no archive. The task ran on `ddp-scrapers:99` (**v97**).
* Cause from the task's own log (CloudWatch): a **Python KeyError**, not a network error: `scrapers/la/bills.py` line 418 in `scrape_bill_page`: `url=digest.attrib["href"]` raised `KeyError: 'href'` (a digest link element with no `href`), right after bill HR171 in session 2026 and the two "Duplicate entry in 'documents'" warnings. 3 h 32 min in.
* Same-hour nightly: Nebraska finished clean (13:09, 4,174 s). Pennsylvania's 04:00 nightly and the US nightly also finished clean.
* I will not retry Louisiana on my own. Tell me whether the scraper needs a fix first; the next scheduled Louisiana nightly would hit the same page.

## v97 rebuild (Ramon: one rebuild at v97's values)
* Rollback images tagged: `ddp-sync:pre-v97-da9641d`, `ddp-openstates-api:pre-v97`. api-v3 image built at `DDP_CORE_SHA=647bb399...`; ddp-sync image build with `DDP_SCRAPERS_SHA=d0bd1826...` in progress. Nothing restarted yet; the restarts follow under the narrow rule when no state holds a lock (none does right now). Iowa `2026s1`, the Iowa re-import and the dry-run recompute come after, in your order.
