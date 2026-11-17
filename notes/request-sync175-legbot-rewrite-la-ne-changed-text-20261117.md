# REQUEST (waits on Ramon's go): rewrite LegBot's Louisiana and Nebraska results for bills whose stored text changed in the 11-16 crossed-out-words refresh (SYNC-175). 2026-11-17 (Mac side)

**Not a GO yet.** Ramon decided the scope on 2026-11-17: "Yes, changed bills only".

## Why
* **The refresh:** OPEN-560 (image v59) stopped reading crossed-out words in LA, NE and WA bill PDFs as if they were still in the bill. Your step 7 on 11-16 (`327f774`) refreshed the stored texts and comparisons:
  * LA: 3,425 stale documents at the gate, 980 comparisons corrected;
  * NE: 1,693 stale documents, 197 comparisons corrected.
* **The problem:** LegBot's results for those bills were written from the old text. Louisiana SB 495's summary quotes a figure that the bill deletes.

## The lists (Mac replica, read only), in this branch
* `notes/sync175-20261117/sync175-la-bills.csv`: **973 LA bills** (session 2026, 3,461 documents). Every LA document whose `updated_at` falls inside your LA refresh commit, 03:26:21 to 03:50:57 UTC on 11-16. 676 of the bills have a stored comparison.
* `notes/sync175-20261117/sync175-ne-bills.csv`: **871 NE bills** (session 109, 1,700 documents). Same rule, inside 04:16:18 to 04:26:43 UTC. 276 of the bills have a stored comparison.
* Columns: `session|bill|bill_openstates_id|docs_refreshed|docs_with_diff`. The ids are bare UUIDs, which is the trigger's `bill_openstates_id`. LA SB 495 is `14eb5285-2cf5-4aa8-99bb-fd59981556c1`.
* **Washington is not listed** (the ticket covers WA's PDF bills too). Its 11-16 rows were updated again by the 19:12 UTC HTML refresh (OPEN-580), so `updated_at` can't separate them. If Ramon wants WA in this pass, rebuild its list from your own step 7 files in `/home/bitnami/ops/step7-struck-20261116/` (the full-diff export plus the commit output) and report the count. Otherwise WA stays out.

## For Ramon to pick with the go: which results to rewrite
A normal run never redoes a `complete` result (only a rejected or missing one). So "rewrite" means rejecting the listed rows first, as for Virginia (OPEN-399, `go-open399-va-changelog-regeneration-part3-20261019.md`).
* **Recommended:** `bill_summary` (it reads the latest text) and `bill_changelog` (it reads the comparison), only on the listed bills.
* Leave out pros/cons, supporting and opposing organisations and concept statements. They are less likely to quote the deleted words, and each rewrite costs a model call.
* Ramon may widen or narrow this.

## Steps (after the go), following the Virginia procedure and ddp-sync's `request-open387-…` rules
1. **Count first (read only):** for each list, how many `bill_summary` and `bill_changelog` rows exist on production, and their status. Report the counts. Then pause only if the total is more than 3,000 rows.
2. **Back up:** write the review fields (id, status, review_status, reviewed_by, reviewed_at) of every row in scope to a CSV on the host.
3. **One-bill test, on LA SB 495:**
   * reject its `bill_summary` (and its `bill_changelog` rows);
   * trigger `POST /trigger/bill-artifact-generation` on the Mac's ddp-sync (`X-DDP-Environment: prod`) with:
     * `jurisdiction_iso2: "LA"`, `session_code: "2026"`;
     * `bill_candidates: [SB 495]`;
     * `artifact_types: ["bill_summary","bill_changelog"]`;
     * `include_org_research: false`, `include_concept_statements: false`;
     * `retry_failed: true`, `background: true`;
   * `dry_run: true` first, then the real call.

   **Check:** the new summary no longer quotes the deleted figure. Report the before and after wording.
4. **Then batches of at most 100 bills:** reject only the rows of the batch you are about to run, run it, check, then the next batch. One batch at a time. The trigger's own lock refuses an overlapping LegBot run; if it refuses, wait, don't force.
5. **After each batch:** every row in the batch is `complete` and `approved`. Read about 5 rewritten summaries a day against their text.

## Window
Any day between **14:00 and 23:30 UTC**, after PA's nightly and its LegBot pass, and before WA's 02:30 nightly. Skip Sunday (the weekly batch and its LegBot passes). If the ddp-sync release with the new weekly days (SYNC-172) goes out first, also skip **Thursday**, the new LA/NE day. Check that no LegBot run is in flight before each batch. **Don't run this at the same time as NC's first-time batch (OPEN-390); that runs after this one.**

## Stop conditions
* A row count that doesn't match;
* an id that maps to a different bill;
* a row still `failed` after one retry;
* an empty summary or a raw `{'…'}` object;
* the SB 495 test failing.

Stop, change nothing more, and report. The way back is the backup CSV: rejected rows can be set back to `approved` only on Ramon's say-so.

## Not authorized
Any state or bill not on the lists; any artifact type other than the two chosen; organisation research (it costs money); any scrape, image, manifest or data pass.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
