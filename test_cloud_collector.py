"""
Tests for cloud_collector.py (OPEN-201).

Uses a small in-memory fake S3 client rather than botocore.stub.Stubber, because S3Memory
calls the high-level `download_file`/`upload_file`/`get_paginator` methods (for the same
multipart-transfer behaviour production traffic gets), and Stubber operates one level lower,
against the raw `get_object`/`put_object` operations those methods dispatch to internally --
matching it there would test botocore's plumbing, not this file's logic. A fake client keeps
these tests fast, dependency-free (no moto), and focused on the three-way-read/ordered-write
properties OPEN-201's acceptance criteria actually name.
"""

import json
import os
import stat
import sys
import time

import pytest
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.dirname(__file__))
import cloud_collector as cc


class FakeS3Client:
    """In-memory stand-in for boto3's S3 client. Raises the same ClientError shapes real S3
    does for a missing key, so S3Memory's three-way matching is exercised for real."""

    def __init__(self):
        self.objects = {}  # key -> bytes
        self.etags = {}  # key -> etag, for put_object/get_object's conditional-write emulation
        self.put_calls = []  # keys, in call order -- what the ordering tests assert on
        self._etag_counter = 0

    def download_file(self, bucket, key, dest):
        if key not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        with open(dest, "wb") as f:
            f.write(self.objects[key])

    def upload_file(self, local_path, bucket, key):
        with open(local_path, "rb") as f:
            self.objects[key] = f.read()
        self.put_calls.append(key)

    def put_object(self, Bucket, Key, Body, IfNoneMatch=None, IfMatch=None):
        """SourceLock's conditional writes -- real S3 semantics, not a stand-in for
        upload_file: IfNoneMatch="*" rejects an existing key, IfMatch rejects a stale one."""
        if IfNoneMatch == "*" and Key in self.objects:
            raise ClientError(
                {"Error": {"Code": "PreconditionFailed", "Message": "At least one of the "
                                                                      "pre-conditions you specified did not hold"}},
                "PutObject")
        if IfMatch is not None and self.etags.get(Key) != IfMatch:
            raise ClientError(
                {"Error": {"Code": "PreconditionFailed", "Message": "At least one of the "
                                                                      "pre-conditions you specified did not hold"}},
                "PutObject")
        self._etag_counter += 1
        etag = f'"fake-etag-{self._etag_counter}"'
        self.objects[Key] = Body if isinstance(Body, bytes) else Body.encode()
        self.etags[Key] = etag
        self.put_calls.append(Key)
        return {"ETag": etag}

    def get_object(self, Bucket, Key):
        import io
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}, "GetObject")
        return {"Body": io.BytesIO(self.objects[Key]), "ETag": self.etags[Key]}

    def get_paginator(self, op_name):
        assert op_name == "list_objects_v2"
        client = self

        class _Paginator:
            def paginate(self, Bucket, Prefix):
                keys = [k for k in client.objects if k.startswith(Prefix)]
                yield {"Contents": [{"Key": k} for k in keys]}

        return _Paginator()


class FlakyS3Client(FakeS3Client):
    """Raises an error that is NOT a 404/NoSuchKey shape -- the "could not tell" case."""

    def download_file(self, bucket, key, dest):
        raise ClientError({"Error": {"Code": "500", "Message": "Internal Error"}}, "HeadObject")

    def get_paginator(self, op_name):
        raise ClientError({"Error": {"Code": "500", "Message": "Internal Error"}}, "ListObjectsV2")


# ── S3Memory: the three-way read ─────────────────────────────────────────────────────────────

def test_fetch_absent_is_not_confused_with_unknown(tmp_path):
    mem = cc.S3Memory(FakeS3Client(), "bucket", "dev-open201")
    assert mem.fetch("prefix/nope", str(tmp_path / "out")) == "absent"


