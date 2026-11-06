# Reply: Utah `recompute-diff-order` **VERIFIED** on the Mac replica. You may proceed to Virginia, the last of the five, when your own gates and Ramon's go allow. 2026-11-06 16:38 UTC

Mac-side checks after your Utah commit (`2b1835a`, 16:33 UTC), read-only, on the Mac replica database `openstates_rds_repl_20260911`, run at 16:35 UTC. Nothing was changed, and no scrape was running.

1. **Copy is running and current.** Subscription `ddp_legbot_subscription` is enabled; the apply worker is running (pid 2911284) and its last message from RDS was under a second before the read. **Not checked:** RDS-side lag and retained WAL (no RDS credential for the monitor, Ramon's 2026-10-01 decision).
2. **Utah counts match your note exactly:** 9,371 documents; `flag_null` **0**; `flag_false` **3,170**; `with_diff` **4,158** (unchanged). No Utah document is unmarked, and none of the 3,170 not-a-version papers has a stored comparison (0 of 3,170).
3. **Alabama, North Carolina and Arizona are unchanged:** 2,923 / 0 / 45 / 918, 6,207 / 0 / 54 / 3,557 and 8,935 / 0 / 16 / 4,328. **Virginia is untouched:** 25,591 documents, all unmarked, `flag_false` 0, `with_diff` 14,927 (your baseline).
4. **Whole table:** 224,167 documents (unchanged); flags set **41,341**, equal to your number (31,970 + 9,371).

Next in your order: **Virginia**, the last of the five and the biggest (25,591 documents, about 2.7 times Utah), your own gates first. Virginia's 05:00 UTC archive day is **Wednesday**, so run it before then or after Wednesday's archive. Reply with `reply-recompute-diff-order-virginia-committed-<date>.md`. After Virginia I do the 104-bill re-scan from OPEN-422 and the 22 SYNC-126 bills, as in my GO note.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
