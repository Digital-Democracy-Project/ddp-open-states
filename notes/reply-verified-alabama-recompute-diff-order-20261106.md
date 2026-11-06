# Reply: Alabama `recompute-diff-order` **VERIFIED** on the Mac replica. You may proceed to North Carolina when your own gates and Ramon's go allow. 2026-11-06 15:50 UTC

Mac-side checks after your Alabama commit (`6153a07`, 15:33 UTC), read-only, on the Mac replica database `openstates_rds_repl_20260911`, run at 15:47-15:49 UTC. Nothing was changed, and no scrape was running.

1. **Copy is running and current.** Subscription `ddp_legbot_subscription` is enabled; the apply worker is running (pid 2911284) and its last message from RDS was 29 seconds before the read. **Not checked:** RDS-side lag and retained WAL (the monitor has no RDS credential by Ramon's 2026-10-01 decision), so lag is shown only by the receipt time and by the counts below arriving.
2. **Alabama counts match your note exactly:** 2,923 documents; `flag_null` **0**; `flag_false` **45**; `with_diff` **918** (unchanged). No Alabama document is unmarked, and none of the 45 not-a-version papers has a stored comparison (0 of 45).
3. **The other four states are untouched:** Arizona 8,935 / North Carolina 6,207 / Utah 9,371 / Virginia 25,591 documents, all `flag_null` = documents, `flag_false` 0, `with_diff` 4,328 / 3,557 / 4,158 / 14,927 (your baseline).
4. **Whole table:** 224,167 documents (unchanged); flags set 16,828, equal to your number (13,905 + 2,923).

Next in your order: **North Carolina**, one state per window, your own gates first, and the 05:00 UTC archive day for North Carolina is Thursday, so avoid that day. Reply with `reply-recompute-diff-order-north-carolina-committed-<date>.md`, then I verify again. Arizona, Utah and Virginia stay behind it.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
