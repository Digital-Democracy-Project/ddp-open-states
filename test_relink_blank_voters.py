"""OPEN-611: relink-blank-voters.py's write path. The list of what a commit changed must never claim a change that
did not happen, and must never be lost when the database may have changed. No database: the plan and the connection
are stand-ins; the plan itself is checked by the script's dry run on the replica (OPEN-611 ticket)."""
import importlib.util
import os
from unittest import mock

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("relink_blank_voters", os.path.join(HERE, "relink-blank-voters.py"))
rbv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rbv)

ROW = dict(
    pv_id=1, state="wa", session="2025-2026", vote_event="ocd-vote/x", bill="HB 1", date="2025-01-24",
    motion="final passage", option="no", voter_name="Hunt", person_id="ocd-person/y", person_name="Victoria Hunt",
)


class _Cursor:
    rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, *args):
        pass


class _Conn:
    def __init__(self, commit_error=None):
        self.commit_error = commit_error
        self.autocommit = False
        self.committed = False

    def cursor(self):
        return _Cursor()

    def commit(self):
        if self.commit_error:
            raise self.commit_error
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        pass


def _run(tmp_path, *argv, conn=None, replace_error=None):
    conn = conn or _Conn()
    replace = mock.Mock(side_effect=replace_error) if replace_error else os.replace
    with mock.patch.object(rbv, "plan_case", return_value=([ROW], [])), mock.patch.object(
        rbv.psycopg2, "connect", return_value=conn
    ), mock.patch.object(rbv, "CASES", [("wa", "lower", "Hunt")]), mock.patch.object(rbv.os, "replace", replace):
        try:
            rbv.main(list(argv))
            code = 0
        except SystemExit as e:
            code = e.code
    return code, sorted(os.listdir(tmp_path)), conn


def test_a_commit_writes_the_list_under_its_name(tmp_path):
    code, files, conn = _run(tmp_path, "--commit", "--list", str(tmp_path / "l.csv"))
    assert (code, files, conn.committed) == (0, ["l.csv"], True)
    assert "Victoria Hunt" in (tmp_path / "l.csv").read_text()


def test_a_failed_commit_keeps_the_list_and_says_the_outcome_is_unknown(tmp_path):
    code, files, _ = _run(tmp_path, "--commit", "--list", str(tmp_path / "l.csv"), conn=_Conn(RuntimeError("lost")))
    assert files == ["l.csv.partial"]
    assert "outcome is unknown" in code


def test_after_a_failed_commit_the_suggested_dry_run_runs_and_keeps_the_list(tmp_path):
    code, _, _ = _run(tmp_path, "--commit", "--list", str(tmp_path / "l.csv"), conn=_Conn(RuntimeError("lost")))
    assert "without --commit and without --list" in code
    code, files, conn = _run(tmp_path)  # the suggested command: a dry run, no list
    assert (code, files, conn.committed) == (0, ["l.csv.partial"], False)


def test_a_failed_rename_after_the_commit_says_it_committed(tmp_path):
    code, files, conn = _run(tmp_path, "--commit", "--list", str(tmp_path / "l.csv"), replace_error=OSError("full"))
    assert conn.committed and files == ["l.csv.partial"]
    assert code.startswith("COMMITTED") and "Do not run again" in code


def test_a_dry_run_writes_the_list_and_commits_nothing(tmp_path):
    code, files, conn = _run(tmp_path, "--list", str(tmp_path / "l.csv"))
    assert (code, files, conn.committed) == (0, ["l.csv"], False)


@pytest.mark.parametrize("existing", ["l.csv", "l.csv.partial"])
def test_an_earlier_list_is_never_overwritten(tmp_path, existing):
    (tmp_path / existing).write_text("earlier record")
    with pytest.raises(SystemExit):
        rbv.main(["--commit", "--list", str(tmp_path / "l.csv")])
    assert (tmp_path / existing).read_text() == "earlier record"


def test_a_commit_needs_a_list():
    with pytest.raises(SystemExit):
        rbv.main(["--commit"])
