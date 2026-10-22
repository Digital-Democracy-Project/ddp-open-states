# REPLY: OPEN-330 live jurisdiction lists on the EC2-broker host, read-only (prod agent, 2026-10-22 16:50 UTC)

Nothing was changed or restarted. Values below are the jurisdiction lists as written. **One disclosure about my own handling:** a search I ran for "other jurisdiction variables" (item 5) used a pattern that also matched `OPENSTATES_*`, so the command output in my session printed the values of `OPENSTATES_API_KEY` (in both `.env` files), `DDP_OPENSTATES_API_KEY` and `DDP_OPENSTATES_BEARER_TOKEN` (broker `.env`) and `RDS_OPENSTATES_API_KEY` (ddp-sync `.env`; same value as the broker's `ddp-ro-` token for this host's api-v3). **No value is in this note or in any file I wrote**, but they are now in this session's transcript on this host. Whether to rotate them is the operator's call (the `OPENSTATES_API_KEY` is the third-party openstates.org key).

## 1. Production broker
* `/opt/ddp-broker-py/.env` `DDP_OPENSTATES_JURISDICTIONS` = **`MI,UT,US,VA,AZ,WA,FL`** (no MA, AL or NC).
* **Running containers** web, celery, celery-beat: the same value, `MI,UT,US,VA,AZ,WA,FL`, in all three. The containers were recreated 2026-10-20 00:43:48 to 00:43:49 UTC, after the file's last edit (2026-10-20 00:41:33), so the file and the running value agree.
* Other jurisdiction-like settings in that `.env`: `SEARCH_ALL_JURISDICTIONS=true` (a flag since 10-19; with it the search covers a list read from the data service: 10 states on 10-19, the 7 above plus AL, MA, NC, via `_jurisdictions_with_data()`, which is not in git or `.env`); `WEBFLOW_COLLECTION_ID_JURISDICTIONS` (a Webflow collection id, not a list).

## 2. ddp-sync on this host
* `DDP_OPENSTATES_JURISDICTIONS`: **unset** in `/opt/ddp-sync/.env` and in the running container. `LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST`: **unset** in both. (`.env` rendered 2026-10-14 15:03:20; container started 2026-10-19 03:59:43.)
* Effect, from the code (not a test): `config.py` turns an unset value into an empty list / empty set. `BILL_SYNC_ENABLED=false` and `LEGISLATOR_SYNC_ENABLED=false` on this host, so the pipelines that read `DDP_OPENSTATES_JURISDICTIONS` (bill sync, legislator sync) are not running here. The code comment says a jurisdiction "has to be on" the allowlist "to dispatch at all" (the replica-freshness check path); LegBot dispatches from this host have worked without it (NC 10-19, US/UT 10-20/21) and their results show `replica_freshness_content_check_bypassed: True`. **I did not read whether an empty allowlist is enforced on this host's path.**

## 3. ddp-sync `config/sync_schedule.yaml`
* Host `HEAD` `3e8a552`, working tree clean: **no local edits** (`git diff HEAD` is empty). `origin/main` is `74d72fe` (fetched today), so **the host is behind main**; `git diff` against `origin/main` is **58 added lines, all of them blocks the host does not have yet**: SYNC-128 `broker_bill_event_signal` (`enabled: false`, `jurisdictions: []`) and **OPEN-330 `jurisdiction_drift_check` (`enabled: true`, 06:20 UTC, every 7 days): it is not running on this host** because the code is not here.
* **The jurisdiction-list keys are identical to `origin/main`** (compared parsed values): `openstates_archive.jurisdictions` = fl, ut, az, wa, va, mi, ma, al, us, nc; `openstates_archive.schedule` = fl mon, ut mon, az tue, wa wed, va wed, mi thu, ma fri, al sat, us sun, nc thu; `openstates_scrape.secondary.jurisdictions` = va, mi, ma, ut, az, nc; `openstates_scrape.cloud_path.jurisdictions` = fl, wa, usa, va, mi, ma, ut, az, nc; `openstates_scrape.primary` = fl, wa, usa. `knowledge_base_embedding` and `bill_search_refresh`: **absent at the top level** in both the host copy and `origin/main` (they may live under another key; I did not search further).

## 4. Checkout freshness
`/opt/ddp-open-states`: `046c050462 2026-09-17 09:43:29 -0400 docs: document govbot-backed coverage sourcing and MI identifier normalization (#256)`; `git status -sb`: `## main...origin/main [behind 67]` (from the cached remote ref); **after a `git fetch` today it is 80 commits behind** (I only fetched, nothing was pulled). Nothing on this host pulls it. `origin/main` carries OPEN-327, 329, 330 and 331 (merged 10-21). So the `jurisdictions.yaml` that ddp-sync reads from this mount is the **09-17 version**, without those changes.

## 5. Other readers of a jurisdiction list on this host
* **ddp-sync `openstates_scrape.py` line 1699:** a hard-coded fallback `["va", "mi", "ma", "ut", "az"]` (no NC) used only when `openstates_scrape.secondary.jurisdictions` is missing from the yaml; today the yaml has the key, so it is not used.
* **Broker code:** the management commands `check_replica_parity`, `measure_search_coverage` and `backfill_eligible_for_scorecard` read `DDP_OPENSTATES_JURISDICTIONS`; a code comment mentions the website's `ExploreFilters.tsx` `TRACKED_JURISDICTIONS` array (a list in the website repo, not on this host).
* **This host's api-v3 container:** no jurisdiction variables.
* **Not visible from here:** the Mac's ddp-agents/CAMS lists, the Fargate task definition's environment (this host's role cannot describe ECS), and the votebot/ddp-api host.

## Not checked
Whether anything runs the drift check manually here; any list in the people-refresh or Webflow settings beyond the names above; the Mac side.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
