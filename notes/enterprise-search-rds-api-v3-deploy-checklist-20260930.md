# Deployment checklist: api-v3 search (OPEN-308, -309, -310) on the RDS-backed instance

Written 2026-09-30 for Ramon / the ops agent. Companion to
`notes/enterprise-search-deploy-and-test-runbook-20260930.md` (section 4.1 has the same steps in
prose; this is the tick-as-you-go version). Runbook for the feature itself: `docs/runbook/ddp-bill-search.md`
in api-v3 PR #14 (not merged yet).

**Nothing in this checklist has been run against RDS or the broker host.** The same steps were run
end to end on the dev database (`openstates_dev`) on 2026-09-30 and all passed (see section 9). The
session that wrote this had no AWS credentials and did not log in to the broker host.

What is being deployed: api-v3 `main` at `ce1447c` or later (contains OPEN-308 `ed6e89b` and OPEN-309
`ce1447c`): a new derived table `ddp_bill_search`, a command to build it, and five `/ddp/search/*`
routes. It adds one table and the `pg_trgm` extension and changes nothing that exists. Nothing calls
the routes yet.

---

## 0. Decisions to settle BEFORE starting (write the answer next to each)

- [ ] **Who runs it, and how they reach the broker host (`10.0.0.11`).** ______
- [ ] **Where the image is built.** `RUNBOOK.md` says build on the Mac, never on the EC2 host (it is
      shared with the production broker). But `deploy/docker-compose.rds.yml` uses `build:`, so
      `up --build` compiles on the host. The api-v3 image is small, but decide on purpose:
      (a) build on the host, accepting that, or (b) build on the Mac and ship the image. Also confirm the
      host's CPU type (arm64 vs x86) matches the image. Decision: ______
- [ ] **Which instance serves search in production.** The handoff says the RDS-backed one (the Mac
      replica was believed to lack abstracts and people; OPEN-312 found it actually holds them, so
      re-confirm). Whatever is chosen, these three must name the SAME instance: where `ensure` and the
      first build run, ddp-sync `local_openstates_api_base`, and ddp-api `OPENSTATES_SERVICE_URL` /
      broker `DDP_OPENSTATES_API_ROOT`. Decision: ______
- [ ] **A quiet window.** No LegBot run in progress (it reads the Mac replica; the first build writes
      heavily on RDS). Window: ______
- [ ] **Path of the api-v3 checkout and the `deploy/` directory on the host**, and whether that host uses
      `docker-compose` or `docker compose`. The steps below use `<api-v3-dir>` and `<deploy-dir>`. Filled in: ______

## 1. Safety rules (same as the main handoff note, repeated because they matter here)

- [ ] Do **not** run a bare `up -d --force-recreate`. Always name the service (`api`) and pass `--no-deps`.
- [ ] Do **not** `git pull origin main` on the EC2 **civic** (votebot / ddp-api) host. This checklist is for
      the broker host only.
- [ ] Do **not** touch the Mac's `ddp-openstates-api-1` container or the `openstates_rds_repl_20260911`
      replica database during this work.
- [ ] Do not send test alerts (Slack, CodeBot).
- [ ] Do not add the `start-os-api.sh` boot block yet (step 8).

## 2. Gate: confirm the replication publication does not cover all tables (RDS, read-only)

Why: the Mac replica subscribes to RDS. If the publication is set to cover ALL tables, creating
`ddp_bill_search` on RDS would start sending its rows to the Mac, which has no such table; the replica's
apply worker would crash-loop and LegBot would read from a stalled copy. Also posted on OPEN-310.

```sql
SELECT pubname, puballtables FROM pg_publication;
SELECT count(*) FROM pg_publication_tables WHERE pubname = 'ddp_legbot_publication';
```

- [ ] `puballtables = f` for `ddp_legbot_publication`. Expected table count: **47** (matches the Mac subscription
      on 2026-09-30). Result recorded on OPEN-310: ______
- [ ] If `puballtables = t`: **STOP.** Do not run `ensure` on RDS. Ask first.

## 3. Record the starting point

- [ ] Running container and image: `docker ps --format '{{.Names}} {{.Image}} {{.Status}}' | grep -E 'openstates'`
- [ ] Deployed api-v3 commit: `git -C <api-v3-dir> rev-parse --short HEAD` (expect it to be behind `ce1447c`).
      Commits behind: `git -C <api-v3-dir> fetch origin && git -C <api-v3-dir> rev-list --count HEAD..origin/main`
- [ ] `curl -s http://localhost:8002/healthz` returns 200 before you change anything.
- [ ] Keep a way back (the compose file reuses the tag `:local`, so a rebuild overwrites it):
      `docker tag ddp-openstates-api:local ddp-openstates-api:pre-open308`

## 4. Update only the api service

- [ ] `git -C <api-v3-dir> checkout main && git -C <api-v3-dir> pull --ff-only origin main`
      Expect head at `ce1447c` or later.
