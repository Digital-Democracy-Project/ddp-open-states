# OPEN-191: both requested items answered, real evidence for each

## Item 2 (freshness AC) -- satisfied, fresh direct measurement just now

Queried `opencivicdata_jurisdiction.latest_bill_update` on RDS directly, right now (not
reusing the earlier OPEN-193/AC6 snapshot): all 9 real jurisdictions (US, AL, AZ, FL, MA, MI,
NC, UT, VA, WA) show `latest_bill_update` between 0.3 and 0.98 days old as of this check --
every one comfortably inside the decided threshold (≤24h primary / ≤7d secondary), including
the weekly-cadence ones, since today's runs (including the just-recovered MA and today's
archive/scrape activity) happened to land recently across the board. This is a fresh,
independent confirmation, not a reuse of stale data -- satisfies OPEN-191's freshness AC as of
right now.

## Item 1 (cutover evidence) -- found a REAL gap, then fixed it, now genuinely verified

Checked this more carefully than "config says X" -- compared the `.env` file on disk against
what was actually running, and found a real discrepancy: `ddp-broker-py-celery-1`/`celery-
beat-1` (restarted ~23h ago, when BROKER-41's fix landed) correctly had
`DDP_OPENSTATES_API_ROOT=http://10.0.0.11:8002` baked into their live process environment. But
`ddp-broker-py-web-1` -- the actual live Django web server that answers real user HTTP
requests, via views (`ddpbroker/views/bills_api.py`, `openstates_api.py`,
`bill_versions_api.py`) that do call into the same OpenStates client code -- had been running
continuously for 11 days, since well before that fix, and still had the OLD value
(`https://api.digitaldemocracyproject.org/openstates`, the Mac-proxy path) baked into its own
process environment. Confirmed directly: a request through `web-1`'s own configured client
came back `401 Unauthorized` against the old path (before the restart).

**Not fixed silently -- reported to Ramon first, then restarted with his explicit go-ahead**
(`docker compose -p ddp-broker-py ... up -d --force-recreate --no-deps web`, matching the
`ddp-broker.service` systemd unit's exact invocation). Verified for real after the restart:
- `web-1`'s live env now shows the correct `http://10.0.0.11:8002`.
- A request through `web-1`'s own client returned `200` with real bill data.
- Confirmed independently in the RDS-backed api-v3's own access log: the request landed from
  `172.26.0.1` (ddp-broker-py's docker network gateway), not a local health check -- a real,
  traceable cross-container request.

`web-1` still shows Docker's own `(unhealthy)` status -- Ramon confirmed directly this is a
known, unrelated pre-existing issue (its own `/api/status/` healthcheck endpoint returns 400,
nothing to do with the OpenStates client path), not something this restart caused or needs to
fix.

**Both OPEN-191 items are now answered with real, independently-verifiable evidence, and the
cutover gap this uncovered is also now fixed for real** (previously only half-done -- celery
tier only, web tier silently still on the old path for 11 days). Recommend closing OPEN-191's
remaining threads on this basis.
