# mi_cookie_publish root cause found: it's not stalled, it's still deliberately disabled from OPEN-193 setup

*Replies to `notes/mi-cookie-publish-stalled-since-sync53-20260908.md`.* Ran the 5 checks from
this EC2 host.

## What I found

1. **Deployed build includes SYNC-53.** `899bd07` is an ancestor of the running checkout's HEAD
   (`cb97977`); the container was rebuilt from it on `2026-09-03 19:45:09 UTC`.
2. **No restart since.** `ddp-sync-ddp-sync-1` has been up continuously 5 days since that
   rebuild — rules out "a restart keeps resetting the 6h interval timer."
3. **Logs show it was never attempted, not that it failed.** First line after that rebuild:
   `mi_cookie_publish: disabled — skipping`. None of the three swallowed-failure log lines
   (`mint_failed`/`publish_failed`/`unexpected_error`) appear anywhere after that point, because
   the job never runs at all.
4. **Root cause: `infrastructure/docker-compose.prod.yml` hardcodes
   `MI_COOKIE_PUBLISH_ENABLED=false`**, with its own comment: this was set during the original
   OPEN-193 canary setup (2026-09-02, alongside `OPENSTATES_ARCHIVE_ENABLED=false`) and
   explicitly deferred — *"the handoff note left these as your call... defaulted to false here
   too, since this host's mandate is specifically the OPEN-193 canary... Flagged back on
   notes/ops-handoff in case that call should go the other way."* That flag doesn't appear to
   have been revisited since, even after SYNC-53 fixed the underlying bucket bug that motivated
   checking this at all.

Check 5 (ScrapeBot reachability from EC2) is moot — the job never gets far enough to call it.

## So: not a bug, a decision that's still open

The cached cookie is still working (MI's incremental scrape keeps succeeding), so nothing is on
fire. But this is exactly the risk called out earlier — Michigan is the one jurisdiction where a
bad/stale cookie turning into a real WAF block would be expensive to walk back from, and the
cache has been static for 6 days on borrowed time from whatever minted it last.

## Next step

This is the "your call" flag from 2026-09-02, still unmade: flip
`MI_COOKIE_PUBLISH_ENABLED=true` in `docker-compose.prod.yml` now that SYNC-53 is confirmed
deployed and working, or leave it off deliberately for longer? Not flipping it myself — it's a
live-site risk decision, not a config-persistence gap. Report back here either way and I (or
whoever picks this up) can make the one-line change + redeploy.
