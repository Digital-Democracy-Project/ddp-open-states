#!/usr/bin/env python3
"""
Cloud collection runner -- OPEN-201.

A from-scratch, infrastructure-agnostic replacement for run-scrape.sh's collection half,
built to run inside a disposable container rather than on this Mac. It does only what
collection needs: read memory, decide full versus incremental, invoke `os-update --scrape`,
classify the outcome, write memory back, upload the run's output, and emit the contract's
completion record. It does NOT import -- that is a separate invocation (OPEN-190), against
a separate exclusion mechanism (OPEN-203) that does not exist yet.

Deliberately reuses rather than reimplements two decisions that already live in this repo's
bash tooling (PLAN-scraper-execution-migration.md's rule 1 for this rebuild):
  * the unreachable-site matcher in import-summary.sh (`scrape_output_shows_unreachable_site`)
  * scraper-memory.sh's exact object layout, three-way read semantics, and publish ordering

Usage:
    python3 cloud_collector.py <source-id> [key=value ...]
    python3 cloud_collector.py mi session=2025-2026
    python3 cloud_collector.py ut session=2025S2 bill_no=HB123

Environment:
    MEMORY_BUCKET          S3 bucket for memory and the working tier (required)
    MEMORY_PREFIX          Object-key namespace, e.g. "prod" or "dev-open201" (required --
                           no default; see scraper-memory.sh's OPEN-159/172 note for why)
    WORKING_TIER_PREFIX    Prefix for raw output within MEMORY_BUCKET (default "working-tier")
    OS_UPDATE              The os-update binary to invoke (default "os-update"; overridable
                           for tests, matching run-scrape.sh's OS_UPDATE_OVERRIDE convention)
    RUN_ID                 Supplied by the caller, or generated here (contract SS1)
    DO_NOT_RETRY_FLAG      Path to touch when this run should not be retried (contract SS3)

Credentials come from boto3's default chain -- an env-var access key here, an ECS task role
in the cloud. That is the whole point of "role-based": this file never branches on where its
credentials came from.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REPO_ROOT = Path(__file__).resolve().parent

# Contract SS3's retry signal, identical to run-scrape.sh's EXIT_DO_NOT_RETRY. Kept as the same
# value on purpose -- a caller that already knows this code from the existing runner should not
# have to learn a second one.
EXIT_DO_NOT_RETRY = 90

# The one jurisdiction that must never run a bare full walk when its baseline is missing.
# LESSONS.md SS5: "a full collection is expensive or block-sensitive" is Michigan's case exactly
# -- ~3,900 requests against a 10/minute cap -- so refusing is the correct behaviour, not a
# degradation. Read from the same cache-file convention scraper-memory.sh uses, rather than a
# second hard-coded name, so the two cannot drift on what "Michigan's baseline" means.
_MI_BASELINE_GLOB = "mi_last_actions_*.json"


class MemoryUnavailable(Exception):
    """The store could not be read (found/absent could not be determined). Never guess."""


class S3Memory:
    """Contract SS4's store: keyed by source + scrape key, three-way reads, ordered writes.

    Mirrors scraper-memory.sh's functions one-for-one so the two clients agree on shape even
    though this one uses boto3/task-role credentials rather than the sudo-gated wrapper.
    """

    def __init__(self, client, bucket, prefix):
        if not prefix:
            raise ValueError(
                "MEMORY_PREFIX is required -- an unnamespaced key would let this run "
                "overwrite another environment's memory (OPEN-159/172)"
            )
        self.client = client
        self.bucket = bucket
        self.prefix = prefix

    def key(self, source, scrape_key, filename):
        return f"{self.prefix}/{source}/{scrape_key}/{filename}"

    def cache_key(self, source, filename):
        return f"{self.prefix}/{source}/_cache/{filename}"

    def fetch(self, key, dest):
        """Returns "found", "absent", or "unknown". Never raises for a missing key.

        Absence is matched positively on the shapes S3 actually emits for a missing object --
        a 404 or NoSuchKey ClientError -- exactly as scraper-memory.sh matches on the wrapper's
        "(404)"/NoSuchKey text. Anything else (throttling, a credential problem, a timeout)
        falls through to "unknown", because collapsing that into "absent" is precisely the
        OPEN-152 mistake: a store that did not answer is not a store that said no.
        """
        tmp = f"{dest}.fetch.{os.getpid()}"
        try:
            self.client.download_file(self.bucket, key, tmp)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                return "absent"
            return "unknown"
        except Exception:
            return "unknown"
        os.replace(tmp, dest)
        return "found"

    def store(self, local_path, key):
        """Raises on failure -- the caller decides what a failed publish means."""
        self.client.upload_file(local_path, self.bucket, key)

    def list(self, prefix):
        """Returns a list of keys, or None if the listing could not be trusted."""
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            keys = []
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                keys.extend(o["Key"] for o in page.get("Contents", []))
            return keys
        except Exception:
            return None

    def hydrate_markers(self, source, scrape_key, local_dir):
        """0/absent/unknown for each of .ts/.count/.imported; raises MemoryUnavailable on
        the first "unknown", matching scraper-memory.sh's hydrate_markers refusal."""
        found_any = False
        for name in (f"{scrape_key}.ts", f"{scrape_key}.count", f"{scrape_key}.imported"):
            outcome = self.fetch(self.key(source, scrape_key, name), os.path.join(local_dir, name))
            if outcome == "unknown":
                raise MemoryUnavailable(f"could not read {name} from the memory store")
            found_any = found_any or outcome == "found"
        return found_any

    def hydrate_cache(self, source, cache_dir, glob):
        """As scraper-memory.sh: only fetches objects matching `glob`, leaves everything else."""
        import fnmatch

        keys = self.list(self.cache_key(source, ""))
        if keys is None:
            raise MemoryUnavailable(f"could not list {source}'s cache memory")
        os.makedirs(cache_dir, exist_ok=True)
        fetched = []
        for key in keys:
            base = os.path.basename(key)
            if not fnmatch.fnmatch(base, glob):
                continue
            if self.fetch(key, os.path.join(cache_dir, base)) == "unknown":
                raise MemoryUnavailable(f"could not read {key} from the memory store")
            fetched.append(base)
        return fetched

    def persist_cache(self, source, cache_dir, glob):
        import glob as globmod

        for path in globmod.glob(os.path.join(cache_dir, glob)):
            self.store(path, self.cache_key(source, os.path.basename(path)))

    def persist_markers(self, source, scrape_key, local_dir):
        """Watermark (.ts) LAST, after the reporting markers -- see scraper-memory.sh's own
        comment for why this ordering, not atomicity, is the safety property here."""
        for name in (f"{scrape_key}.count", f"{scrape_key}.imported", f"{scrape_key}.ts"):
            path = os.path.join(local_dir, name)
            if os.path.isfile(path):
                self.store(path, self.key(source, scrape_key, name))


