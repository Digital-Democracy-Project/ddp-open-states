"""Tests for cloud_people_refresh.py (OPEN-882): the weekly people refresh as a Fargate task.

Nothing here touches the network, S3 or a database: the tarball comes from a fake opener, os-people from a fake runner,
S3 from test_cloud_collector's in-memory client."""
import io
import json
import os
import subprocess
import sys
import tarfile

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import cloud_people_refresh as cpr
from test_cloud_collector import _RDS_SECRET, FakeS3Client

KEY = "working-tier/people-refresh/people-refresh-abc/people-refresh.json"
SHA = "0123456789abcdef0123456789abcdef01234567"
DSN = "postgresql://u:s3cretpw@db.internal/x"


def make_tarball(top="people-main", with_data=True, comment=SHA):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.PAX_FORMAT,
                      pax_headers={"comment": comment} if comment else None) as tar:
        names = [f"{top}/data/ky/legislature/a.yml"] if with_data else [f"{top}/README.md"]
        for name in names:
            payload = b"name: A\n"
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Opener:
    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.urls = payload, error, []

    def __call__(self, url, timeout=None):
        self.urls.append(url)
        if self.error:
            raise self.error
        return FakeResponse(self.payload)


class FakeRun:
    """Stands in for subprocess.run; `outcomes` maps state -> (returncode, output)."""

    def __init__(self, outcomes=None):
        self.outcomes, self.calls = outcomes or {}, []

    def __call__(self, cmd, env=None, **kw):
        state = cmd[-1]
        self.calls.append((cmd, env, kw, os.path.isdir(os.path.join(env["OS_PEOPLE_DIRECTORY"], "data"))))
        code, out = self.outcomes.get(state, (0, f"loaded {state}\n"))
        return subprocess.CompletedProcess(cmd, code, stdout=out)


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("MEMORY_BUCKET", "test-bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "prod")
    monkeypatch.setenv("DATABASE_URL", DSN)
    monkeypatch.delenv("PEOPLE_REPO", raising=False)
    monkeypatch.delenv("PEOPLE_REF", raising=False)


def _go(argv, client=None, opener=None, run=None):
    client = client or FakeS3Client()
    code = cpr.main(argv, s3_client=client, opener=opener or Opener(make_tarball()), run=run or FakeRun())
    return code, client


def test_writes_one_entry_per_state_under_the_run_id(env):
    run = FakeRun()
    code, client = _go(["people-refresh-abc", "KY,Mi"], run=run)
    assert code == 0
    doc = json.loads(client.objects[KEY])
    assert doc["run_id"] == "people-refresh-abc" and doc["people_commit"] == SHA
    assert set(doc["states"]) == {"ky", "mi"}
    assert all(v["status"] == "done" for v in doc["states"].values())
    assert [c[0][1:] for c in run.calls] == [["to-database", "ky"], ["to-database", "mi"]]


def test_a_failed_state_is_named_and_the_rest_still_run(env):
    run = FakeRun({"ky": (1, "boom\n")})
    code, client = _go(["people-refresh-abc", "ky,mi,wa"], run=run)
    assert code == 1  # a failure, but the result is written
    states = json.loads(client.objects[KEY])["states"]
    assert states["ky"]["status"] == "failed" and states["ky"]["exit_code"] == 1
    assert states["mi"]["status"] == "done" and states["wa"]["status"] == "done"
    assert len(run.calls) == 3


def test_os_people_reads_the_downloaded_checkout(env):
    run = FakeRun()
    opener = Opener(make_tarball())
    _go(["people-refresh-abc", "ky"], opener=opener, run=run)
    cmd, child_env, kw, had_data = run.calls[0]
    assert had_data  # OS_PEOPLE_DIRECTORY pointed at a folder holding data/ while os-people ran
    assert child_env["DATABASE_URL"] == DSN
    assert opener.urls == ["https://codeload.github.com/Digital-Democracy-Project/people/tar.gz/refs/heads/main"]


def test_repo_and_branch_come_from_the_environment(env, monkeypatch):
    monkeypatch.setenv("PEOPLE_REPO", "someone/people")
    monkeypatch.setenv("PEOPLE_REF", "release")
    opener = Opener(make_tarball())
    _go(["people-refresh-abc", "ky"], opener=opener)
    assert opener.urls == ["https://codeload.github.com/someone/people/tar.gz/refs/heads/release"]


def test_no_commit_header_still_works(env):
    _, client = _go(["people-refresh-abc", "ky"], opener=Opener(make_tarball(comment=None)))
    assert "people_commit" not in json.loads(client.objects[KEY])


def test_a_failed_download_writes_no_result_and_runs_nothing(env, capsys):
    run = FakeRun()
    code, client = _go(["people-refresh-abc", "ky"], opener=Opener(error=OSError(f"cannot reach {DSN}")), run=run)
    assert code == 2 and client.objects == {} and run.calls == []
    err = capsys.readouterr()
    assert "OSError" in err.err and "s3cretpw" not in err.out + err.err


def test_a_tarball_without_data_is_refused(env):
    code, client = _go(["people-refresh-abc", "ky"], opener=Opener(make_tarball(with_data=False)))
    assert code == 2 and client.objects == {}


@pytest.mark.parametrize("argv", [[], ["only-run-id"], ["r", ""], ["r", "ky,../x"], ["r", "kentucky"], ["r", "ky", "extra"]])
def test_bad_usage_runs_nothing(env, argv):
    run = FakeRun()
    code, client = _go(argv, run=run)
    assert code == 2 and run.calls == [] and client.objects == {}


def test_the_login_is_built_by_the_one_builder_from_the_task_secret(env, monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    for k, v in _RDS_SECRET.items():
        monkeypatch.setenv(k, v)
    run = FakeRun()
    code, _ = _go(["people-refresh-abc", "ky"], run=run)
    assert code == 0
    # written by hand, not built by the code under test
    assert run.calls[0][1]["DATABASE_URL"] == "postgresql://load%40user:p%3Aw%2Fd%40%25x@db.example.internal:5432/open%20states"


def test_no_login_at_all_fails_before_any_download(env, monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    opener = Opener(make_tarball())
    code, client = _go(["people-refresh-abc", "ky"], opener=opener)
    assert code == 2 and opener.urls == [] and client.objects == {}


def test_no_memory_prefix_fails(env, monkeypatch):
    monkeypatch.delenv("MEMORY_PREFIX")
    code, client = _go(["people-refresh-abc", "ky"])
    assert code == 2 and client.objects == {}


def test_os_people_output_never_shows_the_login(env, capsys):
    run = FakeRun({"ky": (1, f"could not connect to {DSN}\npassword s3cretpw\n")})
    _go(["people-refresh-abc", "ky"], run=run)
    out = capsys.readouterr()
    assert "s3cretpw" not in out.out + out.err and "could not connect to ***" in out.err


def test_an_s3_write_failure_is_exit_2_with_the_type_only(env, capsys):
    class Broken(FakeS3Client):
        def upload_file(self, *a):
            raise RuntimeError(f"nope {DSN}")

    code, _ = _go(["people-refresh-abc", "ky"], client=Broken())
    out = capsys.readouterr()
    assert code == 2 and "RuntimeError" in out.err and "s3cretpw" not in out.out + out.err


def test_the_completion_line_lists_states(env, capsys):
    _go(["people-refresh-abc", "ky,mi"], run=FakeRun({"mi": (1, "")}))
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["status"] == "failed" and line["states"] == {"ky": "done", "mi": "failed"}


def test_real_subprocess_path_records_exit_code(env, monkeypatch, tmp_path):
    # the real subprocess.run, with a stand-in executable: proves the command line and the exit code are read for real
    exe = tmp_path / "fake-os-people"
    exe.write_text('#!/bin/sh\n[ "$2" = "mi" ] && exit 3\necho "ran $2 in $OS_PEOPLE_DIRECTORY" >&2\nexit 0\n')
    exe.chmod(0o755)
    monkeypatch.setenv("OS_PEOPLE", str(exe))
    client = FakeS3Client()
    code = cpr.main(["people-refresh-abc", "ky,mi"], s3_client=client, opener=Opener(make_tarball()))
    states = json.loads(client.objects[KEY])["states"]
    assert code == 1
    assert states["ky"]["status"] == "done"
    assert states["mi"]["status"] == "failed" and states["mi"]["exit_code"] == 3


def test_a_state_whose_os_people_cannot_even_start_is_failed_and_earlier_results_are_kept(env):
    class Raises(FakeRun):
        def __call__(self, cmd, env=None, **kw):
            if cmd[-1] == "mi":
                raise FileNotFoundError(f"os-people missing near {DSN}")
            return super().__call__(cmd, env=env, **kw)

    code, client = _go(["people-refresh-abc", "ky,mi,wa"], run=Raises())
    states = json.loads(client.objects[KEY])["states"]
    assert code == 1
    assert states["ky"]["status"] == "done" and states["wa"]["status"] == "done"
    assert states["mi"]["status"] == "failed" and states["mi"]["error"] == "FileNotFoundError"
    assert "s3cretpw" not in json.dumps(states)


def test_the_runner_is_in_the_images_file_list():
    # RUNNER_SCRIPT can only name a file the Dockerfile's COPY put in /app
    here = os.path.dirname(os.path.abspath(__file__))
    lines = open(os.path.join(here, "Dockerfile")).read().splitlines()
    copy_lines = [ln for ln in lines if ln.startswith("COPY cloud_collector.py")]
    assert len(copy_lines) == 1 and " cloud_people_refresh.py " in copy_lines[0]
