# GO: OPEN-390, North Carolina's first-time changelogs (session 2025, 3,550 comparisons in 2,336 bills), **after SYNC-175 finishes**. 2026-11-17 (Mac side)

**Ramon, 2026-11-17** (relayed by the PM session, then confirmed by Ramon to this session in a pop-up, "Yes, all three"): "Go for both, in order". The LA/NE rewrite goes first (`go-sync175-legbot-rewrite-la-ne-20261117.md`), then this, never alongside another LegBot run.

**Follow `request-open390-nc-first-time-changelogs-20261117.md` (`d00d240`)**, with one change:
* **Timing: start when SYNC-175's last batch is reported done. The request's "14:00 to 23:30 UTC, not Sunday/Wednesday" window is dropped.** Same real-reason rules as SYNC-175:
  * no other LegBot run in flight (the trigger lock; wait, don't force);
  * not during the Mac's organization-logo catch-up;
  * no Mac ddp-sync restart or CAMS reload while a batch is in flight.
* **Unchanged steps:**
  1. a read-only count of existing NC `bill_changelog` rows;
  2. the ten-bill test, all ten read against their comparisons before going on;
  3. batches of at most 100 bills, `bill_changelog` only, `include_org_research: false`.

  Stop conditions as in the request.
* **Report** after the test and after the last batch: counts generated and failed, and the ten readings.

## Not authorized
Any other state or artifact type; organization research; `recompute-diff-order nc --flags-only` (OPEN-594's own step); any scrape, image or data pass.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
