# REPLY to `e679d4f`: the US 118/119 re-import start. Recommended route: a ddp-sync start option (SYNC-181), on Ramon's pick. 2026-11-20 (Mac side, State Specific Handling)

**Not a GO.** Nothing to start. Thank you for stopping and reporting instead of changing code. Ramon picks the route; until he does, Part B of `5836c52` stays waiting.

## Recommended: a full re-import option on ddp-sync's trigger (filed as **SYNC-181**, not built)
* **What it is:** `/trigger/openstates-scrape/<state>` gains a full re-import of named sessions, for example `?full=true&sessions=118,119`. It means no `start=` cutoff, those sessions only, then the normal load.
* **The lock is held for the whole run:** renewed while the task runs, or one session at a time under one lock. A nightly for the same state is refused at every point, including past 24 hours.
* **Why this route:**
  1. **It keeps the lock.** A Fargate task started by hand from the Mac does not take ddp-sync's source lock (OPEN-187). So the 03:00 UTC `usa` nightly could start beside it unless the `usa` schedule is held, which needs a `sync_schedule.yaml` change and its own request, every time.
  2. **It is needed again.** Companion phase 2 re-imports every session that holds a polled bill, jurisdiction by jurisdiction (PLAN-companion-lineage §5.3 step 4). A start option serves all of those; the hand route repeats the hand steps each time.
  3. **Your 24-hour warning is real.** About 39,300 US bills against Pennsylvania's roughly 5,300 in about 7 hours: a single run may well pass 24 hours. SYNC-181's acceptance covers it.
* **After it is merged (Ramon's review):**
  * a ddp-sync rebuild on EC2, with the same idle gate as `745a8d1`;
  * then the US start, each step on Ramon's go through a request note from me.

## The other route, if Ramon prefers it
Ramon starts the Fargate collection from the Mac (v69 revision 72 or later, sessions 118 and 119, no `start=`), and you run the loader by hand here on his word, then Part C. It needs:
* **the `usa` schedule held for the whole run:** its own request note, since `sync_schedule.yaml` is not yours to change;
* **118 and 119 run one after the other**, so each stays nearer the lock's 24 hours.

## Also noted
* `/opt/ddp-open-states/.env` at 600: no action from me.
* SYNC-181 blocks OPEN-638's completion; related: SYNC-167 (a stopped scrape's 24-hour lock).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
