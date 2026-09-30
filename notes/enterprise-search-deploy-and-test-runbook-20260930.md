# Enterprise search: what to deploy, in what order, and how to test it (ops handoff)

Written 2026-09-30 for the ops agent / Ramon. Design: `ddp-infra/PLAN-enterprise-search.md` (v0.5,
merged) — §4.5 (OpenStates leg), §5.6 (new Pinecone index), §10.1 (rollout and rollback).
Companion runbook for the api-v3 half: `docs/runbook/ddp-bill-search.md` in api-v3 PR #14 (not merged yet).

**Merged is not deployed.** Everything below is merged to `main` in its repo and NOT deployed anywhere.
Before deploying any repo, check the live checkout is actually behind: `git rev-list --count HEAD..origin/main`.

## 1. Safety rules (read first)

1. **LegBot reads the OpenStates replica through the Mac's `ddp-openstates-api-1` container (:8002).** On
   2026-09-30 that container's `DATABASE_URL` pointed at database `openstates_rds_repl_20260911`. Do not
   restart, rebuild or write to it during a LegBot run without checking activity first. Every change below
   to that database is additive, but it is still a write to a database LegBot reads.
2. **Never run a bare `docker compose up -d --force-recreate`** for api-v3: it recreated the shared
   Postgres once and killed two live scrapes (OPEN-101). Use `ddp-open-states/refresh-api-v3.sh`, which
   scopes to the `api` service and verifies Postgres was not restarted.
3. **Never `git pull origin main` on the EC2 civic (votebot/ddp-api) host**, and **never set
   `KNOWLEDGE_BASE_INDEX_NAME` there**. It runs `feat/rds-openstates-routing-standalone` and is being
   retired. Only the Mac Studio and EC2-broker ddp-sync instances get this code.
4. **Never write to or delete from the existing Pinecone index `votebot-large`** (47,654 vectors on
   2026-09-30). The new index is `ddp-knowledge-base`; nothing in this handoff touches the old one.
5. Test runs must not emit production alerts (Slack, CodeBot). Nothing below sends any; keep it that way.
6. Do not enable the ddp-sync embedding hook until §5 (OPEN-311) is deployed.

## 2. What is merged, per repo (all dormant or off by default)

| Repo | Ticket / PR | Merge | What it adds |
|---|---|---|---|
| api-v3 | OPEN-308 #12 | `ed6e89b` | `ddp_bill_search` table and refresher (`python -m api.search_projection ensure/refresh`) |
| api-v3 | OPEN-309 #13 | `ce1447c` | `/ddp/search` routes: search, suggest, hydrate, coverage, POST refresh |
| api-v3 | OPEN-310 #14 | NOT merged | the runbook; PR base must be retargeted to `main` |
| ddp-broker-py | BROKER-163 #379 | `4ada52e6` | migrations 0064 (`CREATE EXTENSION pg_trgm`, fields), 0065 (two GIN trigram indexes, concurrent) |
| ddp-broker-py | BROKER-165 #380 | `b461fb96` | `ddpbroker/search/fusion.py` (pure code, no deploy step) |
| ddp-broker-py | BROKER-161 #381 | `ca8d2d79` | `manage.py measure_search_coverage` (read-only) + `PINECONE_*` settings |
| ddp-broker-py | BROKER-162 #382 | `6e7adb16` | judged query set + `manage.py run_search_eval` |
| ddp-broker-py | BROKER-179 #383 | `5589731e` | bill-number recognizer accepts one trailing letter |
| ddp-broker-py | BROKER-176 #384 | `847d55a9` | OpenStates search client (dormant until BROKER-166 exists) |
| ddp-broker-py | BROKER-164 #385 | `292f7433` | search-text tasks, `post_save` receivers, nightly 03:30 rebuild, migration 0066 (help text) |
| ddp-broker-py | BROKER-169 #386 | `828b9b3b` | nightly coverage-report task and per-request log helper |
| ddp-sync | SYNC-89 #174 | `69607e8` | `knowledge_base_index_name` setting (unset = off) |
| ddp-sync | SYNC-83 #175 | `b14ac70` | post-archive embedding hook (off by default) |

