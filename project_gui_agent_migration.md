# Memory: migrate com.ddp.* GUI LaunchAgents → system LaunchDaemons

**Status:** partially done. `com.ddp.ddp-sync` migrated 2026-07-08. Created 2026-07-09.

## The issue
The Mac Studio is administered **SSH-only** — no reliable interactive Aqua/console
session, and `agentsmith` (uid 502) has **no sudo**. Per-user **GUI LaunchAgents**
(`~/Library/LaunchAgents/com.ddp.*.plist`, the `gui/502` domain):

- do **not** auto-start after a reboot when nobody logs into the physical console, and
- **cannot be reloaded over SSH** once the GUI domain wedges — `launchctl bootstrap
  gui/502 …` fails `125 Domain does not support specified action` **even as root**.

This took nightly OpenStates scrapes down **2026-07-04 → 07-08**: `com.ddp.ddp-sync`
(the local scrape scheduler) was booted out during a `:8001` port-conflict remediation
and could not be reloaded. Fixed by migrating it to a system LaunchDaemon.

## Fix pattern (proven 2026-07-08)
Convert to a **system LaunchDaemon**: `/Library/LaunchDaemons/`, `system/` domain,
`UserName=agentsmith`, `RunAtLoad`+`KeepAlive`. Templates + runbook:
- `ddp-sync/infrastructure/com.ddp.ddp-sync.plist`  ← **done** (this repo's scraper)
- `ddp-next/deployment/launchd/com.ddp.next.plist`, `com.ddp.next-watcher.plist`  ← done
- `ddp-infra/README.md` → "Restart Procedures" (SSH-only caveat + `:8001` recovery).

## This repo's still-GUI services (migrate these)
- **`com.ddp.openstates-api`** (:8002) — api-v3 launchd one-shot that runs
  `start-os-api.sh` → `docker-compose -f deploy/docker-compose.ddp.yml up -d`. The
  containers are `restart: unless-stopped`, but the launchd one-shot that brings them
  up won't fire after a reboot with no console login → api-v3 stays down. (Also depends
  on Colima auto-starting — see ddp-agents `project_gui_agent_migration.md`.)
- **`com.ddp.openstates-db-backup`** — nightly `pg_dump` (07:00 local) via
  `backup-openstates-db.sh`. Won't run after a reboot until re-loaded. Candidate to fold
  into the ddp-sync APScheduler instead of a launchd job (see RUNBOOK).

See also: `RUNBOOK.md` (scraper/scheduler section) and the ddp-sync topology notes.
