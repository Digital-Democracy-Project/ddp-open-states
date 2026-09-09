#!/usr/bin/env bash
# OPEN-200: thin entrypoint so `docker run ddp-scraper:prototype <source> [key=value ...]`
# matches the fargate draft's target invocation shape exactly. All real logic is
# cloud_collector.py (OPEN-201); this file exists only so `exec` replaces PID 1 with the
# Python process rather than leaving a shell in between -- otherwise SIGTERM on `docker stop`
# would hit bash, not the runner, which is exactly the "gracefully handle SIGTERM" requirement
# the draft names and a shell-wrapped ENTRYPOINT quietly fails.
#
# OPEN-192 (reopened): this image now also carries cloud_archiver.py, so a second ECS
# containerOverrides.environment entry -- RUNNER_SCRIPT -- picks which one actually runs.
# Deliberately an env var, not a positional/subcommand argument: cloud_collector.py's own
# first argument is a jurisdiction abbreviation ("fl", "wa", ...), so any scheme that consumed
# argv[0] as a mode selector would collide with a real jurisdiction code sooner or later.
# ECS RunTask overrides support `command` and `environment`, not `entryPoint` (confirmed
# directly against the API, not assumed) -- so this is the only override-compatible way to
# choose which script this same task definition/image actually runs.
set -euo pipefail
exec python3 "/app/${RUNNER_SCRIPT:-cloud_collector.py}" "$@"
