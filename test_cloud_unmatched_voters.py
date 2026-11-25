"""Tests for cloud_unmatched_voters.py (OPEN-881): the after-load unmatched-voter check as a Fargate task.

The task writes the same JSON `unmatched-voters.py` prints to S3 under the run id, builds its login only through
apply_rds_task_secret(), and never prints a connection string."""
import importlib.util
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import cloud_unmatched_voters as cuv
from test_cloud_collector import _RDS_SECRET, FakeS3Client
from test_unmatched_voters import FakeConn

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("unmatched_voters", os.path.join(HERE, "unmatched-voters.py"))
uv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uv)

NO_MANIFEST = "/nonexistent/jurisdictions.yaml"
KEY = "working-tier/ky/ky-unmatched-abc/unmatched-voters.json"


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("MEMORY_BUCKET", "test-bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "prod")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:secret@db.internal/x")


def _rows():
    return [[("2026", 100, 3)], [("2026", "Lewis C", 3)]]


def _run(argv, client, rows=None, connect=None):
    conn = FakeConn(rows if rows is not None else _rows())
    return cuv.main(argv, s3_client=client, connect=connect or (lambda url: conn)), conn


def test_writes_the_scripts_own_json_under_the_run_id(env, monkeypatch, capsys):
    client = FakeS3Client()
    code, conn = _run(["KY", "ky-unmatched-abc"], client)
    assert code == 0
    assert json.loads(client.objects[KEY]) == {
        "state": "ky",
        "sessions": {"2026": {"total": 100, "unresolved": 3}},
        "names": [{"session": "2026", "name": "Lewis C", "count": 3, "accepted": False}],
    }
    assert conn.readonly is True and conn.closed
    # byte-for-byte the document `unmatched-voters.py` prints for the same rows: one builder, no second query
    capsys.readouterr()
    assert uv.main(["ky"], connect=lambda url: FakeConn(_rows())) == 0
    assert json.loads(capsys.readouterr().out) == json.loads(client.objects[KEY])


def test_a_name_on_the_manifests_accepted_list_is_marked(env, tmp_path):
    import yaml

    from test_validate_jurisdictions import _valid_entry

    entry = _valid_entry()
    entry["quality"]["accepted_unmatched_voters"] = ["Lewis C"]
    manifest = tmp_path / "jurisdictions.yaml"
    manifest.write_text(yaml.safe_dump({"ky": entry}))
    import qa_primitives

    result = qa_primitives.unmatched_voters_result("ky", "postgresql://x", lambda url: FakeConn(_rows()), str(manifest))
    assert result["names"][0]["accepted"] is True


def test_the_result_is_only_written_after_the_query_succeeded(env, capsys):
    client = FakeS3Client()

    def refuse(url):
        raise RuntimeError(f"could not connect to {url}")

    code, _ = _run(["ky", "ky-unmatched-abc"], client, connect=refuse)
    captured = capsys.readouterr()
    assert code == 2
    assert client.objects == {} and client.put_calls == []
    assert "secret" not in captured.out + captured.err and "db.internal" not in captured.out + captured.err
    assert "RuntimeError" in captured.err


def test_the_login_comes_only_from_the_task_secret_when_none_was_passed(env, monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    for k, v in {**_RDS_SECRET, "RDS_HOST": "rds.example", "RDS_PORT": "5432", "RDS_DBNAME": "openstates"}.items():
        monkeypatch.setenv(k, v)
    seen = []
    client = FakeS3Client()
    code, _ = _run(["ky", "ky-unmatched-abc"], client, connect=lambda url: seen.append(url) or FakeConn(_rows()))
    assert code == 0
    assert seen == [os.environ["DATABASE_URL"]] and "rds.example:5432/openstates" in seen[0]


def test_no_login_at_all_fails_and_names_no_value(env, monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL")
    client = FakeS3Client()
    code, _ = _run(["ky", "ky-unmatched-abc"], client)
    assert code == 2 and client.objects == {}
    assert "no DATABASE_URL" in capsys.readouterr().err


def test_a_half_configured_secret_fails_naming_only_variables(env, monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.setenv("RDS_USERNAME", "load@user")
    code, _ = _run(["ky", "ky-unmatched-abc"], FakeS3Client())
    err = capsys.readouterr().err
    assert code == 2 and "RDS_PASSWORD" in err and "load@user" not in err


def test_missing_memory_bucket_or_prefix_fails(env, monkeypatch):
    monkeypatch.delenv("MEMORY_BUCKET")
    assert _run(["ky", "r"], FakeS3Client())[0] == 2
    monkeypatch.setenv("MEMORY_BUCKET", "b")
    monkeypatch.delenv("MEMORY_PREFIX")
    assert _run(["ky", "r"], FakeS3Client())[0] == 2


def test_a_failed_upload_is_exit_2_without_the_address(env, capsys):
    class Broken(FakeS3Client):
        def upload_file(self, *a):
            raise RuntimeError("write to db.internal failed")

    code, _ = _run(["ky", "ky-unmatched-abc"], Broken())
    err = capsys.readouterr().err
    assert code == 2 and "db.internal" not in err and "RuntimeError" in err


def test_usage(env):
    assert cuv.main(["ky"], s3_client=FakeS3Client()) == 2


def test_the_working_tier_prefix_is_honoured(env, monkeypatch):
    monkeypatch.setenv("WORKING_TIER_PREFIX", "wt")
    client = FakeS3Client()
    assert _run(["ky", "ky-unmatched-abc"], client)[0] == 0
    assert list(client.objects) == ["wt/ky/ky-unmatched-abc/unmatched-voters.json"]


def test_the_runner_is_in_the_images_file_list():
    copy = [ln for ln in open(os.path.join(HERE, "Dockerfile")) if ln.startswith("COPY cloud_collector.py")]
    assert len(copy) == 1 and "cloud_unmatched_voters.py" in copy[0].split()
