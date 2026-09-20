# US/119 LegBot run: checked in from the EC2 host, couldn't get a fresher number

Re: `us119-run-confirmed-healthy-20260919.md` (1,698/18,494 as of 2026-09-19 13:55 EDT). Checking
in from `/opt/ddp-open-states` on the EC2 box (`ip-172-31-78-173`) at 2026-09-20 ~19:35 UTC.

**No newer note on this branch** — `origin/notes/ops-handoff` tip is still `6663d31` (the
1,698/18,494 confirmation) as of this check.

**Couldn't refresh the progress number from here:**

- The actual run (`run_id=f563665f-a010-42d9-afc2-2db1df7210be`) is on the **Mac Studio's**
  `ddp-sync`, not this host's. Mac Studio is network-reachable from here (`10.0.0.8:8001/health`
  returns 200), but its `ddp-sync` API only exposes trigger endpoints
  (`/ddp-sync/v1/trigger/legbot-analyze-bill*` etc.) — no run-status-by-id endpoint, and this
  session has no filesystem/log access to that host.
- Tried a live RDS read instead (bill-artifact completion count for US/119, as a jurisdiction-
  agnostic alternative signal) — this session's own auto-mode classifier blocked it under a
  "Production Reads" rule before it ran. Flagging that as a known limitation for whoever
  continues this from an EC2 session: read-only DB checks that worked in earlier sessions here
  may need that permission granted explicitly now.

**So: still assume 1,698/18,494 (9.2%) as of last night, healthy, no fatal errors, ~5-8 day ETA**
until someone with Mac Studio access or DB read permission gets a fresher count.

**Separate, smaller finding — not the manual backlog run:** this EC2 host's own `ddp-sync`
(`ddp-sync-ddp-sync-1` container) logged two `archiver_triggered_legbot_session_resolution_failed`
events for `jurisdiction=us` today, each after 3 retries of "Local api-v3 unreachable" against
its own `ddp-openstates-api-1` container (`http://10.0.0.11:8002`):

- 2026-09-20 03:44:07 UTC
- 2026-09-20 05:14:40 UTC

That container is healthy right now (`/healthz` returns 200 as of this check), so this reads as a
transient blip on the automated per-scrape LegBot trigger path, not a current outage — and it's
unrelated to the manual US/119 backfill run above. Haven't seen this specific failure logged
before; flagging in case it's new or recurring elsewhere. Not filing a ticket for it yet since it
isn't reproducing right now.
