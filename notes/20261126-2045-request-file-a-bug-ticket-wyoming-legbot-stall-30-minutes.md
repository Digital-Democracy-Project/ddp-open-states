# REQUEST (Ramon asked): please file a bug-fix ticket for the Wyoming LegBot stall of 11-26: a 30-minute pause with no GPU and no memory use

Ramon's words: file a bug fix ticket for this Wyoming CAMS stall; he saw no GPU and no memory use, so the dev will need to read the logs to find the problem. This role cannot read the Mac's logs (it has no access), so the evidence below is what the broker and the Mac's run record show from EC2.

## What happened (times UTC, 11-26)
* Run `legbot-session-1b1442a4c176`: Wyoming `2026`, a random sample of 100 bills (the saved list of bill ids is on my host, in the ops folder as `legbot-sample-or-wy-20261126.json`), sent through the Mac's ddp-sync `/ddp-sync/v1/trigger/bill-artifact-generation` in background mode, `X-DDP-Environment: prod`, the nine standard artifact types, concept statements on, org research off, no policy-statement step. Accepted 19:49:22.
* **19:49:29 to 19:50:28: HB 140, SF 32 and HB 114 were processed normally** (25 artifacts in 66 s; two bills at a time).
* **19:50:28 to 20:20:11: nothing was written, for 29 min 43 s.** The Mac's run record stayed `running` and its `updated_at` kept advancing every minute, so ddp-sync was alive. No other state wrote an artifact in that time either (the newest write from any state was 19:50:28). No pending placeholder row for Wyoming. Ramon saw **no GPU and no memory use** on the Mac for the whole gap.
* **20:20:11: the 4th bill, SF 87, started and finished in 12 s, and the run then went on normally**, two bills at a time (HB 2, HB 128, SF 58, HB 66 and on). By 20:29: 210 artifacts for 26 bills, 194 complete, 16 failed, all `generation` / `insufficient_information`.
* **Not the data:** production's api-v3 returns text for every one of the 100 sample bills (including SF 87, 880 characters, and HB 2, 8,753). I could not query the Mac's own api-v3 from EC2 (no key); Ramon can.
* **Oregon, run the same way earlier (`legbot-session-bccd617bfe5d`, 18:45 to 19:45), had no such gap.**

## What I do not know (please find out)
* What the Mac waited on for ~30 minutes. Candidates I can only name, not prove: a queue or lock wait before CAMS accepted the bill (ddp-sync's `legbot_queue_wait_timeout_seconds` is 3,600 and the dispatch timeout is 1,200); a timeout of 1,800 s somewhere; a stuck poll or connection between ddp-sync and CAMS; CAMS holding a turn for something else; the pause happening exactly when the Mac's MLX was idle. The gap length (about 1,800 s) looks like a timeout, which is a guess.
* Whether it can recur on a real run (the automated hook sends whole sessions). A silent 30-minute pause is not visible at the broker and the run record shows only `running`.

## Where to look
The Mac's ddp-sync log and CAMS log for run id `legbot-session-1b1442a4c176` between about 19:50 and 20:20 UTC, and the CAMS task list for that window.

## Not changed
No run was cancelled or restarted; nothing on production was changed for this. The sample is still being written (Wyoming's totals will follow in my next result note).
