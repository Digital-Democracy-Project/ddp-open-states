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

import datetime
import json
import math
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

# OPEN-189/OPEN-188's "publish, do not call in" cookie design, exercised for the first time
# here: this file never mints a Michigan cookie itself (no CAPTCHA-solving, no Playwright
# import at all unless this fetch comes up empty and openstates-core falls back on its own).
# It only reads whatever the Mac's real ScrapeBot mint already published to this same memory
# store -- the same fetch mechanism as the last-action baseline, a different filename.
# CookieProvider._read_cache() (openstates-core) reads this exact filename from --cachedir and,
# if it validates, never touches Playwright at all -- cookies and user_agent travel as one
# unit (OPEN-23), which is why this is a plain file fetch and not two separate values.
_MI_WAF_COOKIE_GLOB = "mi_waf_cookies.json"

# OPEN-188's own gated half, cleared 2026-08-29 (OPEN-200 answered the runtime question this
# was waiting on). How much life a published cookie must still have left before this runner
# will trust it -- not a guess at the mac's own publish cadence (mi_cookie_publish.py,
# ddp-sync, default every 6h), just a floor against a cookie that is technically not-yet-
# expired but only by seconds. A cookie expiring mid-scrape is a separate problem this value
# does not claim to solve -- Michigan's existing resilience/retry path is what handles a
# cookie going bad partway through a run; this only gates whether to START one at all.
_MI_WAF_COOKIE_MIN_FRESHNESS_SECONDS = int(
    os.environ.get("MI_WAF_COOKIE_MIN_FRESHNESS_SECONDS", 600)
)


def _mi_waf_cookies_are_fresh(cache_dir, filename, now, min_remaining_seconds):
    """OPEN-188 acceptance criterion: "stale-beyond-threshold produces a loud skip." Refuses
    -- returns False -- on anything short of a parsed file naming at least one cookie whose
    `expires` is still `min_remaining_seconds` or more in the future: missing file,
    unparsable JSON, an empty cookie set, or a malformed/missing `expires` on any entry all
    count as not fresh. This is a shape check on write_cookie_cache's own format
    (scrapebot_client.py, ddp-sync): `{cookie_name: {value, expires}, "_meta": {...}}`.
    """
    path = os.path.join(cache_dir, filename)
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    cookies = {k: v for k, v in data.items() if k != "_meta"}
    if not cookies:
        return False
    for entry in cookies.values():
        if not isinstance(entry, dict):
            return False
        expires = entry.get("expires")
        # pm-review: json.loads accepts the non-standard `NaN`/`Infinity` literals, and
        # `float("nan") < x` is always False -- so a NaN expires would have passed this
        # check silently without math.isfinite() ruling it out explicitly first.
        if (
            not isinstance(expires, (int, float))
            or isinstance(expires, bool)
            or not math.isfinite(expires)
            or expires < now + min_remaining_seconds
        ):
            return False
    return True


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
        """Fetches .ts/.count/.imported; raises MemoryUnavailable on the first "unknown".
        Returns whether **`.ts` specifically** was found -- not whether any of the three was.

        `.ts` is the authorising object (scraper-memory.sh's own term for it): it is published
        LAST, after the two reporting markers, precisely so a partial publish leaves it absent.
        pm-review caught that an earlier version of this method treated "found .count but not
        .ts" as incremental -- exactly the half-published state watermark-last ordering exists
        to make safe, undone by reading the wrong signal on the way back in.
        """
        outcomes = {}
        for name in (f"{scrape_key}.ts", f"{scrape_key}.count", f"{scrape_key}.imported"):
            outcome = self.fetch(self.key(source, scrape_key, name), os.path.join(local_dir, name))
            if outcome == "unknown":
                raise MemoryUnavailable(f"could not read {name} from the memory store")
            outcomes[name] = outcome
        return outcomes[f"{scrape_key}.ts"] == "found"

    def hydrate_cache(self, source, cache_dir, glob):
        """As scraper-memory.sh: only fetches objects matching `glob`, leaves everything else.

        pm-review caught a real race here: a listing can name a key that is gone by the time
        we download it (deleted between `list` and `fetch`). Only "found" counts as present --
        "absent" must NOT be appended to the result, or a vanished-between-list-and-fetch
        object would look identical to a present one to the caller, defeating Michigan's
        refuse-without-baseline check on exactly the object it exists to protect.
        """
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
            outcome = self.fetch(key, os.path.join(cache_dir, base))
            if outcome == "unknown":
                raise MemoryUnavailable(f"could not read {key} from the memory store")
            if outcome == "found":
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


