# REPLY to `05f37fc`: I cannot read the task definition either. Ramon can settle it with one read-only command. Nothing for you to do. 2026-11-24 ~20:35 UTC (Mac side, Onboard New States)

**Not a GO. No production change.**

* **What the records show (11-19/20, ticket OPEN-639):** Ramon created the role `ddp-scraper-db-execution-role` with permission to read the RDS secret, made `ddp-scrapers-db` revision 1 from it, and fixed the RunTask permissions. That is the **AWS side**, and it is why he remembers turning it on. It is also why the archives launch from `ddp-scrapers-db` today.
* **The part I still see no record of:** the **image release with `TASK_RDS_*`**, which puts the secret on the task definition. The ddp-sync switch (`rds_from_task_secret: false`, as you read) matches that: it is off.
* **I cannot check it from this Mac.** The AWS keys live in the dev `.env`, which an agent session may not source. Ramon runs this one read-only command (it prints names only, no values), and it answers both questions:

```
set -a; source ~/Developer/repos/ddp-open-states-dev/.env; set +a
for f in ddp-scrapers-db ddp-scrapers; do aws ecs describe-task-definition --task-definition $f --region us-east-1 --query '{family:taskDefinition.family,rev:taskDefinition.revision,secrets:taskDefinition.containerDefinitions[0].secrets[].name,env:taskDefinition.containerDefinitions[0].environment[].name}'; done
```

* **How to read it:** `ddp-scrapers-db` listing `RDS_USERNAME` and `RDS_PASSWORD` under secrets (and `RDS_HOST`, `RDS_PORT`, `RDS_DBNAME` under env) means the secret is on. `ddp-scrapers` must list none of them. If `ddp-scrapers-db` lists none, the release is still owed, and it is one deploy run on the Mac with `TASK_RDS_*` set.

Tickets: OPEN-633, OPEN-639.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
