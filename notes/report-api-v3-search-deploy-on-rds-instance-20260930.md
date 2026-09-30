# Report: api-v3 search deploy on the RDS-backed instance, sections 2 to 6 done (2026-09-30)

From the prod agent on the EC2 host (`/opt/ddp-open-states`). Replies to
`enterprise-search-rds-api-v3-deploy-checklist-20260930.md`. Times are UTC. Sibling report for the broker half (same day, including an outage
during that deploy): `report-enterprise-search-broker-deploy-ensure-500s-20260930.md` on ddp-broker-py's `notes/ops-handoff`.
**Sections 7 and 8 are NOT done.** One finding needs a decision: NC has zero people in the projection.

## Where this stands

api-v3 `main` at `ce1447c` (OPEN-308 + OPEN-309) is running on `ddp-openstates-api-1` on this host. `ddp_bill_search` is built on RDS with all 76,909
bills. The user ran the rebuild, `ensure` and both `refresh` passes; the auto-mode classifier blocks me from those. I ran the read-only checks, the rollback
tag and the checkout update.

| Step | Time | Result |
|---|---|---|
| §3 baseline | 22:48 | container `ddp-openstates-api-1` (`ddp-openstates-api:local`) up since 09-13, healthy, healthz 200; checkout `/opt/ddp-open-states/api-v3` on `main` at `ee8fd61`, clean, 2 commits behind `ce1447c` (exactly `ed6e89b` and `ce1447c`); host **x86_64**; 182 GB disk free; 2.4 GB of 7.7 GB memory available; **only the `docker compose` v2 plugin (2.40.1), no `docker-compose` v1** |
| §2 gate (read-only, via the api container's own session) | 22:49 | `ddp_legbot_publication`: `puballtables = false`, **47 tables**. Role `openstates_admin`: `rds_superuser` member, CREATE on the database. `pg_trgm` 1.6 available and trusted, not installed. `ddp_bill_search` absent. PostgreSQL 16.15. DB 3,646 MB. 76,909 bills. One subscriber `ddp_legbot_subscription`, streaming |
| §3 rollback tag | 22:51:11 | `docker tag ddp-openstates-api:local ddp-openstates-api:pre-open308` (image `552bc19113a7`) |
| §4 checkout | 22:51:11 | `git pull --ff-only origin main`: `ee8fd61` to `ce1447c`, 5 files, all additive, tree clean |
| §4 rebuild | about 22:51:57 | `docker compose -f docker-compose.rds.yml up -d --no-deps --build api` from `/opt/ddp-open-states/deploy`; new image `6371e00e828c`; `api` recreated only. Import check `import api.ddp_search, api.search_projection` exits 0. Redis (`ddp-openstates-redis-1`, up 4 weeks) and the broker containers were not restarted |
| §5 `ensure` | by 22:53 | `=== BILL SEARCH ENSURE: ddp_bill_search present ===`. `pg_trgm` 1.6 now installed, table plus 5 indexes (4 plus the primary key), none invalid. Publication still `puballtables = false`, 47 tables, `ddp_bill_search` not in it; replica still streaming |
| §5 dry run | about 22:54 | `would_refresh=76909`, equal to the RDS bill count |
| §5 first `refresh` | about 22:54 to about 23:20 | `refreshed=76909 | with_text=74777 | orphans_removed=0 | seconds=1576.0` (about 26 min). Table 502 MB (reference 509 MB); `fts_idx` 76 MB, `title_idx` 19 MB, `pkey` 5.8 MB, `ident_idx` 1.9 MB, `juris_idx` 0.8 MB. DB 4,149 MB. No stale rows afterwards |
| §5 second `refresh` | about 23:22 | `refreshed=0 | with_text=0 | orphans_removed=0 | seconds=26.2` |
| §5 `refresh --dry-run` | about 23:23 | `would_refresh=0` |
| §6 routes | 23:24 to 23:29 | see below |

**During the first build (my read-only readings from the RDS side):** 21,413 rows at 23:00:46, 37,408 at 23:08:45, 69,423 at 23:17:22. Replica `replay_lag`
stayed between 0.10 s and 0.44 s and the state stayed `streaming`, so the lag stop condition was never close. The build ran about 10 times slower than the
148 s local reference, which I attribute to network latency to RDS but did not confirm with RDS metrics. A no-op `refresh` still costs about 26 s because it has to prove
nothing is stale across 76,909 bills and their documents.

## §6 results

Used ddp-sync's own read-only key for this instance, read in-shell and sent in the `X-API-KEY` header (not the URL, because the URL form lands in the access logs).

- **Coverage, 8 jurisdictions (8.4 s): `projected == bills` for all 8.** US 38,605; FL 7,685; VA 4,382; MI 4,107; WA 3,411; NC 2,338; AZ 2,190; UT 1,021.
  `with_abstract` is nonzero for FL (7,685) and VA (4,382) and 0 elsewhere. `people`: US 725, FL 539, MI 450, VA 356, WA 347, AZ 341, UT 271, **NC 0**.
  The 8 jurisdictions are 63,739 of the 76,909 projected bills; the remainder are other jurisdictions that are not enrolled.
- **Spot checks (all 200):** exact `HB 1` (FL) 0.15 s, `exact` group returns FL "HB 1 Online Protections for Minors" (2024) and "HB 1 Education" (2023);
  misspelling "medicade expansion" (FL, VA, MI) 0.44 s, returns "Medicaid Expansion through Medicaid Buy-in Program" (FL HB 567, HB 61);
  topic "school lunch" (FL, VA, WA) 0.58 s, returns WA "Increasing student access to free meals served" and FL "K-12 School Lunches and Breakfasts";
  legislator "Grijalva" (US) 0.27 s, returns Adelita Grijalva and Raúl Grijalva; `suggest` "HB 10" (FL) 0.24 s, 3 results. These are single requests, not the p95 test.
- **Auth and input:** bad key 401; no key 403; `limit=101` 422; missing `q` 422. Search needs at least one `jurisdiction`, otherwise 400
  ("at least one 'jurisdiction' is required").

## Finding: NC has no people in the projection (the checklist says `people` should be nonzero for all eight)

Read-only on RDS: all 2,338 NC bills have sponsorships (26,099 in total), but **no person has a membership in an NC organization** (0 rows). So NC legislator names
cannot be searched. Bill search is unaffected. I did not investigate why. It looks like NC legislators are not in the people tables at all, so it is a question for
whoever owns the people import, not a fault in this deploy. **Decision needed:** ticket it, or accept NC without name search for now.

## Not done

- **§7:** the p95 through ddp-api (bar 150 ms), read-scope rejection of `POST /openstates/ddp/search/refresh`, the importer freshness test on a non-production database,
  and recording the serving instance. I have no ddp-api token here. Partial fact only: ddp-sync's `RDS_OPENSTATES_API_BASE` is `http://10.0.0.11:8002`, which is this instance. I did **not**
  check ddp-api's `OPENSTATES_SERVICE_URL`, the broker's `DDP_OPENSTATES_API_ROOT`, or ddp-sync's `local_openstates_api_base`, so the "all three name the same instance" condition is unconfirmed.
- **§8:** the `start-os-api.sh` ensure block and the SYNC-87 refresh hook. **Until SYNC-87 (or a scheduled call) exists, nothing refreshes this table.** I searched `ddp-open-states`,
  `ddp-sync` and this host's crontab and found no caller, so new or changed bills will not appear until someone runs `refresh` (or `POST /ddp/search/refresh`).
- **RDS free storage:** I could not read it from SQL and did not check CloudWatch before the build. The build completed, so it was enough, but the margin is unknown.
- I did not touch the Mac's container or the `openstates_rds_repl_20260911` replica, and did not deploy to any civic host.

## Next step

1. Decide what to do about NC `people` (ticket or accept).
2. Someone with a ddp-api token runs §7; the serving-instance confirmation needs ddp-api's and the broker's settings.
3. Build SYNC-87 or schedule a refresh; expect about 26 s per no-op sweep, so per-jurisdiction refreshes are cheaper.
4. Reply on this same branch either way.
