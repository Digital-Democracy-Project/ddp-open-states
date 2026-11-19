# REPLY to 5836c5233 Part B (US 118/119 full re-import, hold lifted in 001c60b32): I cannot start it from this host; a trigger option is needed

Written 23:41 UTC 11-19 (date -u at write time), from the production EC2 host. **The user's words in session (pop-up):** when I explained this, they chose **"Ask the dev for a trigger option"**. Nothing was started.

## Why it cannot start from here
1. **ddp-sync's manual trigger has no way to ask for it.** `POST /ddp-sync/v1/trigger/openstates-scrape/usa` runs "the same pipeline as its scheduled job (SYNC-152): scrape every session, then archive, then LegBot" (api/routes/triggers.py, docstring of `trigger_openstates_scrape`). Its only parameter is `skip_people_check`. It cannot take **sessions 118 and 119 only**, and it cannot say **no `start=` cutoff**, so it would run the incremental nightly, which does not re-walk every bill or rewrite every link.
2. **Your other route needs AWS write access, which this host does not have.** `aws ecs run-task` is outside this host's read-only role (`EC2ServiceAccessReadOnlyRole`; even `ecs:DescribeTaskDefinition` is denied). Your note said to report this instead of changing code, so I am reporting it.

## What a start would need (your design; two routes)
- **A trigger option in ddp-sync**, for example `?full=true&sessions=118,119` (or a body field) on `/trigger/openstates-scrape/usa`, that launches the Fargate collection with no `start`, for those sessions only, then the normal load. After it is merged I rebuild ddp-sync (idle gate, the same recipe as the OPEN-633 Part C checkpoint 745a8d189) on the user's go, then start it.
- **Or Ramon starts the Fargate task from the Mac** (he has the AWS access) and I run the loader here when it finishes, then do Part C's read-only checks. (The load step is ddp-sync's `cloud_loader.py`; I would run it by hand in the ddp-sync container only on his word.)

## Things I found that bear on whichever route
- **The US nightly:** ddp-sync's `usa` job runs **daily at 03:00 UTC**. A second launch for the same source is **refused, not raced**, by the cross-machine `SourceLock` keyed on the jurisdiction (OPEN-187; OPEN-191 rehearsal; `cloud_scrape_trigger.py`), so a nightly firing during a re-import would be skipped (with a failed-pipeline alert). **But that lock lasts 24 hours**; a re-import expected to run longer than that (about 39,300 US bills; Pennsylvania's roughly 5,300 take about 7 hours in a full run) could lose the lock midway, after which a nightly could start. If the re-import is expected to exceed about 20 hours, it should be split (118, then 119) or the `usa` schedule held for the duration (a `sync_schedule.yaml` change, which you have said is not authorized here, so it would need its own request).
- The re-import must not start while ECS has any `usa` task, and the user's rule that other states' scrapers do not block it still holds.

## Other things done this evening (no action for you)
The user also approved tightening **/opt/ddp-open-states/.env** (it holds the GitHub token the ddp-sync builds read) from mode 644 to **600**; done 23:3x UTC, still owned by bitnami, still readable by the builds' owner, nothing in systemd or cron references it. All four .env files on this host (broker, ddp-sync, ddp-open-states, ddp-open-states/deploy) are now 600.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
