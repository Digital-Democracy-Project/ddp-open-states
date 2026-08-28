#!/usr/bin/env bash
# Usage: ./test-mi-browser-fetch-poc.sh [--count N] [--session SESSION] [--delay SECONDS]
#
# Thin wrapper: sources this checkout's ISOLATED dev environment
# (activate-dev.sh, never production's activate.sh) then runs
# test-mi-browser-fetch-poc.py with whatever args are passed through.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/activate-dev.sh"
python3 "$SCRIPT_DIR/test-mi-browser-fetch-poc.py" "$@"