**Not built yet:** BROKER-166 (`/api/search/`), SYNC-87 (ddp-sync refresh hook for the search projection),
SYNC-90 (backfill), SYNC-91, VOTEBOT-8/10, SYNC-92, OPEN-311. So **no visitor-facing search exists to
deploy or test yet**; this handoff gets the plumbing in place and verified.

## 3. Deploy order

1. **api-v3 on the instance that serves production** (§4.1). Verify. Nothing calls it yet.
2. **ddp-broker-py** (§4.2): migrate, restart, register the schedule, run the one-time text backfill.
3. **ddp-sync** on Mac Studio and EC2-broker (§4.3), with the new setting and the hook both OFF.
4. **Later, after OPEN-311 is merged and deployed to api-v3** (§5): turn the hook on for one small
   jurisdiction, verify, then widen.

## 4. Per-component steps

### 4.1 api-v3 (OPEN-308 + OPEN-309)

Two instances exist: the RDS-backed one (broker host `10.0.0.11`, `deploy/docker-compose.rds.yml`) and the
Mac's (:8002). **Correction 2026-09-30 (OPEN-312):** an earlier version of this note said search must be
served from the RDS-backed one because the Mac replica lacks abstracts and people. That is stale: the live
subscription covers 47 tables and the Mac replica holds 27,673 abstracts and 4,088 people, so either instance
can serve search. Prefer the RDS-backed one because it is authoritative and the replica runs about 11 s behind,
but it is a choice, not a requirement. If you do build on the Mac, remember it is the database LegBot reads
(rule 1 above). Decide and record which instance serves production, and make three things name the SAME instance:
where `ensure`/first build run, ddp-sync `local_openstates_api_base`, and ddp-api `OPENSTATES_SERVICE_URL` /
broker `DDP_OPENSTATES_API_ROOT`.

1. Update the checkout and rebuild the `api` image from `main` (contains `api/search_projection.py` and
   `api/ddp_search.py`). Mac: `ddp-open-states/refresh-api-v3.sh` (it does the checkout, pull, rebuild and
   a redeploy scoped to the `api` service, and verifies Postgres did not restart). RDS-backed host: use the deploy method already in place for `docker-compose.rds.yml`,
   scoped to the `api` service only.
2. Import check on the running container (must exit 0):
   `docker exec <api-container> python -c "import api.ddp_search, api.search_projection"`
3. `docker exec <api-container> python -m api.search_projection ensure`
   → `=== BILL SEARCH ENSURE: ddp_bill_search present ===`. It creates extension `pg_trgm`, the table and 4
   indexes; idempotent, about 0.5 s. DDP controls the RDS instance, so the extension permission is not a
   risk there (Ramon, 2026-09-30); record that it worked.
4. `... refresh --dry-run` then `... refresh` (first build, all jurisdictions). Local reference: 148 s for
   75,805 bills via the CLI, 169 s via the POST loop; the table is about 509 MB (fts index 75 MB).
   Expect similar on RDS; network latency changes it. Stop if any single POST call or statement cannot finish
   inside its timeout (POST call about 20 s of work; statement timeout 30 s).
5. Coverage must show `projected == bills` for the 8 enrolled jurisdictions (US, FL, MI, AZ, VA, WA, UT, NC):
   `GET /ddp/search/coverage?jurisdiction=US&jurisdiction=FL&...` (needs an api-v3 key). Local reference
   counts: US 37,809; FL 7,685; VA 4,380; MI 4,013; WA 3,411; NC 2,338; AZ 2,190; UT 1,021 (production will be
   larger). `with_abstract` is nonzero only for FL and VA; `people` nonzero for all.
