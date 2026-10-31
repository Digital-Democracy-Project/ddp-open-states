# Request: deploy api-v3 `dac69bc` (OPEN-467, the "current session" flags) on the EC2 host: build and recreate `api` only, no table change

Written by the Mac session at Ramon's instruction, 2026-10-31 about 19:50 UTC. **Nothing here has been run on production.** Ramon decides the time; please pick a quiet window and say when. The Mac (:8002) is already on `dac69bc` and verified.

## Why
api-v3 PR #42 (merged 2026-10-31 19:38 UTC) makes `GET /jurisdictions` and `GET /jurisdictions/{id}` with `include=legislative_sessions` return `is_current` and `is_previous` on every session. One rule, written once, in `api/current_session.py`; the sync scheduler, the nightly scraper script, the broker and the website will read the flag instead of each keeping their own rule (SYNC-139, OPEN-468, BROKER-369, NEXT-109 are blocked until this is live). Without the include nothing in a response changes.

## What is different from the OPEN-457 deploy
**No schema change, no `ensure`, no `refresh --full`.** The flags are computed per request from the sessions table; nothing is stored. Do **not** run the bill-search steps from the 10-30 request.

## Steps
0. **Before:** record the api-v3 checkout HEAD (expected `4e90dc0`, from your 10-30 report; I have not read it since), the `api` container's start time, `ddp-openstates-redis-1`'s start time and the `api` image ID. Tag the current image **`pre-open467`** (the rollback).
1. **Fast-forward only** `/opt/ddp-open-states/api-v3` to **`dac69bc`**. It is a straight fast-forward from `4e90dc0` (checked: `4e90dc0` is an ancestor). Two commits of mine are in between: `872c67d`/`a280b97` (a runbook sentence, docs only) and `1366c4a`/`dac69bc` (the change). Stop and report if it will not fast-forward. **Leave `/opt/ddp-open-states` itself alone** (your 10-30 report said it is 14 commits behind and not docs-only; that is a separate decision, not part of this request).
2. **Recreate only `api`:** `docker compose -p ddp-openstates-rds -f /opt/ddp-open-states/deploy/docker-compose.rds.yml up -d --build --no-deps api` (the form from 10-30; adapt to the host if it differs, always `--no-deps`, always the `api` service). Quiet window as before: no scrape, archive or text extract starting, few non-health requests. Check `GET /healthz` and that `ddp-openstates-redis-1`'s start time is unchanged.
3. **Smoke test (read key; do not paste it):**
   * `GET /jurisdictions/va?include=legislative_sessions` answers **200** and every session has `is_current` and `is_previous`;
   * `GET /jurisdictions/va` (no include) answers 200 with no `legislative_sessions` key;
   * `GET /ddp/search?q=One+Big+Beautiful+Bill` still answers 200 with HR 1 (US 119) first (the search path is untouched; this only shows the container is serving the table as before).
4. **Check the flags against this table** (what the rule gives on the Mac's data and the production session lists should be the same; today 2026-10-31): US 119 / previous 118; AL 2026rs / 2025rs; AZ 57th-2nd-regular / 57th-1st-regular; FL 2026 / 2025; MA 194th / 193rd; MI 2025-2026 / 2023-2024; NC 2025 / 2023; UT 2026 / 2025; VA 2026 / 2025; WA 2025-2026 / 2023-2024. Read each with `GET /jurisdictions/{id}?include=legislative_sessions` and list the identifiers whose `is_current` is true and whose `is_previous` is true. **A difference is not a failure of the deploy**: report it with the session list (identifier, classification, start and end date) so I can see which input differs. Record **host, value and time** on the report.
5. **Timing:** one `GET /jurisdictions?classification=state&include=legislative_sessions` (status and time). It is the same query as before plus a small computation; report only if it is slower than a second or two.

## Rollback
Re-tag `pre-open467` and recreate `api`. Nothing in the database changed, so there is nothing else to undo.

## Stop conditions
Anything that is not as written (a checkout that will not fast-forward, a 500, a missing flag, a smoke test that fails): stop, change nothing further, report. No retry and no rollback beyond the image re-tag above without authorization.

## Not authorized
`ensure`, `refresh` (full or per jurisdiction) or any other change to `ddp_bill_search`; any database change; fast-forwarding `/opt/ddp-open-states` itself; any change to the broker, ddp-sync, VoteBot or LegBot, a flag or schedule change, a scrape, archive or embedding run, anything in the Fargate task definition.

## Order against other releases
Independent of the broker release (BROKER-355) and of everything else. The consumers named above are separate tickets and wait for this to be live; none of them is part of this request.

## Reply
A `report-api-v3-open-467-...` note: the before and after checkout HEADs, image IDs and times, the smoke test status codes, the flag table from step 4 (current and previous per jurisdiction), the timing from step 5, whether the Redis start time was unchanged, and the `pre-open467` tag.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
