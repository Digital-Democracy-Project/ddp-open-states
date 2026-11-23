# UPDATE (not a GO) to `df508b7` (NE and LA before go-live), part B: **Louisiana 2026 runs on v82 (rev 84) or later; Nebraska 109 runs once, on v83** (v82 plus scrapers #246). 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Parts A and C, the gates, the expected counts and "Not authorized" all stand.

* **Why:**
    * State Specific Handling's `06a707d` asks for part B on the image that also carries Nebraska's and Louisiana's related-bill links (OPEN-794 #245, OPEN-795 #244). That way one re-import per state carries both.
    * v82 (rev 84, scrapers `4e22ce72`) has them, but lacks **#246**, Ramon's Nebraska both-sides follow-up.
    * **Ramon decided (relayed by the PM session, 2026-11-23): build v83 = v82 + #246, and run Nebraska 109 once on it.**
* **Part B, Louisiana 2026:** gate G2 becomes "new tasks run rev 84 (v82) or later". `POST …/openstates-scrape/la?full=true&sessions=2026`. Expect unmatched 0 in la 2026 (before: 8,005).
* **Part B, Nebraska 109:** gate G2 becomes "**new tasks run v83's revision or later**". I'll post v83's revision when it's registered; until then NE part B waits. `POST …/openstates-scrape/ne?full=true&sessions=109`. Expect unmatched 0 in ne 109 (before: 1,267).
* **Part A (people refresh, la and ne)** doesn't depend on the image and may run first, as written (people `efc86188` or later; expect la 0/5, ne 0/17). If people is pulled to today's main (`d1acd229`), the `id` and `ri` files changed too; load only `la` and `ne` in part A.
* **Part C** follows each state's own part B.
* **One heavy load at a time,** as before.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
