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
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${MANIFEST_SOURCE:-$HERE/../jurisdictions.yaml}"
DEST_DIR="${MANIFEST_DEST_DIR:-$HERE/manifest}"
DEST="$DEST_DIR/jurisdictions.yaml"

hash_of() { if command -v md5sum >/dev/null 2>&1; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi; }

[ -s "$SRC" ] || { echo "STOP: $SRC is missing or empty; the existing copy (if any) was not touched" >&2; exit 1; }

if [ "${1:-}" = "--check" ]; then
    [ -s "$DEST" ] || { echo "DIFFERS: no copy at $DEST"; exit 1; }
    if [ "$(hash_of "$SRC")" = "$(hash_of "$DEST")" ]; then
        echo "OK: $DEST matches $SRC (md5 $(hash_of "$DEST"))"; exit 0
    fi
    echo "DIFFERS: $DEST (md5 $(hash_of "$DEST")) is not $SRC (md5 $(hash_of "$SRC"))"; exit 1
fi

[ ! -L "$DEST_DIR" ] || { echo "STOP: $DEST_DIR is a symlink; refusing to write through it" >&2; exit 1; }
[ ! -d "$DEST" ] && [ ! -L "$DEST" ] || { echo "STOP: $DEST is a directory or a symlink (docker creates a directory when a bind mount's source is missing); remove it and rerun" >&2; exit 1; }
mkdir -p "$DEST_DIR"
TMP="$(mktemp "$DEST_DIR/.jurisdictions.yaml.XXXXXX")" || {
    echo "STOP: cannot write in $DEST_DIR (if an earlier 'docker compose up' created it as root, remove the empty directory and rerun)" >&2
    exit 1
}
trap 'rm -f "$TMP"' EXIT
cp -p "$SRC" "$TMP"
chmod 644 "$TMP"
# api-v3 reloads only when the file's modification time CHANGES. cp -p keeps the source's time (so /ddp/enrollment's
# manifest_mtime equals the checkout's), which is a new time on every real pull; if a changed file ever carries the very
# same time as the copy it replaces, give it the current time so the change cannot go unseen.
if [ -e "$DEST" ] && ! cmp -s "$SRC" "$DEST" && ! [ "$TMP" -nt "$DEST" ] && ! [ "$DEST" -nt "$TMP" ]; then
    touch "$TMP"
fi
mv -f "$TMP" "$DEST"
trap - EXIT
echo "synced $SRC -> $DEST (md5 $(hash_of "$DEST"))"
