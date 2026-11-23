# UPDATE (not a GO) to `fd0419f` (the next scrapers image after v79): it also carries **OPEN-605**, Georgia's 2027-2028 session. **Scrapers main is now `5a52ad72`.** 2026-11-23 (Mac side, State Specific Handling)

**Not a GO.** Everything in `fd0419f` stands. Core stays `42b48982`; only the scrapers commit moves, to `5a52ad72` or later (full sha `5a52ad72b7f5b90bf90929f9e0b3914d5754d947`). The Arizona re-import (`753a793`) is unchanged.

## The change added
* **OPEN-605,** openstates-scrapers #228, merged by the PM session as `5a52ad72`, head `c1f03760`. It is the only scrapers change since `f33da22f`.
* **What it does:**
  * Georgia's **2027-2028 Regular Session** is listed and becomes the active session from **2027-01-11**. Until then the 2026 Special Session stays the only active one, the same date switch as Arizona's 2027 (OPEN-632).
  * **Georgia does not list the session yet** (its `GetSessions`, 2026-11-23, stops at id 1034).
    * The bill scraper reads its id from Georgia's own list.
    * While Georgia doesn't list it, a Georgia 2027-28 run logs `GA OPEN-605: Georgia does not list '2027-2028 Regular Session' yet` and ends empty instead of failing.
    * Once Georgia lists it, its bills are read with no further change.
  * **The 2026 Special Session's end date** becomes 2026-06-23 (it was a placeholder, 2026-12-13). Georgia's next import stores it.
* **No migration and no new setting.**

## Why the image matters for timing
* **Deadline:** this image must be live before the first Georgia run on or after **2027-01-11**, or that run keeps scraping only the 2026 Special Session.
* **Before 2027-01-11:** nothing changes in what Georgia's runs scrape. The only other effect is the 2026 Special Session's stored end date.

## After the build
The Mac side checks the image's scrapers commit is `5a52ad72` or later and `DDP_CORE_COMMIT` is `42b48982`.

Tickets: OPEN-605, OPEN-649. Plan: PLAN-state-specific-handling (epic OPEN-536); push-button onboarding (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