- [ ] From `<deploy-dir>`:
      `docker-compose -f docker-compose.rds.yml up -d --no-deps --build api`
      (This recreates `api` only. The host's own Redis, `ddp-openstates-redis-1`, is left alone.)
- [ ] Container healthy: `docker ps` shows `(healthy)`; `curl -s http://localhost:8002/healthz` returns 200.
- [ ] **Import check, must exit 0:**
      `docker exec ddp-openstates-api-1 python -c "import api.ddp_search, api.search_projection"`
- [ ] Nothing else restarted: confirm the broker containers' uptime did not reset.

## 5. Create the table and build the index

Run these from inside the container (it resolves the RDS password live from Secrets Manager).

- [ ] `docker exec ddp-openstates-api-1 python -m api.search_projection ensure`
      Expect `=== BILL SEARCH ENSURE: ddp_bill_search present ===`. About 0.5 s. This creates `pg_trgm`,
      the table and 4 indexes. DDP controls the RDS instance, so the extension permission should not be a
      problem (Ramon, 2026-09-30); **record that it worked.** Result: ______
- [ ] `... refresh --dry-run` prints `would_refresh=<n>`; n should equal the total bill count on RDS. n = ______
- [ ] Start watching the Mac replica lag in another terminal (on the Mac):
      `docker exec ddp-openstates-postgres-1 psql -U openstates -d openstates_rds_repl_20260911 -c "select now()-latest_end_time as lag from pg_stat_subscription"`
- [ ] `... refresh` (first build, all jurisdictions). Local reference on a copy of production data: about
      148 s for 75,805 bills. Record seconds and row count: ______ s / ______ rows
- [ ] **Stop conditions:** a single `POST /ddp/search/refresh` call or single statement that cannot finish
      inside its timeout (POST call about 20 s of work; statement timeout 30 s); or replica lag growing
      steadily during the build.
- [ ] Second run changes nothing: `... refresh` prints `refreshed=0` and `... refresh --dry-run` prints `would_refresh=0`.

## 6. Verify the routes (needs an api-v3 key; do not paste the key into notes)

```bash
B=http://localhost:8002/ddp/search ; K=<api-key>
curl -s -H "X-API-KEY: $K" "$B/coverage?jurisdiction=US&jurisdiction=FL&jurisdiction=MI&jurisdiction=AZ&jurisdiction=VA&jurisdiction=WA&jurisdiction=UT&jurisdiction=NC"
```

- [ ] **Done condition:** `projected == bills` for all 8 enrolled jurisdictions (US, FL, MI, AZ, VA, WA, UT, NC).
      Local reference counts: US 37,809; FL 7,685; VA 4,380; MI 4,013; WA 3,411; NC 2,338; AZ 2,190; UT 1,021
      (production will be larger).
- [ ] `with_abstract` is nonzero for FL and VA; `people` is nonzero for all eight.
- [ ] Size: `SELECT pg_size_pretty(pg_total_relation_size('ddp_bill_search'));` (local reference about 509 MB). Result: ______
- [ ] Spot checks return sensible results: an exact bill number, a misspelling, a topic word, a legislator name.
- [ ] No key gives 403, a bad key gives 401, `limit=101` gives 422.

## 7. Checks that only a real deployment can do

- [ ] **Through ddp-api** (from the broker host, 50 to 100 requests over mixed judged-set queries): `suggest` p95
      at or under **150 ms** full-path. Known slow shapes: `q=S 1` on search about 1.25 s; 3-character suggest
      about 150 ms before the extra hop. If over the bar: stop and revisit plan 4.5.2. p50 / p95: ______ / ______
- [ ] **Authorisation through the real ddp-api:** an unauthenticated `POST /openstates/ddp/search/refresh` and one
      with a READ-scope token are both rejected (401/403); `GET /openstates/ddp/search` with the read token is
      accepted. Also confirm api-v3 itself is reachable only from trusted callers (ddp-api, ddp-sync): its keys
      have no scopes, so any valid key can call its `POST /refresh` directly.
- [ ] **Importer freshness** on a NON-production database: change one bill's abstract through a normal
      scrape/import and confirm `refresh --dry-run` reports `would_refresh=1`.
- [ ] **Record the serving instance** (runbook section 4): ddp-api `OPENSTATES_SERVICE_URL` ______ ;
      ddp-sync `local_openstates_api_base` ______ ; broker `DDP_OPENSTATES_API_ROOT` ______ ; all three match the
      instance where the build ran.

## 8. Only after sections 2 to 7 pass

- [ ] Add the `ensure` block to `start-os-api.sh` in a `ddp-open-states` PR (text in the OPEN-310 runbook,
      section 3). Adding it before the Mac image is rebuilt makes every boot exit 1 and post a Slack alert.
- [ ] Enable the ddp-sync refresh hook (SYNC-87, not built yet). Not part of this deploy.
- [ ] Update OPEN-310 with every recorded value above, retarget and merge api-v3 PR #14, then close OPEN-310.

## 9. Rollback

- Image: `docker tag ddp-openstates-api:pre-open308 ddp-openstates-api:local`, then
  `docker-compose -f docker-compose.rds.yml up -d --no-deps --force-recreate api` (still scoped to `api`).
- The table is derived and nothing else reads it: `DROP TABLE ddp_bill_search;` loses nothing rebuildable. The
  routes return 500 until `ensure` plus a full refresh finish, so do it only with nothing consuming them
  (nothing does today). One `POST /ddp/search/refresh` (no jurisdiction) recreates and refills it.
- Leaving the routes and table in place is also safe; nothing calls them.

## 10. What was already tested (dev database `openstates_dev`, 2026-09-30)

Same code (`ce1447c`), same steps, 2,260 bills: import check, `ensure` (twice), dry run, first build (2,260
rows), second run (0), coverage `projected == bills` for all 7 dev jurisdictions, all five routes with the real
key check (403 / 401 / 200; 4xx for bad input), exact / typo / topic / name queries, stale detection (one
changed bill gave `would_refresh=1`, then 0), scoped `--full`, and drop-and-rebuild via a single
`POST /refresh`. **Not tested there:** anything at production scale, the ddp-api hop, read-scope rejection, the
live importer check, and the RDS publication gate in section 2.
