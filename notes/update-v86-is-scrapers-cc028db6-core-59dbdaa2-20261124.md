# UPDATE (not a GO): **v86 = scrapers main `cc028db6` or later, with core `59dbdaa2`**. Ramon builds it. 2026-11-24 (Mac side, Onboard New States)

**Not a GO.** This confirms the commits named in `4389222`, `85a8950` and `a1c833f`; nothing else changes.

* **Scrapers `cc028db6d4ccf5d85ea51b94473b3ce015ce2108`** (#263, OPEN-819, merged by the PM session). Since v85's `928138b2`, scrapers main gained only:
    * #262 (OPEN-818, New Mexico Senate name suffixes);
    * #263 (OPEN-819, Washington 2027-28; 2025-26 stays the only active session until 2027-01-11).
* **Core `59dbdaa2f3628821baa4cd45f1fabeb2cf936c7a`** (OPEN-817). Before any run on v86, the core rollout to `59dbdaa2` runs (`85a8950`).
* **Mac side** checks that v86's `DDP_CORE_COMMIT` is `59dbdaa2` and that its scrapers contain `cc028db6`. I'll post its revision when Ramon reports it.
* **ddp-sync's SYNC-188 rebuild**, if done after v86: `DDP_SCRAPERS_SHA=cc028db6d4ccf5d85ea51b94473b3ce015ce2108`.
* **After v86, in this order:**
    1. Washington's next nightly is the check (`4389222`).
    2. New Mexico's 2026 re-import (`a1c833f`).
    3. The rest of `0940569` step 5, on whichever image is live.

Tickets: OPEN-819, OPEN-818, OPEN-817 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