6. Timing, warm, one client, local numbers as reference: `GET /ddp/search` p95 about 116 ms, `suggest` p95
   about 83 ms, `hydrate` of 50 ids about 6 ms. **Known slow shapes (not fixed):** `q=S 1` about 1.25 s;
   3-character `suggest` about 150 ms. Then measure `suggest` p95 through ddp-api from the broker host with
   50 to 100 requests; the bar is 150 ms full-path (plan §10.1 stop condition).
7. Authorisation through the real ddp-api: unauthenticated `POST /openstates/ddp/search/refresh` and a
   READ-scope token both rejected (401/403); `GET /openstates/ddp/search` accepted with a read token; the
   key in `DDP_OPENSTATES_BEARER_TOKEN` is read-scope only. api-v3 keys have no scopes, so also confirm
   api-v3 itself is reachable only from ddp-api and ddp-sync.
8. Importer freshness: change one bill's abstract through a normal scrape/import on a NON-production
   database and confirm `refresh --dry-run` reports `would_refresh=1`.
9. Only after 1 to 8: add the `ensure` block to `start-os-api.sh` (text in the OPEN-310 runbook §3), in a
   ddp-open-states PR. Adding it BEFORE the image is rebuilt makes every boot exit 1 and post a Slack alert.

**Rollback:** the table is derived. `DROP TABLE ddp_bill_search` loses nothing rebuildable, but the routes
500 until `ensure` and a full refresh finish, so do it with nothing consuming them (nothing does today).
Redeploying the previous api image is also safe: nothing else reads the table.

### 4.2 ddp-broker-py (BROKER-161/162/163/164/165/169/176/179)

Follow `docs/runbook-prod-broker.md` §5 (full code deploys). Specifics for this release:

1. Read the diff first. **No new Python dependencies** (BROKER-164 reuses `celery_once`). **New optional env
   vars**: `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` (default `votebot-large`), `PINECONE_NAMESPACE` (default
   `default`), used only by `measure_search_coverage`; an empty key just reports "unavailable". Put them in
   `/opt/ddp-broker-py/.env` before recreating anything if you want the Pinecone check to run.
2. `git pull` in `/opt/ddp-broker-py`; the app is bind-mounted, so use `dc restart web celery celery-beat`
   (a plain `up -d --no-deps` does NOT pick up code). Restart `nginx` last.
3. **Before migrating production, confirm the broker DB role can `CREATE EXTENSION pg_trgm`** (plan §10.1
   stop condition; `unaccent` already installs the same way, which is encouraging but not proof).
4. `dc exec web python manage.py migrate` → 0064 (extension + fields), 0065 (two concurrent GIN indexes),
   0066 (help text). Dev timings on a production snapshot (26,617 bills): about 2 s each. Then
   `dc exec web python manage.py makemigrations --check` (expect "No changes detected").
5. **Register the nightly schedule** (merging does not): `dc exec web python manage.py scheduled_tasks_create`.
   It adds the 03:30 rebuild and the 03:30 coverage report.
6. **One-time backfill of search text** (must be done before the search endpoint is exposed):
   `dc exec web python manage.py shell -c "from ddpbroker.search_tasks import rebuild_all_search_documents as t; print(t.run())"`
   Confirm `bills_updated` and `representatives_updated` equal the table totals; a second run updates 0.
   Dev timing: 1.2 s for 26,617 bills.
7. From now on every Bill/Representative save enqueues a small Celery task (`on_commit`, robust to broker
   outage). Confirm celery is running and the queue drains.

**Verify (read-only):**
- `dc exec web python manage.py measure_search_coverage` — expect step 1 to FAIL at 0.0% (known: nothing sets
  the artifact sync fields; plan §4.4 was corrected), steps 2 and 3 "UNAVAILABLE" until the OpenStates
  routes are reachable from the broker, then real numbers. **Step 3 currently reports 10 tracked bills with no
  OpenStates id (BROKER-178, Florida special-session bills)** — a launch gate for search.
- `dc exec web python manage.py run_search_eval --validate-only` — expect "Judged set OK: 65 queries".
  A live run reports UNAVAILABLE until `/api/search/` exists (BROKER-166).