def test_fetch_found_round_trips_bytes(tmp_path):
    client = FakeS3Client()
    client.objects["dev-open201/mi/mi.ts"] = b"2026-08-28T00:00:00"
    mem = cc.S3Memory(client, "bucket", "dev-open201")
    dest = str(tmp_path / "mi.ts")
    assert mem.fetch("dev-open201/mi/mi.ts", dest) == "found"
    assert open(dest, "rb").read() == b"2026-08-28T00:00:00"


def test_fetch_unreadable_store_is_unknown_not_absent(tmp_path):
    """The OPEN-152 property: a store that did not answer must never look like an empty one."""
    mem = cc.S3Memory(FlakyS3Client(), "bucket", "dev-open201")
    assert mem.fetch("dev-open201/mi/mi.ts", str(tmp_path / "out")) == "unknown"


def test_empty_prefix_is_refused_at_construction():
    with pytest.raises(ValueError):
        cc.S3Memory(FakeS3Client(), "bucket", "")


def test_hydrate_markers_raises_on_unknown_rather_than_treating_absent(tmp_path):
    mem = cc.S3Memory(FlakyS3Client(), "bucket", "dev-open201")
    with pytest.raises(cc.MemoryUnavailable):
        mem.hydrate_markers("mi", "mi", str(tmp_path))


def test_hydrate_markers_absent_is_a_clean_full_run(tmp_path):
    mem = cc.S3Memory(FakeS3Client(), "bucket", "dev-open201")
    found = mem.hydrate_markers("ut", "ut_session_2025S2", str(tmp_path))
    assert found is False


# ── Publish ordering -- the safety property scraper-memory.sh established ──────────────────────

def test_persist_markers_writes_watermark_last(tmp_path):
    client = FakeS3Client()
    mem = cc.S3Memory(client, "bucket", "dev-open201")
    for name in ("ut_session.count", "ut_session.imported", "ut_session.ts"):
        (tmp_path / name).write_text("x")
    mem.persist_markers("ut", "ut_session", str(tmp_path))
    assert client.put_calls[-1].endswith(".ts"), (
        "the watermark must be the last object published -- a partial publish must never "
        "leave a fresh cutoff sitting beside stale reporting markers"
    )


def test_hydrate_cache_only_fetches_matching_glob(tmp_path):
    client = FakeS3Client()
    client.objects["dev-open201/mi/_cache/mi_last_actions_2025-2026.json"] = b"[]"
    client.objects["dev-open201/mi/_cache/unrelated.txt"] = b"ignore me"
    mem = cc.S3Memory(client, "bucket", "dev-open201")
    fetched = mem.hydrate_cache("mi", str(tmp_path), "mi_last_actions_*.json")
    assert fetched == ["mi_last_actions_2025-2026.json"]
    assert not (tmp_path / "unrelated.txt").exists()


# ── The unreachable-site matcher -- sourced from import-summary.sh, not reimplemented ──────────

def test_unreachable_matcher_fires_on_waf_marker(tmp_path):
    out = tmp_path / "scrape_output.log"
    out.write_text("some ordinary log line\nWAF block detected on request 3\n")
    assert cc.scrape_output_shows_unreachable_site(str(out)) is True


def test_unreachable_matcher_does_not_fire_on_ordinary_output(tmp_path):
    out = tmp_path / "scrape_output.log"
    out.write_text("scraped 5 bills\nno objects returned from BillScraper\n")
    assert cc.scrape_output_shows_unreachable_site(str(out)) is False


def test_unreachable_matcher_respects_negation(tmp_path):
    out = tmp_path / "scrape_output.log"
    out.write_text("no WAF block detected this run\n")
    assert cc.scrape_output_shows_unreachable_site(str(out)) is False


# ── main(): the end-to-end paths ────────────────────────────────────────────────────────────

