"""
Tests for cloud_loader.py (OPEN-190).

Reuses test_cloud_collector.py's FakeS3Client so both halves of the collect/load split are
exercised against the identical S3-conditional-write semantics -- the two files have to agree
on what a manifest and a lock object look like, since cloud_collector.py writes the former and
scraper-memory.sh's bash-side import lock has to agree on the latter's key shape.

The acceptance question, per OPEN-190's own criteria, is not "does it call os-update". It is:

  * a run is only ever loaded from its own manifest, never from bare object presence -- an
    absent, unparsable, or identity-mismatched manifest refuses rather than guesses.
  * the run_id/source the manifest names must match what this invocation was asked to load
    ("the compared run is the loaded run").
  * the cross-machine IMPORT lock (OPEN-203) is actually acquired before importing and
    released afterwards regardless of outcome, keyed so a mac-side run-scrape.sh import and
    this loader agree on the same S3 object.
  * a partial fetch (one object the manifest names cannot be retrieved intact) never reaches
    os-update at all.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import cloud_loader as cl
from test_cloud_collector import FakeS3Client


def _seed_manifest(client, prefix, source, run_id, objects, *, manifest_run_id=None,
                    manifest_source=None):
    manifest_key = f"working-tier/{source}/{run_id}/_manifest.json"
    body = json.dumps({
        "run_id": manifest_run_id if manifest_run_id is not None else run_id,
        "source": manifest_source if manifest_source is not None else source,
        "objects": objects,
    }).encode()
    client.objects[manifest_key] = body


def _seed_object(client, source, run_id, rel, content=b"{}"):
    key = f"working-tier/{source}/{run_id}/{rel}"
    client.objects[key] = content
    return key


def _fake_proc(returncode=0, lines=None):
    proc = MagicMock()
    proc.stdout = iter(lines or [])
    proc.wait.return_value = None
    proc.returncode = returncode
    return proc


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("MEMORY_BUCKET", "test-bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "prod")


# ── manifest fetch/verification ─────────────────────────────────────────────────────────────


def test_refuses_when_manifest_absent(env, capsys):
    client = FakeS3Client()
    with patch("cloud_loader.subprocess.Popen") as mock_popen:
        rc = cl.main(["mi", "mi-run1"], s3_client=client)
    assert rc == 1
    mock_popen.assert_not_called()
    assert "no completion marker" in capsys.readouterr().err


def test_refuses_when_manifest_unparsable(env, capsys):
    client = FakeS3Client()
    client.objects["working-tier/mi/mi-run1/_manifest.json"] = b"not json"
    with patch("cloud_loader.subprocess.Popen") as mock_popen:
        rc = cl.main(["mi", "mi-run1"], s3_client=client)
    assert rc == 1
    mock_popen.assert_not_called()
    assert "could not be parsed" in capsys.readouterr().err


def test_refuses_when_manifest_run_id_does_not_match(env, capsys):
    client = FakeS3Client()
    _seed_manifest(client, "prod", "mi", "mi-run1", [], manifest_run_id="mi-some-other-run")
    with patch("cloud_loader.subprocess.Popen") as mock_popen:
        rc = cl.main(["mi", "mi-run1"], s3_client=client)
    assert rc == 1
    mock_popen.assert_not_called()
    assert "compared run must be the loaded run" in capsys.readouterr().err


def test_refuses_when_manifest_source_does_not_match(env, capsys):
    client = FakeS3Client()
    _seed_manifest(client, "prod", "mi", "mi-run1", [], manifest_source="ut")
    with patch("cloud_loader.subprocess.Popen") as mock_popen:
        rc = cl.main(["mi", "mi-run1"], s3_client=client)
    assert rc == 1
    mock_popen.assert_not_called()


# ── partial-fetch refusal ────────────────────────────────────────────────────────────────────


def test_refuses_a_partial_load_when_one_object_is_missing(env, capsys):
    client = FakeS3Client()
    present = _seed_object(client, "mi", "mi-run1", "bills/HB1.json")
    missing = "working-tier/mi/mi-run1/bills/HB2.json"  # named but never uploaded
    _seed_manifest(client, "prod", "mi", "mi-run1", [present, missing])
    with patch("cloud_loader.subprocess.Popen") as mock_popen:
        rc = cl.main(["mi", "mi-run1"], s3_client=client)
    assert rc == 1
    mock_popen.assert_not_called()
    assert "refusing a partial load" in capsys.readouterr().err


def test_refuses_an_object_outside_the_runs_own_prefix(env, capsys):
    client = FakeS3Client()
    sneaky = "working-tier/mi/some-other-run/bills/HB1.json"
    client.objects[sneaky] = b"{}"
    _seed_manifest(client, "prod", "mi", "mi-run1", [sneaky])
    with patch("cloud_loader.subprocess.Popen") as mock_popen:
        rc = cl.main(["mi", "mi-run1"], s3_client=client)
    assert rc == 1
    mock_popen.assert_not_called()
    assert "outside this run's own prefix" in capsys.readouterr().err


# ── the successful path ──────────────────────────────────────────────────────────────────────


def test_successful_load_fetches_objects_and_invokes_os_update(env, monkeypatch, capsys):
    monkeypatch.setenv("OS_UPDATE", "fake-os-update")
    client = FakeS3Client()
    obj1 = _seed_object(client, "mi", "mi-run1", "bills/HB1.json")
    obj2 = _seed_object(client, "mi", "mi-run1", "bills/HB2.json")
    _seed_manifest(client, "prod", "mi", "mi-run1", [obj1, obj2])

    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        return _fake_proc(returncode=0)

    with patch("cloud_loader.subprocess.Popen", side_effect=fake_popen) as mock_popen:
        rc = cl.main(["mi", "mi-run1"], s3_client=client)

    assert rc == 0
    mock_popen.assert_called_once()
    assert captured["cmd"][:4] == ["fake-os-update", "mi", "--import", "--cachedir"]
    assert "--datadir" in captured["cmd"]

    out = capsys.readouterr().out
    record = json.loads(out.strip().splitlines()[-1])
    assert record == {"source": "mi", "run_id": "mi-run1", "status": "ok", "phase": "import",
                       "duration_s": record["duration_s"]}


def test_successful_load_passes_session_through(env, monkeypatch):
    monkeypatch.setenv("OS_UPDATE", "fake-os-update")
    client = FakeS3Client()
    _seed_manifest(client, "prod", "mi", "mi-run1", [])
    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        return _fake_proc(returncode=0)

    with patch("cloud_loader.subprocess.Popen", side_effect=fake_popen):
        rc = cl.main(["mi", "mi-run1", "session=2025-2026"], s3_client=client)

    assert rc == 0
    assert "session=2025-2026" in captured["cmd"]


def test_import_failure_reports_failed_status_and_still_releases_the_lock(env, monkeypatch, capsys):
    client = FakeS3Client()
    _seed_manifest(client, "prod", "mi", "mi-run1", [])
    with patch("cloud_loader.subprocess.Popen", return_value=_fake_proc(returncode=1)):
        rc = cl.main(["mi", "mi-run1"], s3_client=client)
    assert rc == 1
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"

    # the lock must have been released on the failure path -- a second load attempt (a
    # retry, in practice) must be able to acquire it, not find it still held.
    _seed_manifest(client, "prod", "mi", "mi-run1", [])
    with patch("cloud_loader.subprocess.Popen", return_value=_fake_proc(returncode=0)):
        rc2 = cl.main(["mi", "mi-run1"], s3_client=client)
    assert rc2 == 0


# ── OPEN-203: the cross-machine import lock ─────────────────────────────────────────────────


def test_import_lock_key_matches_scraper_memory_shs_own_shape(env):
    """cloud_loader must land on the exact same S3 object
    scraper_memory_import_lock_key() (scraper-memory.sh) computes -- '{prefix}/{scrape_key}/
    _import_lock' -- or a mac-side run-scrape.sh import and this loader never exclude each
    other."""
    client = FakeS3Client()
    lock = cl.SourceLock(client, "test-bucket", "prod", holder="x", suffix="_import_lock")
    assert lock.key("mi") == "prod/mi/_import_lock"


def test_refuses_to_load_when_the_import_lock_is_already_held(env, capsys):
    client = FakeS3Client()
    _seed_manifest(client, "prod", "mi", "mi-run1", [])

    holder_lock = cl.SourceLock(client, "test-bucket", "prod", holder="someone-else",
                                 suffix="_import_lock")
    assert holder_lock.acquire("mi") is True  # a mac-side import already holds it

    with patch("cloud_loader.subprocess.Popen") as mock_popen:
        rc = cl.main(["mi", "mi-run1"], s3_client=client)

    assert rc == cl.EXIT_DO_NOT_RETRY
    mock_popen.assert_not_called()
    assert "already holds the lock" in capsys.readouterr().err


def test_import_lock_is_keyed_on_scrape_key_not_bare_source(env):
    """USA lower/upper share bare $STATE; the import lock must be keyed on the full scrape
    key (source_session) so they don't collide -- matching run-scrape.sh's own local import
    lock's reasoning exactly (scraper-memory.sh's scraper_memory_import_lock_key docstring)."""
    client = FakeS3Client()
    _seed_manifest(client, "prod", "usa", "usa-run1", [])

    with patch("cloud_loader.subprocess.Popen", return_value=_fake_proc(returncode=0)):
        rc = cl.main(["usa", "usa-run1", "session=upper"], s3_client=client)
    assert rc == 0

    # a DIFFERENT session for the same bare source must not find the lock still held
    _seed_manifest(client, "prod", "usa", "usa-run2", [])
    with patch("cloud_loader.subprocess.Popen", return_value=_fake_proc(returncode=0)):
        rc2 = cl.main(["usa", "usa-run2", "session=lower"], s3_client=client)
    assert rc2 == 0


# ── missing configuration ────────────────────────────────────────────────────────────────────


def test_fails_cleanly_when_memory_bucket_is_not_set(monkeypatch, capsys):
    monkeypatch.delenv("MEMORY_BUCKET", raising=False)
    client = FakeS3Client()
    with patch("cloud_loader.subprocess.Popen") as mock_popen:
        rc = cl.main(["mi", "mi-run1"], s3_client=client)
    assert rc == 1
    mock_popen.assert_not_called()
    assert "MEMORY_BUCKET is required" in capsys.readouterr().err
