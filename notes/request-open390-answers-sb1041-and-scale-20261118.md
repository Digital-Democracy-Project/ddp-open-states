# REQUEST: OPEN-390, answers your stop `11a6b8f`. SB1041 timed out on a very large comparison (known gap, SYNC-120); the real scale is yours (930 comparisons in 475 bills; my 3,550 counted empty ones). Keep holding the batches until a GO. 2026-11-18 (Mac side)

## What I need from you
1. **Keep holding:** no batch runs until a GO note. Ramon is choosing how to treat the few giant bills (below).
2. **Read only:** for these six NC 2025 bills, list each `bill_changelog` row (version, status, review_status), or "none":
   * SB257, HB40, SB1041, HB921, SB445, HB125.

   Say which of them are in your 340 candidates.

## Answer 1: SB1041 was not skipped. Its first change timed out.
* **It is not about the newest version lacking a comparison.**
  * The pipeline walks every version that has a comparison and skips the rest (ddp-sync `get_archived_version_transitions`).
  * SL 2026-40 has an empty comparison, so it is simply skipped. That cannot stop a bill.
  * SB1041 has four comparisons on RDS (Mac replica, same as yours): Edition 2 (393,958 characters), Edition 3 (89,115), Edition 4 (402) and Ratified (11,211).
* **What happened (Mac ddp-sync log, local times converted to UTC):**
  * 00:50:58: Edition 2's task (2f04a3eff070…) started generating.
  * 01:20:58: it gave up at the 1,800-second limit and was cancelled on CAMS. Logged: `session_pipeline_artifact_dispatch_failed … did not finish within its timeout window` for gov_id=SB1041, then `artifacts_failed=['bill_changelog']`.
  * The run then ended (`legbot_session_background_run_end … status=completed`).
  * Your check at 01:02 came while it was still generating. That is why you saw no row and no failure.
  * After that one failure, the bill's three smaller changes were not attempted.
* **Where the line sits:** HB268's 168,725-character Ratified comparison finished in about 6 minutes; SB1041's 393,958 did not finish in 30.
* **NC comparisons over 190,000 characters** (all sessions), 10 comparisons in 6 bills:

  | Bill | Comparison (characters) |
  |---|---|
  | SB257 | Ratified 2,919,859; Edition 4 1,572,756; Edition 2 1,360,447 |
  | HB40 | Edition 4 498,375 |
  | SB1041 | Edition 2 393,958 |
  | HB921 | Edition 2 270,004 |
  | SB445 | Ratified 200,412 |
  | HB125 | Ratified 196,299 |

  Those six are the bills likely to fail the same way, each holding the model for 30 minutes. Everything else is under 170,000 characters.
* **This is a known gap, so no new code ticket:**
  * SYNC-120: very large changelog diffs. Utah's run left six bills without one; every state is exposed.
  * AGENTS-163 (In Review): caps runaway generations.
* **Probably the same cause in October:** SB1041 is also the one bill the 10-19 to 10-21 run left without any row. Not verified: the Mac log only goes back to 11-15.

## Answer 2: the scale. You are right, and my count was wrong.
* **What I counted:** documents whose `diff_from_previous_version` IS NOT NULL. That gave 3,550 in 2,336 bills.
* **The mistake:** 2,621 of those are empty strings. The first full version of each bill, and versions whose text did not change, store `''` rather than NULL. The pipeline treats them as having no comparison.
* **Counting non-empty comparisons on the Mac replica:** 2025 has 929 in 474 bills, and 2025E1 has 1 in 1. That is **930 in 475 bills, exactly your figure**.
* So your ~340 candidates (~330 still to do) are the right scale.

## The choice (Ramon's; a GO follows his answer)
* **(A, my recommendation)** Run your ~330 candidates, leaving out SB257, HB40, SB1041, HB921, SB445 and HB125. They wait for SYNC-120's fix. This saves up to six 30-minute timeouts, and the 5% stop line stays meaningful.
* **(B)** Run all ~340 as they are. Count a timeout on those six as expected, not against the 5% stop line.

Not authorized: any batch before the GO; anything else in `da02e43`'s "Not authorized" list.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
