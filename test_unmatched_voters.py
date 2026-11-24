"""Tests for unmatched-voters.py (OPEN-855): the read-only JSON reader ddp-sync runs after each load."""
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("unmatched_voters", os.path.join(HERE, "unmatched-voters.py"))
uv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uv)


class FakeCursor:
    def __init__(self, results):
        self._results = list(results)
        self.executed = []

    def execute(self, sql, params):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._results.pop(0)


class FakeConn:
    def __init__(self, results):
        self._cursor = FakeCursor(results)
        self.readonly = None
        self.closed = False

    def cursor(self):
        return self._cursor

    def set_session(self, readonly):
        self.readonly = readonly

    def close(self):
        self.closed = True


def test_prints_the_json_and_reads_only(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:secret@db/x")
    conn = FakeConn([[("2026", 100, 3)], [("2026", "Lewis C", 3)]])
    assert uv.main(["KY"], connect=lambda url: conn, manifest_path="/nonexistent/jurisdictions.yaml") == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {
        "state": "ky",
        "sessions": {"2026": {"total": 100, "unresolved": 3}},
        "names": [{"session": "2026", "name": "Lewis C", "count": 3, "accepted": False}],
    }
    assert conn.readonly is True
    assert conn.closed


def test_no_database_url_is_exit_2(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert uv.main(["me"], connect=lambda url: None) == 2
    assert "DATABASE_URL" in capsys.readouterr().err


def test_a_database_failure_is_exit_2_without_the_connection_string(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:secret@db/x")

    def refuse(url):
        raise RuntimeError(f"could not connect to {url}")

    assert uv.main(["me"], connect=refuse) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "secret" not in captured.err


def test_a_name_on_the_manifests_accepted_list_is_marked(monkeypatch, capsys, tmp_path):
    import yaml

    from test_validate_jurisdictions import _valid_entry

    entry = _valid_entry()
    entry["quality"]["accepted_unmatched_voters"] = ["Mr. Speaker"]
    manifest = tmp_path / "jurisdictions.yaml"
    manifest.write_text(yaml.safe_dump({"ky": entry}))
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:secret@db/x")
    conn = FakeConn([[("2026", 100, 5)], [("2026", "Mr. Speaker", 4), ("2026", "Lewis C", 1)]])
    assert uv.main(["ky"], connect=lambda url: conn, manifest_path=str(manifest)) == 0
    names = json.loads(capsys.readouterr().out)["names"]
    assert [(n["name"], n["accepted"]) for n in names] == [("Mr. Speaker", True), ("Lewis C", False)]


def test_a_manifest_that_does_not_validate_accepts_nothing(tmp_path):
    manifest = tmp_path / "jurisdictions.yaml"
    manifest.write_text("ky: {quality: {accepted_unmatched_voters: [Mr. Speaker]}}\n")  # far from a valid entry
    assert uv.accepted_names("ky", str(manifest)) == set()
