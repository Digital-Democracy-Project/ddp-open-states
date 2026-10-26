"""Tests for check-wa-chapter-citations.py (pure functions; the database part is exercised read-only by hand)."""
import importlib.util
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("check_wa", os.path.join(HERE, "check-wa-chapter-citations.py"))
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)


@pytest.mark.parametrize("identifier,expected", [("HB 1052", "HB1052"), ("SB  5167", "SB5167"), ("HJM 4001", "HJM4001")])
def test_bill_no_matches_the_scrapers_argument_shape(identifier, expected):
    assert chk.bill_no(identifier) == expected


@pytest.mark.parametrize(
    "text,matches",
    [
        ("Chapter 327, 2025 Laws.", True),
        ("Chapter 39, 2025 Laws", True),
        ("Delivered to Governor.", False),
        ("Governor signed. Chapter 12, Laws of 2025", False),  # not the legislature's status line
        ("See Chapter 327, 2025 Laws.", False),  # anchored: only the status line itself
    ],
)
def test_chapter_action_pattern(text, matches):
    assert bool(re.search(chk.CHAPTER_ACTION_RE, text)) is matches


def test_summarize_counts_per_session_and_lists_the_bills_missing_a_citation():
    rows = [
        ("2025-2026", "HB 1052", True, False),  # enacted, citation missing
        ("2025-2026", "HB 1053", True, True),  # enacted, has it
        ("2025-2026", "HB 1054", False, False),  # not enacted
        ("2025-2026", "HB 1055", False, True),  # citation but no Chapter action: counted, not "missing"
        ("2023-2024", "SB 5000", True, False),
    ]
    s = chk.summarize(rows)
    assert s["2025-2026"] == {"bills": 4, "chapter_action": 2, "missing": ["HB 1052"], "citation_without_action": 1}
    assert s["2023-2024"]["missing"] == ["SB 5000"]


def test_summarize_of_nothing_is_empty():
    assert chk.summarize([]) == {}


def test_chunks_splits_into_runs_that_keep_the_argument_short():
    assert chk.chunks(["a", "b", "c", "d", "e"], 2) == [["a", "b"], ["c", "d"], ["e"]]
    assert chk.chunks([], 20) == []
    # the marker file name run-scrape.sh derives from the argument stays under 255 bytes
    ids = [chk.bill_no(f"HJM {4000 + i}") for i in range(20)]
    name = "wa_session_2025-2026_bill_no_" + ",".join(ids) + ".imported"
    assert len(name) < 255
