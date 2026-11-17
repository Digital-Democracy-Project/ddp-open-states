# GO: SYNC-175, rewrite LegBot's `bill_summary` and `bill_changelog` for the LA and NE bills whose text changed in the 11-16 refresh. Then, after it finishes, OPEN-390 (its own GO note). 2026-11-17 (Mac side)

**Ramon, 2026-11-17** (relayed by the PM session, then confirmed by Ramon to this session in a pop-up, "Yes, all three"): "Summary + changelog", "Leave WA out for now", "Go for both, in order". Run the LA/NE rewrite first, then OPEN-390's NC first-time changelogs, never alongside another LegBot run. His standing note: no arbitrary dates or windows.

**Follow `request-sync175-legbot-rewrite-la-ne-changed-text-20261117.md` (`d00d240`)**, with these changes:
* **Scope:** `artifact_types: ["bill_summary","bill_changelog"]` only, on the bills in `notes/sync175-20261117/sync175-la-bills.csv` (973) and `…/sync175-ne-bills.csv` (871). **WA is out.**
* **Timing: start as soon as you're ready. The request's "14:00 to 23:30 UTC, not Sunday/Thursday" window is dropped.** The only timing rules, each for a real reason:
  * **No other LegBot run in flight.** The trigger's own lock refuses an overlap; if it refuses, wait and retry. Don't force it. This includes the archive hooks' automatic LegBot passes after a scrape.
  * **Not while the Mac's organization-logo catch-up is running.** It shares the Mac's model server (CAMS). Check that the run has logged `organization_logo_catch_up_done` before starting a batch.
  * **Nobody restarts the Mac's ddp-sync or reloads CAMS while a batch is in flight.** The Mac half of the ddp-sync release (Ramon's step) waits for a gap between batches.
* **Order of steps, unchanged:**
  1. read-only count and report;
  2. back up the review fields to a CSV;
  3. the one-bill test on LA SB 495, which must no longer quote the deleted figure;
  4. batches of at most 100 bills, rejecting only the batch about to run;
  5. check each batch.

  Stop conditions as in the request.
* **When the last batch is done,** report the totals: rewritten, still failed, and SB 495 before and after. **Then start OPEN-390** (`go-open390-nc-first-time-changelogs-20261117.md`). No new go is needed.

## Not authorized
WA; any other state or bill; any other artifact type; organization research; any scrape, image, manifest or data pass.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
