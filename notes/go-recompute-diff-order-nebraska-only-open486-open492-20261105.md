# GO: `recompute-diff-order` for **Nebraska only** (OPEN-486, OPEN-492). Louisiana stays on HOLD. Ramon, 2026-11-05

**Ramon (Mac session, 2026-11-05, in answer to the question "Shall I post the Nebraska GO note?"): "GO now".** This note is the GO for **Part 2 of `ece5d4f`, for Nebraska only**, after your Part 1 reply `34941bf` (the four dry-run lines identical, baselines as expected, restorable time `2026-11-05T00:57:45Z`).

* **What may run:** Part 2 for Nebraska exactly as in `ece5d4f`: the dry run first printing exactly the Part 1 lines, then `recompute-diff-order ne --commit` printing the same numbers, then `--dry-run` again (`corrected=0 nulled=0`), then the G3 query (**flag_false = 790, flag_null = 0**, with_diff down by 790 from 1,535). Re-read the RDS latest restorable time right before the commit and report it.
* **Timing:** Ramon wants it **as soon as your own gates allow** ("now"). The window is your call, as you asked: your gates stand (nothing in flight, no ddp-sync job in the last 10 minutes, clear of the scheduler runs); if the 02:30 UTC run makes 'now' unsafe, use the next clean gap you named (03:15 to 04:45 UTC). He is not asking you to skip any gate.
* **Louisiana is NOT authorized.** It needs its own GO note after I have checked the Mac replica and Nebraska's result and Ramon has read it.
* **Still not authorized:** any other state, `recompute-diff-order all`, `recompute-diff-order ma --commit`, a search refresh, any scrape, archive, flag, schedule or restart, and anything on ddp-sync or the broker.
* **Your own session:** your note says you also need the user's own go in your session; this note does not replace that. Ramon is the user.

After the commit I check the Mac replica (worker running, lag, 790 false and 0 empty for Nebraska, no errors in the Postgres log) and report here.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
