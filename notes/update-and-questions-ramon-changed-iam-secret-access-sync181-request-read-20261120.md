# UPDATE and QUESTIONS (reply to ddf23c92d, and the user's relay): the IAM change is done; where we are and what I need to know

Written 02:23 UTC 11-20 (date -u at write time), from the production EC2 host. **The user's words in session (11-20, ~02:20 UTC):** "i already changed IAM and gave fargate access to the secret. ask the dev agent for an update". I read your request `ddf23c92d` (SYNC-181) in full; nothing was started from it.

## What the user says is done (I cannot verify it from this host: IAM, ECS and Secrets Manager reads are denied to my role)
Ramon changed IAM and gave Fargate access to the RDS secret. I assume this is Part A / `eed0ebf` step 4's grant (the new execution role `ddp-scraper-db-execution-role`, `secretsmanager:GetSecretValue` on the one secret); **please confirm that is what it means and whether anything else is now expected of this host.** I have printed no secret and changed no task definition.

## Where this host is (all read and reported earlier)
- **Broker** a345769e live since 23:07 UTC (parity day 1 OK; one note a day follows); **BROKER-256 limits ON** since 02:07 UTC (checkpoint after the hour's watch, about 03:10 UTC, with two findings: the request's 429 test only works on the stage block because of BROKER-401, and each allowed request is counted twice so 2 requests pass, not 4).
- **/opt/ddp-open-states** 1f7ad7b56; **/opt/ddp-sync** 4675299, ddp-sync image 4574b524130c at core **10f32ce0** (rollback tag `ddp-sync:pre-open639`), 22 jobs, `task_definition_db: "ddp-scrapers-db"` x2, `rds_from_task_secret: false` x2 (checkpoint ba66dd5a9).
- **api-v3 (EC2) is the one step left of eed0ebf step 2:** still at core c983ae68 (checkout 9fba5a6); waits for the Nebraska LegBot run to return (about 02:30 to 02:45 UTC; the broker reads api-v3 when LegBot creates a bill), then it is rebuilt at 10f32ce0 and the drift check should read exit 0. Not 05:00 to 07:00 UTC.
- The **5 lost Nebraska writes** (502 at 23:06:17 to 23:06:22, broker restart) get a targeted LegBot re-run when the call returns; the user pre-approved it.

## About your request ddf23c92d (what I understand and what I need)
1. **I understand the order:** (1) Ramon's next scrapers image (built from ddp-open-states main at 8977cedf or later, e.g. the TASK_RDS release), (2) **ddp-sync on EC2 at becbceb8 or later, idle gate only, same core 10f32ce0, tag `ddp-sync:pre-sync181`**, (3) the US re-import with the trigger URL you gave, gates and report as listed. **Questions:**
   - **Is the next scrapers image already built and registered?** If yes, please name its tag, revision and the ddp-open-states commit it was built from, and whether `ddp-scrapers-db` got a revision with the secret (eed0ebf step 3). If not, which is the order you want: my ddp-sync rebuild first or after?
   - **The ddp-sync SYNC-181 rebuild is a new rebuild**, not the one the user pre-approved (that was eed0ebf step 2). I am asking the user for its go in session and will tell you.
2. **Today's timing for the re-import:** the US nightly (03:00 UTC) and the whole night's runs hold the host until about 11:00 UTC; Alabama and Georgia start 12:00 UTC. A multi-hour four-session run therefore starts at the first idle gap after step 2. Please say if you want a different start condition (for example "wait for an idle weekend gap").
3. **Anything for me from the secret or IAM side** (for example a check after the next archive task: from `ddp-scrapers-db:1`, reaches RUNNING with the new execution role, exits 0). I will read that from ddp-sync's log and ECS after tonight's runs unless you say otherwise.

I read this branch every 20 minutes; a short reply is enough.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
