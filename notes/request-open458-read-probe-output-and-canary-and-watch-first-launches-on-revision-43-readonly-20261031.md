# Request (read-only): read the Colorado probe's output on the new image (v40, revision 43), run or watch an Arizona canary, and watch the first launches

2026-10-31 about 18:10 UTC. Ramon asked me to ask you for what I need. **Nothing here changes anything: do not stop, restart, re-run, launch, pull or edit anything** unless Part 2 says so. Please do not print secrets (log lines, counts, ids and file contents only).

## What happened (for the record)
* Ramon built and pushed the scrapers image **v40** from `main` at the #310 merge (adds the manifest-driven Michigan refusal, the Stage 3 checks and the voter-attribution gate to the probe; **no scraper file and neither fork changed since v39**, both forks' last commits are from 10-27). The script stopped at its confirm prompt, so at my side I registered **`ddp-scrapers` revision 43 on v40 at 16:28:52 UTC** (previous: revision 42 on v39; nothing was running; I read both back from AWS). **Revision 43 is live for every state.** Rollback: `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:43` (the family then resolves to 42). **Stop and report; do not roll back on your own.**
* Ramon also had me deregister the unused `ddp-scrapers-probe:1`. The probe stays on `ddp-scrapers`.
* At 18:00 UTC I launched one Colorado probe task on revision 43: task id `deab5ca9b4bc436bb2483854926a2062`, command `co --fargate --sample-bills 10 --max-objects 200`, `MEMORY_PREFIX=dev-probe-co-20261031`, `RUN_ID=probe-co-20261031-v40`. It ran 18:00:44 to 18:06:37 UTC and **exited 0** (my keys can read the exit code, not the log). No database, no import.

## Part 1. Please read and give me the probe's output
1. **The log** (group `/aws/ecs/ddp-scrapers`, stream `scraper/scraper/deab5ca9b4bc436bb2483854926a2062`): the first 60 lines and the last 30, verbatim, and any `406`, `HTTPError`, `Traceback`, `refus` or `ERROR` line. I want to see that the new gates ran (I and J) and that nothing failed to import (`qa_primitives`, the manifest files).
2. **The three files** under `s3://ddp-openstates-scraper-memory/dev-probe-co-20261031/probe/co/probe-co-20261031-v40/`: `result.json` (uploaded last: if missing, the upload did not finish), `report.md`, `sample.tar.gz`. Please **commit all three unchanged to this branch under `notes/probe-co-20261031/`**. If one is too big, say its size.
3. Object count and total size under that prefix, and whether anything was written outside it (for example under `working-tier/`).

## Part 2. The Arizona canary (your call on who launches it)
Image v40 changes no scraper file, so this only shows that a real scrape still runs on revision 43. Either launch the RUNBOOK's incremental Arizona run yourself (the 10-27 canary took about 82 min) or tell me you would rather I ask Ramon to launch it. Today's quiet window runs to **Sun 11-01 02:00 UTC**. After it: exit status, duration, any traceback, and Arizona's counts against your 10-30 baseline (bills 2,190, vote events 3,411, person votes 75,720).

## Part 3. Please watch the first launches on revision 43 (read-only)
* **Sat 05:00 UTC archive AL already ran on 42 or earlier; the first on 43 are** Sun 11-01 02:00 UTC FL and the weekly batch (VA, MI, MA, UT, AZ, NC), Sun 02:30 WA, Sun 03:00 USA (lower then upper). Please say, for each, whether it ran on revision 43, finished or is running, and anything off (traceback, block or `WAF` line), with duration against last week's.
* **Counts after the Sunday chain**, same fields as your baseline; a drop of more than 2% in bills or 5% in vote events is not normal.

## What I will do with the answers
Finish the probe's Mac half (`verify-jurisdiction co --from-dir ...` with the people loaded first), record results on OPEN-458, 459, 460, 445, 261, 464 and 447, and tell Ramon whether revision 43 looks healthy. After a clean canary, `probe-on-fargate --all` is the next launch and needs Ramon's go.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
