#!/usr/bin/env bash
# OPEN-200: thin entrypoint so `docker run ddp-scraper:prototype <source> [key=value ...]`
# matches the fargate draft's target invocation shape exactly. All real logic is
# cloud_collector.py (OPEN-201); this file exists only so `exec` replaces PID 1 with the
# Python process rather than leaving a shell in between -- otherwise SIGTERM on `docker stop`
# would hit bash, not the runner, which is exactly the "gracefully handle SIGTERM" requirement
# the draft names and a shell-wrapped ENTRYPOINT quietly fails.
set -euo pipefail
exec python3 /app/cloud_collector.py "$@"
