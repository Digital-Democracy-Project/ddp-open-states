# OPEN-285: sixth bug fixed, PR #146 pushed

Nicely traced. Filed and pushed the fix: `ddp-sync` PR #146
(https://github.com/Digital-Democracy-Project/ddp-sync/pull/146).

Now sets `DATABASE_URL_OVERRIDE` (the variable `activate.sh`'s own OPEN-159 safety gate
actually honors) alongside plain `DATABASE_URL`, so the live-resolved RDS URL survives
`activate.sh` overwriting it back to the local-dev default. Updated the regression test to
assert on `DATABASE_URL_OVERRIDE` specifically so it would have caught this the first time.

Full suite: 1247 passed, no regressions. Not merging it myself -- leaving it for Ramon's
review. Once merged and deployed, please trigger `openstates_people_refresh` again --
seventh attempt. Still holding the crontab removal until you get a real clean run.

Also saw the OPEN-192 reconciliation-gap note and your correction -- updated OPEN-288's Jira
description with the precise version (final flow-status write is real; the actual gap is
narrower, in-flight reconciliation across a restart specifically). No action needed from you
there, just wanted you to know the ticket reflects the corrected diagnosis now.
