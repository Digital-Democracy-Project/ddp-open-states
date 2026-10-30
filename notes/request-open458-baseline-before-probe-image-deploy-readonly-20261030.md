# Request (read-only): baseline before a scrapers image deploy that adds the onboarding probe (OPEN-458)

2026-10-30 about 18:15 UTC. Ramon asked me to ask you. **Nothing here changes anything: no pull, no restart, no launch, no edit, no flag.** Please do not print secrets (counts, ids and times only). **No deploy has happened and none is scheduled yet**; Ramon picks the window after reading your answer.

## What is planned
Ramon will run `deploy-scrapers-image.sh` on the Mac (the RUNBOOK's one command) to build the next scrapers image and register it as a new `ddp-scrapers` task-definition revision. One family serves every state, so every launch after that uses the new image.

## What changes (checked, not assumed)
* Live now, read from the Mac at 18:10 UTC: `ddp-scrapers` revision **41**, image **v38**, no task running on the cluster.
* Files baked into the image that changed on ddp-open-states `main` since 10-27: **only `verify-jurisdiction`** (the onboarding probe, OPEN-446, 456, 458) and the Dockerfile's `COPY` line that adds it. `cloud_collector.py`, `cloud_archiver.py`, `cloud_text_extract.py`, `import-summary.sh` and `docker-entrypoint.sh` are unchanged.
* The two scraper forks (`openstates-scrapers`, `openstates-core`) have no commit after 10-27 21:44 UTC; v38 was registered at 22:06 UTC the same day, so the rebuild should carry the same scraper code. I have not read the build itself.
* So no scrape's behaviour should change. The reason for a baseline anyway is the RUNBOOK's rule: the revision moves every state at once.

## Please read and answer
1. **Launches due.** Every scheduled scrape, archive and cadence-review launch due from now until Monday 2026-11-02 00:00 UTC (state, time UTC), including the weekly Sunday batch, and anything running or queued now.
2. **The baseline the OPEN-437 request asked for**, same script and same fields, as of now: per state, bills, vote events and person votes; the newest working-tier run id per state; the duplicate and `H VOTE:`-style check outputs. If a full rerun is expensive, say which parts you skipped.
3. **A quiet window.** The longest gap with no launch due in that period (start and end UTC), so Ramon can pick a time to register the revision.

## What I will do with the answer
Record it on OPEN-458 and give Ramon the window. After the deploy I will ask you for the same counts again and compare, and I will ask for one canary state by hand (never Michigan), as the RUNBOOK's "Canary first" section says.

## Not asked
Please do not build or pull anything. Building is the Mac's job.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
