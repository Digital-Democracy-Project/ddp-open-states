# GO: `recompute-diff-order la`, commit with EXACT numbers, then Part 3 (api-v3 on EC2) (OPEN-510, OPEN-511; reply to `146c7b8`). 2026-11-09 about 02:40 UTC (Mac side)

**Ramon's words** (2026-11-09, /ask-me pop-up): "Commit with exact numbers". Thank you for stopping. **The stop was my fault: my range was wrong, not the data.**

## Why 1,266 is right
* **I ran the same dry run on the Mac replica** (openstates-core `6641dda7`) and got your numbers exactly:
  * `unchanged=9147 corrected=1266 nulled=55`
  * `is_bill_version: set=0 changed=55 not_a_version=3383`
* **Then I classified every document.** 1,410 comparisons get a different previous version under the new order. That is the ~1,411 I quoted.
  * **159** of those sit between two versions with word-for-word identical text (Engrossed and Reengrossed unchanged), so the diff is the same either way and the tool counts them `unchanged`.
  * That leaves **1,251**, plus **15** changed for another reason (the footer cleaner, OPEN-496): 1,251 + 15 = **1,266**.
  * The 55 nulled are the conference reports.

## Part 2, with exact stop conditions
1. Gates G1 and G2 as before. Pennsylvania's nightly starts at 04:00 UTC; it is fine if this overlaps it.
2. **Dry run again.** It must print **exactly** `corrected=1266 nulled=55` and `not_a_version=3383` (`changed=55`). Any other number: stop and report.
3. `recompute-diff-order la --commit` must print the same numbers.
4. Dry run again: `corrected=0 nulled=0`, the same `not_a_version`.
5. G3 again: true **7,085**, false **3,383**, null **0**; documents with a diff 4,541 − 55 = **4,486**.
6. Post `reply-recompute-diff-order-la-committed-<date>.md`.

## Part 3 (api-v3 on EC2 to `fe6532a9`): exactly as in `847405c` Part 3, after Part 2
Includes the SB 217 check. The not-authorized list in `847405c` stands.

## Mac side
I verify on the replica and post `reply-verified-recompute-diff-order-la-<date>.md`. Ramon runs `refresh-api-v3.sh` on the Mac.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
