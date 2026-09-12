# ddp-broker repointed off the Mac-proxy path to this EC2 host's api-v3 — done, verified

Resolves the concern in `acdd632`/re-retracted in `b5db39e`: production `ddp-broker`
(`DDP_OPENSTATES_API_ROOT=https://api.digitaldemocracyproject.org/openstates`) really was
depending indirectly on the Mac's api-v3 through that proxy domain. It would have broken once
OPEN-272's repoint deployed there.

**Fix, with Ramon's explicit go-ahead:** switched `ddp-broker` to BROKER-41's "direct" auth mode
against this EC2 host's own RDS-backed api-v3 instead:
- `DDP_OPENSTATES_API_ROOT=http://10.0.0.11:8002` (was the public proxy URL)
- `DDP_OPENSTATES_API_KEY=<same value as DDP_OPENSTATES_BEARER_TOKEN>` (setting this is what
  flips the client from Bearer/proxy mode to `x-api-key`/direct mode)

Prerequisite work already done before this switch: rotated this host's api-v3 RDS credential
(`deploy/rotate-database-url.sh`, stale after the 7-day auto-rotation), and inserted a
`profiles_profile` row for the broker's token so api-v3's own auth would accept it.

**One real mistake made and caught during this**: my first recreate omitted `-p ddp-broker-py`
on the `docker compose` invocation, so it fell back to the cwd's basename ("compose") as the
project name and created a whole separate, disconnected stack (`compose-celery-1`,
`compose-celery-beat-1`) instead of touching the real prod containers — found the real
project name in `/etc/systemd/system/ddp-broker.service`'s `ExecStart`, which explicitly passes
`-p ddp-broker-py`. Real prod containers were untouched by the mistake (confirmed via
`docker inspect`/uptime before touching anything further). Cleaned up the orphan containers +
network, then redid the recreate scoped to just `celery`+`celery-beat` (not `web`/`nginx`/`db`)
under the correct project name.

**Verified working**: post-recreate, a real `GET /people?jurisdiction=mi&per_page=1` from
inside the real `ddp-broker-py-celery-1` container returned `200` with real person data via the
new direct path. Both `celery` and `celery-beat` logs are clean (Redis connected, worker ready,
beat scheduler started, no errors).

**Net effect on OPEN-272**: the Mac's api-v3 repoint should now be unblocked from this
direction — `ddp-broker` no longer depends on it at all, direct or indirect.
