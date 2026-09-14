# OPEN-290: 4th config-override instance fixed, pushed to the PR

Good catch -- confirmed your root cause and fixed it the same way. `get_settings()` now
has the same per-host env-override treatment `REDIS_URL`/`mac_ddp_sync_base_url`/
`rds_openstates_api_base` already had, extended to all four
`legbot_scrape_completion_trigger_*` fields:

- `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ARTIFACT_TYPES`
- `LEGBOT_SCRAPE_COMPLETION_TRIGGER_LIMIT`
- `LEGBOT_SCRAPE_COMPLETION_TRIGGER_INCLUDE_CONCEPT_STATEMENTS`
- `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` -- included this one too even though OPEN-290
  didn't newly depend on it. It's the exact same bug on a sibling field in the same feature
  area, and it's already load-bearing today for whether `_maybe_trigger_legbot_for_archive`'s
  EC2 branch even attempts a WireGuard call at all -- if it's been silently inert on EC2 this
  whole time (same root cause: `_load_from_env()` never running there), the archive-
  completion hook may have been a no-op on every EC2-orchestrated archive completion since
  SYNC-65 shipped, independent of OPEN-290. Worth checking directly once you're setting the
  other three, since it's the same one-line fix and the same env var either way.

Pushed to the PR branch (`feat/OPEN-290-consolidate-legbot-trigger-endpoints`, commit
`15a41da`). Added the same precedence tests the earlier three fields have (env wins over a
conflicting Secrets Manager value, not just "applies when the secret omits it entirely").
Full suite: 1250 passed.

Over to you for the `docker-compose.prod.yml` env vars + live verification, same as you
outlined. Let me know if anything else turns up.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
