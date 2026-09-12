# OPEN-193: go ahead on AC6, plus a real check on the other 4 remaining ACs

Ramon wants to finish closing out OPEN-193 for real. I've updated the ticket to reflect your
last note: AC1 is now checked off (load runs next to the DB, `ddp-sync` on EC2 -- confirmed
live by you, pre-dates this session, detail linked back to your `1ef0e04` note).

## AC6 -- go ahead

Please run the freshness measurement you proposed: per-jurisdiction RDS data currency against
real-world activity (most-recent-bill-action timestamp, and/or Fargate run-history watermarks
vs. real legislative activity) for the jurisdictions currently live in `cloud_path`
(fl/wa/usa/va/mi/ma/ut/az/nc, per `sync_schedule.yaml`). No specific methodology has been
decided beyond what you already proposed -- use your own judgment on the exact query/comparison,
just show your work (the actual numbers/timestamps per jurisdiction, not just a pass/fail) so it
can be checked. Report back with real per-jurisdiction results.

## The other 4 ACs -- please check these for real too, same standard as AC1/AC6

I don't have visibility into the EC2 host or `ddp-sync`'s current internals from here, and I'd
rather have you check the live system directly than guess from tickets/docs. For each, please
confirm true/false against the running system, with the evidence (file/config/log reference),
the same way you did for AC1:

1. **Cadence/eligibility/retry/backoff/failure-classification in one place.** Is
   `sync_schedule.yaml` still the single source of policy truth for the EC2 `ddp-sync`
   instance, or has any of this leaked into cloud-native scheduling (e.g. an EventBridge rule,
   an ECS scheduled task, cron on the box) that duplicates/overrides it? Check for any scheduling
   mechanism outside `ddp-sync` itself that could set cadence/retry policy independently.

2. **Path ownership per jurisdiction still decided in that same place.** Per OPEN-208,
   `sync_schedule.yaml` should be the one place that decides which path (Mac vs. cloud) owns a
   jurisdiction. Confirm this is still true post-move -- no jurisdiction's path ownership is
   being decided anywhere else (a hardcoded list in code, a separate EC2-only config, etc.).

3. **Failure triage still reaches Agent Smith across the new EC2/on-prem boundary.** When a
   cloud-path scrape or load fails on this EC2 `ddp-sync`, does that failure actually reach
   Agent Smith's triage loop (however that's wired -- Slack, a queue, a shared log Agent Smith
   polls)? If you can find a real recent failure and trace it through, that's the strongest
   evidence; if none recently, at least confirm the wiring exists and where.

4. **Rollback demonstrated: the load runs on-prem against RDS.** Has this ever actually been
   exercised (on-prem `ddp-sync`/load pointed at RDS, not just asserted as theoretically
   possible)? If yes, when/how, with what evidence. If no, note that plainly -- don't guess or
   simulate one, just report the real state.

Report back on `notes/ops-handoff` when you have real answers (partial is fine -- report
whichever of the 5 remaining items you can check now, don't block one on another). I'll update
the ticket and Jira status from what you find. Not asking you to build anything currently
missing here (e.g., if failure triage doesn't actually reach Agent Smith, that's a real gap to
report and possibly a follow-up ticket, not something to improvise a fix for right now) --
this pass is about getting the real state on record, not shipping new work.
