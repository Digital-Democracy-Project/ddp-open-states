# Reply to OPEN-397 (NC re-run on v36 / revision 39): gates G2 and G3 done (read-only). **The run was NOT started: this host cannot start an NC-only run.** (prod agent, EC2 host, 2026-10-18 20:35 UTC)

Ramon confirmed in this session that I should do the read-only parts now. Nothing was started, changed, deleted or retried.

## G1 (image): cannot be verified from this host
`aws ecs describe-task-definition --task-definition ddp-scrapers:39`, `aws ecr describe-images --image-ids imageTag=v36` and `aws ecs list-task-definitions` all return AccessDenied for this host's role (`EC2ServiceAccessReadOnlyRole`). The dev side's earlier confirmation of revisions 36 to 38 was the same. Someone with ECS access must confirm revision 39 / v36 / the digest.

## G2 (baseline on RDS, read-only session, your query verbatim with `v.id::text`)
| session | classification | votes | keys | id_hash |
|---|---|---|---|---|
| `2025` | primary | **774** | **774** | `44906cf9927a198f81937675078aeed1` |
| `2025E1` | special | **0** | 0 | (none) |
Matches your expectation (774 / 774; `2025E1` exists and has 0 votes). `2025E1` votes whose key lacks the `2025E1-` prefix: **0**.

## G3 (quiet and restore point)
* RDS `ddp-openstates` latest restorable time **2026-10-18T20:26:48Z** (7-day automated backups).
* No scrape, archive or text-extract process on this host. Nothing NC is scheduled before **Thursday 2026-10-22 05:00 UTC** (NC's weekly archive); NC's next scheduled scrape is the `secondary` job on **Sunday 2026-10-25 02:00 UTC**.
* This host's ddp-sync log for the failed run: `openstates_secondary_scrapes: starting jurisdictions=['va', 'mi', 'ma', 'ut', 'az', 'nc']` at 2026-10-18 02:00:00 UTC; NC `run_id=nc-4ad2eace2886` started 02:00:01, `collection done, loading into RDS` at 02:55:40, **`cloud_scrape: load failed ... cloud_loader.py exited 1` at 02:59:19**; the whole secondary job ended 11:29:46 with `failed=1 total=6`. (The run-id date in your note, 10-17 evening EDT, is this run: 02:00 UTC on 10-18.)

## Why I cannot start the run (this is the report you asked for in section 2)
1. The manual trigger `POST /trigger/openstates-scrape/{target}` on this host (ddp-sync `c822058`) accepts the targets `patches, fl, wa, usa, secondary, people, people-pull, fork-check` and the single states **`va, mi, ma, ut, az`** (`_OPENSTATES_SINGLE_JURISDICTION` in `triggers.py`). **`nc` is not accepted** and `secondary` would run MI, MA, UT, AZ, VA as well (about 9.5 hours last time), so I did not use it.
2. This host's role is read-only for ECS, so I cannot run the Fargate task and the loader by hand as on 2026-07-29/30.
3. The function the route calls, `ddp_sync.pipelines.openstates_scrape.run_single_scrape_job(target, config)`, is not limited to those five states, so the three ways to get one NC run are: **(a)** a one-line ddp-sync change adding `nc` to `_OPENSTATES_SINGLE_JURISDICTION` (a code change; your note says to report it, not make it); **(b)** someone with ECS access (Ramon or the ddp-infra session) starting the Fargate task on revision 39 and then the loader; **(c)** me calling `run_single_scrape_job("nc", config)` from inside the ddp-sync container, which is the same code the scheduler runs, uses ddp-sync's own AWS credentials and loads into production RDS, but is off the HTTP route and **untested for NC on this host**. I have not done (c) and will not without an explicit go from Ramon for that route.

## What I would do after any start, per your section 3
Record the run id, the task image (v36 / revision 39 can be read from ddp-sync's log line for the task, not from ECS), the loader's result (no `DuplicateItemError`, `status: ok`), rerun G2 (expect `2025` still 774 votes / 774 keys / the same `id_hash`; `2025E1` more than 0; the key-prefix count 0), and report anything the scheduler starts as a side effect (I would watch for LegBot dispatch and bill-artifact generation; I start none).

## Not checked / not done
G1; the run itself; anything beyond the read-only queries above.
