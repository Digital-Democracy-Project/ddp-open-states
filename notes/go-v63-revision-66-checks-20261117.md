# GO: v63 = `ddp-scrapers:66` registered 15:59:19 UTC 2026-11-17; checks only (follows request `984f0bf`). (Mac side)

**Ramon, 2026-11-17:** ran `CONFIRM=1 bash deploy-scrapers-image.sh` (v63 built, all image checks passed, pushed; the confirm prompt had no terminal, so it stopped before registering), then "can you register it yourself". The Mac session registered it with the script's own register step.

* Image `ddp-scrapers:v63`, digest `sha256:696cf041aaea880fcef067acb1d1cb2936a4c0e30e4fd0ab91c9cde914591bf8`; built from ddp-open-states main `6fc7133`; core `b5728c4326fea4bdc33b721738ecdbe5ac4d8b02` (image's `DDP_CORE_COMMIT`); Python 3.13.18; UT one-bill smoke scrape passed.
* Revision 66 is the latest ACTIVE `ddp-scrapers`; previous image was v62 (revision 65). No tasks were running on the cluster at registration.
* Rollback: `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:66` (ECS then resolves to 65).
* Contents and effects: see `request-scrapers-image-v63-open608-609-607-20261117.md`. Alabama's fix (OPEN-569) was already in v62.

## Authorized (read only)
1. Confirm the next launched task of any state reports revision 66 and image v63.
2. On EC2: `check-core-pin-drift.py --image-core b5728c4326fea4bdc33b721738ecdbe5ac4d8b02 --container ddp-openstates-api-1`. **Gate:** exit 0 (the accepted gap from `be6f951` should now be closed). Report the Mac api-v3 result too if you can read it.
3. Report each state's first run on revision 66: status and failed. Massachusetts should still be a full run (its `start_filter` is `false`).

## Not authorized yet
* **The extra Oregon run** (request step 3): waits on Ramon's separate go. Without it, Oregon's joint-committee voters link on its next scheduled run.
* Any manifest, broker, ddp-sync, api-v3 or data change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
