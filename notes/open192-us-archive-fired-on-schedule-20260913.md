# OPEN-192: `us` archive job fired on schedule for real -- first genuinely automatic archive run ever on this host

Confirmed: `openstates_archive` scheduler ran the `us` job exactly on time --
`apscheduler.executors.default INFO Running job "OpenStates: bill-document archive (us)
(trigger: cron[day_of_week='sun', hour='5', minute='0']...)" (scheduled at 2026-09-13
05:00:00+00:00)`. Real Fargate task launched (`e547f81775b445ddb3688fad76c093e2`), confirmed
`RUNNING`, fresh CloudWatch log (~2 min old at last check) showing genuine document fetches
(`GET https://www.govinfo.gov/content/pkg/PLAW-119publ39/uslm/PLAW-119publ39.pdf`) -- real
work, not a startup crash.

This is the first time archiving has ever fired on its own automatic schedule on this host --
every prior success (rev23, GLACIER_IR proof, etc.) was a manual validation trigger. Will
report the final result once it completes; not waiting on that to post this milestone since
it may run a while (`us` is by far the largest jurisdiction).
