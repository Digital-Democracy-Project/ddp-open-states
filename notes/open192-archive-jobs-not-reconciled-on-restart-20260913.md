# OPEN-192: real gap found -- openstates_archive's Fargate jobs have no OPEN-251-style reconciliation

Just illustrated live, not hypothetical: restarting `ddp-sync` to deploy PR #145 (needed for
OPEN-285's DATABASE_URL fix) restarted while the `us` archive job (fired on schedule at 05:00,
see `notes/open192-us-archive-fired-on-schedule-20260913.md`) was still running. The scrape
side's own MA job correctly showed up as resumed
(`cloud_scrape: resuming a Fargate job orphaned by a previous restart jurisdiction=ma ...`) --
`openstates_archive.py` has no equivalent. Confirmed by grep: no
`inflight_fargate_jobs`/`record_started`/`reconcile` references anywhere in that file at all.

**Real consequence**: the `us` archive task itself is unaffected -- confirmed still `RUNNING`
in ECS, real work continuing (S3 uploads/RDS writes happen inside the Fargate task, independent
of `ddp-sync` watching it). But nothing in `ddp-sync` is watching for it to finish anymore --
no flow-status update, no Slack alert on completion or failure, same "collected but nobody's
watching" gap OPEN-251 was built to close for scrape jobs, just never extended to archive.

Not urgent (I'm watching this specific task manually via ECS/CloudWatch to get its real result),
but worth porting OPEN-251's same mechanism to `openstates_archive.py` at some point -- a
restart during a real, multi-hour `us` archive run (this one especially, by far the largest
jurisdiction) will keep recurring as a real risk otherwise, especially now that the scheduler
is genuinely live and archive jobs will keep firing weekly.
