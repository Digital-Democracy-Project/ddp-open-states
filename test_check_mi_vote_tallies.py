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
