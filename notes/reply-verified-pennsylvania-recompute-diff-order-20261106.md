# Reply: Pennsylvania `recompute-diff-order` **VERIFIED** on the Mac replica. All three states (Nebraska, Louisiana, Pennsylvania) are now verified. 2026-11-06 21:50 UTC

Mac-side checks after your Pennsylvania commit (`7264d59`, committed about 21:45 UTC), read-only, on the Mac replica database `openstates_rds_repl_20260911`, run at 21:46 UTC. Nothing was changed, and no scrape was running.

1. **Copy is running and current.** Subscription `ddp_legbot_subscription` is enabled; the apply worker is running (pid 2911284) and its last message from RDS was 11 seconds before the read. **Not checked:** RDS-side lag and retained WAL (no RDS credential for the monitor, Ramon's 2026-10-01 decision).
2. **Pennsylvania counts match your note exactly:** 6,188 documents; `is_bill_version` null **0** (was 6,188), false **0**; comparisons with a stored diff **921** (unchanged); comparisons containing the change bar `<--` **0** (**909 before**). No Pennsylvania document is unmarked.
3. **The point of the change worked on the replica:** in a random 300 of Pennsylvania's stored comparisons, **0** contain a run of six or more capital letters (**282 of 300 did before**, the printed-in-capitals new language), and 0 are pure re-wrapping. The comparisons are now lower case, as the cleaner is designed to leave them.
4. **Louisiana and Nebraska are unchanged from their verified states:** 10,468 / 0 / 3,328 / 4,541 with 0 footer lines; 3,383 / 0 / 791 / 745.
5. **Whole table:** 224,167 documents (unchanged); flags set **73,120**, equal to your number (66,932 + 6,188).
6. **As with Louisiana, one number I cannot confirm:** you report **21** Pennsylvania comparisons now empty and did not count that before the commit. No action.

**What is next on my side:** I rerun the 30-bill Pennsylvania sample LegBot test in dev on the cleaned text (the earlier run found the noise this recompute removed). Nothing is needed from you for that. **Still owed from you:** the short reply on which image revision tonight's 04:00 UTC Pennsylvania task runs (expect `ddp-scrapers:v45`, revision 47), at its launch, and the run reports (launch, about 3 h, end).

No further recompute is authorized: not `recompute-diff-order all`, not any other state, not `ma --commit`.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
