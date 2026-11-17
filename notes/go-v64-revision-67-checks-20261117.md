# GO: v64 = `ddp-scrapers:67` registered 17:56:39 UTC 2026-11-17 (follows request `ad41f91`): checks now; api-v3 rebuild waits on Ramon's explicit go. (Mac side)

**Ramon, 2026-11-17 12:44 EST (Slack DM, read by this session):** "the agent has my permission to register the image himself, because it doesn't require sudo access". Ramon built and pushed v64 with `deploy-scrapers-image.sh`. Its confirm prompt had no terminal, so this session registered it.

* Image `ddp-scrapers:v64`, digest `sha256:e2dd814432e521a33a7af453e2b69f79f04d60bc5a8d281a57ef3647d08e7ae0` (pushed 16:58 UTC). Built from ddp-open-states main `22b6a00`; core `71fd44d61ce7f116a23933e29fbe9ea01372a99c`; Python 3.13.18; the UT smoke scrape passed.
* **Merges in it** (checked inside the image: its `motion_classification.yaml` is byte-identical to scrapers main at `56fb5c064`, and `nv/__init__.py` has `SESSION_84_START = "2027-02-01"`):
  * OPEN-582: PA resolution adoptions are `passage` (#120 → `3cc2a4e7`);
  * OPEN-583: LA concurrences, conference reports and resolution adoptions are `passage` (#121 → `9063af8c`);
  * OPEN-606: NV switches to its 84th session on 2027-02-01 (#122 → `d17ba434`);
  * OPEN-617: PA concurrences are `passage` (#123 → `56fb5c06`, merged 11:48 EST, before the build);
  * core #117, OPEN-615: relabel counts every computed field;
  * ddp-open-states #406, OPEN-616: the api-v3 build imports the app.
* Revision 67 is the latest ACTIVE `ddp-scrapers` (previous: 66 = v63). No task was running on the cluster at registration.
* **Rollback:** `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:67`.
* **Nothing published changes:** PA and LA are `scraping`, and their stored votes are relabelled only at each state's go-live, from a list Ramon approves. Don't run `backfill-motion-classification.py` for pa or la. NV is unchanged until 2027-02-01.

## Authorized now (read only)
1. The next launched task reports revision 67 and image v64, and its `DDP_CORE_COMMIT` is `71fd44d6…`.
2. Report the first PA, LA and NV runs on revision 67: status and failed count. NV still shows `{'2025Special36'}`.
3. Expect `check-core-pin-drift.py` to report **one disagreement** until step 4: the image is on `71fd44d6`, while EC2 api-v3 is still on `b5728c43`. That is expected; report it and leave it.

## Waits on Ramon's explicit go (not authorized yet)
4. **The api-v3 rebuild on EC2 at core `71fd44d6`**, as `ad41f91` step 2:
   * bring `/opt/ddp-open-states` to main at or after `22b6a00`;
   * tag the running image `pre-v64`;
   * build with `docker-compose.rds.yml` and `DDP_CORE_SHA=71fd44d61ce7f116a23933e29fbe9ea01372a99c`, then `up -d --no-deps api`;
   * **gate:** the build's import step passes, `/healthz` returns 200, and the drift check exits 0.

   The Mac side rebuilds the Mac api-v3 on the same go.

## Not authorized
Any stored-data change, manifest, broker or ddp-sync change, or extra scrape.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
