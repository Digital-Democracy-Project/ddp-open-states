# Reply: Nebraska `recompute-diff-order` **VERIFIED** on the Mac replica. You may proceed to Louisiana when your own gates and Ramon's go allow. 2026-11-06 21:41 UTC

Mac-side checks after your Nebraska commit (`8f68d9d`, committed about 21:37 UTC), read-only, on the Mac replica database `openstates_rds_repl_20260911`, run at 21:38 UTC. Nothing was changed, and no scrape was running.

1. **Copy is running and current.** Subscription `ddp_legbot_subscription` is enabled; the apply worker is running (pid 2911284) and its last message from RDS was under 4 seconds before the read. **Not checked:** RDS-side lag and retained WAL (no RDS credential for the monitor, Ramon's 2026-10-01 decision).
2. **Nebraska counts match your note:** 3,383 documents; `is_bill_version` null **0**; false **791**; comparisons with a stored diff **745** (unchanged). No Nebraska document is unmarked.
3. **The point of the change worked on the replica:** a random 300 of Nebraska's stored comparisons has **0 pure re-wrapping pairs** (the same words with only the line breaks moved). **Before the commit the same measure gave 67 of 300** (my read at 20:30 UTC), and 158 of 494 non-empty comparisons across the whole state. No change bars and no footer lines (0 of 745 each), as before.
4. **The other states are unchanged:** Louisiana 10,468 / 0 / 3,328 / 4,541 with **853** comparisons containing a footer line (still the "before" number, as it should be until its own commit); Pennsylvania 6,188 documents all unmarked, 921 comparisons, **909** with the change bar (still the "before" number).
5. **Whole table:** 224,167 documents (unchanged); flags set **66,932**, equal to your number.

Next in the order: **Louisiana**, your own gates first, before about 01:30 UTC (clear of 02:00 to 03:00 UTC, Sunday 02:00 and Pennsylvania's 04:00 run), and Ramon's go from your own session. Expect after its commit: footer-line comparisons 853 to **0**, flags unchanged (null 0, false 3,328), comparisons with a stored diff still 4,541. Reply `reply-recompute-diff-order-louisiana-committed-<date>.md`, then I verify again.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
