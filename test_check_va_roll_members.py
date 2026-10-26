"""Tests for check-va-roll-members.py. Pure: no network, no database."""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("chk", os.path.join(HERE, "check-va-roll-members.py"))
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)

STORED = {"Barry D. Knight": "not voting", "Betsy B. Carr": "yes", "Bill Wiley": "no"}


def test_identical_roll_has_no_differences():
    live = [("Barry D. Knight", "X"), ("Betsy B. Carr", "Y"), ("Bill Wiley", "N")]
    assert not any(chk.compare_vote(STORED, live).values())


def test_a_member_lis_no_longer_lists_is_dropped():
    live = [("Betsy B. Carr", "Y"), ("Bill Wiley", "N")]  # OPEN-429: Knight gone from the 2026-02-17 rolls
    assert chk.compare_vote(STORED, live)["dropped"] == ["Barry D. Knight"]


def test_a_member_with_no_response_is_reported_apart_from_dropped_and_added():
    stored = {"Betsy B. Carr": "yes"}
    live = [("Betsy B. Carr", "Y"), ("Luke E. Torian", None)]  # the scraper skips these rows on purpose
    out = chk.compare_vote(stored, live)
    assert out["no-response"] == ["Luke E. Torian"] and not out["added"] and not out["dropped"]


def test_a_new_member_with_a_response_is_added():
    out = chk.compare_vote({"Betsy B. Carr": "yes"}, [("Betsy B. Carr", "Y"), ("Bill Wiley", "N")])
    assert out["added"] == ["Bill Wiley"]


def test_a_changed_option_is_reported_and_the_accepted_labels_are_not():
    out = chk.compare_vote({"Betsy B. Carr": "no", "Bill Wiley": "abstain"}, [("Betsy B. Carr", "Y"), ("Bill Wiley", "A")])
    assert out["option"] == ["Betsy B. Carr"]  # LIS "A" stored as abstain or other is not a difference


def test_names_are_compared_stripped():
    assert not any(chk.compare_vote({"Betsy B. Carr": "yes"}, [(" Betsy B. Carr ", "Y")]).values())


def test_summary_counts_votes_and_members_per_kind():
    rows = [
        ("1", "HB 1", "2026-02-17", chk.compare_vote(STORED, [("Betsy B. Carr", "Y"), ("Bill Wiley", "N")])),
        ("2", "HB 2", "2026-02-19", chk.compare_vote(STORED, [("Betsy B. Carr", "Y"), ("Bill Wiley", "N")])),
        ("3", "HB 3", "2026-02-20", chk.compare_vote(STORED, [("Barry D. Knight", "X"), ("Betsy B. Carr", "Y"), ("Bill Wiley", "N")])),
    ]
    totals, by_kind, dates = chk.summarize(rows)
    assert totals["compared"] == 3 and totals["identical"] == 1 and totals["votes with dropped"] == 2
    assert by_kind["dropped"]["Barry D. Knight"] == 2 and sorted(dates["dropped"]) == ["2026-02-17", "2026-02-19"]


def test_the_read_path_only_selects():
    assert "UPDATE" not in chk.STORED_SQL.upper() and "DELETE" not in chk.STORED_SQL.upper()


def test_one_vote_can_carry_several_kinds_and_each_member_lands_in_one():
    stored = {"A": "yes", "B": "no", "C": "yes"}
    live = [("A", "N"), ("B", "N"), ("D", "Y"), ("E", None)]  # A option, C dropped, D added, E no-response
    out = chk.compare_vote(stored, live)
    assert out == {"dropped": ["C"], "no-response": ["E"], "added": ["D"], "option": ["A"]}
    assert sum(len(v) for v in out.values()) == 4  # no member counted twice


def test_an_audit_with_uncompared_votes_is_incomplete():
    assert chk.incomplete_reason(10, 10, [], {"HB1": 1}) is None
    assert "could not be compared" in chk.incomplete_reason(10, 9, [("HB 1", "1")], {"HB1": 1})
    assert "no legislation list" in chk.incomplete_reason(10, 0, [], {})
