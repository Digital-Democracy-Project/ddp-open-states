# REQUEST (read only): inventory of the EC2 host's own Python 3.9 tool environment (OPEN-614, step 1). 2026-11-17 (Mac side)

**Why:** OPEN-515 moved the scrapers image, openstates-core and the Mac tools to Python 3.13. The tool environment installed directly on the EC2 host (used for one-off passes such as `recompute-diff-order`, `reverse-action-order`, `remove-stale-documents`) is the last 3.9 install. Ramon chose "Upgrade old EC2 tools" (2026-11-17). Before anyone writes the switch runbook, we need to know exactly what uses it. **Read only: change nothing.**

## Please report
1. **Where it is:** the path(s) of every Python virtual environment on the host outside containers (e.g. `/opt/venv-openstates`, `~/venv*`, `/opt/ddp-open-states/.venv*`). For each: `bin/python --version`, and whether it's a symlink to a system Python (which one, and its package).
2. **What's in it:** for each, `bin/pip list --format=freeze | grep -i -E 'openstates|psycopg|django|pydantic|boto'`, plus the installed openstates-core commit if recorded (`DDP_CORE_COMMIT` or `pip show openstates` location).
3. **Who calls it:**
   * `crontab -l` for bitnami and root, systemd units/timers (`systemctl list-timers --all`, `grep -rl <venv path> /etc/systemd /etc/cron* 2>/dev/null`);
   * scripts under `/opt/ddp-open-states` and `/home/bitnami` that reference the venv path (`grep -rl` the path; names only);
   * ddp-sync or other containers that bind-mount it (`docker inspect` mounts, names only).
4. **System Pythons available:** `ls /usr/bin/python3* /usr/local/bin/python3* 2>/dev/null` and whether a 3.13 exists, and how it was installed if so.
5. **Disk:** free space on the volume holding the venv (`df -h <path>`).

## Not authorized
Installing, removing or changing anything: no new venv, no pip install, no package manager. Any scrape, image, manifest, ddp-sync, broker or data change.

The Mac side writes the side-by-side 3.13 runbook (new environment, switch, rollback, old one kept until one real pass has run) from this reply, for Ramon's go.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