def _fake_os_update(tmp_path, *, exit_code=0, stderr_text="", bill_files=1, argv_file=None):
    """A stand-in for the real os-update binary, matching run-scrape.sh's own
    OS_UPDATE_OVERRIDE convention for driving this script without the real toolchain.

    When `argv_file` is given, records the exact argv this invocation received -- one per
    line -- so a test can assert on the command cloud_collector actually built rather than
    only on its externally-visible effects.
    """
    script = tmp_path / "fake_os_update.sh"
    lines = ["#!/usr/bin/env bash", "set -e"]
    if argv_file:
        lines.append(f'printf "%s\\n" "$@" > {str(argv_file)!r}')
    if stderr_text:
        lines.append(f"echo {stderr_text!r} 1>&2")
    # `--datadir DIR` is always the last two arguments in cloud_collector's invocation.
    # `${!#}` (indirect expansion on $#) rather than `${@: -1}` -- LESSONS.md SS7: this Mac's
    # bash is 3.2.57 and negative-offset parameter slicing needs bash 4.3+.
    lines.append('DATADIR="${!#}"')
    lines.append("mkdir -p \"$DATADIR/bills\"")
    for i in range(bill_files):
        lines.append(f'echo "{{}}" > "$DATADIR/bills/bill_{i}.json"')
    lines.append(f"exit {exit_code}")
    script.write_text("\n".join(lines) + "\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


def test_main_full_run_ok(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, bill_files=3))
    client = FakeS3Client()

    rc = cc.main(["ut", "session=2025S2"], s3_client=client)
    assert rc == 0

    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "ok"
    assert record["mode"] == "full"
    assert record["found"] == 3
    assert "new" not in record and "updated" not in record and "noop" not in record

    manifest_key = [k for k in client.put_calls if k.endswith("_manifest.json")]
    assert manifest_key, "a successful run must publish a completion marker"
    watermark_keys = [k for k in client.put_calls if k.endswith(".ts")]
    assert watermark_keys, "a successful run must publish its watermark"


def test_main_second_run_is_incremental(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    argv_file = tmp_path / "argv.txt"
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, bill_files=1, argv_file=argv_file))
    client = FakeS3Client()
    client.objects["dev-open201/ut/ut_2025S2/ut_2025S2.ts"] = b"2026-08-28T00:00:00"

    rc = cc.main(["ut", "session=2025S2"], s3_client=client)
    assert rc == 0
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["mode"] == "incremental"

    # pm-review: an "incremental" label with no effect on the scraper is not incremental --
    # confirm the actual argv includes both the derived start= cutoff and a --cachedir so
    # mi/bills.py-style per-jurisdiction cache reads have somewhere real to look.
    argv = argv_file.read_text().splitlines()
    assert any(a.startswith("start=2026-08-27T23:00:00") for a in argv), argv
    assert "--cachedir" in argv, argv


def test_main_mode_requires_ts_specifically_not_any_marker(tmp_path, monkeypatch, capsys):
    """pm-review's sharpest correctness finding: a `.count` present without a `.ts` must
    still be a full run. `.ts` is published last precisely so a partial publish leaves it
    absent -- reading "any marker present" as "incremental" defeats that on the way back in.
    """
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, bill_files=1))
    client = FakeS3Client()
    # .count and .imported exist (a prior partial publish); .ts does not.
    client.objects["dev-open201/ut/ut_2025S2/ut_2025S2.count"] = b"5:full"
    client.objects["dev-open201/ut/ut_2025S2/ut_2025S2.imported"] = b"ok:5:0:0:full"

    rc = cc.main(["ut", "session=2025S2"], s3_client=client)
    assert rc == 0
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["mode"] == "full"


def test_main_drops_stale_imported_marker_from_a_collect_only_run(tmp_path, monkeypatch):
    """A collect-only run must never republish someone else's `.imported` -- it describes a
    LOAD outcome this runner did not produce."""
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, bill_files=1))
    client = FakeS3Client()
    client.objects["dev-open201/ut/ut_2025S2/ut_2025S2.imported"] = b"ok:1:0:0:full"

    rc = cc.main(["ut", "session=2025S2"], s3_client=client)
    assert rc == 0
    assert not any(k.endswith(".imported") for k in client.put_calls), client.put_calls


