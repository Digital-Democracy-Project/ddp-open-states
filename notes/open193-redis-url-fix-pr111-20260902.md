# PR #110 confirmation received; Finding 3 (redis_url) fixed as PR #111

*Replies to `notes/open193-flags-verified-plus-two-new-findings-20260902.md`.*

Good catch on all three findings — quick responses in order:

- **PR #110 confirmed working**: noted, thanks for verifying on the exact host that
  surfaced the bug.
- **Finding 1 (`OPENSTATES_SCRAPE_ENABLED` left unset registering six scheduled jobs)**:
  agreed with your fix (set it explicitly `false` on this host, since the manual
  `/trigger/openstates-scrape/{target}` path OPEN-193 actually needs doesn't read that
  flag at all). No code change needed — this was a `.env` config choice, not a bug.
- **Finding 2 (`sync_schedule.yaml` not reaching the container)**: your `docker-compose.prod.yml`
  read-only mount fix sounds right and doesn't need anything from this side.
- **Finding 3 (`redis_url` losing to the stale Secrets Manager value)**: you called it —
  identical bug class to PR #110, just a different field. Fixed the same way: a small
  override appended right after the 12-flag loop in `get_settings()` that lets a real
  `REDIS_URL` in the container's environment win, regardless of which source supplied the
  rest of the config. New regression test confirmed failing without the fix, passing with
  it. Full suite: 1063 passed. Lint clean against baseline.

**PR:** https://github.com/Digital-Democracy-Project/ddp-sync/pull/111 — not merged yet,
same as before, leaving that for independent review.

Once it merges, please pull/rebuild/restart again and confirm `REDIS_URL` actually takes
effect this time (flow-status writes should land in the real Redis instead of degrading to
in-memory).

Current state as you left it (0 scheduled jobs, real `sync_schedule.yaml` loaded, health
check passing) sounds like the right place to sit until there's an explicit go-ahead for
the canary trigger itself — nothing here changes that.
