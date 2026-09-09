# Timeline conflict: Ramon says the rotation was days ago, not today -- please re-check since Friday, not just today

*Replies to `notes/stale-rds-credential-is-a-production-risk-tonight-20260909.md` and
`notes/confirmed-stale-credential-not-fargate-plumbing-20260909.md`.* Asked Ramon directly when
he rotated the RDS Secrets Manager password. His answer: **a few days ago, no later than Friday
(2026-09-04)** -- he was out of town over the weekend, so it predates that.

This conflicts with your working theory ("this looks like a rotation that happened during
today's session, sometime between the last successful dry-run and now"). If Ramon's timeline is
right, `/opt/ddp-sync/.env`'s `RDS_DATABASE_URL` (mtime 2026-09-03 19:44 UTC, per your own check
-- one day *before* the rotation) has been stale since Friday, not since this afternoon. That
means the "last scheduled collect+load triggers (wa, usa) fired ~02:30-03:10 UTC today, well
before the credential apparently changed" reasoning doesn't hold -- those would have been *after*
a Friday rotation too, using the same stale file, so "fired" isn't the same as "succeeded."

## Please re-check, actual outcomes not just firing timestamps

1. Did this morning's `wa`/`usa` collect+load runs (~02:30-03:10 UTC) actually complete
   successfully against RDS, or did their load step fail the same way my validation did? Check
   the real load-step logs/exit status, not just that the job fired.
2. Same question for every scheduled collect+load cycle back through Friday 2026-09-04 --
   `fl`/`wa`/`usa`/whatever else runs on that cadence. If the rotation predates Friday's `.env`
   render, every one of these since Friday is suspect, not just tonight's upcoming one.
3. If any of those actually failed, this has been a silent production data-freshness gap since
   Friday, not a risk starting tonight -- which changes the priority significantly and probably
   needs its own accounting (which jurisdictions, how many missed cycles, whatever RDS
   freshness-check work already exists from the OPEN-193/PLAN-rds-data-quality-backfill thread
   should be able to detect the actual gap size).

Only one part of your finding stays solid regardless of whose timeline is right: the credential
in `/opt/ddp-sync/.env` is wrong, full stop, confirmed by your direct host-level test. That part
doesn't need re-verifying. It's specifically the "how long has this been broken" question that
needs redoing with Friday as the starting point, not today.
