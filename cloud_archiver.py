#!/usr/bin/env python3
"""
Cloud archive runner -- OPEN-192 (Phase 3 of the scraper-execution migration).

A from-scratch runner for `os-text-extract archive`, built to run inside the same disposable
container `cloud_collector.py` (OPEN-201) already runs in, reading bill rows from RDS with
ordinary credentials rather than from this Mac's own Postgres. It does only what archiving
needs: acquire exclusion, hydrate Michigan's WAF cookie if the state being archived is Michigan,
invoke `os-text-extract archive` with `ARCHIVE_S3_MODE=direct` so uploads go straight to S3
instead of through the sudo-gated Mac wrapper, parse its own summary line for counts, and emit
a completion record. It does NOT decide *which* S3 buckets to write to -- that is
`WORKING_TIER_S3_BUCKET`, a required environment variable this file only reads and passes
through, matching OPEN-192's own acceptance criteria: which bucket the working tier lives in is
an operator decision this file does not make on anyone's behalf.

Deliberately reuses rather than reimplements what cloud_collector.py (OPEN-201) already built
and proved, per this repo's own stated rule for this rebuild (PLAN-scraper-execution-
migration.md rule 1: a judgement call lives in one place, sourced, not copied twice where it
can drift): `S3Memory` and `SourceLock` (S3-conditional-write cross-machine exclusion),
Michigan's WAF-cookie freshness check, `touch_do_not_retry`/`EXIT_DO_NOT_RETRY`. All imported
directly from `cloud_collector`, not duplicated.

What is genuinely NEW here, not reused, because collection and archiving are different shapes
of work:
  * `SourceLock` is acquired with `suffix="_archive_lock"` -- a third lock, alongside the
    existing `_lock` (collection, OPEN-187) and `_import_lock` (load, OPEN-203) -- so an
    on-prem archiver and this cloud archiver can never race the same jurisdiction, the exact
    class of hazard OPEN-208 named for collection.
  * No baseline/watermark hydration at all. `os-text-extract archive` has no `start=` cutoff
    argument (unlike `os-update --scrape`) -- `archive_bill_versions()` is naturally idempotent
    per document via its own natural-key skip-check (version_note, version_date, source_url),
    so there is no external watermark for this runner to read or write.
  * No completion-record shape borrowed from `cloud_collector.emit_completion_record()` --
    that function's own docstring is explicit about being scrape-shaped ("mode" full/
    incremental, "found" meaning objects scraped). Archiving has neither concept, and
    contorting one operation's record shape onto a structurally different one would be a worse
    fit than writing five honest fields of its own.

Usage:
    python3 cloud_archiver.py <state> [session=<session>] [n=<count>]
    python3 cloud_archiver.py fl session=2026E
    python3 cloud_archiver.py mi

Environment:
    MEMORY_BUCKET          S3 bucket for the memory store (required) -- same store
                           cloud_collector.py uses, reused here only for Michigan's cookie
    MEMORY_PREFIX          Object-key namespace (required, no default -- OPEN-159/172)
    WORKING_TIER_S3_BUCKET Required. The readable-tier bucket `_upload_and_verify_direct()`
                           (openstates-core, OPEN-192) writes every document to, alongside the
                           Deep Archive vault. This file does not default or guess it -- see
                           OPEN-192's own acceptance criteria for why.
    OS_TEXT_EXTRACT        The os-text-extract binary to invoke (default "os-text-extract",
                           overridable for tests, matching cloud_collector.py's OS_UPDATE
                           convention)
    RUN_ID                 Supplied by the caller, or generated here
    DO_NOT_RETRY_FLAG      Path to touch when this run should not be retried

DATABASE_URL / DATABASE_URL_OVERRIDE are read by `os-text-extract` itself (Django), not by this
file -- whatever the container's own environment already points at (RDS, in production) is what
gets archived from. This file never touches the database directly.

Credentials come from boto3's default chain -- an env-var access key here, an ECS task role in
the cloud, matching cloud_collector.py's own "role-based" framing exactly.
"""

import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

import boto3

from cloud_collector import (
    EXIT_DO_NOT_RETRY,
    S3Memory,
    SourceLock,
    LockUnavailable,
    MemoryUnavailable,
    _MI_WAF_COOKIE_GLOB,
    _MI_WAF_COOKIE_MIN_FRESHNESS_SECONDS,
    _mi_waf_cookies_are_fresh,
    touch_do_not_retry,
)

