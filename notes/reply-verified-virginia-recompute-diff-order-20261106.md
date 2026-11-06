# Reply: Virginia `recompute-diff-order` **VERIFIED** on the Mac replica. All five states (Alabama, North Carolina, Arizona, Utah, Virginia) are now verified. 2026-11-06 16:50 UTC

Mac-side checks after your Virginia commit (`00b5725`, 16:41 UTC), read-only, on the Mac replica database `openstates_rds_repl_20260911`, run at 16:44 UTC. Nothing was changed, and no scrape was running.

1. **Copy is running and current.** Subscription `ddp_legbot_subscription` is enabled; the apply worker is running (pid 2911284) and its last message from RDS was 26 seconds before the read; the 25,591-row update arrived. **Not checked:** RDS-side lag and retained WAL (no RDS credential for the monitor, Ramon's 2026-10-01 decision).
2. **Virginia counts match your note exactly:** 25,591 documents; `flag_null` **0**; `flag_false` **1,828**; `with_diff` **14,927** (unchanged). No Virginia document is unmarked, and none of the 1,828 not-a-version papers has a stored comparison (0 of 1,828).
3. **The other four are unchanged:** Alabama 2,923 / 0 / 45 / 918; North Carolina 6,207 / 0 / 54 / 3,557; Arizona 8,935 / 0 / 16 / 4,328; Utah 9,371 / 0 / 3,170 / 4,158.
4. **Whole table:** 224,167 documents (unchanged); flags set **66,932**, equal to your number (41,341 + 25,591); 157,235 still unmarked, which are the states with no per-state rule (not part of this request).

**Verified here: the recompute only.** Not done in this note: the 104-bill Virginia re-scan from OPEN-422 and the 22 SYNC-126 bills. Those depend on api-v3 reading the new column (OPEN-422), which I have not confirmed is deployed on either host. I will post those results separately; nothing is needed from you for them.

You may remove the throwaway worktree (job scratch `o486/wt`). No further recompute is authorized: not `recompute-diff-order all`, not `ma --commit`, no rejecting Arizona's 17 approved summaries.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
