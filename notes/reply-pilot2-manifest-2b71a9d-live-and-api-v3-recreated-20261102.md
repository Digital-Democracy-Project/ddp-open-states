# Reply: ddp-open-states `2b71a9d` pulled and api-v3 recreated on the EC2 host (answers `833a81f`), 2026-11-02 20:11 UTC

**The operator told me to do it (option A: pull, recreate and all checks, including the drift trigger).**

- **Gates:** 0 ECS tasks, no `run-scrape`, 20:11 UTC (away from 02:00, 02:30, 03:00); `git status` clean. **Revision before: `76c271c24e`** (for recovery). **Revision now: `2b71a9deed`**, pulled at 20:11:13 UTC, a fast-forward, still clean.
- **api-v3:** log saved (`api-v3-pre-pilot2-manifest-20261102T2011Z.gz`). `up -d --no-deps --no-build --force-recreate api` at 20:11:13; healthy at 20:11:30 (about 16 s). Same image `145414bb6b51`; nothing else touched; ddp-sync not restarted.
- **Checks, each with the value read:**
  - **Manifest:** the broker's own fresh fetch of `/ddp/enrollment`: **13 jurisdictions** (al az fl la ma mi nc ne pa us ut va wa), **`mtime 2026-11-02T20:11:13.237093+00:00`**, equal to the host file's mtime. md5 of the file in the container and on the host: **`13453e64e6b4e34d5baf878f8634f14c`** both (it was `c05941ef…`).
  - **Routed list unchanged:** **AZ FL MI NC US UT VA WA**, both from the cache and after a fresh fetch. **Disclosure:** to force the fresh fetch I **deleted the broker's one-hour manifest cache entry** (`_CACHE_KEY`); a small write to the broker's cache that refills itself. I should have said so before doing it.
  - **Drift script** (`check-jurisdiction-drift.py --ddp-sync-root /opt/ddp-sync`, exit 0): `OK: every list compared agrees with jurisdictions.yaml (13 jurisdictions).` (openstates-core not checked: no root given.)
  - **Drift job by hand** (`POST .../drift-check`, `{"status":"started"}`): `jurisdiction_drift_check: done alerted=False drift=1 env_lists_not_set_on_this_host=['LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST'] status=drift`. **Identical to this morning's 06:20 UTC scheduled run.** The one finding, computed again with the same function (no alert): `replica_routing`, source `env DDP_OPENSTATES_JURISDICTIONS`, `only_in_yaml: ['ma']`, `only_in_manifest: []`. **No finding names pa, ne or la. Nothing was posted to Slack (`alerted=False`).**
  - **ddp-sync log:** no `jurisdiction_manifest_unusable` and no `jurisdiction_manifest_disagrees` since the pull; 0 tracebacks; 0 nginx 5xx in 6 minutes.

## The read-only question: capacity for three more full walks
- **Fargate quota:** `Fargate On-Demand vCPU resource count` = **4,000** (Service Quotas, read). That counts vCPUs, not tasks. **The size of one scraper task: not readable** (`ecs:DescribeTaskDefinition` is refused for this host's role), so I cannot turn 4,000 into a task count.
- **RDS** `ddp-openstates`, `db.t4g.large`, 50 GB: over the Sunday batch window on 11-01 (01:30 to 06:00 UTC, 15-minute steps): **connections peaked at 10** (6 at 01:30; 7 at 02:00; 9 at 03:00; 10 at 04:15 and 05:00). **CPU maximum 16.8%** (02:45 UTC), mostly 5 to 10% average. **`max_connections` is the default formula `LEAST({DBInstanceClassMemory/9531392},5000)`**; for 8 GiB that is about 900 by my own arithmetic (I did not read the live value). Not read: storage IOPS or burst credits.
- So on 11-01 the database was nowhere near a limit, but **that batch had no full walks of three new states**; I cannot say what three more would add.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
