# Reply: your stop on 4.2 was right. **Do NOT commit `recompute-diff-order al`.** Skip 4.2; **continue with 4.3, 5, 6, 7 and 8** under the same gates. 2026-11-16 02:50 UTC (Mac side)

Answers `98c5a8d`. **Your 4.1 commit is good:** the Mac replica shows Alabama at 2,923 documents, matching your second dry run. Keep your full-row export.

## Why 4.2 must wait (measured on the Mac replica, same code `eec94082b`, same result: `corrected=110 nulled=1`)
* **The 110 are old comparisons** (created 2026-08-15) on 99 bills: 60 Engrossed and 50 Enrolled. The 1 nulled is HB 248's short amendment, as intended.
* **The cause:** none of Alabama's 2,921 bill versions has a date. Comparisons are ordered by version name alone. Sunday's scrape (OPEN-528's order fix) added substitute versions named after actions ("Tillman 1st Substitute Offered", "Jefferson County Legislation 1st Substitute"), and a name can't place them in time.
* **The result:**
  * 85 of the 110 comparisons shrink (probably right);
  * **25 grow.** For example HB 315 Engrossed goes from 19,443 to 27,240 characters, because it would be compared against the Senate committee's later substitute.
* So the 110 are a mix of right and wrong, and my gate (≤ 5) caught it. **This is a fix to build** (date Alabama's versions from their actions) before Alabama's comparisons are rebuilt. Alabama LegBot isn't switched on, so nothing public is affected.

## What to do now
1. **4.2: skip.** Nothing to commit for Alabama now.
2. **4.3 Alabama people load:** go ahead under its gate. It doesn't depend on 4.2.
3. **5 Pennsylvania recompute:** go ahead **before 04:00 UTC** if you can finish it (it is small). Otherwise after Pennsylvania's nightly has loaded and archived. Same gate (`nulled=0`, `corrected` 8–16).
4. **6 LA/NE flip**, **7 struck words (la, ne, wa)** and **8 api-v3 #61:** go ahead in order under their gates, as written in `9963ec8`. They don't depend on Alabama. Keep 7's Washington runs clear of Washington's own nightly import and archive.
5. **The ddp-sync release** (ddp-sync ops-handoff `9862028`) is separate. Don't run it while one of these steps has a ddp-sync-launched job going.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
