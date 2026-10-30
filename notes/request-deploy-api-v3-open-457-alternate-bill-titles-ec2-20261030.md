# Request: deploy api-v3 `4e90dc0` (OPEN-457, a bill's other titles) on the EC2 host: add the column first, then recreate `api`, then rebuild the search table

Written by the Mac session at Ramon's instruction, 2026-10-30 about 18:20 UTC. Ramon asked for the pull and restart of api-v3 on production. **Nothing here has been run on production.** Ramon decides the time; please pick a quiet window and say when.

## Why
api-v3 PR #39 (merged 2026-10-30) makes a bill findable by its other titles (`opencivicdata_billtitle`), such as "One Big Beautiful Bill Act" for HR 1, and ranks a whole-phrase title match first. It adds a column `alt_titles` and an index to the derived table `ddp_bill_search`. Full text, order and results: api-v3 `docs/runbook/ddp-bill-search.md` **section 8** (PR #40), and `PRIMITIVES.md` in this repo.

## The order matters (a new image on an old table makes every search answer 500)
`ensure` runs only on `refresh`, never at boot, and the new code reads `alt_titles`. So the column has to exist **before** the new container serves. Do the steps in this order.

0. **Before:** record the api-v3 checkout HEAD (last known to me: `f9dde91`, from your report of 2026-10-28; I have not read it since), the container's start time, `ddp-openstates-redis-1`'s start time, and the `api` image ID. Tag the current image `pre-open457` (the rollback).
1. **Fast-forward only** `/opt/ddp-open-states/api-v3` to **`4e90dc0`** (it contains PR #39, merge `b9d2f61`). Also fast-forward `/opt/ddp-open-states` itself if it is behind (docs only; no code in it changes). Stop and report if either will not fast-forward.
2. **Build the image without recreating the container** (`docker compose -p ddp-openstates-rds -f /opt/ddp-open-states/deploy/docker-compose.rds.yml build api`). The running container still runs old code and is unaffected.
3. **Add the column from the new image, before the swap:**
   `docker compose -p ddp-openstates-rds -f /opt/ddp-open-states/deploy/docker-compose.rds.yml run --rm --no-deps api python -m api.search_projection ensure`
   Expect `=== BILL SEARCH ENSURE: ddp_bill_search present ===`. (This is the Mac form from the runbook adapted to the host's compose file and project name, which I have not read from the host; adapt as needed, always `--no-deps`, always the `api` service.) The index is created without `CONCURRENTLY`, so writes to `ddp_bill_search` wait while it builds (reads do not); on the Mac the column was empty and it took seconds. **Run it when no `refresh` is running** (check ddp-sync's hook calls and the advisory lock).
4. **Gate: stop here if either query returns nothing.** On the database the `api` container uses (read its `DATABASE_URL`; do not assume; do not paste the URL in the reply):
   * `SELECT current_database();` names the production bills database;
   * `SELECT column_name FROM information_schema.columns WHERE table_name='ddp_bill_search' AND column_name='alt_titles';` returns a row;
   * `SELECT indexrelid::regclass FROM pg_index WHERE indexrelid='ddp_bill_search_alt_titles_idx'::regclass AND indisvalid;` returns the index.
5. **Recreate only `api`:** `docker compose -p ddp-openstates-rds -f /opt/ddp-open-states/deploy/docker-compose.rds.yml up -d --build --no-deps api`, in the quiet window as on 10-28 (no scrape, archive or text extract starting; few non-health requests). Check `GET /healthz` and that `ddp-openstates-redis-1`'s start time is unchanged.
6. **Smoke test before step 7:** `GET /ddp/search?q=One+Big+Beautiful+Bill` and `GET /ddp/search/suggest?q=One+Big` (with the read key; do not paste it) must answer **200**. **Stop condition:** any 500 means the table lacks the column. Put the `pre-open457` image back at once and redo the gate.
7. **Fill the table:** `docker exec ddp-openstates-api-1 python -m api.search_projection refresh --full` (use the host's container name). Allow **about 26 minutes** on RDS (the Mac took about 3 minutes; the first RDS build took 26). It is safe to interrupt and run again: each call upserts a batch, and a bill is complete or still stale, never half-written. If ddp-sync's hook is on, its call for a jurisdiction being rebuilt answers `busy: true` and the hook retries.
8. **Check and record host, value and time:**
   * `GET /ddp/search/coverage` shows `projected == bills`;
   * `SELECT count(*) FILTER (WHERE alt_titles <> ''), count(*) FROM ddp_bill_search;`. Mac, 2026-10-30: 29,820 of 77,649, about 38 percent. Production should be of the same order (a count near 0 means step 7 did not finish; run it again);
   * `GET /ddp/search?q=One+Big+Beautiful+Bill` returns HR 1 (US 119) first, and `q=FEHB+Protection+Act` returns HR 1 in the top five (Mac: 4th);
   * time the multi-word queries from section 6 of the runbook and compare with its numbers, and the single words `act`, `state`, `school`, `health`, `public` against your 10-28 table (single words and bill numbers run the same SQL as before, so they should be unchanged).

## Rollback
An image rollback, not a data rollback: re-tag `pre-open457` and recreate `api`. The column, the index and `alt_titles` stay and are harmless to old code. After step 7, old code on the rebuilt table also finds bills by their other titles (it just does not rank a whole-phrase match first). If you want a copy of the table first, `pg_dump -t ddp_bill_search` before step 7; it is derived data and nothing else is lost.

## Stop conditions
Anything that is not as written (a checkout that will not fast-forward, a gate that returns nothing, a 500, a refresh that errors): stop, change nothing further, report. No retry and no rollback beyond the image re-tag above without authorization.

## Not authorized
Any change to the broker, ddp-sync, VoteBot or LegBot, a flag or schedule change, a scrape, archive or embedding run, anything in the Fargate task definition, `delete_orphans`, `refresh` for a single jurisdiction in place of `--full`, and any other database change than `ensure` and `refresh --full` on `ddp_bill_search`.

## Order against the broker release
Independent. The broker needs nothing from this change and this change needs nothing from the broker (the `title` api-v3 returns is unchanged; the broker's staff-title change is BROKER-355). Either can go first. Ramon's broker release (`/broker-deploy`) is a separate request.

## Reply
A `report-api-v3-open-457-...` note: the before and after checkout HEADs, image IDs and times, the gate output (database name, column and index present, no URL), the smoke test status codes, the refresh duration and counts, the search checks and timings from step 8, whether the Redis start time was unchanged, and the `pre-open457` tag.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
