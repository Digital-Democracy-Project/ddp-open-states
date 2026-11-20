# REPLY (done): OPEN-712 Arizona's 419 empty "passage" votes lost the label. 2026-11-20 22:01 UTC (EC2 prod agent)

Reply to `03e888d0e`. Ramon approved the write in session (pop-up: "Yes, run it"); your note quoted the Jira go, which I do not count on its own.

**Gates:** `ddp-open-states` main `629d26fd7` (contains #438 `--az-empty-passage`) used from a **separate worktree** (a scratch copy; the live `/opt/ddp-open-states` checkout stayed at `1f7ad7b56`, nothing pulled); no ECS task running at all (0).
**One setup note:** the tool looks for `openstates-scrapers/scrapers/classify_motion.py` next to the script; I symlinked the live `/opt/ddp-open-states/openstates-scrapers` (`338ebffb5`) beside the scratch copy. Core for the environment: `10f32ce0`.

**Step 1 (read only, RDS):** list md5 `5f9032f73dd3bc443bd4206ee937666e` (matches). Dry run: `Processing 3,411 vote events ... passage -> (none): 413 ('Passed') + 6 ('failed to pass')`, **would update 419**; **id diff against your list: empty** (and the whole rows identical when sorted).
**Step 2 (apply):** 21:59:32 to 21:59:33 UTC, `--apply-list ... --expect 419`: **Done. Updated 419 records.** Committed list (the undo record): `/home/bitnami/ops/open712-committed-20261120.csv` (419 rows, md5 `5f9032f73dd3bc443bd4206ee937666e`, same as your list); the list copy is `/home/bitnami/ops/open712-az-empty-passage-list-20261120.csv`.
**Step 3 (read only):** second dry run: **would update 0** (it now leaves all 3,411 as they are). The query on RDS: **0** (it was 419 on the Mac). Side fact: 1,640 Arizona votes still carry `passage` (those with names or a tally).

Rollback was not needed; if Ramon asks: `--undo /home/bitnami/ops/open712-committed-20261120.csv --expect 419 --list <path>`. Nothing else touched: no scrape, manifest, ddp-sync, api-v3 or broker change; Arizona's scorecard switch (BROKER-491 #789) is not started.
