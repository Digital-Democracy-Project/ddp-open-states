#!/usr/bin/env python3
"""
Cloud people-refresh runner -- OPEN-882 (OPEN-633 section 8, decision D3).

The weekly people refresh as a Fargate task. ddp-sync launches this on the database task definition (ddp-scrapers-db),
waits for it to stop, reads the per-state JSON this writes to S3, and does the rest itself (the scorecard signal for the
states that worked, the status record, the Slack alert). An exit code cannot say WHICH state failed, so S3 does.

Usage:
    python3 cloud_people_refresh.py <run-id> <state>[,<state>...]

What it does: downloads the `people` repo (Digital-Democracy-Project/people, a PUBLIC repository, so no credential: a plain
HTTPS tarball of the branch, which is what `git pull` in run-people-refresh.sh fetched; the image has no git and gains none),
then runs `os-people to-database <state>` once per requested state, a subprocess each so one state's failure is recorded and
the next state still runs (run-people-refresh.sh's "continuing" rule, now with the answer kept per state).

Environment:
    MEMORY_BUCKET, MEMORY_PREFIX   the S3 memory store (both required, as cloud_loader.py)
    WORKING_TIER_PREFIX            prefix for the run's objects in the bucket (default "working-tier", as the other runners)
    DATABASE_URL                   a launcher-passed one wins; otherwise built from the task definition's RDS secret
                                   (cloud_collector.apply_rds_task_secret, the only connection-string builder)
    PEOPLE_REPO, PEOPLE_REF        which repository and branch (default Digital-Democracy-Project/people, main)
    OS_PEOPLE                      the os-people executable (default "os-people")

Result object: `<WORKING_TIER_PREFIX>/people-refresh/<run-id>/people-refresh.json`, written after every requested state has
been tried: {"run_id", "people_commit" (when the tarball says), "states": {"<state>": {"status": "done"|"failed", ...}}}.
Exit 0 when every state worked, 1 when at least one failed (the result is still written: read it), 2 when nothing could be
tried (usage, no login, download, S3: no result is written, an absent object means the task did not finish).
No message contains a connection string: os-people's output is passed through with the login's values removed.
"""

import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from urllib.parse import unquote, urlsplit

import boto3

from cloud_collector import S3Memory, apply_rds_task_secret

RESULT_NAME = "people-refresh.json"
RESULT_SOURCE = "people-refresh"  # the key's place of a state: this job is not one state's
STATE_RE = re.compile(r"^[a-z]{2}$")
DOWNLOAD_TIMEOUT_S = 120


def emit_completion_record(*, status, run_id, states=None, duration_s=None):
    record = {"source": RESULT_SOURCE, "run_id": run_id, "status": status, "phase": "people_refresh"}
    if states is not None:
        record["states"] = states
    if duration_s is not None:
        record["duration_s"] = duration_s
    print(json.dumps(record))


def download_people(repo, ref, dest, opener=urllib.request.urlopen):
    """Extracts the repo's tarball into `dest` and returns (data root, commit or None). The commit is read from the
    tarball's own header (GitHub puts it there); None if absent. Raises on any download or extract problem."""
    url = f"https://codeload.github.com/{repo}/tar.gz/refs/heads/{ref}"
    with opener(url, timeout=DOWNLOAD_TIMEOUT_S) as response:
        payload = response.read()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        commit = (tar.pax_headers or {}).get("comment")
        tar.extractall(dest, filter="data")
    roots = [d for d in os.listdir(dest) if os.path.isdir(os.path.join(dest, d))]
    if len(roots) != 1 or not os.path.isdir(os.path.join(dest, roots[0], "data")):
        raise ValueError("the tarball has no single top folder with a data/ folder")
    return os.path.join(dest, roots[0]), commit