- Trigram timing on the real data, in a rolled-back transaction, using the queries in BROKER-164's comments.
  **Relevance warning:** at the 0.3 threshold "school lunch" and "hb1" return 0 broker rows and "medicade
  expansion" returns 1; the threshold/operator must be tuned against the judged set before exposure
  (BROKER-166 / BROKER-162).

**Rollback:** the migrations are reversible (`migrate common 0063`; 0064 drops the extension only if nothing
else uses it, and fails loudly if another trigram index exists). Disable the schedule by deleting the two
periodic tasks in Django admin. The receivers can be neutralised by redeploying the previous commit.

### 4.3 ddp-sync (SYNC-89 setting, SYNC-83 hook)

Deploy to **Mac Studio and EC2-broker only** (never EC2 civic). Mac:
`cd /Users/agentsmith/Developer/repos/ddp-sync && git pull origin main` then
`sudo launchctl kickstart -k system/com.ddp.ddp-sync`, then
`curl -s http://localhost:8001/ddp-sync/v1/schedule` (the OpenStates jobs must still be listed). The service
runs as a system LaunchDaemon, so the restart needs root. Merging alone changes nothing on either host.

The new code is inert until both are set on a host: env `KNOWLEDGE_BASE_INDEX_NAME=ddp-knowledge-base` and the
yaml block `openstates_archive.knowledge_base_embedding.enabled: true` (OPEN-124: scheduler settings live in
`sync_schedule.yaml`). The embedding needs OpenAI and Pinecone keys on that host; ddp-sync's own env lacked them
on 2026-09-30 (the measurement borrowed keys from `ddp-agents/.env`), so provision them deliberately.
The hook never writes to `votebot-large`; `knowledge_base_settings()` refuses that name.

**Pinecone state:** index `ddp-knowledge-base` was created 2026-09-30 with `votebot-large`'s settings (dense,
3072 dimensions, cosine, aws us-east-1, deletion protection on) and is EMPTY. Verify with `describe_index_stats`
(read-only) before and after anything you enable.

## 5. Blocker before turning the embedding hook on: OPEN-311

api-v3 does NOT yet return the archive `document_id`, version stage/ordinal, or text for stage-unknown versions
(about 5% of documents). The hook depends on them and does nothing (with a warning per bill) until they exist.
The change is on a local, unpushed api-v3 branch `feat/ddp-version-document-id-stage` (commit `0e786ab`); OPEN-311
tracks it. It needs its own PR, merge and api-v3 deploy (repeat §4.1 steps 1 to 2). **Do not enable
`knowledge_base_embedding` before that is live.**

When it is: enable the hook for ONE small jurisdiction first (UT: 1,021 bills), let one archive run finish,
then check: (a) `describe_index_stats` shows vectors; (b) a sampled bill has `bill-text:<ocd_bill_id>:<document_id>`
per version, `bill-version-diff:...` for versions with a stored diff, and `bill-votes:<ocd_bill_id>`; labels
`version_note/date/stage/ordinal` present; (c) a second archive run writes 0 new documents; (d) no
`bill_version` legacy keys or `votebot-large` counts changed. Backfill estimates (revised 2026-09-30): about 600M
tokens, 671k vectors, roughly $78 for all versions plus diffs; about 58 to 95 hours at the measured speed with
sequential embedding; the backfill (SYNC-90) is not built.

## 6. Known gaps and follow-ups (all ticketed or noted)

- No alert exists for a missed nightly rebuild/report run; it shows as a missing "finished" log line.
- `log_search_request` has no callers until BROKER-166; request metrics have no data until then.
- ddp-sync hook does not write `is_ddp_curated`/`ddp_url` metadata, and does not remove index entries for
  versions api-v3 stops returning.
- BROKER-178: 10 tracked Florida bills have no OpenStates id (7 fixable by the reconcile job).
- Trailing-letter numbers work (BROKER-179); Michigan letter-only resolutions (`HJR A`) and other states'
  formats are BROKER-180.
