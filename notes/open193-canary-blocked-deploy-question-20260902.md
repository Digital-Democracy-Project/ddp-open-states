# OPEN-193 — item 4 (canary) blocked before it starts; two things need a decision

*Replies to `notes/open193-subnets-confirmed-public-20260902.md`.*

Asked to run the FL canary. Two real problems surfaced before actually triggering anything —
neither is something to push through on judgment alone.

## 1. ddp-sync has never actually been deployed on this host

Checked directly: no venv, no `.env`, no systemd unit installed. `infrastructure/ddp-sync.service`
as it ships doesn't match this box either — `User=ubuntu`, `WorkingDirectory=/home/ubuntu/ddp-sync`
(this host is `bitnami`/`/opt`), and `Wants=redis-server.service` (a systemd-managed Redis that
doesn't exist here — Redis runs as Docker containers instead, one per stack).

Looked at how the other two services on this box are actually deployed, hoping one would be a
clean template:

- **`ddp-broker-py`** — Docker Compose (`infra/compose/prod.yml`) wrapped in a `systemd` oneshot
  unit that just runs `docker compose up -d`/`stop`.
- **`api-v3`** — Docker Compose, but **no systemd wrapper at all** — kept alive purely by
  `restart: unless-stopped` on the container itself. Its own `refresh-api-v3.sh` is hardcoded to
  Mac Studio paths (`/Users/agentsmith/Developer/repos/...`), so it clearly wasn't used to deploy
  the copy running here; this host's stack came from `deploy/docker-compose.rds.yml` (the INFRA-1
  "self-contained api-v3 compose stack for RDS/EC2" commit) some other way.
- **`ddp-sync`** — no Dockerfile/compose anywhere in its own repo, only the systemd+venv unit
  above.

Three services, three different deployment shapes, none a drop-in fit for `ddp-sync`. Adapting
the existing systemd unit (fix user/paths, point its Redis config at the Docker Redis container
instead of a systemd one) is doable, but that's a real decision about how this service should be
run long-term, not just a path substitution — didn't want to make that call unilaterally.

**Separately, and more importantly:** `ddp-broker-py`'s own nginx config has a
`NGINX_BROKER_PORT` (default 8080) with the comment *"restricted broker API path for
`ddp-api`/`ddp-sync`"*, gated by a `DDP_SYNC_WIREGUARD_CIDR` env var. That reads like `ddp-sync`
is meant to run on a **separate** host and reach this one over WireGuard — which conflicts with
the earlier note in this thread confirming "same EC2 host runs `ddp-broker`/`api-v3`/`ddp-sync`."
I only ever independently corroborated the `ddp-broker`/`api-v3` half of that claim (both
verifiably running here); I hadn't checked the `ddp-sync` half against this nginx signal before
now. Worth resolving which is actually true before installing anything — if `ddp-sync` belongs on
a different host, deploying it here would be the wrong fix entirely.

## 2. Incidental credential exposure, flagging for a rotation decision

While comparing deployment patterns, `docker inspect ddp-openstates-api-1` was run to check its
restart policy, and its output included the container's full environment — which contains the
**live RDS master password in plaintext** inside `DATABASE_URL`. That value is now sitting in
this session's tool output/logs (not repeated in any note, here or elsewhere, and not going
anywhere beyond this session). Flagging rather than deciding unilaterally: is that exposure
enough to warrant rotating the RDS master credential, or is session-local exposure acceptable
here? Whoever owns that call, please make it — I'm not rotating it myself without a decision.

## What's needed to move forward

1. Confirm whether `ddp-sync` is actually meant to run on this host or a separate one (settles
   the WireGuard/nginx question above).
2. If this host is correct: a decision on the deployment shape (adapted bare systemd+venv per the
   existing unit file, vs. writing new Docker packaging to match the other two services) —
   whichever it is, happy to build it once that's decided.
3. A call on the exposed RDS password above.

Nothing else about item 4 has actually been touched — no config flipped, nothing triggered.
