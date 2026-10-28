# Report: OPEN-318 on the EC2 host. The api-v3 enrollment endpoint is live; both checkouts pulled; api recreated in about 4 s

Prod agent, Wed 2026-10-28 00:15 UTC. The operator said "Option A, go now" in my session (in the quiet window: api-v3 had no non-health request in the last 5 min, VoteBot no query, nothing in flight). Output saved in `/home/bitnami/ops/open318-readonly-20261028T0008Z/`.

## What changed
1. **Pulls (fast-forward only, both trees clean before):** `/opt/ddp-open-states` `9baa61ed59` to **`3b78732760dd7aa4948743d92517262471889f25`**; `/opt/ddp-open-states/api-v3` `a2f5db8` to **`d5b37dc60d4c02db8d68c8fdeed4b51d8f7937e2`**. The 13 commits touch nothing in `deploy/`, `api-v3/` or `people/`. Host `jurisdictions.yaml`: 0 to **10** `scheduled:` lines, mtime 00:13:35.470 UTC.
2. **Before the recreate:** compose `config` for `api` showed the mount (`/opt/ddp-open-states/jurisdictions.yaml` to `/app/jurisdictions.yaml`, ro) and 11 environment variables identical (by value) to the running container's; old container log saved to `log-archive/ddp-openstates-api-1-*.log.gz`.
3. **`docker compose -p ddp-openstates-rds -f deploy/docker-compose.rds.yml up -d --build --no-deps api`:** built and recreated in **4 s**; healthy by 00:14:06. New container created 00:13:50, started 00:13:51, `restart: unless-stopped`, image `6e3a0d7e0e10` (old: `84fa…1511`, 10-21). Downtime was a few seconds.
4. **Redis:** `ddp-openstates-redis-1` start time unchanged (2026-10-11T19:49:12.477Z). No Postgres on this host.

## Verification (no key printed)
* Mount present, read-only. **File mtime identical inside and on the host** (1793146415.470006 vs .470005935). **10 `scheduled:` lines** inside the container.
* `GET /ddp/enrollment`: **HTTP 200** with the key from `DDP_OPENSTATES_API_KEY`; **403** without a key. Response keys: `jurisdictions`, `manifest_mtime`; **`manifest_mtime` = 2026-10-28T00:13:35.470006+00:00** (matches the host file).
* Other callers still fine: `GET /bills?jurisdiction=AZ&per_page=1` 200, `GET /ddp/embedding/ledger?jurisdiction=az` 200, broker search through Django 200 (`partial` false). No error or traceback in the new container's log. Health check 200.

## Not done (as instructed) and still open
* **ddp-sync was not restarted**, so its `jurisdiction_manifest_unusable ... 'scheduled'` warning is still the last word until its next restart; I will check it then. The drift job stays **disabled** here (`jurisdiction_drift_check_enabled` False); enabling it is your later request (`JURISDICTION_DRIFT_CHECK_ENABLED=true` in ddp-sync's `.env` plus a restart; note that on this host ddp-sync's `.env` is regenerated from Secrets Manager at every start, so a hand edit will not survive, the value must go into the secret).
* **Broker** untouched; `DDP_ENROLLMENT_SOURCE` is not set (default `env`). Whether the hourly drift log line appears I cannot say, as before.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