# The summary line `archive()` (openstates-core, text_extract.py) prints on every run, win or
# lose: "<state>: <N> bills checked | fetched=X skipped=Y archived=Z fetch_errors=A blocked=B
# extract_errors=C conflicts=D concurrent_writes=E s3_verified=F s3_unverified=G". Parsed rather
# than re-derived, per this repo's own "one place, sourced" rule -- the counts this runner
# reports are exactly what the archiver itself already computed, not a second count of the same
# thing arrived at a different way.
_SUMMARY_LINE_RE = re.compile(
    r"(?P<state>\S+): (?P<checked>\d+) bills checked \| "
    r"fetched=(?P<fetched>\d+) skipped=(?P<skipped>\d+) "
    r"archived=(?P<archived>\d+) fetch_errors=(?P<fetch_errors>\d+) "
    r"blocked=(?P<blocked>\d+) extract_errors=(?P<extract_errors>\d+) "
    r"conflicts=(?P<conflicts>\d+) concurrent_writes=(?P<concurrent_writes>\d+) "
    r"s3_verified=(?P<s3_verified>\d+) s3_unverified=(?P<s3_unverified>\d+)"
)


def parse_summary_line(output: str):
    """Returns the last matching summary line's counts as a dict of ints, or None if the
    archiver's output never produced one -- e.g. it crashed before printing anything, or
    printed only the WAF-abort line (`click.secho(f"{state}: aborted -- {e}", ...)`), which
    has a different shape and is deliberately not matched here."""
    match = None
    for line in output.splitlines():
        m = _SUMMARY_LINE_RE.search(line)
        if m:
            match = m
    if match is None:
        return None
    return {k: (v if k == "state" else int(v)) for k, v in match.groupdict().items()}


def emit_completion_record(*, status, source, run_id, session=None, counts=None,
                            duration_s=None):
    """This runner's own completion record -- deliberately not `cloud_collector`'s
    `emit_completion_record()`. See the module docstring's "What is genuinely NEW" section for
    why: that function's `mode`/`found` fields are scrape-shaped and neither applies here."""
    record = {"source": source, "run_id": run_id, "status": status}
    if session:
        record["session"] = session
    if counts is not None:
        record.update(counts)
    if duration_s is not None:
        record["duration_s"] = duration_s
    print(json.dumps(record))


def parse_kv_args(argv):
    """`key=value` pairs after the state, order-independent -- same contract as
    cloud_collector.py's own `parse_kv_args`, duplicated rather than imported because this
    file's caller only ever needs `session`/`n`, and importing a second module's argument
    parser for two lines of logic is not a saving worth the coupling."""
    params = {}
    for arg in argv:
        if "=" not in arg:
            raise ValueError(f"expected key=value, got {arg!r}")
        k, v = arg.split("=", 1)
        params[k] = v
    return params


def main(argv, s3_client=None):
    if len(argv) < 1:
        print("usage: cloud_archiver.py <state> [session=<session>] [n=<count>]",
              file=sys.stderr)
        return 1
    state, kv_argv = argv[0], argv[1:]
    started = time.time()
    run_id = os.environ.get("RUN_ID") or f"{state}-archive-{uuid.uuid4().hex[:12]}"

    try:
        params = parse_kv_args(kv_argv)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        emit_completion_record(status="failed", source=state, run_id=run_id)
        return 1

    session = params.get("session")

    working_tier_bucket = os.environ.get("WORKING_TIER_S3_BUCKET")
    if not working_tier_bucket:
        # Fails here rather than letting every individual document upload fail one at a time
        # inside openstates-core -- same information, surfaced once, before any source-site
        # request is made, rather than N times after N of them already were.
        print(
            "ERROR: WORKING_TIER_S3_BUCKET is required -- OPEN-192's own bucket decision is "
            "not made yet (see that ticket's first acceptance criterion)",
            file=sys.stderr,
        )
        emit_completion_record(status="failed", source=state, run_id=run_id, session=session)
        return 1

    try:
        bucket = os.environ["MEMORY_BUCKET"]
    except KeyError:
        print("ERROR: MEMORY_BUCKET is required", file=sys.stderr)
        emit_completion_record(status="failed", source=state, run_id=run_id, session=session)
        return 1

    client = s3_client or boto3.client("s3")
    prefix = os.environ.get("MEMORY_PREFIX", "")
    try:
        memory = S3Memory(client, bucket, prefix)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        emit_completion_record(status="failed", source=state, run_id=run_id, session=session)
        return 1

    # A third lock alongside collection's `_lock` (OPEN-187) and the loader's `_import_lock`
    # (OPEN-203) -- same SourceLock class, same S3-conditional-write mechanism, a new suffix so
    # none of the three ever collide with each other's key. Keyed on the bare state, matching
    # both siblings: archiving one jurisdiction from two places at once is the same class of
    # hazard collection already named this class to prevent.
    lock = SourceLock(client, bucket, prefix, holder=run_id, suffix="_archive_lock")
    try:
        acquired = lock.acquire(state)
    except LockUnavailable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        emit_completion_record(status="failed", source=state, run_id=run_id, session=session)
        touch_do_not_retry()
        return EXIT_DO_NOT_RETRY
    if not acquired:
        print(f"ERROR: another archive run of {state} already holds the lock -- refusing to "
              f"start a second one", file=sys.stderr)
        emit_completion_record(status="failed", source=state, run_id=run_id, session=session)
        touch_do_not_retry()
        return EXIT_DO_NOT_RETRY

    try:
        try:
            return _archive(state, session, params, run_id, started, memory,
                             working_tier_bucket)
        except Exception:
            print(f"ERROR: unhandled exception during {state} archive", file=sys.stderr)
            emit_completion_record(status="failed", source=state, run_id=run_id,
                                    session=session)
            raise
    finally:
        lock.release(state)


