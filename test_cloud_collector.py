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

import pytest
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.dirname(__file__))
import cloud_collector as cc


class FakeS3Client:
    """In-memory stand-in for boto3's S3 client. Raises the same ClientError shapes real S3
    does for a missing key, so S3Memory's three-way matching is exercised for real."""

    def __init__(self):
        self.objects = {}  # key -> bytes
        self.put_calls = []  # keys, in call order -- what the ordering tests assert on

    def download_file(self, bucket, key, dest):
        if key not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        with open(dest, "wb") as f:
            f.write(self.objects[key])

    def upload_file(self, local_path, bucket, key):
        with open(local_path, "rb") as f:
            self.objects[key] = f.read()
        self.put_calls.append(key)

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


def test_main_michigan_proceeds_with_baseline_present(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open201")
    monkeypatch.setenv("OS_UPDATE", _fake_os_update(tmp_path, bill_files=2))
    client = FakeS3Client()
    client.objects["dev-open201/mi/_cache/mi_last_actions_2025-2026.json"] = b"[]"

    rc = cc.main(["mi"], s3_client=client)
    assert rc == 0
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "ok"


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
