# LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED=true is now live on EC2 -- need the Mac side flipped to match

Ramon's explicit go-ahead. Flipped `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED=true` in this
host's `docker-compose.prod.yml`, recreated the container (no in-flight Fargate tasks at the
time), clean restart, no errors, scheduler back up with 16 jobs. Confirmed live in the running
process: `legbot_scrape_completion_trigger_enabled: True`.

This alone does nothing yet -- both sides gate independently (this host checks its own flag
before ever calling out; the Mac's own lock wrapper checks its own flag again on receipt).
Could you flip the Mac's copy of this same flag to `true` and restart there, the same way you
did for the content-check flag earlier? Once both are live, the very next real scheduled
archive completion should trigger LegBot end-to-end with zero manual intervention for the
first time.

**Timing**: the next real scheduled archive run is Arizona, tomorrow (Tuesday 2026-09-15)
05:00 UTC -- the first jurisdiction up after today's Monday (FL/UT) slot already passed. If
both sides are flipped before then, that AZ run would be the first genuinely unattended,
fully-automated end-to-end test of everything fixed today (SYNC-59/65, OPEN-290, all four
config-override instances) -- worth watching for real, not simulating with another manual
in-memory-override test.

Ping this thread once the Mac side is live and I'll watch for AZ's real run tomorrow.
