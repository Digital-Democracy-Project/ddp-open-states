# Request (read-only): read the all-states probe's output (55 Fargate probe tasks, OPEN-460), 2026-10-31 about 18:45 UTC

Ramon gave the go and I launched the all-states probe at 18:39 to 18:41 UTC with the tool (`probe-on-fargate --all`), on `ddp-scrapers` revision 43 (v40). **Nothing here changes anything: do not stop, restart, re-run, launch, pull or edit anything.** Please do not print or commit secrets: the tail of each log is botocore DEBUG upload headers that include the task role's session token; redact it as you did for Colorado.

## What was launched
* **55 tasks, one per state**, launched in three waves 30 s apart, all with `RUNNER_SCRIPT=verify-jurisdiction`, command `<st> --fargate --sample-bills 10 --max-objects 200`, `MEMORY_PREFIX=dev-probe-all-20261031`, `RUN_ID=probe-<st>-20261031`. States: ak al ar az ca co ct dc de fl ga gu hi ia id il in ks ky la ma md me mn mo mp ms mt nc nd ne nh nj nm nv ny oh ok or pa pr ri sc sd tn tx us ut va vi vt wa wi wv wy (Michigan is refused by the probe and not launched; `us` is USA). No database, no import.
* Colorado is the 18:30 UTC canary (task `9599e11f70f041b789825e50de378eef`, exit 0); the tool reused it instead of starting a second one.
* Output per state: `s3://ddp-openstates-scraper-memory/dev-probe-all-20261031/probe/<st>/probe-<st>-20261031/` (`result.json` last, `report.md`, `sample.tar.gz`). Logs: `/aws/ecs/ddp-scrapers`, streams `scraper/scraper/<task id>`.
* At 18:41 UTC the tool showed 13 finished and uploaded, 1 stopped otherwise, 41 running. **I will post an update with the final exit codes per state** when the last task stops (expected within about 30 minutes; slow states take longer). **Please wait for that update before reading**, so nothing is still running.

## What I need (after my update)
1. **Per state, committed unchanged to this branch under `notes/probe-all-20261031/<st>/`: `result.json` and `report.md`.** Skip `sample.tar.gz` unless I ask for a state's (a 55-state commit of samples would be large). If a state has no `result.json`, say so (the upload did not finish).
2. **A one-line digest per state** from the log, for any state that did not end exit 0 or whose report is RED: the last 10 log lines, and any `406`, `403`, `HTTPError`, `Traceback`, `refus`, `block`, `WAF` or `ERROR` line (verbatim, redacted).
3. Object count and total size under the prefix, and whether anything was written outside it (`working-tier/`, `prod/`, other probe prefixes).

## What I will do with the answers
Read all 55 reports, rank the states by how much is already green or yellow (A through J, with the new gates), and bring Ramon the list for the pilot #2 choice (OPEN-447) and for the Stage 0 manifest entries (OPEN-461).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
