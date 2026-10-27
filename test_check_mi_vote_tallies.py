"""Tests for check-mi-vote-tallies.py (pure functions; the database part is exercised read-only by hand)."""
import importlib.util
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("check_mi", os.path.join(HERE, "check-mi-vote-tallies.py"))
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("PASSED ROLL CALL # 319 YEAS 22 NAYS 13 EXCUSED 2 NOT VOTING 0", (22, 13)),
        ("passed; given immediate effect Roll Call #55 Yeas 65 Nays 40 Excused 0 Not Voting 5", (65, 40)),
        ("Yeas—36 Nays—0", (36, 0)),
        ("referred to committee", None),
        ("YEAS 22", None),
        (None, None),
    ],
)
def test_declared_tally(text, expected):
    assert chk.declared_tally(text) == expected


@pytest.mark.parametrize(
    "stored,declared,expected",
    [
        ((22, 13), (22, 13), "ok"),
        ((0, 7), (22, 14), "no-yea"),
        ((35, 4), (35, 1), "nays-high"),
        ((30, 4), (36, 0), "other"),
        ((0, 0), (0, 0), "ok"),
    ],
)
def test_verdict(stored, declared, expected):
    assert chk.verdict(*stored, declared) == expected


def test_read_bills_accepts_lines_and_json(tmp_path):
    lines = tmp_path / "a.txt"
    lines.write_text("SB 415\n\nHB 4961\n")
    js = tmp_path / "b.json"
    js.write_text('["SB 415", "HB 4961"]')
    assert chk.read_bills(str(lines)) == chk.read_bills(str(js)) == {"SB 415", "HB 4961"}


def test_unaudited_bills_lists_bills_with_nothing_checked():
    # a listed bill that is missing, or whose every vote lacked a tally, must not read as clean
    assert chk.unaudited_bills({"SB 415", "HB 4961", "SB 1"}, {"SB 415"}) == ["HB 4961", "SB 1"]
    assert chk.unaudited_bills({"SB 415"}, {"SB 415", "HB 9"}) == []


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, *a, **k):
        pass

    def fetchall(self):
        return self.rows


class _FakeConn:
    def __init__(self, rows):
        self.rows = rows

    def set_session(self, **k):
        pass

    def cursor(self):
        return _FakeCursor(self.rows)

    def rollback(self):
        pass

    def close(self):
        pass


def _run(monkeypatch, tmp_path, rows, bills):
    listed = tmp_path / "bills.txt"
    listed.write_text("\n".join(bills))
    monkeypatch.setattr(chk.psycopg2, "connect", lambda **k: _FakeConn(rows))
    monkeypatch.setattr("sys.argv", ["chk", "--bills", str(listed), "--expect-clean"])
    try:
        chk.main()
    except SystemExit as e:
        return e.code
    return 0


TALLY_OK = ("v1", "upper", "2026-01-01", "Passed ROLL CALL # 1 YEAS 20 NAYS 10", "SB 1", 20, 10)
TALLY_BAD = ("v2", "upper", "2026-01-02", "Passed ROLL CALL # 2 YEAS 20 NAYS 10", "SB 2", 0, 10)
NO_TALLY = ("v3", "upper", "2026-01-03", "Referred to committee", "SB 3", 0, 0)


def test_expect_clean_passes_when_every_listed_bill_is_audited_and_agrees(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, [TALLY_OK], ["SB 1"]) == 0


def test_expect_clean_exits_2_for_a_listed_bill_that_is_absent(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, [TALLY_OK], ["SB 1", "SB 99"]) == 2


def test_expect_clean_exits_2_for_a_listed_bill_whose_votes_have_no_tally(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, [TALLY_OK, NO_TALLY], ["SB 1", "SB 3"]) == 2


def test_expect_clean_exits_1_when_a_vote_disagrees_even_if_a_bill_is_also_unaudited(monkeypatch, tmp_path):
    # exit 1 (a real disagreement) takes precedence over exit 2 (incomplete audit); both are printed
    assert _run(monkeypatch, tmp_path, [TALLY_BAD], ["SB 2", "SB 99"]) == 1


def test_an_empty_bills_file_is_an_error_not_a_clean_audit(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, [TALLY_OK], []) not in (0, None)
