#!/usr/bin/env python3
"""
Cloud unmatched-voter runner -- OPEN-881 (OPEN-633 section 8).

The after-load unmatched-voter check as a Fargate task. ddp-sync launches this on the database task definition
(ddp-scrapers-db) after a state's load, waits for it to stop, reads the JSON this writes to S3, and does the rest itself
(the comparison with the last run, the Redis memory and the alert). An exit code cannot carry the result, so S3 does.

Usage:
    python3 cloud_unmatched_voters.py <state> <run-id>

It makes the SAME result `unmatched-voters.py` prints (qa_primitives.unmatched_voters_result: Stage 3's Gate 1 vote rule,
read-only, names the manifest accepts marked `accepted`); there is no second query here.

Environment:
    MEMORY_BUCKET, MEMORY_PREFIX   the S3 memory store (both required, as cloud_loader.py)
    WORKING_TIER_PREFIX            prefix for the run's objects in the bucket (default "working-tier", as the other runners)
    DATABASE_URL                   a launcher-passed one wins; otherwise built from the task definition's RDS secret
                                   (cloud_collector.apply_rds_task_secret, the only connection-string builder)

Result object: `<WORKING_TIER_PREFIX>/<state>/<run-id>/unmatched-voters.json`, written only after the query succeeded (an
absent object means the task did not finish). Exit 0 on success, 2 on any failure (usage, no login, database, S3); the
message never contains a connection string (an exception's type only).
"""

import json
import os
import sys
import tempfile
import time

import boto3

from cloud_collector import S3Memory, apply_rds_task_secret
from qa_primitives import unmatched_voters_result

RESULT_NAME = "unmatched-voters.json"


def emit_completion_record(*, status, source, run_id, names=None, duration_s=None):
    record = {"source": source, "run_id": run_id, "status": status, "phase": "unmatched_voters"}
    if names is not None:
        record["names"] = names
    if duration_s is not None:
        record["duration_s"] = duration_s
    print(json.dumps(record))


def main(argv, s3_client=None, connect=None):
    if len(argv) != 2:
        print("usage: cloud_unmatched_voters.py <state> <run-id>", file=sys.stderr)
        return 2
    state, run_id = argv[0].lower(), argv[1]
    started = time.time()

    def fail(message):
        print(f"ERROR: {message}", file=sys.stderr)
        emit_completion_record(status="failed", source=state, run_id=run_id)
        return 2

    try:
        apply_rds_task_secret()
    except ValueError as e:  # names only the missing variables
        return fail(str(e))
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return fail("no DATABASE_URL and no RDS secret in the task definition")
    bucket = os.environ.get("MEMORY_BUCKET")
    if not bucket:
        return fail("MEMORY_BUCKET is required")
    try:
        memory = S3Memory(s3_client or boto3.client("s3"), bucket, os.environ.get("MEMORY_PREFIX", ""))
    except ValueError as e:
        return fail(str(e))

    try:
        result = unmatched_voters_result(state, database_url, connect)
    except Exception as e:  # noqa: BLE001 -- the type only: the message of a connect error can carry the address
        return fail(f"could not read {state}: {type(e).__name__}")

    key = f"{os.environ.get('WORKING_TIER_PREFIX', 'working-tier')}/{state}/{run_id}/{RESULT_NAME}"
    with tempfile.TemporaryDirectory(prefix="cloud-unmatched-voters-") as staging:
        path = os.path.join(staging, RESULT_NAME)
        with open(path, "w") as f:
            json.dump(result, f)
        try:
            memory.store(path, key)
        except Exception as e:  # noqa: BLE001
            return fail(f"could not write {key}: {type(e).__name__}")
    emit_completion_record(status="ok", source=state, run_id=run_id, names=len(result["names"]),
                           duration_s=int(time.time() - started))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