def _scrubber(environ):
    url = environ.get("DATABASE_URL")
    password = urlsplit(url).password if url else None  # the login's own password, however the URL was made
    secrets = [v for v in (password, password and unquote(password), environ.get("RDS_PASSWORD"), url) if v]
    secrets.sort(key=len, reverse=True)  # the whole URL first, so a password inside it does not leave the rest behind

    def scrub(text):
        for s in secrets:
            text = text.replace(s, "***")
        return text

    return scrub


def run_state(state, people_dir, environ, scrub, run=subprocess.run):
    """One `os-people to-database <state>`; returns that state's result entry."""
    started = time.time()
    env = dict(environ, OS_PEOPLE_DIRECTORY=people_dir)
    try:
        proc = run([environ.get("OS_PEOPLE", "os-people"), "to-database", state], env=env,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception as e:  # noqa: BLE001 -- the executable missing or the OS refusing: this state failed, the rest still run
        print(f"ERROR: could not run os-people for {state}: {type(e).__name__}", file=sys.stderr)
        return {"status": "failed", "duration_s": int(time.time() - started), "error": type(e).__name__}
    print(scrub(proc.stdout or ""), end="", file=sys.stderr)
    entry = {"status": "done" if proc.returncode == 0 else "failed", "duration_s": int(time.time() - started)}
    if proc.returncode != 0:
        entry["exit_code"] = proc.returncode
    return entry


def main(argv, s3_client=None, opener=urllib.request.urlopen, run=subprocess.run):
    if len(argv) != 2:
        print("usage: cloud_people_refresh.py <run-id> <state>[,<state>...]", file=sys.stderr)
        return 2
    run_id = argv[0]
    states = [s.strip().lower() for s in argv[1].split(",") if s.strip()]
    started = time.time()

    def fail(message):
        print(f"ERROR: {message}", file=sys.stderr)
        emit_completion_record(status="failed", run_id=run_id)
        return 2

    if not states or not all(STATE_RE.match(s) for s in states):
        return fail("states must be a comma list of two-letter codes")
    try:
        apply_rds_task_secret()
    except ValueError as e:  # names only the missing variables
        return fail(str(e))
    if not os.environ.get("DATABASE_URL"):
        return fail("no DATABASE_URL and no RDS secret in the task definition")
    bucket = os.environ.get("MEMORY_BUCKET")
    if not bucket:
        return fail("MEMORY_BUCKET is required")
    try:
        memory = S3Memory(s3_client or boto3.client("s3"), bucket, os.environ.get("MEMORY_PREFIX", ""))
    except ValueError as e:
        return fail(str(e))

    scrub = _scrubber(os.environ)
    results = {}
    commit = None
    with tempfile.TemporaryDirectory(prefix="cloud-people-refresh-") as staging:
        try:
            people_dir, commit = download_people(os.environ.get("PEOPLE_REPO", "Digital-Democracy-Project/people"),
                                                 os.environ.get("PEOPLE_REF", "main"),
                                                 os.path.join(staging, "people"), opener)
        except Exception as e:  # noqa: BLE001 -- the type only
            return fail(f"could not download the people repo: {type(e).__name__}")
        for state in states:
            print(f"==== os-people to-database {state} ====", file=sys.stderr)
            results[state] = run_state(state, people_dir, os.environ, scrub, run)

        document = {"run_id": run_id, "states": results}
        if commit:
            document["people_commit"] = commit
        key = f"{os.environ.get('WORKING_TIER_PREFIX', 'working-tier')}/{RESULT_SOURCE}/{run_id}/{RESULT_NAME}"
        path = os.path.join(staging, RESULT_NAME)
        with open(path, "w") as f:
            json.dump(document, f)
        try:
            memory.store(path, key)
        except Exception as e:  # noqa: BLE001
            return fail(f"could not write {key}: {type(e).__name__}")

    failed = sorted(s for s, r in results.items() if r["status"] != "done")
    emit_completion_record(status="failed" if failed else "ok", run_id=run_id,
                           states={s: r["status"] for s, r in results.items()},
                           duration_s=int(time.time() - started))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