def test_main_michigan_baseline_vanishing_between_list_and_fetch_still_refuses(tmp_path, monkeypatch, capsys):
    """pm-review's race: the object is listed but gone by download time. Must refuse exactly
    as if it had never been listed at all -- not treated as present."""
    class VanishingClient(FakeS3Client):
        def download_file(self, bucket, key, dest):
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "GetObject")

    client = VanishingClient()
    client.objects["dev-open201/mi/_cache/mi_last_actions_2025-2026.json"] = b"[]"
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path))

    rc = cc.main(["mi"], s3_client=client)

    assert rc == cc.EXIT_DO_NOT_RETRY
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"


def test_main_manifest_not_published_if_memory_persist_fails(tmp_path, monkeypatch):
    """The completion marker must not become visible while memory publication can still
    fail -- pm-review's ordering finding. A loader must never see a run as complete while
    the watermark that run should have advanced might not have."""
    class FailsOnWatermark(FakeS3Client):
        def upload_file(self, local_path, bucket, key):
            if key.endswith(".ts"):
                raise RuntimeError("simulated S3 outage")
            super().upload_file(local_path, bucket, key)

    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, bill_files=1))
    client = FailsOnWatermark()

    with pytest.raises(RuntimeError):
        cc.main(["ut", "session=2025S2"], s3_client=client)

    assert not any(k.endswith("_manifest.json") for k in client.put_calls), (
        "a run whose watermark failed to publish must not leave a completion marker behind"
    )


def test_main_unexpected_exception_still_emits_a_completion_record(tmp_path, monkeypatch, capsys):
    """Contract SS2: only a killed process may emit no record at all. An unhandled exception
    with no more specific handler -- here, an upload failure for the raw scraped output,
    which nothing in _collect wraps -- must still report `failed` before it propagates."""
    class ExplodesOnUpload(FakeS3Client):
        def upload_file(self, local_path, bucket, key):
            raise RuntimeError("boom")

    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, bill_files=1))

    with pytest.raises(RuntimeError):
        cc.main(["ut", "session=2025S2"], s3_client=ExplodesOnUpload())

    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"


def test_main_michigan_refuses_without_baseline(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path))
    flag = tmp_path / "do-not-retry"
    monkeypatch.setenv("DO_NOT_RETRY_FLAG", str(flag))

    rc = cc.main(["mi"], s3_client=FakeS3Client())

    assert rc == cc.EXIT_DO_NOT_RETRY
    assert flag.exists(), "a refusal to run must signal do-not-retry, not just a nonzero exit"
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"


def _fresh_mi_cookie_body(now=None, expires_in=7200):
    now = now if now is not None else time.time()
    return json.dumps({
        "x-bni-fpc": {"value": "fake-cookie-value", "expires": now + expires_in},
        "_meta": {"user_agent": "fake-ua"},
    }).encode()


def test_main_michigan_proceeds_with_baseline_and_fresh_cookie_present(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, bill_files=2))
    client = FakeS3Client()
    client.objects["dev-open201/mi/_cache/mi_last_actions_2025-2026.json"] = b"[]"
    client.objects["dev-open201/mi/_cache/mi_waf_cookies.json"] = _fresh_mi_cookie_body()

    rc = cc.main(["mi"], s3_client=client)
    assert rc == 0
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "ok"


def test_main_michigan_refuses_without_a_published_cookie(tmp_path, monkeypatch, capsys):
    """OPEN-188: a bare run (baseline present, but no published cookie at all) must be
    impossible by construction -- exactly the OPEN-152/153 mistake."""
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path))
    client = FakeS3Client()
    client.objects["dev-open201/mi/_cache/mi_last_actions_2025-2026.json"] = b"[]"
    # deliberately no mi_waf_cookies.json object at all

    rc = cc.main(["mi"], s3_client=client)

    assert rc == 1
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"


def test_main_michigan_refuses_with_a_stale_cookie(tmp_path, monkeypatch, capsys):
    """A cookie that technically parses but is expired (or expiring within the freshness
    floor) must refuse exactly as if it were missing -- OPEN-188's "stale beyond threshold"
    criterion."""
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path))
    client = FakeS3Client()
    client.objects["dev-open201/mi/_cache/mi_last_actions_2025-2026.json"] = b"[]"
    client.objects["dev-open201/mi/_cache/mi_waf_cookies.json"] = _fresh_mi_cookie_body(
        expires_in=-60  # already expired
    )

    rc = cc.main(["mi"], s3_client=client)

    assert rc == 1
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"


