# REQUEST (waits on Ramon's go): North Carolina's first-time changelogs, session 2025, about 3,550 (OPEN-390). 2026-11-17 (Mac side)

**Not a GO yet.** Ramon accepted the first-time batch on 2026-10-16 ("no hold"). It never started: the 10-19 run only did 5 bills of `2025E1`. NC is `live`.

## What
* **The comparisons (Mac replica, 11-17):** NC session `2025` has **3,550 stored comparisons in 2,336 bills**, and `2025E1` has 7 in 5 bills (done on 10-19).
* **None is on a paper that isn't a version:** 0 comparisons with `is_bill_version = false`. The ~54 stamp pages lost their comparisons in the OPEN-366/371 fixes. OPEN-594's 206 amendment papers (core #119, merged, not in v64) have none either, per its author's replica read. So no changelog can be written from one.
* **Nothing to reject:** first-time generation fills missing rows only. Step 1 confirms there is nothing live.

## Steps (after the go)
1. **Check first (read only):** count NC `bill_changelog` rows on production by session and status. Expected: about 0 for `2025`. If any exist, list the bills and versions, and say whether any was written from a stamp page or an amendment paper (reject those, per the ticket).
2. **Ten-bill test:**
   * Trigger `POST /trigger/bill-artifact-generation` on the Mac's ddp-sync (`X-DDP-Environment: prod`) with:
     * `jurisdiction_iso2: "NC"`, `session_code: "2025"`;
     * `bill_candidates`: 10 bills, mixing Edition, Ratified and Session Law comparisons (the Mac side can supply them);
     * `artifact_types: ["bill_changelog"]`;
     * `include_org_research: false`, `include_concept_statements: false`;
     * `retry_failed: false`, `background: true`;
     * `dry_run: true` first.
   * **Read all ten against their comparisons** before going on: the ticket's sample rule, and the first real scale test of the wording on NC's bill structure.
3. **Then batches of at most 100 bills** (about 24), one at a time, each checked: rows `complete` + `approved`, no empty output, no raw `{'…'}`.
4. **Expected time:** about 20 to 45 seconds a changelog, so roughly 20 to 45 hours of model time in all, spread over several windows.

## Window
Same as SYNC-175 (`request-sync175-legbot-rewrite-la-ne-changed-text-20261117.md`): **14:00 to 23:30 UTC**, not Sunday. If SYNC-172 is released, also not **Wednesday**, NC's new weekly day. **Run after SYNC-175 has finished, never alongside it:** the published LA and NE text is known wrong, while NC's changelogs are simply missing.

## Stop conditions
* A changelog on a paper that isn't a version;
* a row-count mismatch;
* failures above 5% in a batch;
* any of the ten test readings wrong in substance.

Stop and report.

## Not authorized
Any other state; any other artifact type; organisation research; any scrape, image or data pass; `recompute-diff-order nc --flags-only` (that's OPEN-594's own step, after the next image).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