class LockUnavailable(Exception):
    """The lock's held/free state could not be determined -- never guessed (same discipline
    as MemoryUnavailable). A lock this process cannot confirm is free is not one it should
    treat as free."""


class SourceLock:
    """Cross-machine mutual exclusion for one jurisdiction's collection (OPEN-187), backed by
    S3 conditional writes rather than run-scrape.sh's local `mkdir` (OPEN-154) -- a directory
    on one machine's /tmp is invisible to a Fargate task and vice versa, so the two runners
    coexisting (OPEN-201) silently stopped protecting against a double collection the moment
    either one could run somewhere the other couldn't see.

    Keyed on SOURCE ALONE, not the scrape key -- matching OPEN-154's own reasoning exactly:
    the hazard is the shared data directory openstates-core wipes at scrape start, and FL's
    eight sessions share one, so a per-scrape-key lock would let them race each other.

    `suffix` (default `_lock`) is what OPEN-190's loader overrides to `_import_lock` when
    reusing this same class for the cross-machine IMPORT lock -- exactly the reuse this
    class's own key-binding comment above anticipated. It must produce
    `f"{prefix}/{key}/_import_lock"` to land on the identical S3 object
    `scraper_memory_import_lock_key` (scraper-memory.sh, OPEN-203) computes for the same
    jurisdiction's import, since a mac-side `run-scrape.sh` import and a cloud-side loader
    import only exclude each other if both name the same key.

    Age-based expiry only, not liveness. run-scrape.sh's local lock can ask the OS "is this
    pid still alive" (`kill -0`) because a dead local process and a live one are both visible
    to it; nothing here is comparably checkable across a Mac and a Fargate task, so "the
    holder is gone" can only ever mean "past its own stated expiry". LOCK_TTL_SECONDS matches
    the local lock's existing 24h dead-holder threshold for the same reason it was chosen
    there: deliberately far longer than any real scrape (MA's full walk measured 8.2h) so
    reclaiming can only ever fire on a genuinely abandoned lock, never a slow, healthy one.

    Release marks the lock immediately expired rather than deleting it, so this never needs
    s3:DeleteObject at all -- the next acquire() sees an expired lock and reclaims it exactly
    as it would after a real timeout. A release that fails to land (a dead network on the way
    out, say) costs nothing beyond the lock living out its TTL, the same outcome as today's
    genuinely-abandoned case.
    """

    LOCK_TTL_SECONDS = 24 * 60 * 60

    def __init__(self, client, bucket, prefix, holder, suffix="_lock"):
        self.client = client
        self.bucket = bucket
        self.prefix = prefix
        self.holder = holder
        self.suffix = suffix
        # Set together, only on a successful acquire/reclaim, and checked together in
        # release() -- a second pm-review round on this same design (in scraper-memory.sh,
        # its bash counterpart) caught that an etag alone is not bound to which key it was
        # acquired for. Not yet reachable through this class's own current caller (main()
        # constructs one SourceLock per run and always acquires/releases the same source), but
        # OPEN-203 is expected to reuse this exact class for an import lock, and a caller that
        # acquires one lock, then attempts (and fails) to acquire a second, must not have the
        # second's release silently reuse the first's leftover etag.
        #
        # One held lock at a time per instance -- a SUCCESSFUL second acquire (a different key,
        # or the same one renewed) still replaces this tracking, by design: this class does not
        # support one instance holding two locks concurrently. A caller needing two concurrent
        # locks (a scrape lock and an import lock, say) uses two instances, each with its own
        # independent _key/_etag -- not one instance juggling both.
        self._key = None
        self._etag = None

    def key(self, source):
        return f"{self.prefix}/{source}/{self.suffix}"

    def _lock_body(self, now):
        return json.dumps({
            "holder": self.holder,
            "acquired_at": now,
            "expires_at": now + self.LOCK_TTL_SECONDS,
        }).encode()

    def acquire(self, source):
        """True if acquired (including reclaiming a stale lock), False if another live holder
        has it. Raises LockUnavailable if the held/free state could not be determined at all
        (a credential problem, a timeout) -- distinct from False, which means "asked, and the
        answer was no"."""
        key = self.key(source)
        # pm-review round 3: an earlier version of this fix cleared _key/_etag unconditionally
        # here, reasoning that stale state should never survive into a new attempt. That was
        # an over-correction with its own real bug: a failed acquire(B) would wipe out a
        # still-valid, still-held lock A's state, leaving A unreleasable (and therefore alive
        # for its full 24h TTL) even though this process legitimately still holds it. Not
        # needed anyway -- _key/_etag are only ever written by a SUCCESSFUL put_object below,
        # so a failed attempt already leaves whatever this instance previously held
        # untouched, and release()'s own key-match check (not this clearing) is what actually
        # closes round 2's cross-key finding.
        for _attempt in range(2):
            now = time.time()
            try:
                resp = self.client.put_object(Bucket=self.bucket, Key=key,
                                               Body=self._lock_body(now), IfNoneMatch="*")
                self._key = key
                self._etag = resp["ETag"]
                return True
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") not in ("PreconditionFailed", "412"):
                    raise LockUnavailable(f"could not acquire {source}'s lock: {e}")

            try:
                existing = self.client.get_object(Bucket=self.bucket, Key=key)
                etag = existing["ETag"]
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if code in ("404", "NoSuchKey"):
                    continue  # raced a release/expiry between the PUT and this GET -- retry
                raise LockUnavailable(f"could not read {source}'s lock: {e}")

            # pm-review: a lock body this process cannot parse at all (malformed, truncated,
            # or some future shape neither client writes today) must not be treated as "not
            # live" and reclaimed -- json.JSONDecodeError/AttributeError/TypeError (and, for
            # invalid UTF-8 bytes specifically, UnicodeDecodeError -- a second pm-review round
            # caught this one wasn't covered) are not ClientErrors, so without this they would
            # propagate as a raw, uncaught exception out of acquire() entirely, past the
            # LockUnavailable handling in main() and past contract SS2's "every setup failure
            # still emits a completion record" guarantee.
            try:
                data = json.loads(existing["Body"].read())
                expires_at = data["expires_at"]
                is_live = now <= expires_at
            except (json.JSONDecodeError, KeyError, TypeError, AttributeError,
                     UnicodeDecodeError) as e:
                raise LockUnavailable(f"could not parse {source}'s lock contents: {e}")

            if is_live:
                return False  # a live holder

            try:
                resp = self.client.put_object(Bucket=self.bucket, Key=key,
                                               Body=self._lock_body(now), IfMatch=etag)
                self._key = key
                self._etag = resp["ETag"]
                return True
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") in ("PreconditionFailed", "412"):
                    return False  # someone else reclaimed it first
                raise LockUnavailable(f"could not reclaim {source}'s lock: {e}")
        return False

    def release(self, source):
        """Refuses unless self._key matches this call's key -- a caller that acquired one
        lock, then attempted (and failed) a second, must not have the second's release
        silently reuse the first's leftover etag against the wrong key. See __init__."""
        key = self.key(source)
        if self._etag is None or self._key != key:
            return
        try:
            now = time.time()
            body = json.dumps({
                "holder": self.holder, "acquired_at": now, "expires_at": now - 1,
            }).encode()
            self.client.put_object(Bucket=self.bucket, Key=key, Body=body, IfMatch=self._etag)
        except ClientError:
            pass
        self._key = None
        self._etag = None