def test_main_michigan_refuses_with_an_unparsable_cookie_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path))
    client = FakeS3Client()
    client.objects["dev-open201/mi/_cache/mi_last_actions_2025-2026.json"] = b"[]"
    client.objects["dev-open201/mi/_cache/mi_waf_cookies.json"] = b"not json"

    rc = cc.main(["mi"], s3_client=client)

    assert rc == 1
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"


def test_main_michigan_cookie_refusal_is_retryable_not_do_not_retry(tmp_path, monkeypatch, capsys):
    """Unlike the missing-baseline case, a missing/stale cookie is expected to self-heal at
    the mac's own next scheduled publish tick -- it must NOT set the do-not-retry flag."""
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path))
    flag = tmp_path / "do-not-retry"
    monkeypatch.setenv("DO_NOT_RETRY_FLAG", str(flag))
    client = FakeS3Client()
    client.objects["dev-open201/mi/_cache/mi_last_actions_2025-2026.json"] = b"[]"

    rc = cc.main(["mi"], s3_client=client)

    assert rc == 1
    assert rc != cc.EXIT_DO_NOT_RETRY
    assert not flag.exists()


def test_mi_waf_cookies_are_fresh_rejects_empty_cookie_set(tmp_path):
    path = tmp_path / "mi_waf_cookies.json"
    path.write_text(json.dumps({"_meta": {"user_agent": "ua"}}))
    assert cc._mi_waf_cookies_are_fresh(str(tmp_path), "mi_waf_cookies.json", time.time(), 600) is False


def test_mi_waf_cookies_are_fresh_rejects_nan_expires(tmp_path):
    """pm-review: json.loads accepts the non-standard NaN literal, and float("nan") < x is
    always False -- so this must be checked explicitly rather than relying on the comparison
    alone to reject it."""
    path = tmp_path / "mi_waf_cookies.json"
    # json.dumps also emits NaN for float("nan") -- write the literal directly rather than
    # relying on that, so this test exercises exactly what a real (malformed) file looks like.
    path.write_text('{"x": {"value": "y", "expires": NaN}}')
    assert cc._mi_waf_cookies_are_fresh(str(tmp_path), "mi_waf_cookies.json", time.time(), 600) is False


def test_mi_waf_cookies_are_fresh_rejects_infinite_expires(tmp_path):
    path = tmp_path / "mi_waf_cookies.json"
    path.write_text('{"x": {"value": "y", "expires": Infinity}}')
    assert cc._mi_waf_cookies_are_fresh(str(tmp_path), "mi_waf_cookies.json", time.time(), 600) is False


def test_mi_waf_cookies_are_fresh_rejects_boolean_expires(tmp_path):
    """bool is a subclass of int in Python -- True/False must not be accepted as a numeric
    expires just because isinstance(x, (int, float)) is technically satisfied."""
    path = tmp_path / "mi_waf_cookies.json"
    path.write_text(json.dumps({"x": {"value": "y", "expires": True}}))
    assert cc._mi_waf_cookies_are_fresh(str(tmp_path), "mi_waf_cookies.json", time.time(), 600) is False


def test_mi_waf_cookies_are_fresh_accepts_a_genuinely_fresh_file(tmp_path):
    now = time.time()
    path = tmp_path / "mi_waf_cookies.json"
    path.write_bytes(_fresh_mi_cookie_body(now=now, expires_in=3600))
    assert cc._mi_waf_cookies_are_fresh(str(tmp_path), "mi_waf_cookies.json", now, 600) is True


