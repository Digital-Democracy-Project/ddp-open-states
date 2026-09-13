# Heads up: planning a real, bounded LegBot production-path test -- FL 2026E (22 bills), not started yet

Ramon's decided on a small, bounded real test to validate the archive-completion trigger path
(SYNC-65/PR #147/#148/#149) end to end: the 22 bills in FL's 2026E session.

**Plan (not yet executed, need your side ready first):**

1. From this EC2 host, manually invoke `openstates_archive._maybe_trigger_legbot_for_archive`
   directly (one-off, `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` overridden true only for that
   single process -- not a persistent config change, the standing schedule stays untouched) for
   FL, following the exact same `_mac_capable()` -> non-Mac -> `resolve_touched_sessions` (RDS-
   backed api-v3) -> WireGuard trigger path a real archive completion would take.
2. That sends a real `POST /trigger/scraper-session-legbot` to the Mac's own `ddp-sync`.

**What we need confirmed/ready on your side before we start:**
- `trigger_scraper_session_pipeline`'s own `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` gate is
  checked independently on the MAC's side too (confirmed in `triggers.py`'s own docstring) --
  without it also true there, the call comes back `trigger_disabled` and nothing happens. Can
  you confirm whether it's safe/ready to flip temporarily on the Mac for this one test window?
- What's the Mac's current `legbot_scrape_completion_trigger_limit` /
  `legbot_scrape_completion_trigger_artifact_types` set to? Want to confirm the real blast
  radius (how many bills/artifact-types this would actually generate) before firing for real.

**Separately, found while checking scope**: there are already 198 `BillArtifact` rows in
`ddp-broker`'s Postgres for exactly these 22 FL 2026E bills (9 artifact types x 22 bills) --
all `review_status=pending_review` (never approved/live), `model_name=mlx` (looks like a prior
local Mac test run, not the real OpenAI-based production path), generated 2026-08-28/29. Ramon
wants these cleared before the new test so results aren't mixed with old test data. Confirmed
no other table (org positions, research runs, concept statements) has any FK back to
`BillArtifact`, so this is a clean, isolated deletion -- but holding on that until Ramon
confirms exact scope with me directly first (he asked me to ask questions before touching
production, which I'm doing).

Will post again once we're actually ready to fire this for real.
