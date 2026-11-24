# UPDATE (not a GO) to `e30bb8e` (the v88 request): **Missouri's re-import waits for the next image that contains scrapers #279.** v88 is unchanged. 2026-11-24 ~16:45 UTC (Mac side, Onboard New States)

**Not a GO.** Everything else in `e30bb8e` stands: v88 = scrapers `0aba6be6`, core `0d373728`.

* Ramon said yes to Missouri's journal chamber (OPEN-869, "use the journal chamber"). Scrapers **#279** merged as **`85d9ce59bccfc937d5704831af062243741acac7`**. It is **not** in v88, which was built at `0aba6be6`.
* **Step 4c (Missouri's re-import, `mo?full=true&sessions=2026`) is therefore removed from the v88 order.** Missouri then re-imports **once**, on the next image that holds #279, with its other fixes (OPEN-848's 28 missing Senate bills is already in v88's scrapers). **Ramon decides the timing.**
* **What #279 changes (builder's measure, offline):** 306 Missouri actions on 105 bills change chamber (247 House → Senate, 59 Senate → House), including 27 Senate "Truly Agreed To and Finally Passed" votes that were stored under the House. 144 "House/Senate Message" lines sit under the chamber whose journal reads them in.
* **Missouri's relabel and recompute dry runs** (`e30bb8e` steps 5 and 6) also wait until after that re-import. Don't run them on today's data.
* The rest of the v88 order (WY, KY, HI, NV re-imports, the other relabels and recomputes, text and stale-archive steps) is unchanged.

Tickets: OPEN-869, OPEN-848, OPEN-671 (OPEN-146).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
