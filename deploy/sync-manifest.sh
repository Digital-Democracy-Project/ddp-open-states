#!/usr/bin/env bash
# Refresh the copy of jurisdictions.yaml that api-v3 reads, after a `git pull` (OPEN-483).
#
# Why a copy in its own directory: api-v3 serves the shared state list at GET /ddp/enrollment and re-reads it when the
# file's modification time changes. A single-file bind mount cannot see a `git pull`, because git replaces the file
# (new inode) and the container keeps the old one for good (proven on native Linux Docker, 2026-11-03, OPEN-483), so
# every pull used to need an api container recreate. A DIRECTORY mount sees replaced files at once. Mounting the whole
# checkout is not an option (it holds .env files), so the compose files mount ONLY deploy/manifest/, which holds nothing
# but this copy. This script keeps the copy current.
#
#   bash deploy/sync-manifest.sh          # copy, print what it did
#   bash deploy/sync-manifest.sh --check  # change nothing; exit 1 if the copy is missing or differs from the checkout
#
# (MANIFEST_SOURCE and MANIFEST_DEST_DIR exist for the tests only; a host uses the defaults.)
#
# The copy is written atomically (temp file, then rename), keeps the source's modification time (so
# /ddp/enrollment's manifest_mtime equals the checkout file's), and an unreadable or empty source leaves the existing
# copy untouched. It touches nothing else: no container, no .env, no git.
#
# A list the repo's own validator (validate_jurisdictions.py) rejects is NEVER copied, so the boot script and
# refresh-api-v3.sh, which call this without rollout-manifest.sh, cannot serve an unvalidated list after a pull whose
# validation failed (OPEN-488): the existing copy is left untouched and the script exits 1. --check does not validate.
# (MANIFEST_PYTHON picks the interpreter, like ROLLOUT_PYTHON; the default is the repo's .venv, else python3.)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${MANIFEST_SOURCE:-$HERE/../jurisdictions.yaml}"
DEST_DIR="${MANIFEST_DEST_DIR:-$HERE/manifest}"
DEST="$DEST_DIR/jurisdictions.yaml"
VALIDATOR="$HERE/../validate_jurisdictions.py"
PY="${MANIFEST_PYTHON:-}"
if [ -z "$PY" ]; then
    if [ -x "$HERE/../.venv/bin/python3" ]; then PY="$HERE/../.venv/bin/python3"; else PY="python3"; fi
fi

hash_of() { if command -v md5sum >/dev/null 2>&1; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi; }

[ -s "$SRC" ] || { echo "STOP: $SRC is missing or empty; the existing copy (if any) was not touched" >&2; exit 1; }

if [ "${1:-}" = "--check" ]; then
    [ -s "$DEST" ] || { echo "DIFFERS: no copy at $DEST"; exit 1; }
    if [ "$(hash_of "$SRC")" = "$(hash_of "$DEST")" ]; then
        echo "OK: $DEST matches $SRC (md5 $(hash_of "$DEST"))"; exit 0
    fi
    echo "DIFFERS: $DEST (md5 $(hash_of "$DEST")) is not $SRC (md5 $(hash_of "$SRC"))"; exit 1
fi

[ -f "$VALIDATOR" ] || { echo "STOP: $VALIDATOR is missing, so the list cannot be checked; the existing copy (if any) was not touched" >&2; exit 1; }
# Validate a SNAPSHOT and publish that same snapshot, so the bytes that pass the validator are the bytes that are installed
# even if the checkout file changes (a pull) in between.
SNAP="$(mktemp "${TMPDIR:-/tmp}/sync-manifest-snapshot.XXXXXX")"
trap 'rm -f "$SNAP"' EXIT
cp -p "$SRC" "$SNAP"
rc=0
VALIDATION="$("$PY" "$VALIDATOR" "$SNAP" 2>&1)" || rc=$?
if [ "$rc" -ne 0 ]; then
    VALIDATION="$(printf '%s\n' "$VALIDATION" | sed "s|$SNAP|$SRC|g; s/^/    /")"
    if [ "$rc" -eq 1 ]; then
        echo "STOP: $SRC does not validate, so it was NOT copied; the existing copy (if any) keeps serving. Fix the list on main and pull again:" >&2
    else
        echo "STOP: the validator could not run (exit $rc; interpreter '$PY', usually PyYAML missing), so the list was NOT checked or copied; the existing copy (if any) keeps serving. This is the host's Python, not the list:" >&2
    fi
    printf '%s\n' "$VALIDATION" >&2
    exit 1
fi

[ ! -L "$DEST_DIR" ] || { echo "STOP: $DEST_DIR is a symlink; refusing to write through it" >&2; exit 1; }
[ ! -d "$DEST" ] && [ ! -L "$DEST" ] || { echo "STOP: $DEST is a directory or a symlink (docker creates a directory when a bind mount's source is missing); remove it and rerun" >&2; exit 1; }
mkdir -p "$DEST_DIR"
TMP="$(mktemp "$DEST_DIR/.jurisdictions.yaml.XXXXXX")" || {
    echo "STOP: cannot write in $DEST_DIR (if an earlier 'docker compose up' created it as root, remove the empty directory and rerun)" >&2
    exit 1
}
trap 'rm -f "$TMP" "$SNAP"' EXIT
cp -p "$SNAP" "$TMP"
chmod 644 "$TMP"
# api-v3 reloads only when the file's modification time CHANGES. cp -p keeps the source's time (so /ddp/enrollment's
# manifest_mtime equals the checkout's), which is a new time on every real pull; if a changed file ever carries the very
# same time as the copy it replaces, give it the current time so the change cannot go unseen.
if [ -e "$DEST" ] && ! cmp -s "$SNAP" "$DEST" && ! [ "$TMP" -nt "$DEST" ] && ! [ "$DEST" -nt "$TMP" ]; then
    touch "$TMP"
fi
mv -f "$TMP" "$DEST"
rm -f "$SNAP"; trap - EXIT
echo "synced $SRC -> $DEST (md5 $(hash_of "$DEST"))"
