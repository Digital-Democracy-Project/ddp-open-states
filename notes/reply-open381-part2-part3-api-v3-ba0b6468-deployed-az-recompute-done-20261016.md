# Reply to OPEN-381 Parts 2 and 3: api-v3 `ba0b6468` is live on the RDS-backed instance and the Arizona recompute is DONE. Every gate passed. (prod agent, EC2 host, 2026-10-16 05:00 UTC)

Followed GO note `bbc429b7` (and `dc6da59`). Ramon confirmed both parts in this session. Only Arizona and only api-v3 were touched: no other state, no `all`, no flag, schedule, scrape, archive, embedding or LegBot run, no change to existing installs, the Fargate task definition or `delete_orphans`, no rollback.

## Part 2: api-v3
* **Quiet:** no Mac writes in 5 minutes, no scrape/archive/text-extract process, 8 api-v3 requests in 2 minutes.
* **Rollback tag:** `ddp-openstates-api:pre-open381` = image `8b7df04cc29f` (the `5a0ee983` build of 01:25 UTC). Earlier tags (`pre-open352`, `pre-open361` ...) also kept.
* **Checkout:** `/opt/ddp-open-states/api-v3` clean at `5a0ee983`; `git pull --ff-only` to **`ba0b64685b2eab50bf605c6eec29ace99ce7bf0a`** (PR #31, includes #30).
* **Build and swap:** `docker compose -f deploy/docker-compose.rds.yml build api`, then `up -d --no-deps api` (the `api` container only). New image **`cc7deeaaa1a9`** (built 2026-10-16 04:56:42 UTC), healthy after about 40 seconds.
* **Check, through this instance's API:** Arizona `HB 2014` (57th-2nd-regular) versions
  * before: `Introduced Version`, `House Engrossed Version`, `HOUSE - Appropriations`, `HOUSE - Natural Resources, Energy & Water`, `SENATE - Natural Resources`
  * after: **`Introduced Version`, `HOUSE - Natural Resources, Energy & Water`, `HOUSE - Appropriations`, `House Engrossed Version`, `SENATE - Natural Resources`** (the Engrossed version is after both House committee documents and before the Senate one, as expected).
  * The OPEN-352 checks still pass: NC HB 59 `Edition 1` = amendment, WA SJM 8012 `Joint Memorial` = introduced. Broker `/api/status/` 200; no errors in the api-v3 log afterwards.

## Part 3: the Arizona recompute (one state, never `all`)
* **Code:** throwaway `git worktree` of `/opt/ddp-open-states/openstates-core` at exactly `53feef5bdde1f277195719a9144f88f6c38fe4dc`, first on `PYTHONPATH`, the existing venv's Python and `os-text-extract`, `DATABASE_URL` from the environment only (never printed). **G1:** `OK <worktree>/openstates/__init__.py`.
* **G3 before:** failed-amendment documents 16 (all 16 with a diff); blank documents with a diff 0; Arizona documents 8,933, 4,342 with a diff.
* **RDS latest restorable time just before the commit: 2026-10-16T04:51:46Z.** Quiet: no scrape, archive or text-extract process on this host.

| step | exact output line | time |
|---|---|---|
| dry run (equal to the gate line) | `az: [DRY RUN] 2190 bills checked \| unchanged=6934 corrected=1982 nulled=17` | 04:58:24 (26 s) |
| commit | `az: [COMMITTED] 2190 bills checked \| unchanged=6934 corrected=1982 nulled=17` | 04:58:54 (30 s) |
| second dry run | `az: [DRY RUN] 2190 bills checked \| unchanged=8933 corrected=0 nulled=0` | 04:59:20 |
* **G3 after:** failed-amendment documents with a diff **0** (was 16); blank documents with a diff **0**; Arizona documents 8,933 (unchanged), **4,326 with a diff** (was 4,342; the difference is the net of 17 diffs removed and 1 added).
* The worktree was removed; the host's own core checkout is still `5c79b47d`.

## Not done
No Arizona summary regeneration (OPEN-383 is a separate GO), and no other recompute. No run of any kind was started by me.

Files and outputs: `/home/bitnami/ops/open381-part1-20261016/` (Part 1) and `/home/bitnami/ops/open381-part3-20261016/` (`run.log`, `summary.json`, the dry-run and commit outputs) on this host.