def _archive(state, session, params, run_id, started, memory, working_tier_bucket):
    import tempfile

    archive_env = dict(os.environ, ARCHIVE_S3_MODE="direct",
                        WORKING_TIER_S3_BUCKET=working_tier_bucket)

    # Michigan's documents are fetched from the same WAF-protected site its bills are scraped
    # from -- this needs the identical published-cookie handoff cloud_collector.py already
    # built for OPEN-188/189, not a second implementation of it. Skipped entirely for every
    # other state: no other jurisdiction's archive fetches go through a cookie gate at all.
    if state == "mi":
        with tempfile.TemporaryDirectory() as cache_dir:
            try:
                cookie_fetched = memory.hydrate_cache(state, cache_dir, _MI_WAF_COOKIE_GLOB)
            except MemoryUnavailable as e:
                print(f"ERROR: {e} -- refusing to attempt Michigan's archive without being "
                      f"able to check for a published cookie", file=sys.stderr)
                emit_completion_record(status="failed", source=state, run_id=run_id,
                                        session=session)
                return 1
            if not cookie_fetched or not _mi_waf_cookies_are_fresh(
                cache_dir, _MI_WAF_COOKIE_GLOB, time.time(),
                _MI_WAF_COOKIE_MIN_FRESHNESS_SECONDS,
            ):
                print(
                    "ERROR: no fresh published Michigan WAF cookie in the memory store -- "
                    "refusing to attempt a bare archive run (same rule OPEN-188 applies to "
                    "collection)",
                    file=sys.stderr,
                )
                emit_completion_record(status="failed", source=state, run_id=run_id,
                                        session=session)
                # Retryable, not EXIT_DO_NOT_RETRY -- expected to self-heal at the Mac's next
                # scheduled publish tick, exactly as cloud_collector.py's identical check does.
                return 1
            archive_env["CACHE_DIR"] = cache_dir
            return _run_archive_command(state, session, params, run_id, started, archive_env)

    return _run_archive_command(state, session, params, run_id, started, archive_env)


def _run_archive_command(state, session, params, run_id, started, archive_env):
    cmd = [os.environ.get("OS_TEXT_EXTRACT", "os-text-extract"), "archive", state]
    if session:
        cmd += ["session", session]
    if "n" in params:
        cmd += ["n", params["n"]]

    # Streamed to stderr as it's produced, not buffered -- same reasoning as
    # cloud_collector.py's identical choice: a task killed mid-run (`ecs stop-task`) has no
    # SIGTERM handler here, so anything only written after the process exits is lost with the
    # container. Streaming means CloudWatch has already seen it.
    output_lines = []
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             env=archive_env, text=True, bufsize=1)
    for line in proc.stdout:
        output_lines.append(line)
        print(line, end="", file=sys.stderr)
    proc.wait()
    output = "".join(output_lines)

    duration_s = int(time.time() - started)
    counts = parse_summary_line(output)

    if proc.returncode != 0:
        print(f"ERROR: {state} archive failed, exit {proc.returncode}", file=sys.stderr)
        emit_completion_record(status="failed", source=state, run_id=run_id, session=session,
                                counts=counts, duration_s=duration_s)
        return 1

    emit_completion_record(status="ok", source=state, run_id=run_id, session=session,
                            counts=counts, duration_s=duration_s)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
