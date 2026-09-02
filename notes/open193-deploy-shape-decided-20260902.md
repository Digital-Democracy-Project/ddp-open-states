# OPEN-193 — deploy host + shape decided; Redis DB separation to check before wiring it in

*Replies to `notes/open193-canary-blocked-deploy-question-20260902.md`.*

Ramon answered both open questions from that note directly.

## 1. Host: this is correct, and it's a first

This is genuinely the first time `ddp-sync` colocates with `ddp-broker`/`api-v3` on prod —
confirmed deliberately, not a leftover assumption from an earlier round. The
`DDP_SYNC_WIREGUARD_CIDR`-gated nginx port you found is real signal, but it describes a
different (likely earlier or still-future) topology, not a reason to redirect this deploy
elsewhere. Proceed with this host.

## 2. Deploy shape: Docker, following `ddp-broker-py`'s pattern specifically

Not `api-v3`'s bare `restart: unless-stopped`-only pattern, and not an adapted version of the
existing bare venv+systemd unit (wrong user/paths/Redis wiring anyway, so "adapt" would mean
rewriting most of it from scratch regardless). `ddp-broker-py`'s shape -- Docker Compose wrapped
in a systemd oneshot that runs `docker compose up -d`/`stop` -- is the template: gives Docker's
packaging/isolation benefits plus systemd's start/stop/monitoring hooks, and there's already a
project precedent for packaging a Python service into a container (the OPEN-200 Fargate
scraper image) to build from.

## Before wiring `ddp-sync`'s Redis config in: check for a DB-number collision

Raised independently, not part of your original blocker: `ddp-sync` and `ddp-broker`'s Celery/
Celery-beat sharing one Redis instance is fine in principle, but two real risks are worth
closing off first:

- **Key collisions.** `ddp-sync`'s own keys are already namespaced (`ddp:flow_history:*`,
  `ddp:scrape_cadence:*`, `votebot:active_jurisdictions`) -- please confirm these don't collide
  with whatever Celery/Celery-beat's actual configured key patterns are on this box (not
  assumed from here).
- **Blast radius / eviction interaction.** Whatever Redis DB number Celery's broker/backend
  uses by default (commonly `0`), put `ddp-sync` on a **different logical DB** rather than
  sharing one -- a config difference (`REDIS_URL=...db=1` or equivalent), not new
  infrastructure. This doesn't fully close off a `FLUSHALL` (instance-wide, not per-DB), but it
  does eliminate key-collision risk and `FLUSHDB`/eviction-policy cross-contamination between
  the two services' keyspaces.

Please check Celery's actual configured DB number on this box and pick `ddp-sync`'s
accordingly, alongside building the Docker/systemd packaging above.

## Still open, not part of this note

The exposed RDS master password from the `docker inspect` finding -- rotation decision is still
with Ramon, not decided here. Raising it again only so it doesn't get lost while this note
focuses on the deploy-shape/Redis questions.
