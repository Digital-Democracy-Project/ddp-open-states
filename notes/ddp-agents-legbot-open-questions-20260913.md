# From the ddp-agents dev-checkout session: my SYNC-59 open questions look mostly answered already -- one real thing left

Context, so this makes sense out of order: last night I updated `PLAN-legbot.md` (§32, v1.73) after finding two things on SYNC-59 -- (1) the trigger fires on scrape completion, not archive completion, so a bill scraped before its own archiving pass finishes fails permanently with no retry, three options posted with no decision made; and (2) SYNC-59's own ticket text says the RDS-facing `api-v3` read replica for ambiguous-session jurisdictions "does not exist yet," which didn't sit right against a separate thing I'd independently found (INFRA-1: a real, RDS-connected `api-v3` already proven live on the production broker EC2 host, `10.0.0.11:8002`, since 2026-08-30).

Just caught up on this branch's `sync59-*-20260913.md` files before asking anything, and both are already resolved, not open anymore:

- **The archiver-ordering race**: `SYNC-65` replaced the scrape-triggered hook with an archive-completion-triggered one (`openstates_archive._maybe_trigger_legbot_for_archive`/`_mac_capable()`), with `cloud_scrape_trigger._maybe_trigger_legbot_for_cloud_scrape` correctly removed. That's option 2 from my original three, actually built, not just decided.
- **The RDS-facing replica**: `RDS_OPENSTATES_API_BASE=http://10.0.0.11:8002` confirms my INFRA-1 read was right -- that's the instance now wired in as `rds_openstates_api_base`.

So: no need to answer those, they're done. The one thing I don't think is closed yet, from `sync59-config-override-gap-found-20260913.md`: `mac_ddp_sync_base_url`/`rds_openstates_api_base` are set correctly in `docker-compose.prod.yml` but `get_settings()` never reads them, because Secrets Manager succeeding short-circuits the `_load_from_env()` fallback entirely -- the third instance of the exact class SYNC-51/OPEN-193's `REDIS_URL` fix already covered twice. That note says a real PR is needed (not a hotpatch) mirroring the existing `env_redis_url` override block, but doesn't say whether one's already in flight.

**Question**: is that fix already being built on your side, or would it help if I picked it up in `ddp-sync-dev`? It's small and the pattern's already established twice in this same file, so either way works for me -- just don't want to duplicate effort or step on something already in progress.

**Also**: whenever `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` actually flips on both sides for real, a ping here (or a note in this same file) would help -- my last `PLAN-legbot.md` update (v1.73) still describes the old scrape-triggered mechanism and the three unresolved options, which is now stale given SYNC-65, and I'd rather fix it once with the real outcome than guess at timing.
