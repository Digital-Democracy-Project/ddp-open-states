# mi_cookie_publish looks stalled since the SYNC-53 fix landed — needs EC2-side digging

*Follows up on `notes/open193-mi-cookie-correction-sync53-20260902.md`.*

Weekend check-in on the Fargate scrapers + EC2 ddp-sync schedule (all from CloudWatch Logs and
the `ddp-openstates-scraper-memory` S3 bucket — no EC2/SSH access from this session, so I could
only see what showed up in those two places). Short version: the scrape/import pipeline itself
looks healthy all weekend — every jurisdiction on the actual schedule (`us`, `fl`, `wa` nightly;
`va`/`mi`/`ut`/`az`/`ma` in Saturday night's weekly batch) ran and reported `status: ok`, and
each left an `_import_lock` marker confirming the load step ran too. One thing doesn't look
right, though: **`mi_cookie_publish` appears to have stopped actually publishing right after its
own SYNC-53 fix merged.**

## What I found

- `prod/mi/_cache/mi_waf_cookies.json` in `ddp-openstates-scraper-memory` was last modified
  **2026-09-03T02:08:22Z**.
- SYNC-53 (PR #119, the fix that made this job write to the *correct* bucket) merged at
  **2026-09-03T02:02:42Z** — six minutes earlier. That timing lines up with this being the
  first correct-bucket write right after deploy, not a coincidence.
- `mi_cookie_publish.py`'s job (`config/sync_schedule.yaml`: `enabled: true`,
  `interval_hours: 6`) unconditionally re-mints and overwrites that object on every successful
  tick — there's no "skip if still fresh" branch. So if it had run successfully since, the
  `LastModified` timestamp would have moved. It hasn't, across roughly 5 days / ~20 expected
  ticks.
- This isn't blocking anything visibly yet — Michigan's incremental scrape still succeeded
  both nights this weekend (correctly no-op'd via the OPEN-134 last-action diff, 4017 bills
  checked, 0 changed), so whatever cookie is cached is apparently still good. But a stale,
  silently-not-refreshing cookie is exactly the failure mode SYNC-53's own module docstring
  describes happening once already (~4 days stale before anyone noticed) — Michigan is also
  the one jurisdiction where a bad cookie turning into a real block would be expensive to walk
  back from.
- The job's own contract is "never raise, never crash the scheduler" on a bad tick (mint
  failure, publish failure, and any other exception are all swallowed and just logged) — by
  design, so this wouldn't show up as an alert or a failed run anywhere. That's likely exactly
  why nothing caught it yet.

## Specific things to check on the EC2 box

1. **Is the deployed ddp-sync build actually SYNC-53 or later?** Confirm the running process's
   code (git SHA, or however the EC2 deploy is versioned) includes `899bd07` (SYNC-53) and
   isn't running something older that predates the bucket fix.
2. **Has ddp-sync restarted or redeployed on EC2 since 2026-09-03T02:02:42Z?** `mi_cookie_publish`
   is registered as an `IntervalTrigger(hours=6)` job at process startup
   (`scheduler.py:_register_mi_cookie_publish_job`) — if the process has restarted more often
   than every 6 hours since then (e.g. from other deploys), it's worth confirming the interval
   timer isn't effectively getting reset before it ever fires, rather than assuming it just
   free-runs in the background.
3. **What do the actual scheduler/app logs say for `mi_cookie_publish` since 2026-09-03?** Look
   for the `mi_cookie_publish: registered` line at startup, and on each tick one of:
   `mi_cookie_publish: published fresh Michigan WAF cookies` (success),
   `mint_failed` / `publish_failed` / `unexpected_error` (the three swallowed-failure log lines
   in `mi_cookie_publish.py`). Any of those tells us which half is actually broken, if it's
   broken at all rather than just not running.
4. **Is `MI_COOKIE_PUBLISH_ENABLED` actually `true` in EC2's real, persisted `.env`?** Same
   category of gap OPEN-253 found for `OPENSTATES_SCRAPE_ENABLED` — a flag that looks right in
   the checked-in YAML can still be overridden false in the per-host env.
5. **Is ScrapeBot's mint path itself reachable/healthy from EC2 right now?** `mi_cookie_publish`
   calls `scrapebot_client.dispatch_mint_cookies("mi")` — if ScrapeBot itself is down or
   unreachable from EC2 specifically (as opposed to from the Mac, where the 2026-09-02 manual
   mint in the note above worked fine), every tick would silently no-op via the `mint_failed`
   path.

If it turns out to be something small and config-shaped (flag not persisted, or a restart
resetting the timer) — same as OPEN-253 — feel free to just fix it directly rather than routing
back through here first. If it's a real code bug in the mint or publish path, flag it back here
with whatever the logs show and I'll help get it filed and fixed from the dev side.
