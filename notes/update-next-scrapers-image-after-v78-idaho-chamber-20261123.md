# UPDATE to `4f42180` / `22d7100` (the next scrapers image after v78): it now also carries **OPEN-770 (Idaho roll calls stored under the right chamber)**. Scrapers main is now **`0292506c`**; core is still `42b48982`. 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Everything in `9e2caaa`, `a9fbb18`, `35b5cda`, `22d7100` and `4f42180` stands. Build the image at scrapers `main` **`0292506c19479396e54a8660887789c10fb2e5f1`** or later.

## Added since `4f42180` (scrapers main `9493a09b` → `0292506c`)
| Merge | What |
|---|---|
| #226 (OPEN-770, head `c05c9415`, merged by the PM session as `0292506c`; Onboard New States) | Idaho: a failed roll call's own "Ret'd to House" ending no longer moves the bill, and a committee report in the second chamber no longer flips it. Each roll call is stored under the chamber that took it. Offline, over every bill page of 2025 and 2026 (1,417 roll calls), exactly 2 votes change chamber (2026 H 760 03/25 → Senate; 2025 S 1180 04/03 → House). Vote keys (#223, OPEN-769) are unchanged |

* `scrapers/id/bills.py` and tests only. No migration and no new setting; no core change.
* **Idaho isn't scraped yet** (`probing`), so no stored data needs fixing. Idaho's first scrape (OPEN-664, ddp-open-states #461) waits on this image; its request comes separately, on Ramon's go.
* The image check on the Mac side should confirm the image's scrapers tree matches `0292506c`.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