def scrape_output_shows_unreachable_site(output_path):
    """Shells out to import-summary.sh's own matcher rather than re-deriving the marker list
    in Python -- PLAN-scraper-execution-migration.md's rule 1: a judgement call lives in one
    place, sourced, not copied twice where it can drift.

    pm-review's point stands and is only partially answered here: a missing bash, a missing
    or broken import-summary.sh, and a genuine "no marker found" all produce the same nonzero
    exit from this `&&` chain. Fully distinguishing them needs a change to import-summary.sh's
    own contract (a distinct exit code for "could not even check"), which is out of scope for
    this PR -- that file is shared with run-scrape.sh and changing its contract belongs with
    whoever owns it. The proportionate fix here is to stop swallowing the difference silently:
    surface stderr when the exit was nonzero, so a broken environment is visible in the log
    even though it is still classified as "not unreachable" today.
    """
    result = subprocess.run(
        ["bash", "-c", 'source "$1"/import-summary.sh && scrape_output_shows_unreachable_site "$2"',
         "_", str(REPO_ROOT), output_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and result.stderr.strip():
        print(f"WARNING: unreachable-site check exited {result.returncode}: {result.stderr.strip()}",
              file=sys.stderr)
    return result.returncode == 0


def _scrape_output_shows_no_op(output_path):
    """OPEN-244/OPEN-152: 'no objects returned from' is what openstates-core raises whenever a
    scraper yields nothing at all, which covers both "nothing changed since the incremental
    cutoff" (benign) and "the site could not be read" (a real failure) -- so this alone is
    necessary but not sufficient to call a run a no-op. The caller must also confirm
    scrape_output_shows_unreachable_site() is False first, exactly mirroring run-scrape.sh's
    own precedence (run-scrape.sh:1030-1039) -- that ordering is what OPEN-152 exists to
    enforce, after a WAF-blocked MI run once recorded `ok:0:0:0` and silently advanced its
    watermark past a window it never actually examined."""
    with open(output_path, encoding="utf-8", errors="replace") as f:
        return "no objects returned from" in f.read()


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


def _incremental_start_arg(ts_path):
    """Reads a hydrated `.ts` file and returns a `start=<cutoff>` scrape parameter, exactly as
    run-scrape.sh derives INCREMENTAL_FLAG (run-scrape.sh:235-245) -- one hour before the
    recorded watermark, same format, same one-hour overlap. Returns None if the file is absent
    or unparsable, in which case the caller falls back to a full run rather than guessing.
    """
    import datetime

    if not os.path.isfile(ts_path):
        return None
    try:
        last_run = open(ts_path).read().strip()
        dt = datetime.datetime.strptime(last_run, "%Y-%m-%dT%H:%M:%S")
        start = (dt - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        return f"start={start}"
    except Exception:
        return None


def derive_scrape_key(source, params):
    """Distinguishes different scrape targets that share one jurisdiction so their watermarks
    and OPEN-203 import locks never collide -- found missing during OPEN-191's Fargate
    rehearsal (2026-08-29/30): USA's `session=119 chamber=lower` and `session=119 chamber=upper`
    both derived the bare `usa_119` key (session-only), so upper silently hydrated lower's
    watermark and ran "incremental" against a cutoff from a chamber it had never actually
    collected, producing zero objects and a hard `ScrapeError`. run-scrape.sh's own SCRAPE_KEY
    (run-scrape.sh:82) already folds every key=value param into the key for exactly this reason.

    Backward compatible with every key already persisted in S3: a single `session` param with
    nothing else still derives the existing `{source}_{session}` form (e.g. `fl_2026`), and no
    params at all still derives bare `source` -- neither format changes here.
    """
    session = params.get("session")
    extra = {k: v for k, v in params.items() if k != "session"}
    if not session and not extra:
        return source
    parts = [source]
    if session:
        parts.append(session)
    parts.extend(v for _, v in sorted(extra.items()))
    return "_".join(parts)


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
    scrape_key = derive_scrape_key(source, params)

    try:
        bucket = os.environ["MEMORY_BUCKET"]
    except KeyError:
        print("ERROR: MEMORY_BUCKET is required", file=sys.stderr)
        emit_completion_record(status="failed", mode="full", source=source, run_id=run_id,
                                session=session)
        return 1

    client = s3_client or boto3.client("s3")
    prefix = os.environ.get("MEMORY_PREFIX", "")
    try:
        memory = S3Memory(client, bucket, prefix)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        emit_completion_record(status="failed", mode="full", source=source, run_id=run_id,
                                session=session)
        return 1

    # OPEN-187: acquired before anything else touches memory or the source site, released in
    # `finally` regardless of how _collect() exits. Keyed on `source` alone, matching
    # run-scrape.sh's local lock (OPEN-154) -- see SourceLock's own docstring for why.
    lock = SourceLock(client, bucket, prefix, holder=run_id)
    try:
        acquired = lock.acquire(source)
    except LockUnavailable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        emit_completion_record(status="failed", mode="full", source=source, run_id=run_id,
                                session=session)
        touch_do_not_retry()
        return EXIT_DO_NOT_RETRY
    if not acquired:
        # Same classification run-scrape.sh's local lock uses for the identical situation
        # (OPEN-154): `failed`, not `unreachable` -- the source was never asked -- and
        # EXIT_DO_NOT_RETRY so a retrying wrapper does not collide again on every attempt.
        print(f"ERROR: another run of {source} already holds the lock -- refusing to start "
              f"a second one (OPEN-187)", file=sys.stderr)
        emit_completion_record(status="failed", mode="full", source=source, run_id=run_id,
                                session=session)
        touch_do_not_retry()
        return EXIT_DO_NOT_RETRY

    # pm-review: every setup/publish failure must still leave a completion record, matching
    # run-scrape.sh's EXIT-trap guarantee (contract SS2 -- "no record" is reserved for the
    # runner dying outright, not an ordinary exception this process could have reported).
    # A bare `except Exception` at the top level is the Python analogue of that trap: it can
    # only fire once, after which the crash is re-raised so the exit code still reflects it.
    try:
        try:
            return _collect(source, scrape_key, session, params, run_id, started, memory)
        except Exception:
            print(f"ERROR: unhandled exception during {source} collection", file=sys.stderr)
            emit_completion_record(status="failed", mode="full", source=source, run_id=run_id,
                                    session=session)
            raise
    finally:
        lock.release(source)


def _collect(source, scrape_key, session, params, run_id, started, memory):
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

                # OPEN-188: a bare run (no usable published cookie) must be impossible by
                # construction, not convention -- exactly what produced the block and the
                # laundered "measured zero" on 2026-08-24 (OPEN-152/OPEN-153). Refuses loudly
                # on anything short of a fresh, parsed cookie file, rather than falling
                # through to a local mint attempt (this runner deliberately never mints its
                # own -- see _MI_WAF_COOKIE_GLOB's own comment) or proceeding cookie-less.
                cookie_fetched = memory.hydrate_cache(source, cache_dir, _MI_WAF_COOKIE_GLOB)
                if not cookie_fetched or not _mi_waf_cookies_are_fresh(
                    cache_dir, _MI_WAF_COOKIE_GLOB, time.time(),
                    _MI_WAF_COOKIE_MIN_FRESHNESS_SECONDS,
                ):
                    print(
                        "ERROR: no fresh published Michigan WAF cookie in the memory store "
                        "-- refusing to attempt a bare run (OPEN-188)",
                        file=sys.stderr,
                    )
                    # `failed`, not `unreachable`: the source was never asked. Retryable
                    # (no touch_do_not_retry/EXIT_DO_NOT_RETRY) -- unlike the baseline case
                    # above, this is expected to self-heal at the mac's own next scheduled
                    # publish tick (mi_cookie_publish.py, default every 6h), not something an
                    # operator has to intervene on.
                    emit_completion_record(status="failed", mode="full", source=source,
                                            run_id=run_id, session=session)
                    return 1

            found_watermark = memory.hydrate_markers(source, scrape_key, last_run_dir)
        except MemoryUnavailable as e:
            print(f"ERROR: {e} -- refusing to run rather than assuming a first-ever run "
                  f"(OPEN-181/contract SS4)", file=sys.stderr)
            emit_completion_record(status="failed", mode="full", source=source, run_id=run_id,
                                    session=session)
            return 1

        mode = "incremental" if found_watermark else "full"

        # pm-review: a hydrated `.imported` describes what the LAST *import* did. This runner
        # never imports, so it has nothing new to say about it -- carrying the stale file
        # forward and republishing it below would leave next run's `.imported` describing a
        # collection it has no relationship to. Drop it; the load step (OPEN-190/203) is what
        # writes the next real one.
        stale_imported = os.path.join(last_run_dir, f"{scrape_key}.imported")
        if os.path.isfile(stale_imported):
            os.remove(stale_imported)

        # pm-review's most substantive finding: the hydrated watermark was never actually
        # handed to the scraper, so "incremental" was a label with no effect. Mirrors
        # run-scrape.sh's own derivation (run-scrape.sh:233-245) exactly -- one hour of
        # overlap, same format -- via the *hydrated* `.ts` this process just fetched, not a
        # local file left over from some other run.
        start_arg = _incremental_start_arg(os.path.join(last_run_dir, f"{scrape_key}.ts"))

        os.makedirs(cache_dir, exist_ok=True)
        out_dir = os.path.join(staging, "scraped")
        os.makedirs(out_dir, exist_ok=True)
        scrape_output = os.path.join(staging, "scrape_output.log")

        cmd = [os.environ.get("OS_UPDATE", "os-update"), source, "--scrape", "bills"]
        for k, v in params.items():
            cmd.append(f"{k}={v}")
        if start_arg:
            cmd.append(start_arg)
        # --cachedir is what makes Michigan's hydrated baseline reachable by mi/bills.py
        # itself (run-scrape.sh's own DIR_FLAGS, run-scrape.sh:512) -- without it the baseline
        # this function just fetched from S3 sits in a directory the scraper never looks in.
        cmd += ["--cachedir", cache_dir, "--datadir", out_dir]

        # --cachedir alone does NOT make the hydrated mi_waf_cookies.json reachable by
        # MI_COOKIE_PROVIDER: that's a module-level singleton in openstates-core's
        # mi_cookies.py built as `CookieProvider(cache_path=os.path.join(settings.CACHE_DIR,
        # ...))` at *import* time, and that import happens (via get_jurisdiction()) before
        # update.py's own override_settings() context manager ever applies --cachedir's value
        # to settings.CACHE_DIR. By the time the override lands, the singleton's cache_path is
        # already baked in against the old value. settings.py's CACHE_DIR, in turn, is seeded
        # from the CACHE_DIR *environment* variable at settings-module import time -- so
        # setting it in the subprocess's own environment (rather than relying on --cachedir)
        # is what actually reaches the singleton before it's constructed. Found by tracing
        # through cookie_provider.py -> mi_cookies.py -> update.py's override_settings/
        # get_jurisdiction ordering after a real run showed _read_cache() missing a cookie
        # file that was hydrated to the right directory on disk.
        scrape_env = dict(os.environ, CACHE_DIR=cache_dir)

        # Streamed line-by-line to stderr as it's produced, not buffered to a file and only
        # printed afterward. A buffer-then-print (even one printed unconditionally rather than
        # only on failure) is still invisible to CloudWatch for a run an operator has to
        # `ecs stop-task`: SIGTERM has no handler here, so the process dies inside
        # subprocess.run() before any code after it ever executes, and everything the scraper
        # had already logged is lost with the container. Found the hard way twice in one
        # session -- once on a run that succeeded quietly (the MI cookie test: nothing but the
        # final completion record, no way to see whether the cache was actually read), once on
        # a run that had to be killed after running far longer than expected (no evidence of
        # what it had been doing at all). Streaming means whatever ran before a kill already
        # reached CloudWatch, since the awslogs driver ships stdout/stderr continuously rather
        # than only at container exit.
        with open(scrape_output, "w") as f:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     env=scrape_env, text=True, bufsize=1)
            for line in proc.stdout:
                f.write(line)
                print(line, end="", file=sys.stderr)
            proc.wait()

        duration_s = int(time.time() - started)

        if proc.returncode != 0 and scrape_output_shows_unreachable_site(scrape_output):
            # OPEN-53: retrying a block makes it worse. Terminal, not retryable.
            print(f"ERROR: {source} appears unreachable", file=sys.stderr)
            emit_completion_record(status="unreachable", mode=mode, source=source,
                                    run_id=run_id, session=session, duration_s=duration_s)
            touch_do_not_retry()
            return EXIT_DO_NOT_RETRY

        # OPEN-244: mirrors run-scrape.sh's finish_no_op() (run-scrape.sh:841-870, invoked at
        # run-scrape.sh:1030-1039). An incremental run whose scraper output shows "no objects
        # returned from" -- once the unreachable check above has already ruled out a WAF
        # block/site-down masquerading as the same message -- is a genuine, benign no-op:
        # nothing changed since the watermark, not a failure to collect. Watermark and count
        # still advance and memory still persists, exactly as a successful found=0 run would,
        # so the next incremental run doesn't re-collect a window this one already covered
        # (OPEN-181's "memory advances on every successful run" requirement).
        if proc.returncode != 0 and mode == "incremental" and _scrape_output_shows_no_op(scrape_output):
            print(f"{source}: no new objects since cutoff (no-op)", file=sys.stderr)
            with open(os.path.join(last_run_dir, f"{scrape_key}.ts"), "w") as f:
                f.write(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))
            with open(os.path.join(last_run_dir, f"{scrape_key}.count"), "w") as f:
                f.write(f"0:{mode}")
            memory.persist_markers(source, scrape_key, last_run_dir)

            # OPEN-245: cloud_loader.py (OPEN-190) treats the ABSENCE of a manifest as "this
            # run never finished" and refuses to load -- correct for a genuinely missing run,
            # wrong for a no-op that legitimately has nothing to load. Before this fix, a no-op
            # exited 1 here, so run_cloud_scrape() never even reached the load step; now it
            # exits 0, so the loader needs its own authorizing signal. Publishing an
            # empty-objects manifest, in the exact same shape/location the success path below
            # writes, gives it that signal for free: cloud_loader.py's existing
            # _validate_manifest()/_fetch_run_objects() already handle an empty `objects` list
            # cleanly, and os-update --import against an empty --datadir already imports zero
            # bills and exits 0 (confirmed against openstates-core: import_directory() globs
            # for files and import_data() with an empty iterable just returns a zeroed report).
            work_prefix = os.environ.get("WORKING_TIER_PREFIX", "working-tier")
            marker_path = os.path.join(staging, "manifest.json")
            with open(marker_path, "w") as f:
                json.dump({"run_id": run_id, "source": source, "objects": []}, f)
            memory.store(marker_path, f"{work_prefix}/{source}/{run_id}/_manifest.json")

            emit_completion_record(status="ok", mode=mode, source=source, run_id=run_id,
                                    session=session, found=0, duration_s=duration_s)
            return 0

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

        # Memory published BEFORE the completion marker -- reordered per pm-review. The marker
        # is what OPEN-190's loader treats as authorising a load; if it were visible before
        # memory finished publishing and persist_markers then failed, a loader could load this
        # run while the NEXT collection still starts from the old watermark (full, not
        # incremental) -- disagreeing with what was actually loaded. Cache-resident memory
        # first, watermark last, exactly as scraper-memory.sh established.
        memory.persist_cache(source, cache_dir, _MI_BASELINE_GLOB)
        memory.persist_markers(source, scrape_key, last_run_dir)

        # The completion marker, written LAST of all, after every object it names -- including
        # memory -- is durable (PLAN-scraper-execution-migration.md SS3, "the handoff
        # contract"). A marker visible before that is incomplete, not small.
        marker_path = os.path.join(staging, "manifest.json")
        with open(marker_path, "w") as f:
            json.dump({"run_id": run_id, "source": source, "objects": manifest}, f)
        memory.store(marker_path, f"{work_prefix}/{source}/{run_id}/_manifest.json")

        emit_completion_record(status="ok", mode=mode, source=source, run_id=run_id,
                                session=session, found=found, duration_s=duration_s)
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
