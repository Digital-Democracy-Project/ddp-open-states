# GO: OPEN-390, run the NC changelog batches, leaving out the six bills with giant comparisons. Answers `11a6b8f` and replaces the "keep holding" in `257060a`. 2026-11-18 (Mac side)

**Ramon, 2026-11-17 (relayed by the PM session, recorded on SYNC-120 comment 21301):** "run without the six, then have the agent build SYNC-120".

## What I need from you
1. **Run the batches as in `da02e43` step 4, unchanged except for one thing:**
   * `bill_candidates`: your ~340 candidates (NC 2025 bills with a comparison and either no `bill_changelog` row or only rejected ones), **minus the nine bills done in the ten-bill test, minus these six:**
     * **SB257, HB40, SB1041, HB921, SB445, HB125.**
   * The six have comparisons of 196,000 to 2.9 million characters and would hold the model for 30 minutes each before timing out. They wait for SYNC-120 (being built now).
   * Leave any row the six already have exactly as it is. Do not reject anything more.
2. **Each batch:** at most 100 bills; `bill_changelog` only; `include_org_research: false`; `include_concept_statements: false`; `retry_failed: false`; `background: true`; `dry_run: true` first.
3. **Check after each batch, as in `da02e43` step 5:**
   * each row `complete` and approved;
   * no empty output or raw `{'…'}`.
4. **At the end, report:**
   * the totals;
   * every NC comparison outside the six has a non-rejected changelog;
   * the rejected count among the non-six bills is 0;
   * for the six, what rows they have (version, status, review_status).
   * Answer `257060a`'s read-only ask 2 here too.

## Timing (real reasons only)
* No other LegBot run in flight: wait for the trigger lock, never force it.
* No Mac ddp-sync restart or CAMS reload while a batch is in flight.
* If the Mac's logo catch-up is switched back on, pause between batches.

## Stop conditions
* Failures above 5% in a batch (the six are out, so the line means what it says again).
* A row whose bill or version doesn't match.
* Anything that writes to a bill outside the candidate list.

Stop and report.

## Not authorized
* The six bills.
* Deleting any row.
* Rejecting any row.
* `retry_failed: true`.
* Any other state, artifact type, or organization research.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
