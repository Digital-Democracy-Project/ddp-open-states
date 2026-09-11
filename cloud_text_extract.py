#!/usr/bin/env python3
"""
Cloud text-extract runner -- OPEN-268.

The thinnest possible runner: exec `os-text-extract` with this process's own argv passed
straight through. Lets `RUNNER_SCRIPT=cloud_text_extract.py` (docker-entrypoint.sh) select this
over cloud_collector.py/cloud_archiver.py, so ad-hoc `os-text-extract` subcommands
(`reextract`/`refresh-extraction`/`recompute-diff-order`) can run inside the same already-built,
already-deployed image and task definition as the scrape/archive paths, instead of a bare venv
on whatever host happens to invoke them.

Usage (as this file's own argv, i.e. the ECS `command` override that follows RUNNER_SCRIPT):
    python3 cloud_text_extract.py recompute-diff-order fl --dry-run
    python3 cloud_text_extract.py refresh-extraction ut --session 2025S2 --commit

DATABASE_URL is read by `os-text-extract` itself (Django) -- same convention as
cloud_archiver.py, whatever the container's own environment already points at (RDS, in
production) is what gets operated on. This file never touches the database directly, and never
touches S3 or the memory store either -- it is pure argv passthrough, nothing else.

Credentials come from boto3's default chain -- an env-var access key here, an ECS task role in
the cloud, matching cloud_collector.py/cloud_archiver.py's own "role-based" framing exactly.
"""

import os
import sys


def main() -> None:
    os.execvp("os-text-extract", ["os-text-extract", *sys.argv[1:]])


if __name__ == "__main__":
    main()