def scrape_output_shows_unreachable_site(output_path):
    """Shells out to import-summary.sh's own matcher rather than re-deriving the marker list
    in Python -- PLAN-scraper-execution-migration.md's rule 1: a judgement call lives in one
    place, sourced, not copied twice where it can drift."""
    result = subprocess.run(
        ["bash", "-c", 'source "$1"/import-summary.sh && scrape_output_shows_unreachable_site "$2"',
         "_", str(REPO_ROOT), output_path],
        capture_output=True,
    )
    return result.returncode == 0


def parse_kv_args(argv):
    """`key=value` pairs, order-independent, per contract SS1. Anything without an "=" is a
    parse error -- this runner does not guess a caller's positional intent."""
    params = {}
    for arg in argv:
        if "=" not in arg:
            raise ValueError(f"expected key=value, got {arg!r}")
        k, v = arg.split("=", 1)
        params[k] = v
    return params


def emit_completion_record(*, status, mode, source, run_id, session=None, found=None,
                            duration_s=None):
    """Contract SS2's one JSON line. Deliberately omits new/updated/noop even on `ok` --
    those are what the LOAD measured, and this runner never loads (OPEN-201's own scope:
    "No load"). Contract SS2 itself anticipates the split: "found is not required to equal
    new + updated + noop -- the first counts what was collected, the others what the load
    made of it." A collect-only completion record is the case that clause was written for;
    it is called out explicitly in this ticket's PR rather than assumed, since SS2's "required
    when ok" line was written before the collect/load split existed."""
    record = {"source": source, "run_id": run_id, "mode": mode, "status": status}
    if session:
        record["session"] = session
    if found is not None:
        record["found"] = found
    if duration_s is not None:
        record["duration_s"] = duration_s
    print(json.dumps(record))


def touch_do_not_retry():
    flag = os.environ.get("DO_NOT_RETRY_FLAG")
    if flag:
        Path(flag).touch()


