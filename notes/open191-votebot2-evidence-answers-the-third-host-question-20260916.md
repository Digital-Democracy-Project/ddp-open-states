# OPEN-191: VOTEBOT-2's own real verification (closed yesterday) already answers your third-host question

Re: your `open180-4-ticket-status-check-20260916.md`, the OPEN-191 section -- you flagged not
being able to confirm what the third EC2 host (`i-09381338adcbb35e2`, behind
`api.digitaldemocracyproject.org`) actually has its own api-v3/proxy config pointed at, and
mentioned a VoteBot/`ddp-api` repoint thread that stalled on a security-group gap (port 8002, no
inbound rules).

Checked `VOTEBOT-2` directly (closed 2026-09-15 22:07, yesterday) -- it already has the answer,
with real end-to-end evidence, not just a status claim:

* `ddp-api` PR #15 merged/deployed: fixed `OPENSTATES_SERVICE_URL`/`OPENSTATES_PROXY_KEY`, which
  had been stale (pointed at the old Mac Studio Postgres, `10.0.0.8:8002`) with no env override
  for the internal key at all. Now correctly points at the real production api-v3
  (`10.0.0.11:8002`).
* `votebot` PR #6 merged/deployed: all 3 of VoteBot's OpenStates call sites now route through
  `ddp-api`'s `/openstates/*` proxy with a Bearer token, instead of hitting the public
  `v3.openstates.org` directly.
* **The functional verification (`ddp-api`'s own `notes/ops-handoff`,
  `votebot-pr6-deployed-and-verified-20260916.md`) used a real chat request through
  `api.digitaldemocracyproject.org/openstates/...`** -- the exact public domain/host you couldn't
  inspect tonight -- asking about a real Virginia bill's vote record. Response came back with
  accurate Senate/House vote tallies, and server logs confirmed the lookup hit the DDP replica
  endpoint specifically, not raw openstates.org. Re-tested against a second bill after the first
  came back "not found," confirmed via logs that was a real replica miss, not a routing failure.

So: a real request through that exact host, yesterday, reached the real production api-v3
replica correctly. That resolves the specific uncertainty blocking OPEN-191 -- the third host's
proxy config is confirmed correct and AWS-native, at least for this path.

**On the security-group thread**: given VOTEBOT-2's shipped design routes through `ddp-api`'s own
internal proxy (Bearer-token mode) rather than a direct connection to port 8002, and it verified
working without that inbound rule ever being opened, that stalled thread looks like it was a
separate, earlier *direct*-connection approach (the ticket's own text names this as "Direct...
not applicable to VoteBot unless it gets WireGuard") that got superseded by the proxy approach
actually shipped -- not a live blocker on the path that's actually in use.

Not closing OPEN-191 myself -- flagging so you can re-check it against this evidence rather than
treating the third host as still-unconfirmed.