def test_main_unreachable_site_is_terminal(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv(
        "OS_UPDATE",
        _fake_os_update(tmp_path, exit_code=1, stderr_text="WAF block detected"),
    )
    flag = tmp_path / "do-not-retry"
    monkeypatch.setenv("DO_NOT_RETRY_FLAG", str(flag))

    rc = cc.main(["mi_test"], s3_client=FakeS3Client())

    assert rc == cc.EXIT_DO_NOT_RETRY
    assert flag.exists()
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "unreachable"
    assert "found" not in record, "an unreachable run measured nothing and must not report a count"


def test_main_ordinary_failure_is_retryable(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, exit_code=1, stderr_text="Traceback (boom)"))

    rc = cc.main(["mi_test"], s3_client=FakeS3Client())

    assert rc == 1
    assert rc != cc.EXIT_DO_NOT_RETRY
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"


def test_main_rejects_malformed_params(capsys):
    rc = cc.main(["ut", "not-a-kv-pair"])
    assert rc == 1
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"


# --- SourceLock (OPEN-187) -----------------------------------------------------------------


def test_lock_acquire_then_second_attempt_is_refused():
    client = FakeS3Client()
    first = cc.SourceLock(client, "bucket", "dev-open187", holder="run-a")
    second = cc.SourceLock(client, "bucket", "dev-open187", holder="run-b")

    assert first.acquire("mi") is True
    assert second.acquire("mi") is False


def test_lock_released_lock_can_be_reacquired():
    client = FakeS3Client()
    first = cc.SourceLock(client, "bucket", "dev-open187", holder="run-a")
    second = cc.SourceLock(client, "bucket", "dev-open187", holder="run-b")

    assert first.acquire("mi") is True
    first.release("mi")
    assert second.acquire("mi") is True


def test_lock_stale_lock_is_reclaimed_not_refused():
    """A holder that died leaves its lock object exactly as it wrote it -- expires_at in the
    past is the only signal that distinguishes "abandoned" from "still running", since there
    is no pid to check across machines (SourceLock's own docstring)."""
    client = FakeS3Client()
    stale = json.dumps({"holder": "dead-run", "acquired_at": 0, "expires_at": 1}).encode()
    client.put_object(Bucket="bucket", Key="dev-open187/mi/_lock", Body=stale)

    lock = cc.SourceLock(client, "bucket", "dev-open187", holder="run-b")
    assert lock.acquire("mi") is True


def test_lock_live_lock_is_not_reclaimed():
    client = FakeS3Client()
    live = json.dumps({"holder": "live-run", "acquired_at": cc.time.time(),
                        "expires_at": cc.time.time() + 3600}).encode()
    client.put_object(Bucket="bucket", Key="dev-open187/mi/_lock", Body=live)

    lock = cc.SourceLock(client, "bucket", "dev-open187", holder="run-b")
    assert lock.acquire("mi") is False


def test_lock_keyed_on_source_not_scrape_key():
    """FL's eight sessions share one data directory -- OPEN-154's own reasoning for keying the
    local lock on $STATE rather than the scrape key applies identically here."""
    client = FakeS3Client()
    lock = cc.SourceLock(client, "bucket", "dev-open187", holder="run-a")
    assert lock.key("fl") == "dev-open187/fl/_lock"


def test_lock_unavailable_is_not_the_same_as_refused():
    """A credential/network problem must not be read as "someone else holds it" -- that would
    silently convert an S3 blip into every jurisdiction refusing to run at once."""
    class ExplodingClient(FakeS3Client):
        def put_object(self, **kwargs):
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "nope"}}, "PutObject")

    lock = cc.SourceLock(ExplodingClient(), "bucket", "dev-open187", holder="run-a")
    with pytest.raises(cc.LockUnavailable):
        lock.acquire("mi")


def test_lock_release_without_acquire_is_a_noop():
    client = FakeS3Client()
    cc.SourceLock(client, "bucket", "dev-open187", holder="run-a").release("mi")
    assert client.objects == {}