def main(argv, s3_client=None):
    if len(argv) < 1:
        print("usage: cloud_collector.py <source-id> [key=value ...]", file=sys.stderr)
        return 1
    source, kv_argv = argv[0], argv[1:]
    started = time.time()
    run_id = os.environ.get("RUN_ID") or f"{source}-{uuid.uuid4().hex[:12]}"

    try:
        params = parse_kv_args(kv_argv)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        emit_completion_record(status="failed", mode="full", source=source, run_id=run_id)
        return 1

    session = params.get("session")
    scrape_key = f"{source}_{session}" if session else source

    bucket = os.environ["MEMORY_BUCKET"]
    memory = S3Memory(s3_client or boto3.client("s3"), bucket, os.environ.get("MEMORY_PREFIX", ""))

    with tempfile.TemporaryDirectory() as staging:
        last_run_dir = os.path.join(staging, "last-run")
        cache_dir = os.path.join(staging, "cache")
        os.makedirs(last_run_dir, exist_ok=True)

        try:
            if source == "mi":
                fetched = memory.hydrate_cache(source, cache_dir, _MI_BASELINE_GLOB)
                if not fetched:
                    # LESSONS.md SS5: refuse rather than seed from the site. This is a hard
                    # input, not an optimisation -- see scraper-memory.sh's own header note.
                    print(
                        "ERROR: Michigan's last-action baseline is missing from the memory "
                        "store -- refusing to run incrementally rather than seeding from the "
                        "site (LESSONS.md SS5)",
                        file=sys.stderr,
                    )
                    emit_completion_record(status="failed", mode="full", source=source,
                                            run_id=run_id, session=session)
                    touch_do_not_retry()
                    return EXIT_DO_NOT_RETRY

            found_watermark = memory.hydrate_markers(source, scrape_key, last_run_dir)
        except MemoryUnavailable as e:
            print(f"ERROR: {e} -- refusing to run rather than assuming a first-ever run "
                  f"(OPEN-181/contract SS4)", file=sys.stderr)
            emit_completion_record(status="failed", mode="full", source=source, run_id=run_id,
                                    session=session)
            return 1

        mode = "incremental" if found_watermark else "full"

        out_dir = os.path.join(staging, "scraped")
        os.makedirs(out_dir, exist_ok=True)
        scrape_output = os.path.join(staging, "scrape_output.log")

        cmd = [os.environ.get("OS_UPDATE", "os-update"), source, "--scrape", "bills"]
        for k, v in params.items():
            cmd.append(f"{k}={v}")
        cmd += ["--datadir", out_dir]

        with open(scrape_output, "w") as f:
            proc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)

        duration_s = int(time.time() - started)

        if proc.returncode != 0 and scrape_output_shows_unreachable_site(scrape_output):
            # OPEN-53: retrying a block makes it worse. Terminal, not retryable.
            print(f"ERROR: {source} appears unreachable -- see {scrape_output}", file=sys.stderr)
            emit_completion_record(status="unreachable", mode=mode, source=source,
                                    run_id=run_id, session=session, duration_s=duration_s)
            touch_do_not_retry()
            return EXIT_DO_NOT_RETRY

        if proc.returncode != 0:
            print(f"ERROR: {source} scrape failed, exit {proc.returncode}", file=sys.stderr)
            emit_completion_record(status="failed", mode=mode, source=source, run_id=run_id,
                                    session=session, duration_s=duration_s)
            return 1

        found = sum(1 for p in Path(out_dir).rglob("*") if p.is_file())

        # Write the watermark and its count locally first, exactly as run-scrape.sh does
        # (run-scrape.sh:1181-1182) -- persist_markers only ever publishes what already
        # exists on disk, and nothing else in this collect-only run creates these files.
        # No `.imported` marker: that describes an IMPORT outcome, and this runner never
        # loads (see emit_completion_record's note on new/updated/noop).
        import datetime

        with open(os.path.join(last_run_dir, f"{scrape_key}.ts"), "w") as f:
            f.write(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))
        with open(os.path.join(last_run_dir, f"{scrape_key}.count"), "w") as f:
            f.write(f"{found}:{mode}")

        work_prefix = os.environ.get("WORKING_TIER_PREFIX", "working-tier")
        manifest = []
        for p in sorted(Path(out_dir).rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(out_dir)
            object_key = f"{work_prefix}/{source}/{run_id}/{rel}"
            memory.store(str(p), object_key)
            manifest.append(object_key)

        # The completion marker, written LAST, after every object it names is durable -- a
        # marker visible before its objects means a loader could see an incomplete set and
        # not know it (PLAN-scraper-execution-migration.md SS3, "the handoff contract").
        marker_path = os.path.join(staging, "manifest.json")
        with open(marker_path, "w") as f:
            json.dump({"run_id": run_id, "source": source, "objects": manifest}, f)
        memory.store(marker_path, f"{work_prefix}/{source}/{run_id}/_manifest.json")

        # Cache-resident memory first, watermark last -- see S3Memory.persist_markers.
        memory.persist_cache(source, cache_dir, _MI_BASELINE_GLOB)
        memory.persist_markers(source, scrape_key, last_run_dir)

        emit_completion_record(status="ok", mode=mode, source=source, run_id=run_id,
                                session=session, found=found, duration_s=duration_s)
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
