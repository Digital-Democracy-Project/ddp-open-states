# PROPOSAL (Ramon asked me to send it): narrower no-restart windows for ddp-sync (and a question on the broker's)

Ramon, 11-25 ~02:55 UTC: "we've moved a lot of things to fargate and we've internalized the broker scorecard build chain, so that we have much more latitude to push fixes without waiting ages for a quiet window". This is a **proposal for you to confirm or correct**; I keep the old rules until you and Ramon say otherwise, and I change nothing.

## Why the old rule exists, and why it is blunt
The rule I have used ("never 02:15-04:45 UTC for ddp-sync") is a proxy: it brackets the nightly starts I remembered (WA 02:30, USA 03:00, PA 04:00). Two real risks sit behind it, and they are narrower than that window:
1. **A scheduled start that falls in the restart's downtime may be skipped.** ddp-sync is down about 10-15 s for a recreate (11 s observed: "RESTART 01:30:28, up 01:30:39"; the scheduler registers its jobs about 6 s after start). The scheduler is `AsyncIOScheduler` with `coalesce=True` and `misfire_grace_time=3600` (scheduler.py:485-486), but I found **no persistent job store** (no jobstore setting in src/ddp_sync), so the grace applies only to jobs the *running* process already holds: **a trigger time inside the downtime is, as far as I can tell, simply skipped.** Please confirm that. The exposure is then only about [T - 20 s, T + 5 s] around each trigger time T.
2. **Work in flight inside the container:** a load that is running (a local `cloud_loader` subprocess for every state except az) is killed and leaves a 24 h S3 lock; the people pull/refresh runs in the container too; LegBot hand-off waits (EC2 -> Mac trigger, up to 3,600 s) and background LegBot runs end with the process (SYNC-179). Collections (Fargate) resume from Redis; archives are lost for their follow-ups until #312 is live (your e6a8927 correction).

## The real trigger times (read from the live ddp-sync /schedule at 02:50 UTC; 35 jobs)
- **Daily:** 00:30 cadence review; 02:30 WA; 03:00 USA and the people pull; 04:00 PA; 06:20 jurisdiction drift check.
- **Weekly:** **Sun 02:00** (16 states at once: fl hi ia id ky md me mi mo ms mt nd nm ok ri wy); **Sun 10:00** people refresh; **12:00:** Mon ma, Tue ut va, Wed az nc, Thu la ne, Fri al ga, Sat nv or.
- **Monthly:** the 1st 07:00 grantbot.
- Note the 12:00 starts (Mon to Sat) and the Sunday 10:00 people refresh are **not** inside the old window at all.

## Proposed rule (replaces the 02:15-04:45 window)
1. **Never within [T - 2 min, T + 1 min] of any trigger time above** (generous against the 15 s exposure; I can read the times from /schedule at run time so the list cannot go stale).
2. **In-flight guard, checked three times a few seconds apart:** no run in its load phase (log); no local `cloud_loader` process; no `ddp-scrapers-db` task whose **`lastStatus`** is not STOPPED (from the RUNNING and the STOPPED lists); **plus two I do not check yet:** no people pull or refresh in progress, and no LegBot hand-off waiting for a result. Could you tell me how to read those two (an `activity` record? a Redis key?). **Once #312 is live** the archive part of the third check can go; **once a state loads on Fargate (az first)**, the load check no longer applies to it.
3. **Keep a specific hold only where a canary needs it** (today: nothing between 11:30 and 12:30 UTC for Arizona's first Fargate load; drop it after).
4. Review again when more states load on Fargate and when OPEN-881/882 move the unmatched-voter check and people refresh to tasks: rule 2 then shrinks to "no local-load state is loading".

## Questions
- **ddp-sync:** do you agree with the exposure estimate (no persistent job store, so skipped, not caught up)? Is there anything else that a restart breaks that I have not listed?
- **Broker and api-v3 (Ramon mentioned the scorecard chain is now internal):** I have been applying "no broker restart 05:00-07:40 UTC, none during the 08:00-08:45 Webflow job, no api-v3 restart 05:00-07:00 UTC", and I found on 11-24 that celery is **never idle** (the 30-minute data_update_chain re-queues itself), so the wait-for-idle gate cannot be met and I used a warm shutdown (the worker drains, the container restarts itself, queued tasks stay in Redis). Which of those windows still has a reason now? What does the scorecard chain do if the worker restarts mid-chain (resume, re-run, or leave stale rows)? If it is safe, I would propose: broker/celery restart any time by warm shutdown outside the chain's own run, api-v3 restart any time (about 6 s down).
- I will not relax any rule until you and Ramon confirm in a note or in my session.
