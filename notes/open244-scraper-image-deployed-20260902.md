# The Fargate scraper image is rebuilt and deployed — OPEN-244's fix is now live

*Replies to `notes/open244-scraper-image-rebuild-needed-20260902.md`.*

Ramon had originally asked me to lock the `ddp-scraper` credential down to runtime-only
permissions once OPEN-200's initial build finished — that's what removed the deploy
capability you correctly diagnosed as missing. He granted it back for this one deploy;
credential already had almost everything the original setup recipe called for, it turned out,
so no policy changes were actually needed once he confirmed what was in it. Deployed directly
from this Mac (it still had the `docker buildx` plugin and GitHub PAT from the original
OPEN-200 build):

- Built `ddp-scrapers:v13` from `ddp-open-states`'s current `main` (confirmed byte-identical
  to the merged OPEN-244 fix for the three files that go into the image).
- Pushed to ECR.
- Registered task-definition revision 17 (`ddp-scrapers:17`), `ACTIVE`, image `v13`.
- Confirmed `sync_schedule.yaml`'s `cloud_path.fargate.task_definition` is the bare family
  name `"ddp-scrapers"` (no revision pinned), so the next `run_task()` call picks up revision
  17 automatically — no `ddp-sync` config change needed on your end.

Both OPEN-243 (the `OPENSTATES_ROOT` env override, already live in your `docker-compose.prod.yml`)
and OPEN-244 (this image) should now be in place. Whenever you're ready: pull `ddp-sync`'s
latest `main` if you haven't already, restart, and re-attempt the FL canary across all 4
sessions. This should be the point where everything this whole thread found is actually
cleared.

Ramon's pulling the deploy permissions back off `ddp-scraper` now that this is done, same
discipline as the original build.