def test_lock_malformed_body_is_unavailable_not_reclaimed():
    """pm-review's finding: json.JSONDecodeError/TypeError are not ClientErrors, so without
    converting them, a lock body this process can't parse would propagate as a raw, uncaught
    exception out of acquire() -- past LockUnavailable's handling in main(), past contract
    SS2's "every setup failure still emits a completion record" guarantee -- rather than being
    treated as "could not tell", which is the only safe reading of a body it cannot verify as
    either live or expired."""
    client = FakeS3Client()
    client.put_object(Bucket="bucket", Key="dev-open187/mi/_lock", Body=b"not valid json")

    lock = cc.SourceLock(client, "bucket", "dev-open187", holder="run-a")
    with pytest.raises(cc.LockUnavailable):
        lock.acquire("mi")


def test_lock_leftover_etag_not_reused_across_a_second_failed_acquire():
    """Second pm-review round's finding: an etag alone is not bound to which key it was
    acquired for -- release("fl") must not reuse "mi"'s leftover etag against "fl"'s key.

    Third round's finding, on the first fix attempt: clearing _key/_etag unconditionally at
    the top of every acquire() call over-corrected this into a NEW bug -- a failed second
    acquire would wipe out a still-valid, still-held first lock, leaving it unreleasable (and
    therefore alive for its full TTL) even though this process legitimately still holds it.
    The correct fix needs no clearing at all: _key/_etag are only ever written by a
    SUCCESSFUL put_object, so a failed acquire("fl") already leaves "mi"'s state exactly as
    it was, and it's release()'s own key-match check that prevents the cross-key reuse."""
    client = FakeS3Client()
    other_holder = cc.SourceLock(client, "bucket", "dev-open187", holder="run-other")
    assert other_holder.acquire("fl") is True  # someone else already holds "fl" live

    lock = cc.SourceLock(client, "bucket", "dev-open187", holder="run-a")
    assert lock.acquire("mi") is True
    mi_body_before = client.objects["dev-open187/mi/_lock"]

    assert lock.acquire("fl") is False  # "fl" is live-held by someone else -- refused

    fl_body_before = client.objects["dev-open187/fl/_lock"]
    lock.release("fl")  # must be a no-op: this instance never actually held "fl"
    assert client.objects["dev-open187/fl/_lock"] == fl_body_before

    # THE regression: "mi" must still be releasable -- the failed "fl" attempt must not have
    # cost this process its own, still-legitimately-held lock.
    lock.release("mi")
    mi_data = json.loads(client.objects["dev-open187/mi/_lock"])
    assert mi_data["expires_at"] < cc.time.time()


def test_lock_failed_reacquire_of_the_same_key_does_not_lose_the_original_release():
    """pm-review round 3's specific additional ask: the same-key case, not just cross-key.
    A single instance acquires "mi", then calls acquire("mi") again on itself -- since the key
    now exists (its own prior write) and hasn't expired, this second call is correctly refused
    (False). That refusal must not cost the instance its own, still-legitimately-held lock."""
    client = FakeS3Client()
    lock = cc.SourceLock(client, "bucket", "dev-open187", holder="run-a")
    assert lock.acquire("mi") is True

    assert lock.acquire("mi") is False  # the key it itself wrote is live, so this refuses

    lock.release("mi")
    mi_data = json.loads(client.objects["dev-open187/mi/_lock"])
    assert mi_data["expires_at"] < cc.time.time()


def test_lock_stale_owner_release_does_not_clobber_a_reclaimed_lock():
    """THE regression for pm-review's core finding, on the Python side (which was already
    correct): if A's lock expires, B reclaims it, and A then releases using the ETag captured
    at A's OWN acquisition -- never a fresh read -- A's conditional write must fail harmlessly
    against B's current (different) ETag rather than overwriting B's live lock."""
    client = FakeS3Client()
    a = cc.SourceLock(client, "bucket", "dev-open187", holder="run-a")
    stale = json.dumps({"holder": "run-a", "acquired_at": 0, "expires_at": 1}).encode()
    client.put_object(Bucket="bucket", Key="dev-open187/mi/_lock", Body=stale)
    # Simulates A having acquired this exact write -- both _key and _etag, matching what a
    # real acquire() sets, so this actually exercises the etag-mismatch conditional-write path
    # rather than short-circuiting on release()'s separate key-match check.
    a._key = "dev-open187/mi/_lock"
    a._etag = client.etags["dev-open187/mi/_lock"]

    b = cc.SourceLock(client, "bucket", "dev-open187", holder="run-b")
    assert b.acquire("mi") is True  # B reclaims the expired lock for real
    b_body_before = client.objects["dev-open187/mi/_lock"]

    a.release("mi")  # A releases using the etag it originally held, not a fresh read

    assert client.objects["dev-open187/mi/_lock"] == b_body_before


