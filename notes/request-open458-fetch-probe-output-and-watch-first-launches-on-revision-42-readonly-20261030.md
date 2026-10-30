# Request (read-only): fetch the Colorado probe's output, and watch the first launches on the new scrapers image (revision 42)

2026-10-30 about 19:15 UTC. Ramon asked me to ask you for what I need. **Nothing here changes anything: do not stop, restart, re-run, launch, pull or edit anything.** Please do not print secrets (log lines, counts, ids and file contents only).

## What happened (for the record)
* Ramon built and pushed the scrapers image **v39** (it adds the onboarding probe, OPEN-458; no other baked-in file changed since v38) and its step 6 **registered `ddp-scrapers` revision 42 at 19:01 UTC** (previous: revision 41 on v38; no task was running; I read both from the Mac). **Revision 42 is live for every state**; it was not meant to go live before your baseline was re-read, but nothing was running and nothing is due until Sat 10-31 00:30 UTC (cadence review, launches nothing), so Ramon chose to keep it. Rollback if you or he find a reason: `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:42` (the family then resolves to 41 again; running tasks keep their image). **Stop and report; do not roll back on your own.**
* At about 19:05 UTC I launched one probe task for Colorado on revision 42: task id `b012eff6fc9b45e8988b7ae9a7b86bf4`, cluster `ddp-scrapers`, command `co --fargate --sample-bills 20`, `MEMORY_PREFIX=dev-probe-co-20261030b`, `RUN_ID=probe-co-20261030`. It has no database and no import, and writes only under that prefix.

## Part 1. Please read and give me the probe's output
The task should stop within about 15 minutes of 19:05 UTC. If it is still running when you read this, wait for it to stop; do not touch it.
1. **The log** (group `/aws/ecs/ddp-scrapers`, stream `scraper/scraper/b012eff6fc9b45e8988b7ae9a7b86bf4`): the first 60 lines and the last 30, verbatim, and any `406`, `HTTPError`, `Traceback`, `refus` or `ERROR` line.
2. **The task's end:** exit code and stop reason if your role can read them (it could not on 10-30: if not, say so; the last log line is enough).
3. **The three files** under `s3://ddp-openstates-scraper-memory/dev-probe-co-20261030b/probe/co/probe-co-20261030/`: `result.json` (uploaded last: if it is missing the upload did not finish; say so), `report.md` and `sample.tar.gz`. Please **commit all three, unchanged, to this branch under `notes/probe-co-20261030/`** so I can read them here (they are small, public legislative data from leg.colorado.gov, no secrets). If one is too large for a commit, say its size and I will ask for another way.
4. The object count and total size under that prefix, and whether anything was written outside it (for example under `working-tier/`).

## Part 2. Please watch the first launches on revision 42 (read-only)
After the next launches, say whether they ran on revision 42 and whether anything is off:
* **Sat 10-31 02:30 UTC WA scrape** and its archive; **03:00 UTC USA scrape** (lower then upper) and its archives. For each: image tag if you can see it, exit status, any traceback, block or `WAF` line, run id, duration against the 10-30 run (WA about 5.5 min scrape and about 1.5 min archive; USA 03:00 to 04:31).
* **Counts after the 03:00 to 04:31 chain**, same fields as your 18:25 UTC baseline: WA bills 3,411, vote events 2,302, person votes 171,556 and USA bills 39,097, vote events 1,604, person votes 561,033 (small USA growth is normal; a drop of more than 2% in bills or 5% in vote events is not).
* **Sun 11-01 02:00 UTC weekly batch** (FL, VA, MI, MA, UT, AZ, NC): a short note that each started on revision 42 and finished or is still running, when you next read.

## What I will do with the answers
Finish the probe's Mac half (`verify-jurisdiction co --from-dir ...`), record both results on OPEN-458 and OPEN-447, and tell Ramon whether revision 42 looks healthy.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
