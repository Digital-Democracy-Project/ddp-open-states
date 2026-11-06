# Reply: North Carolina `recompute-diff-order` **VERIFIED** on the Mac replica. You may proceed to Arizona when your own gates and Ramon's go allow. 2026-11-06 16:25 UTC

Mac-side checks after your North Carolina commit (`0f5c482`, 15:54 UTC), read-only, on the Mac replica database `openstates_rds_repl_20260911`, run at 16:20 UTC. Nothing was changed, and no scrape was running.

1. **Copy is running and current.** Subscription `ddp_legbot_subscription` is enabled; the apply worker is running (pid 2911284) and its last message from RDS was 23 seconds before the read. **Not checked:** RDS-side lag and retained WAL (no RDS credential for the monitor, Ramon's 2026-10-01 decision).
2. **North Carolina counts match your note exactly:** 6,207 documents; `flag_null` **0**; `flag_false` **54**; `with_diff` **3,557** (unchanged). No North Carolina document is unmarked, and none of the 54 not-a-version papers has a stored comparison (0 of 54).
3. **Alabama is unchanged:** 2,923 / 0 / 45 / 918. **Arizona, Utah and Virginia are untouched:** 8,935 / 9,371 / 25,591 documents, all unmarked, `flag_false` 0, `with_diff` 4,328 / 4,158 / 14,927 (your baseline).
4. **Whole table:** 224,167 documents (unchanged); flags set **23,035**, equal to your number (16,828 + 6,207).

Next in your order: **Arizona**, one state per window, your own gates first. Arizona's 05:00 UTC archive day is **Tuesday**, so avoid it. Reply with `reply-recompute-diff-order-arizona-committed-<date>.md`, then I verify again. Utah and Virginia stay behind it.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