# --- OPEN-203: the import lock, as a second independent SourceLock instance ----------------
#
# There is no separate "ImportLock" class -- SourceLock is already generic (it just needs a
# distinct key string), and OPEN-190's future loader is expected to hold a scrape lock and an
# import lock in the SAME process at once (mirroring what run-scrape.sh already does). The
# pattern that makes that safe is simply: use a SEPARATE instance per lock, never one instance
# for both. Proven directly here rather than left implicit.


def test_lock_scrape_and_import_locks_coexist_as_separate_instances():
    client = FakeS3Client()
    scrape_lock = cc.SourceLock(client, "bucket", "dev-open201", holder="run-a")
    import_lock = cc.SourceLock(client, "bucket", "dev-open201", holder="run-a")

    assert scrape_lock.acquire("mi") is True
    assert import_lock.acquire("mi_2025-2026-import") is True

    # Acquiring the import lock must not have disturbed the scrape lock's own tracked state --
    # each instance's _key/_etag are its own, never shared globals like the bash equivalent
    # (which is exactly why OPEN-203 gave that side its own separate variable pair).
    scrape_lock.release("mi")
    import_lock.release("mi_2025-2026-import")

    scrape_data = json.loads(client.objects["dev-open201/mi/_lock"])
    import_data = json.loads(client.objects["dev-open201/mi_2025-2026-import/_lock"])
    assert scrape_data["expires_at"] < cc.time.time()
    assert import_data["expires_at"] < cc.time.time()


# --- SourceLock integrated into main() -----------------------------------------------------


def test_main_refuses_when_another_run_holds_the_lock(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, bill_files=3))
    client = FakeS3Client()
    live = json.dumps({"holder": "other-run", "acquired_at": cc.time.time(),
                        "expires_at": cc.time.time() + 3600}).encode()
    client.put_object(Bucket="bucket", Key="dev-open201/ut/_lock", Body=live)

    rc = cc.main(["ut", "session=2025S2"], s3_client=client)

    assert rc == cc.EXIT_DO_NOT_RETRY
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"
    # The source was never asked -- OPEN-187's acceptance criterion, mirroring OPEN-154's own.
    assert "os-update" not in " ".join(client.put_calls)  # nothing scraped, nothing to publish
    assert not any(k.endswith(".ts") for k in client.put_calls)


def test_main_reclaims_stale_lock_and_proceeds(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, bill_files=3))
    client = FakeS3Client()
    stale = json.dumps({"holder": "dead-run", "acquired_at": 0, "expires_at": 1}).encode()
    client.put_object(Bucket="bucket", Key="dev-open201/ut/_lock", Body=stale)

    rc = cc.main(["ut", "session=2025S2"], s3_client=client)

    assert rc == 0
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "ok"


def test_main_releases_lock_after_a_successful_run(tmp_path, monkeypatch):
    """Released, not deleted (SourceLock avoids needing s3:DeleteObject) -- so a successful
    run must leave the lock object present but already expired, immediately reclaimable."""
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, bill_files=3))
    client = FakeS3Client()

    cc.main(["ut", "session=2025S2"], s3_client=client)

    lock_data = json.loads(client.objects["dev-open201/ut/_lock"])
    assert lock_data["expires_at"] < cc.time.time()


def test_main_releases_lock_even_when_the_run_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, exit_code=1, stderr_text="boom"))
    client = FakeS3Client()

    cc.main(["mi_test"], s3_client=client)

    lock_data = json.loads(client.objects["dev-open201/mi_test/_lock"])
    assert lock_data["expires_at"] < cc.time.time()
