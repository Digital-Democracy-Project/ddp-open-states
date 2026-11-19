# UPDATE to `b1349d2` (OPEN-633/OPEN-639 order): Ramon made the DB role and definition by hand; what is left. 2026-11-19 (Mac side, State Specific Handling)

**Not a GO.** This replaces steps 1 to 5 of the order in `fb75817`/`9429eef`/`b1349d2`. Each step below waits for its own go.

## Done tonight (Ramon; details on OPEN-639)
* **Image v71:** `ddp-scrapers:74`, digest `sha256:79101fcb204acfd0b190ee9a77bd245a296f10d81a3ed9a3aa744e8de043e63a`. Checked on the Mac by pulling it:
  * it carries **core `10f32ce08088e544e88d54ec64aa325aea80756f`** (OPEN-554 merged), `/app/cloud_loader.py`, and `openstates/ddp_states/`.
  * It was built with the **old** deploy script, from Ramon's `ddp-open-states-dev` checkout at `76c271c`. That script clones main, so the image is main, but it did not create `ddp-scrapers-db`.
* **New execution role** `ddp-scraper-db-execution-role`: the old role's ECR and log access, plus `secretsmanager:GetSecretValue` on the one RDS secret only.
  * The KMS key is AWS-managed, so no `kms:Decrypt` is needed.
  * The simulator says allowed for the new role and `implicitDeny` for the old one. This is the tighter option in OPEN-639.
* **`ddp-scrapers-db` revision 1**, made by hand: a copy of `ddp-scrapers:74` (v71) with the new execution role, the same task role, and **no secret**. Checked on the Mac (`describe-task-definition`): image v71, role `ddp-scraper-db-execution-role`, `secrets: null`.
* **ddp-sync #301 merged** as `46752992`. Load and archive tasks launch from `task_definition_db` = `ddp-scrapers-db`.

## What is left, in order
1. **Ramon: update `ddp-open-states-dev` to main** before the next image.
   * The deploy script runs from that checkout, and only main's script (OPEN-639, #430) registers each image on **both** families, keeps the secret on `ddp-scrapers-db` only, and refuses it on `ddp-scrapers`.
   * An old script would register a new `ddp-scrapers` revision and leave `ddp-scrapers-db` on v71.
   * Main's script copies `ddp-scrapers-db`'s **own** current revision forward, so the new execution role stays.
2. **Prod agent, EC2, on its go, only when nothing is running** (the same gate and procedure as the Part C checkpoint `745a8d1`; **not** `systemctl restart`):
   * **ddp-sync:**
     * `/opt/ddp-sync` fast-forward to main (`46752992` or later; includes #300 BROKER-541 and #301 OPEN-639);
     * rebuild with `DDP_CORE_SHA=10f32ce08088e544e88d54ec64aa325aea80756f` (v71's core);
     * `up -d --no-deps ddp-sync`;
     * tag the running image `ddp-sync:pre-open639` first, for rollback.
   * **api-v3, both hosts** (EC2 and Mac), at core `10f32ce08088e544e88d54ec64aa325aea80756f`, by the api-v3 release procedure (RUNBOOK → api-v3 release). api-v3 imports core's version rules.
   * **`/opt/ddp-open-states`:** `deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync` if it is behind main.
   * **Checks:**
     * `check-core-pin-drift.py --image-core 10f32ce08088e544e88d54ec64aa325aea80756f --container ddp-openstates-api-1 --sync-container ddp-sync-ddp-sync-1` exits 0;
     * `grep -c 'task_definition_db: "ddp-scrapers-db"' /opt/ddp-sync/config/sync_schedule.yaml` = 2, and `rds_from_task_secret: false` still appears twice;
     * the **next archive run**'s ECS task is from `ddp-scrapers-db:1`, reaches RUNNING with the new execution role (image pull and logs work) and exits 0. ddp-sync still passes `DATABASE_URL` until step 4;
     * the next collection is from `ddp-scrapers` (v71), as before.
   * **Rollback:** retag `ddp-sync:pre-open639`, then `up -d --no-deps ddp-sync`.
3. **Ramon: a release with `TASK_RDS_SECRET_ARN` and `TASK_RDS_HOST/PORT/DBNAME`**, run from the updated checkout (step 1). The values are in reply `8c4315c`.
   * The secret goes on `ddp-scrapers-db` only; `ddp-scrapers` stays without it.
   * **Check:** the script prints `RDS secret in ddp-scrapers: no` and `RDS secret in ddp-scrapers-db: yes`. The next archive task from the new `ddp-scrapers-db` revision reaches RUNNING, which proves the new role can read the secret.
   * **Rollback:** deregister that `ddp-scrapers-db` revision.
4. **Later, each its own note:**
   * `rds_from_task_secret: true` in ddp-sync;
   * then the first state's `scrape.load_on_fargate: true`. The Mac rehearsal passed on v70 (OPEN-633 comment 21607).

## Not authorized here
Anything beyond steps 1 to 3 as written: no `rds_from_task_secret` change, no `load_on_fargate` change, no data change.

Tickets: OPEN-633, OPEN-639. Plan: ddp-infra `PLAN-cloud-load-on-fargate.md` (#538).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
