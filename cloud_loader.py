#!/usr/bin/env python3
"""
Cloud load runner -- OPEN-190.

The load half of the collect/load split OPEN-201 introduced: consumes one complete cloud
collection run (cloud_collector.py, OPEN-201) from its own manifest-verified objects and
imports it into the on-prem Postgres database via `os-update --import`. Deliberately its own
invocation, not a mode of cloud_collector.py -- per this ticket, collection runs in the cloud
and the load still runs on-prem into the existing database, and the two have different failure
domains (a source site's WAF vs. this machine's own database).

Usage:
    python3 cloud_loader.py <source-id> <run-id> [key=value ...]
    python3 cloud_loader.py mi mi-a1b2c3d4e5f6 session=2025-2026

Environment:
    MEMORY_BUCKET          S3 bucket holding the run's objects (required -- the same bucket
                           cloud_collector.py published this run to)
    MEMORY_PREFIX          Object-key namespace the run was published under (required, same
                           reasoning as cloud_collector.py's own -- an unnamespaced key would
                           let this load a different environment's run)
    WORKING_TIER_PREFIX    Prefix for raw run output within MEMORY_BUCKET (default
                           "working-tier", matching cloud_collector.py)
    OS_UPDATE              The os-update binary to invoke (default "os-update")

The handoff contract (PLAN-scraper-execution-migration.md SS3): a run is only ever consumed
from the manifest cloud_collector.py wrote LAST, after every object it names was already
durable -- so this runner treats that manifest, not the mere existence of objects under the
run's own prefix, as what authorises a load. It refuses to proceed if the manifest's own
run_id/source do not match what it was asked to load -- OPEN-190's own acceptance criterion,
"the run_id in the completion record matches the directory loaded".

Known gap, not yet handled: run-scrape.sh's IMPORT_FLAGS (`--allow_duplicates` for a specific
jurisdiction allowlist, run-scrape.sh:572-574) has no equivalent here. OPEN-190's rollout is
one jurisdiction at a time, smallest first -- add that flag when (and if) a jurisdiction that
actually needs it is rolled out, rather than guessing at its scope now.

Known trust boundary: the manifest cloud_collector.py writes does not carry `session` (only
run_id/source/objects), so this runner cannot independently verify a caller-supplied
`session=` argument against the run it names -- the caller (whatever launches this loader) is
trusted to pass the same session the collection was actually launched with, exactly as
cloud_collector.py's own `session=` argument is trusted today. A wrong session here would
still refuse to load the wrong DATA (run_id/source are checked), but would acquire the OPEN-203
import lock under the wrong key and pass the wrong `session=` to os-update -- both are launch-
time correctness properties this file cannot check for itself.

Rollout gate: this file's cross-machine exclusion (below) only actually excludes a mac-side
`run-scrape.sh` import if OPEN-203's matching bash-side lock (scraper-memory.sh's
scraper_memory_import_lock_key) is merged AND deployed first. Do not run this loader against a
jurisdiction still eligible for a local import until that is true.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import boto3

from cloud_collector import (
    EXIT_DO_NOT_RETRY,
    LockUnavailable,
    S3Memory,
    SourceLock,
    derive_scrape_key,
    parse_kv_args,
)


def emit_completion_record(*, status, source, run_id, session=None, duration_s=None):
    """The load-side analogue of cloud_collector.py's own completion record. Deliberately
    does not claim new/updated/noop counts: os-update --import's own stdout is not
    structured, streamed to the caller's log rather than parsed here, and inventing counts
    this runner cannot actually verify would be worse than omitting them."""
    record = {"source": source, "run_id": run_id, "status": status, "phase": "import"}
    if session:
        record["session"] = session
    if duration_s is not None:
        record["duration_s"] = duration_s
    print(json.dumps(record))


def _fetch_manifest(memory, work_prefix, source, run_id):
    """Returns (manifest_dict, None) on success, or (None, reason) otherwise. Never guesses:
    an absent manifest means this run has not finished collecting (or never will), which is a
    different fact than "could not tell", which is different again from "found but
    unparsable" -- collapsing any of those into another is exactly the OPEN-152 mistake this
    project has already paid for once."""
    key = f"{work_prefix}/{source}/{run_id}/_manifest.json"
    fd, tmp_path = tempfile.mkstemp(prefix="cloud-loader-manifest-")
    os.close(fd)
    try:
        status = memory.fetch(key, tmp_path)
        if status == "absent":
            return None, f"no completion marker at {key} -- run not finished, or never happened"
        if status == "unknown":
            return None, f"could not determine whether {key} exists -- refusing to guess"
        try:
            with open(tmp_path) as f:
                return json.load(f), None
        except (json.JSONDecodeError, OSError) as e:
            return None, f"manifest at {key} could not be parsed: {e}"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _validate_manifest(manifest):
    """pm-review: a manifest that is valid JSON but not the expected shape (not an object, no
    `objects` list, or an `objects` entry that isn't a string) must not be silently treated as
    an empty or best-effort run -- that is the same "collapse an unexpected shape into a
    convenient default" mistake OPEN-152 already cost this project once. Returns a reason
    string, or None if the shape is acceptable."""
    if not isinstance(manifest, dict):
        return f"manifest is not a JSON object (got {type(manifest).__name__})"
    objects = manifest.get("objects")
    if not isinstance(objects, list):
        return f"manifest has no 'objects' list (got {type(objects).__name__})"
    for entry in objects:
        if not isinstance(entry, str):
            return f"manifest 'objects' contains a non-string entry: {entry!r}"
    return None


def _fetch_run_objects(memory, work_prefix, source, run_id, manifest, data_dir):
    """Downloads every object the manifest names into data_dir, reconstructing the exact
    <module>/... layout os-update --scrape originally wrote it in (each key's suffix, after
    the run's own prefix, IS that relative path). Returns None on success, or a reason string
    on the first object that cannot be fetched intact -- refusing a partial load rather than
    importing whatever happened to arrive.

    pm-review: `object_key.startswith(run_prefix)` alone does not make the derived local path
    safe -- a key like `<run_prefix>../../etc/cron.d/evil` still starts with `run_prefix` as a
    string, and a key like `<run_prefix>/etc/passwd` (note the doubled slash) produces a `rel`
    beginning with `/`, which `os.path.join` treats as absolute and silently discards data_dir
    entirely. The manifest is written by cloud_collector.py, not user input directly, but nothing
    stops it (or the object this function reads) from carrying a corrupted or tampered key --
    and the failure mode is an on-prem file write outside the staging directory, so this is
    checked explicitly rather than trusted.

    pm-review round 2: containment-after-resolve alone still let `rel` be empty (or reduce to
    one via a `.`/`..` component), which lands `dest` ON data_dir itself rather than a file
    beneath it -- not an escape, but a fetch aimed at a directory instead of a file, and two
    keys that both normalize to the same destination (`a/../b` and a plain `b`) could silently
    overwrite each other. cloud_collector.py's own manifest only ever lists real
    `Path.relative_to()` suffixes from an actual filesystem walk, which never contain an empty,
    `.`, or `..` component -- so rejecting any that do is a correctness check on the relative
    path's shape, checked before ever resolving it, not a new restriction on a legitimate case.
    """
    run_prefix = f"{work_prefix}/{source}/{run_id}/"
    data_root = Path(data_dir).resolve()
    for object_key in manifest.get("objects", []):
        if not object_key.startswith(run_prefix):
            return (f"manifest lists {object_key!r}, outside this run's own prefix "
                     f"{run_prefix!r} -- refusing to fetch it")
        rel = object_key[len(run_prefix):]
        if not rel or any(part in ("", ".", "..") for part in rel.split("/")):
            return (f"manifest lists {object_key!r} with an invalid relative path {rel!r} "
                     f"-- refusing to fetch it")
        dest = (data_root / rel).resolve()
        if data_root != dest and data_root not in dest.parents:
            return (f"manifest lists {object_key!r}, which resolves outside the staging "
                     f"directory -- refusing to fetch it")
        os.makedirs(dest.parent, exist_ok=True)
        status = memory.fetch(object_key, str(dest))
        if status != "found":
            return (f"manifest names {object_key!r} but it could not be fetched "
                     f"({status}) -- refusing a partial load")
    return None


def _run_import(source, data_dir, cache_dir):
    """Invokes os-update --import, streamed line-by-line rather than buffered -- the same
    CloudWatch-observability lesson cloud_collector.py's own scrape invocation learned the
    hard way (a killed or long-running process leaves zero trail otherwise). Mirrors
    run-scrape.sh's own default (non-sweep) import invocation: `$OS_UPDATE $STATE --import
    $IMPORT_FLAGS $DIR_FLAGS` (run-scrape.sh:1126-1129), with IMPORT_FLAGS empty here (see
    module docstring) and DIR_FLAGS as --cachedir/--datadir.

    Deliberately does NOT pass `session=...` as a positional argument -- caught live, running
    this for real: update.py's `key=value` grammar is `(scraper_type (k:v)+)+`
    (openstates/cli/update.py's do_update(), "argument {} before scraper name"), so a bare
    `session=X` with no preceding scraper-type token raises CommandError. That grammar is
    for --scrape's own params (cloud_collector.py's own invocation passes `bills` as the
    scraper type before any k=v). run-scrape.sh's real --import invocation never passes
    session= at all -- --import determines what to load purely from what is under --datadir,
    not from a session argument -- and this now matches that exactly."""
    cmd = [os.environ.get("OS_UPDATE", "os-update"), source, "--import",
           "--cachedir", cache_dir, "--datadir", data_dir]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, bufsize=1)
    for line in proc.stdout:
        print(line, end="", file=sys.stderr)
    proc.wait()
    return proc.returncode


def _load(source, scrape_key, session, params, run_id, manifest, memory, work_prefix, started):
    with tempfile.TemporaryDirectory(prefix=f"cloud-loader-{run_id}-") as staging:
        data_dir = os.path.join(staging, "scraped")
        cache_dir = os.path.join(staging, "cache")
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)

        err = _fetch_run_objects(memory, work_prefix, source, run_id, manifest, data_dir)
        if err is not None:
            print(f"ERROR: {err}", file=sys.stderr)
            emit_completion_record(status="failed", source=source, run_id=run_id, session=session)
            return 1

        returncode = _run_import(source, data_dir, cache_dir)
        duration_s = int(time.time() - started)

        if returncode != 0:
            print(f"ERROR: {source}/{run_id} import failed, exit {returncode}", file=sys.stderr)
            emit_completion_record(status="failed", source=source, run_id=run_id,
                                    session=session, duration_s=duration_s)
            return 1

        emit_completion_record(status="ok", source=source, run_id=run_id, session=session,
                                duration_s=duration_s)
        return 0


def main(argv, s3_client=None):
    if len(argv) < 2:
        print("usage: cloud_loader.py <source-id> <run-id> [key=value ...]", file=sys.stderr)
        return 1
    source, run_id, kv_argv = argv[0], argv[1], argv[2:]
    started = time.time()

    try:
        params = parse_kv_args(kv_argv)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        emit_completion_record(status="failed", source=source, run_id=run_id)
        return 1

    session = params.get("session")
    scrape_key = derive_scrape_key(source, params)

    try:
        bucket = os.environ["MEMORY_BUCKET"]
    except KeyError:
        print("ERROR: MEMORY_BUCKET is required", file=sys.stderr)
        emit_completion_record(status="failed", source=source, run_id=run_id, session=session)
        return 1

    client = s3_client or boto3.client("s3")
    prefix = os.environ.get("MEMORY_PREFIX", "")
    try:
        memory = S3Memory(client, bucket, prefix)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        emit_completion_record(status="failed", source=source, run_id=run_id, session=session)
        return 1

    work_prefix = os.environ.get("WORKING_TIER_PREFIX", "working-tier")

    manifest, err = _fetch_manifest(memory, work_prefix, source, run_id)
    if err is not None:
        print(f"ERROR: {err}", file=sys.stderr)
        emit_completion_record(status="failed", source=source, run_id=run_id, session=session)
        return 1

    shape_err = _validate_manifest(manifest)
    if shape_err is not None:
        print(f"ERROR: {shape_err}", file=sys.stderr)
        emit_completion_record(status="failed", source=source, run_id=run_id, session=session)
        return 1

    if manifest.get("run_id") != run_id or manifest.get("source") != source:
        print(f"ERROR: manifest identifies run_id={manifest.get('run_id')!r} "
              f"source={manifest.get('source')!r}, refusing to load it as {source}/{run_id} "
              f"(OPEN-190: the compared run must be the loaded run)", file=sys.stderr)
        emit_completion_record(status="failed", source=source, run_id=run_id, session=session)
        return 1

    # OPEN-203: the cross-machine IMPORT lock. Keyed on scrape_key, not bare source, to land
    # on the exact same S3 object scraper_memory_import_lock_key (scraper-memory.sh) computes
    # for run-scrape.sh's own local-import-lock-turned-shared-lock -- a mac import and a cloud
    # load only exclude each other if both name the same key. A SEPARATE SourceLock instance
    # from any scrape lock a caller might also hold (one instance, one lock -- see SourceLock's
    # own docstring for why one instance cannot juggle two).
    import_lock = SourceLock(client, bucket, prefix, holder=run_id, suffix="_import_lock")
    try:
        acquired = import_lock.acquire(scrape_key)
    except LockUnavailable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        emit_completion_record(status="failed", source=source, run_id=run_id, session=session)
        return EXIT_DO_NOT_RETRY
    if not acquired:
        print(f"ERROR: another import of {scrape_key} already holds the lock -- refusing to "
              f"load {source}/{run_id} on top of it (OPEN-203)", file=sys.stderr)
        emit_completion_record(status="failed", source=source, run_id=run_id, session=session)
        return EXIT_DO_NOT_RETRY

    try:
        try:
            return _load(source, scrape_key, session, params, run_id, manifest, memory,
                         work_prefix, started)
        except Exception:
            print(f"ERROR: unhandled exception during {source}/{run_id} load", file=sys.stderr)
            emit_completion_record(status="failed", source=source, run_id=run_id, session=session)
            raise
    finally:
        import_lock.release(scrape_key)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
