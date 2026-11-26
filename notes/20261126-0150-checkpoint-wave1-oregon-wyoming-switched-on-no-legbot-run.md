# Checkpoint 11-26 01:50 UTC: LegBot wave 1 (Oregon, Wyoming) switched on on EC2; no LegBot run started

Ramon's go in this session (naming the wave 1 request) and his **named waiver of the parity gate**: `check_replica_parity` no longer exists (removed by BROKER-495), so I could not run it.

## Gates (read)
* Quiet: no Oregon or Wyoming task; Georgia and Maine were collecting (other states).
* Recorded start: `/opt/ddp-open-states` at `b0d8b101c`; broker list `MI,UT,US,VA,AZ,WA,FL,NC,PA,NE,LA,NM`; restore point 01:39 UTC.
* Gate 0: #498 (`a69063ac`) is in `origin/main`; its diff against the recorded revision was exactly the four lines (`or` and `wy`, both flags) plus one docs file (PRIMITIVES.md).
* Production people (RDS, read-only): Oregon 242, Wyoming 259 (all memberships). Production bills: Oregon 304, Wyoming 335. **The broker's own people table is much smaller than the replica's: `onboard_jurisdiction --check` prints "people: replica 93, broker 39" for OR and "replica 96, broker 11" for WY.** I did not treat that as a gate; please say whether the broker side needs a people refresh before LegBot runs.
* Map outlines: every layer has a file for both (newest year 2026, US Senate 2020).

## Part 1 (session rows)
* `--check` before: only the session line missing (OR 2026R1, WY 2026). `--dry-run`: would create only that state's current session. Real run: OR then WY; `--check` after: sessions ok. Oregon now holds 7 session rows, Wyoming 5.

## Part 2 (EC2, in order)
1. Manifest rollout 01:41 UTC (skip of the cloud-task check; no restart): the pull brought only #498's four lines and the docs file; md5 of checkout file, api copy and the file inside the container equal (`57633a35...`); ddp-sync's own read: OR and WY `replica_routing` and `legbot_replica` true, ID still false; schedule 35 jobs.
2. api-v3 recreated by service name only (`--no-build --no-deps`): health 200 before and 10 s after; core-pin drift exit 0.
3. Broker `.env`: `OR,WY` appended to `DDP_OPENSTATES_JURISDICTIONS` (backup mode 600, no other line changed). Beat stopped 01:43:08, warm shutdown 01:43:10, celery exited by itself (exit 0) 01:43:20; web, celery, beat recreated by name; web healthy 01:43:54; restart policy `unless-stopped` on all; celery ping 1 node. The running broker now lists `...,NM,OR,WY`. Old celery log saved before the recreate.
4. ddp-sync: the env allowlist no longer exists (SYNC-157); ddp-sync's own manifest-derived LegBot allowed codes now read `AZ FL LA MA MI NC NE NM OR PA US UT VA WA WY`. No ddp-sync restart was needed or done.
5. `check-jurisdiction-drift.py --ddp-sync-root /opt/ddp-sync`: OK (30 jurisdictions agree), exit 0.
6. **The Mac host's copy is not mine**: this role has no access to the Mac. Ramon's step: manifest pull, api-v3/ddp-sync recreate and drift check there. LegBot's gate on the Mac reads that copy.

## Part 3 (read-only)
* Bills route through the broker: OR 2026R1 total 304; WY 2026 total 335 (both 200). Note: the route needs `session` as well as `jurisdiction`; with only `jurisdiction` it answers 400.
* LegBot gate on EC2's ddp-sync, `dry_run: true`, `limit: 1`, one bare-UUID candidate each (OR `HB 4001`, WY `HB 1`), nothing dispatched: both answered 200, 1 bill considered and processed, `artifacts_generated` empty, **no `jurisdiction_not_on_rds_replica_allowlist`**. (The request body also needs `artifact_types`, `include_concept_statements` and `retry_failed`; the first two tries answered 422 and did nothing.)
* `dc ps` healthy, 0 Tracebacks in web, celery or beat since the recreate; BillArtifact newest row still 13:18 UTC yesterday, 498,989 rows; no nginx 5xx.
* The broker enrollment read from api-v3 I did not do: it needs an api key I did not have a name for; ddp-sync's own manifest read above covers the flags.

## Not done
No LegBot run; no scorecard switch; Idaho untouched; no ddp-sync restart; no scrape or archive launch.
