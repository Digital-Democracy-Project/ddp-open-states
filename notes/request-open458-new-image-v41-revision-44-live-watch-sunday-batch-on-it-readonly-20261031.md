# Request (read-only): the scrapers image moved again: v41 = `ddp-scrapers` revision 44 is live; please watch Sunday's batch on revision 44, not 43. 2026-10-31 about 22:25 UTC

Ramon asked for the rebuild and the push live ("all the code is merged into main. let's rebuild and push live"). **Nothing here asks you to change anything: do not stop, restart, re-run, launch, pull or edit anything.** Please do not print secrets.

## What happened
* I ran `deploy-scrapers-image.sh` from `main` at `ce8a2ff` (it builds, runs its in-image checks including a real Utah bill through the scrape path, pushes, registers). Image **v41** pushed; **`ddp-scrapers` revision 44 registered at 22:19:44 UTC** (previous: revision 43 on v40). I read the revision back from AWS. **No task was running** on the cluster before (0) or after (0). Revision 44 is live for every state.
* What v41 adds over v40 (all probe-side; no scraper file and neither fork changed since v39; both forks' last commits are from 10-27): the probe no longer dies with no report when one gate crashes (OPEN-470, Vermont's generator); `mdbtools` in the runtime stage (OPEN-471, New Mexico's `mdb-export`). The Mac-side fixes (OPEN-472) are not in the image.
* Rollback: `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:44` (the family then resolves to 43 again; running tasks keep their image). **Stop and report; do not roll back on your own.**

## What I need (read-only)
1. **Sunday 11-01 02:00 UTC weekly batch (FL, VA, MI, MA, UT, AZ, NC) and the daily WA 02:30 and USA 03:00 launches:** say whether each ran on **revision 44** (your role cannot read ECS: give me the task ids or the start times and I will read the revision from the Mac), whether it finished, anything off (traceback, block, `WAF` line, a new `mdb-`/package error), and duration against last week's. Counts after the chain against your 10-30 baseline (a drop of more than 2% in bills or 5% in vote events is not normal).
2. Your earlier Part 3 request (watch on revision 43) is **superseded**: the batch will run on 44.

## What I will do next
After Ramon agrees, probe Vermont and New Mexico on Fargate on revision 44 (they are the two states the new image fixes), with their own `dev-probe-...` prefix; I will post what I launched and ask you to read the output the same way as before.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
