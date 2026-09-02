# OPEN-193 — third task added: give api-v3 the same systemd wrapper while it's cheap to change

*Replies to `notes/open193-deploy-shape-decided-20260902.md`.*

One more, alongside the `ddp-sync` Docker packaging and the Redis DB-separation check:
**wrap `api-v3` in the same systemd-oneshot pattern `ddp-broker-py` already uses**, instead of
leaving it on bare `restart: unless-stopped` with no systemd entry point.

Why now specifically: this copy of api-v3 only serves OPEN-191's own rehearsal/validation
traffic today, not real end-user requests through `ddp-broker` -- Ramon's reasoning is that
this is the cheapest point this ever gets to change it, before it's load-bearing. It's also low
effort as changes go: the compose file (`deploy/docker-compose.rds.yml`) already works, so this
is adding the thin wrapper unit around it, not new packaging from scratch the way `ddp-sync`
needs.

One thing to check before wrapping it: whether anything currently monitors or restarts api-v3
by talking to Docker directly rather than through systemd -- if so, that path needs to keep
working (or get updated at the same time), not silently orphaned by the change.

End state once all three land: `ddp-broker-py`, `api-v3`, and `ddp-sync` all managed the same
way on this host (`systemctl start/stop/status <service>`), no outlier.
