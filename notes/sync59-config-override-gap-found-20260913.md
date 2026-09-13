# PR #147/#148 deployed on EC2 host — new real bug found: MAC_DDP_SYNC_BASE_URL / RDS_OPENSTATES_API_BASE silently empty (SYNC-51/OPEN-193 pattern, 3rd instance)

`ddp-sync` at `af65fc3` (PR #147 SYNC-65 rework + PR #148's `_mac_capable()` fix) is now built
and deployed on this EC2 host. Clean restart, no errors, MA's in-flight Fargate scrape job
correctly reconciled again. Code verified present and correct by direct inspection in the
running container:

- `openstates_archive._maybe_trigger_legbot_for_archive` / `_mac_capable` present;
  `cloud_scrape_trigger._maybe_trigger_legbot_for_cloud_scrape` correctly gone.
- `_mac_capable()` correctly returns `False` on this host.
- The archive hook's non-Mac-capable branch matches exactly what was reported before: resolves
  sessions via `rds_openstates_api_base`/`rds_openstates_api_key` with
  `since_param="document_updated_since"`, dispatches via
  `_trigger_legbot_session_via_mac_wireguard` using `mac_ddp_sync_base_url`/`mac_ddp_sync_api_key`.

**But the requested end-to-end positive-match test (`resolve_touched_sessions` against `US`,
since the recent OPEN-192 Fargate archive completion) came back `[]` again — and this time
it's a real config bug, not a data-quality question.**

Root cause, confirmed directly in the running container:

`get_settings()` (`config.py`) calls `_load_from_secrets_manager()` first; on any host where
that succeeds (this one: `get_config_source()` returns `"secrets_manager"`), `_load_from_env()`
**never runs at all** — this is the exact same failure class already found and fixed twice
before (SYNC-51's 12 task-enable flags, OPEN-193's `REDIS_URL`), both of which got an explicit
per-host override loop added afterward in `get_settings()` (see the `_TASK_ENABLE_FLAG_ENV_VARS`
loop and the `env_redis_url` block, config.py ~723-740). **`mac_ddp_sync_base_url` and
`rds_openstates_api_base` never got that same treatment** — they're new fields added for
SYNC-59/PR#148, and unlike the actual secret-backed fields (`mac_ddp_sync_api_key`,
`rds_openstates_api_key`, which flow straight through `_load_from_secrets_manager()`'s raw JSON
since Ramon added them directly to `ddp-sync/credentials`), these two are plain per-host
resource addresses set only via `docker-compose.prod.yml`'s `environment:` block — exactly like
`REDIS_URL` already was, and for the same reason (different value needed per host).

Verified directly:
- Container env has both `RDS_OPENSTATES_API_BASE=http://10.0.0.11:8002` and
  `MAC_DDP_SYNC_BASE_URL=http://10.0.0.8:8001` set correctly (`docker exec ... printenv`).
- `get_settings().rds_openstates_api_base` and `.mac_ddp_sync_base_url` both come back `''`
  regardless — confirmed via direct `python3 -c` inspection in the running container.
- `get_settings().mac_ddp_sync_api_key` / `.rds_openstates_api_key` are both present and correct
  length (64/50 chars) — proving the secrets-manager path itself is fine, this is specific to
  the two non-secret fields.
- Live failure mode confirmed: calling `resolve_touched_sessions("US", ..., api_base="")`
  raises `httpx.UnsupportedProtocol` inside the HTTP call, caught by the caller's own
  `except Exception` in `_maybe_trigger_legbot_for_archive` (logged as
  `archiver_triggered_legbot_session_resolution_failed`), returns silently. **No crash, no
  visible error unless someone greps for that specific log line — the archive-completion hook
  would appear to run successfully and simply never trigger LegBot, on every EC2-orchestrated
  archive completion.** This is a new instance of the exact silent-gap class PR #148 was written
  to close, just from a different cause than the one PR #148 fixed.

**No live production impact yet** — `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` is still `false`
on this host, confirmed. But this must be fixed before that flag can safely go on, since as
currently deployed the EC2 fallback path PR #148 built would silently no-op every time.

**Suggested fix** (not applied — this needs a real PR, not a live hotpatch, since it must
survive the next deploy): add `mac_ddp_sync_base_url` and `rds_openstates_api_base` to the same
per-host override treatment `REDIS_URL` already has in `get_settings()` — read
`os.getenv("MAC_DDP_SYNC_BASE_URL")` / `os.getenv("RDS_OPENSTATES_API_BASE")` unconditionally
and override `filtered[...]` when set, exactly mirroring the existing `env_redis_url` block.

Not flipping `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` — holding per Ramon's standing
instruction to coordinate this deliberately, now doubly warranted.
