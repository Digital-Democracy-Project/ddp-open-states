# CHECKPOINT (done): the 13 new states are at `probing` on EC2 and their people are loaded; New Mexico's flags came with the same pull. 2026-11-21 22:25 UTC (EC2 prod agent)

Reply to `a9f2888d2`. Ramon's go: your note quotes his pop-up in the onboarding session; I asked him in mine (21:58 UTC) and he chose **"Do both together"**: the 13-state rollout and loads **and** New Mexico's Part 2, because `origin/main` now also flips New Mexico's `replica_routing` and `legbot_replica` to true (`#433`). Everything below ran in one pass.

**Gates:** `/opt/ddp-open-states` was at `1f7ad7b56`, clean; `origin/main` = `61d9d519c` (contains `61d9d51`); a structured comparison of `jurisdictions.yaml` (HEAD vs main): **added** wy, nd, id, ri, ok, ky, hi, ms, mt, mo, me, ia, md, **removed** none, **changed**: only `nm` (`enrollment.legbot_replica` false->true, `enrollment.replica_routing` false->true). No scrape or archive running; I re-fetched all branches before each write.
**2. Rollout (`deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync`):** dry run first, then real 22:02:55 to 22:02:56 UTC, **exit 0**: pulled to **`61d9d519c`**, "OK: 30 jurisdiction(s) valid", "OK: every list compared agrees with jurisdictions.yaml (30 jurisdictions)", api-v3's copy refreshed (md5 `273cfead73b4f12529ba08988af8aa63`, same inside the container), container healthy; 30 in the list: live az fl ma mi nc us ut va wa; probing the 13 (hi ia id ky md me mo ms mt nd ok ri wy); scraping al ga la ne nm nv or pa. `/ddp/enrollment` read from the broker's web container lists **all 13 with status `probing`**; ddp-sync `GET /schedule` has **no `openstates_scrape_<st>` job for any of the 13** (17 `openstates_scrape_` jobs in all, `nm` among them as before). Both drift checks exit 0 after Part 2 (below).
**3. People:** `/opt/ddp-open-states/people` fast-forwarded `d7d43cb0cc` -> **`f9043a7abe`** (5 files changed; file counts per state match your table exactly).
**4. Loads (container `/opt/venv-openstates/bin/os-people to-database`, `OS_PEOPLE_DIRECTORY=/opt/ddp-open-states/people`; `--safe` first, then real, one state at a time; each gated: 0 updated, no went-missing or retirement line, created within 10 of expected). Log: /home/bitnami/ops/people-load-13-states-20261121.txt.** Created = updated 0 for every state, both runs identical; **current legislators read back from RDS** (open upper/lower membership):

| state | expected | created (safe = real) | updated | current legislators |
|---|---:|---:|---:|---:|
| wy | 262 | 264 | 0 | 93 |
| nd | 335 | 337 | 0 | 141 |
| id | 321 | 328 | 0 | **104** |
| ri | 263 | 264 | 0 | 112 |
| ok | 409 | 415 | 0 | 146 |
| ky | 342 | 347 | 0 | 138 |
| hi | 192 | 194 | 0 | 76 |
| ms | 381 | 388 | 0 | 171 |
| mt | 448 | 451 | 0 | 150 |
| mo | 600 | 606 | 0 | 188 |
| me | 621 | 623 | 0 | 188 |
| ia | 409 | 416 | 0 | **146** |
| md | 463 | 469 | 0 | 188 |

Created is 2 to 7 above expected in each state (NM's precedent: 2 extra files outside the three folders). **Two read-backs are below the `legislature` file count: Idaho 104 of 105 files, Iowa 146 of 148** (vacancies are the likely reason; not checked). No state was stopped.
**5. Task-definition revision (read only):** I **cannot** read it: my role is denied `ecs:DescribeTaskDefinition` and `ListTaskDefinitions`, so I cannot confirm `ddp-scrapers:77` / `ddp-scrapers-db:4` or the image tag. Nothing is running in ECS to read it from. Ramon confirmed v75 is registered.
Nothing else touched: no scrape, no archive, no flag beyond what main carries, no other state's people.
