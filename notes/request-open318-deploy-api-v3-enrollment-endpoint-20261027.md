# Request: deploy the api-v3 enrollment endpoint on the EC2 host, and pull ddp-open-states there (OPEN-318 / OPEN-329 / OPEN-330)

2026-10-27 (late). Ramon's go to do this on the Mac is given and done; **this asks you to do the same on the production host.** It is a write: it recreates the api-v3 container (about a minute without api-v3). **Stop and report if anything below does not look as described. Do not retry a failed step, and do not touch the Postgres container.** Do not print any key, token or URL with credentials; read variables by exact name only.

## Why
OPEN-318 is a blocker for pilot #2. Its code is merged, but it is not live. The EC2 host's `/opt/ddp-open-states` was 80 commits behind on 2026-10-22 and nothing pulls it, so the manifest has no `scheduled` field there (ddp-sync logs `jurisdiction_manifest_unusable error="missing field 'scheduled'"` on this host). api-v3 also needs the `GET /ddp/enrollment` endpoint (api-v3 #33) and a read-only mount of `jurisdictions.yaml`.

## What I found on the Mac (so you know what to expect)
* The running container was started 2026-10-21, **before** the mount existed, and its image was built 2026-10-21 00:50, **before** the endpoint was merged. The endpoint answered 404. A plain `docker restart` would not have fixed it: the mount is added by the compose file, so the container had to be **recreated**, and the image **rebuilt** from the current api-v3 checkout.
* On the Mac I ran `refresh-api-v3.sh` (pull main, rebuild the `api` image, recreate `api` only with `--no-deps`, confirm Postgres's start time is unchanged). Result: container healthy, mount present, the file's modified time is **identical inside the container and on the host**, and the manifest inside the container has the 10 `scheduled:` lines.

## Please do, in this order
1. **Before changing anything, report:** the commit of `/opt/ddp-open-states` and of the api-v3 source the production api image is built from; how the production api-v3 container is built and started (which compose file; the Mac uses `deploy/docker-compose.ddp.yml`, the RDS-backed one is `deploy/docker-compose.rds.yml`); the api container's start time, and whether it has a `jurisdictions.yaml` mount (`docker inspect ... .Mounts`).
2. **Pull `/opt/ddp-open-states` to current `main`** (fast-forward only; if it has local changes or will not fast-forward, stop and report). Report the new commit.
3. **Rebuild and recreate only the api service** from the current api-v3 source with the compose file that production uses, scoped to the `api` service with `--no-deps`. Record the Postgres container's start time before and after and confirm it did not change. If production's api image is not built on this host, tell me how it is deployed instead of improvising.
4. **Verify without needing an API key:** the container is healthy; `docker exec <api> python -c "import os;print(os.stat('/app/jurisdictions.yaml').st_mtime)"` equals the host file's mtime; the mounted file has 10 `scheduled:` lines. (`GET /ddp/enrollment` needs an API key; if you call it with the key from its variable, report only the HTTP status and the `manifest_mtime` field, never the key.)
5. **ddp-sync on this host:** report whether its `jurisdiction_manifest_unusable ... 'scheduled'` warning is gone after its next restart or start-up (do not restart it for this; read the log). Report whether the daily drift job (OPEN-330) is enabled in this host's config and whether it has ever run. **Do not enable it yet.**
6. **Broker on this host:** report the value of `DDP_ENROLLMENT_SOURCE` (name and value only) and whether the broker's hourly comparison against `/ddp/enrollment` logged anything after step 3.

## Report
The commands you ran and their output (secrets removed), what changed, and anything that did not match. Nothing else changes.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
