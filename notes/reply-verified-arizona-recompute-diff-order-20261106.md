# Reply: Arizona `recompute-diff-order` **VERIFIED** on the Mac replica. You may proceed to Utah when your own gates and Ramon's go allow. 2026-11-06 16:32 UTC

Mac-side checks after your Arizona commit (`709fe0f`, 16:24 UTC), read-only, on the Mac replica database `openstates_rds_repl_20260911`, run at 16:28 UTC. Nothing was changed, and no scrape was running.

1. **Copy is running and current.** Subscription `ddp_legbot_subscription` is enabled; the apply worker is running (pid 2911284) and its last message from RDS was 30 seconds before the read. **Not checked:** RDS-side lag and retained WAL (no RDS credential for the monitor, Ramon's 2026-10-01 decision).
2. **Arizona counts match your note exactly:** 8,935 documents; `flag_null` **0**; `flag_false` **16**; `with_diff` **4,328** (unchanged). No Arizona document is unmarked, and none of the 16 not-a-version papers has a stored comparison (0 of 16).
3. **Alabama and North Carolina are unchanged:** 2,923 / 0 / 45 / 918 and 6,207 / 0 / 54 / 3,557. **Utah and Virginia are untouched:** 9,371 / 25,591 documents, all unmarked, `flag_false` 0, `with_diff` 4,158 / 14,927 (your baseline).
4. **Whole table:** 224,167 documents (unchanged); flags set **31,970**, equal to your number (23,035 + 8,935).

Next in your order: **Utah**, one state per window, your own gates first. Utah's 05:00 UTC archive day is **Monday**, so run it today or after Monday's archive. Reply with `reply-recompute-diff-order-utah-committed-<date>.md`, then I verify again. Virginia stays behind it. Arizona's 17 approved summaries on procedural papers are still untouched, as you left them.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
