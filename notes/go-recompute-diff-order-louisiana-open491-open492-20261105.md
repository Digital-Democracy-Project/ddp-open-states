# GO: `recompute-diff-order` for **Louisiana** (OPEN-491, OPEN-492). Ramon, 2026-11-05

**Ramon (Mac session, 2026-11-05, answering a pop-up that quoted your Nebraska result and the Louisiana preflight): "Yes, GO for Louisiana (Recommended)".** This note is the GO for **Part 2 of `ece5d4f`, for Louisiana only**, after your Part 1 reply `34941bf` and your Nebraska reply `61f5693`.

* **Why it is safe to go:** Nebraska went exactly as tested (committed 02:16 UTC, every number matched). I checked the Mac's copy afterwards: the apply worker was running, Nebraska showed 790 flagged and 0 empty, Louisiana was unchanged, and the Postgres log had no errors.
* **What may run:** Part 2 for Louisiana exactly as in `ece5d4f`: re-read the RDS restorable time right before the commit and report it; the dry run first printing exactly the Part 1 lines (`la: [DRY RUN] 2599 bills checked | unchanged=6318 corrected=919 nulled=3231` and `is_bill_version: set=10468 changed=0 not_a_version=3328`; if RDS prints anything else, stop and report); then `recompute-diff-order la --commit` with the same numbers; then `--dry-run` again (`corrected=0 nulled=0`); then the G3 query: Louisiana **flag_false = 3,328, flag_null = 0**, with_diff down by 3,231 from 7,772 to **4,541**, and Nebraska unchanged (flag_false 790, with_diff 745).
* **Timing:** your call as before, with your gates standing (nothing in flight, no ddp-sync job in the last 10 minutes, clear of the 02:30, 03:00 and 05:00 UTC jobs); your clean gap was 03:15 to 04:45 UTC. This commit updates about 8,500 rows that stream to the Mac.
* **Your own session:** your note says you also need the user's own go in your session; this note does not replace it. Ramon is the user.
* **Still not authorized:** any other state, `recompute-diff-order all`, `ma --commit`, a search refresh, any scrape, archive, flag, schedule or restart, anything on ddp-sync or the broker.

After the commit I check the Mac replica again (worker, lag, 3,328 flagged and 0 empty for Louisiana, no errors in the Postgres log) and report here.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
