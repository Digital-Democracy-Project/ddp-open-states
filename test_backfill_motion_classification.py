"""OPEN-625: backfill-motion-classification.py. Arizona is classified by the scraper's own floor-step rule or not at
all, and a write either applies every planned change or none. No database: rows and the connection are stand-ins; the
plan itself is checked by the dry run on the replica and the commit + undo rehearsal on a throwaway copy (OPEN-625)."""
import csv
import importlib.util
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("backfill_motion", os.path.join(HERE, "backfill-motion-classification.py"))
bmc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bmc)

AZ = "ocd-jurisdiction/country:us/state:az/government"
SOURCE = "https://apps.azleg.gov/api/BillStatusFloorAction?billStatusId={}&billStatusActionId={}&includeVotes=true"


def row(vote_id, action_id, text, classification, jurisdiction=AZ, bill="HB 2689"):
    return dict(
        id=vote_id, motion_text=text, motion_classification=classification, bill_action=None,
        jurisdiction_id=jurisdiction, bill=bill, start_date="2026-02-11", chamber="lower",
        source=SOURCE.format(84496, action_id), voters=60,
    )


# Real 2026 rows: HB 2689's "COW Motion to Amend" (241050) failed 24-32; HB 2758's third reading (241330) passed
# 32-24; SB 1418's motion to reconsider its failed third reading (242129) passed 16-8.
STEPS = {241050: "MOTION", 241330: "THIRD", 242129: "RECON_3RD"}
ROWS = [
    row("ocd-vote/1", 241050, "failed to pass", ["passage"]),
    row("ocd-vote/2", 241330, "Passed", ["passage"], bill="HB 2758"),
    row("ocd-vote/3", 242129, "Passed", ["passage"], bill="SB 1418"),
]


def test_arizona_follows_the_scrapers_floor_step_rule():
    changes, unclassified = bmc.plan(ROWS, STEPS)
    assert unclassified == 0
    assert [(c["id"], c["floor_step"], c["old"], c["new"]) for c in changes] == [
        ("ocd-vote/1", "MOTION", "passage", ""),
        ("ocd-vote/3", "RECON_3RD", "passage", ""),
    ]


def test_arizona_is_never_reclassified_from_its_text_alone():
    # Without the Bill pages, the text rules would make every "failed to pass" a passage vote again.
    relabelled = [dict(r, motion_classification=[]) for r in ROWS[:1]]
    changes, unclassified = bmc.plan(relabelled, None)
    assert (changes, unclassified) == ([], 1)


def test_arizona_vote_whose_floor_step_is_unknown_is_left_alone():
    changes, unclassified = bmc.plan([row("ocd-vote/9", 999999, "failed to pass", ["passage"])], STEPS)
    assert (changes, unclassified) == ([], 1)


def test_arizona_empty_roll_call_is_left_alone():
    # HB 2918 (2026-03-03): an empty 0-0 "Passed" (MISC) shares its day and text with the real third reading
    # (32-24); the broker keeps one Motion for both, so relabelling the empty one would drop the real vote.
    empty = dict(row("ocd-vote/5", 242129, "Passed", ["passage"], bill="HB 2918"), voters=0)
    changes, unclassified = bmc.plan([empty], STEPS)
    assert (changes, unclassified) == ([], 1)


def test_other_jurisdictions_keep_the_text_rules():
    us = row("ocd-vote/4", 1, "On Passage", [], jurisdiction="ocd-jurisdiction/country:us/government")
    changes, _ = bmc.plan([us], None)
    assert [(c["old"], c["new"]) for c in changes] == [("", "passage")]


def test_floor_steps_are_read_from_the_cached_bill_pages(tmp_path):
    page = {"FloorHeaders": [{"BillStatusActionId": 241050, "CommitteeShortName": "MOTION"},
                             {"BillStatusActionId": 241054, "CommitteeShortName": "COW"}]}
    (tmp_path / "apps.azleg.gov,api,Bill,billNumber=HB2689&sessionId=130&legislativeBody=H,35ef").write_bytes(
        b"status: 200\nContent-Type: application/json\n\n" + json.dumps(page).encode())
    (tmp_path / "apps.azleg.gov,api,BillStatusFloorAction,billStatusActionId=241050,ab").write_bytes(b"[]")
    assert bmc.az_floor_steps(str(tmp_path)) == {241050: "MOTION", 241054: "COW"}


class _Cursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params):
        new, vote_id, old = params
        self.conn.sql.append(" ".join(sql.split()))
        self.rowcount = 1 if self.conn.stored.get(vote_id) == old else 0
        if self.rowcount:
            self.conn.pending[vote_id] = new


class _Conn:
    def __init__(self, stored):
        self.stored = dict(stored)
        self.pending = {}
        self.sql = []

    def cursor(self):
        return _Cursor(self)

    def commit(self):
        self.stored.update(self.pending)

    def rollback(self):
        self.pending = {}


def test_a_stale_row_aborts_the_whole_write(tmp_path):
    changes, _ = bmc.plan(ROWS, STEPS)
    conn = _Conn({"ocd-vote/1": ["passage"], "ocd-vote/3": []})  # vote 3 already changed underneath
    with pytest.raises(SystemExit, match="nothing written"):
        bmc.write(conn, changes, str(tmp_path / "committed.csv"))
    assert conn.stored == {"ocd-vote/1": ["passage"], "ocd-vote/3": []}
    assert os.listdir(tmp_path) == []


def test_commit_then_undo_round_trips(tmp_path):
    changes, _ = bmc.plan(ROWS, STEPS)
    conn = _Conn({"ocd-vote/1": ["passage"], "ocd-vote/3": ["passage"]})
    bmc.write(conn, changes, str(tmp_path / "committed.csv"))
    assert conn.stored == {"ocd-vote/1": [], "ocd-vote/3": []}
    with open(tmp_path / "committed.csv", newline="") as f:
        assert [r["id"] for r in csv.DictReader(f)] == ["ocd-vote/1", "ocd-vote/3"]
    bmc.write(conn, bmc.read_list(str(tmp_path / "committed.csv"), undo=True), None)
    assert conn.stored == {"ocd-vote/1": ["passage"], "ocd-vote/3": ["passage"]}


# OPEN-627: Arizona's stored result is the az scraper's vote_result(): azleg's outcome in the motion text, not yeas >
# nays. Real 2026 rows (Mac replica): HB 2918's third reading failed 28-25 and is stored "pass"; SB 1152's failed 16-11
# (16 is a Senate majority) and is stored "pass"; HB 2913's failed 22-30 and HB 2758's passed 32-24 are right already.
def result_row(vote_id, text, result, yes, no, chamber="lower", voters=60, jurisdiction=AZ, bill="HB 2918"):
    return dict(row(vote_id, 0, text, ["passage"], jurisdiction=jurisdiction, bill=bill), result=result, yes=yes,
                no=no, chamber=chamber, voters=voters)


RESULT_ROWS = [
    result_row("ocd-vote/10", "failed to pass", "pass", 28, 25),
    result_row("ocd-vote/11", "failed to pass", "pass", 16, 11, chamber="upper", voters=30, bill="SB 1152"),
    result_row("ocd-vote/12", "failed to pass", "fail", 22, 30, bill="HB 2913"),
    result_row("ocd-vote/13", "Passed", "pass", 32, 24, bill="HB 2758"),
]


def test_arizona_result_is_azlegs_outcome_not_yeas_over_nays():
    changes, unclassified = bmc.plan_results(RESULT_ROWS)
    assert unclassified == 0
    assert [(c["id"], c["field"], c["old"], c["new"], c["yes"], c["no"]) for c in changes] == [
        ("ocd-vote/10", "result", "pass", "fail", 28, 25),
        ("ocd-vote/11", "result", "pass", "fail", 16, 11),
    ]


def test_arizona_result_leaves_empty_roll_calls_and_other_states_alone():
    empty = result_row("ocd-vote/14", "failed to pass", "pass", 0, 0, voters=0)
    us = result_row("ocd-vote/15", "failed to pass", "pass", 28, 25, jurisdiction="ocd-jurisdiction/country:us/government")
    assert bmc.plan_results([empty, us]) == ([], 2)


def test_result_list_writes_the_result_column_and_undoes(tmp_path):
    changes, _ = bmc.plan_results(RESULT_ROWS)
    conn = _Conn({"ocd-vote/10": "pass", "ocd-vote/11": "pass"})
    bmc.write(conn, changes, str(tmp_path / "committed.csv"))
    assert conn.stored == {"ocd-vote/10": "fail", "ocd-vote/11": "fail"}
    assert all("SET result = %s WHERE id = %s AND result = %s" in sql for sql in conn.sql)
    applied = bmc.read_list(str(tmp_path / "committed.csv"), undo=False)
    assert [(r["field"], r["old"], r["new"]) for r in applied] == [("result", "pass", "fail")] * 2
    bmc.write(conn, bmc.read_list(str(tmp_path / "committed.csv"), undo=True), None)
    assert conn.stored == {"ocd-vote/10": "pass", "ocd-vote/11": "pass"}


def test_a_stale_result_aborts_the_whole_write(tmp_path):
    changes, _ = bmc.plan_results(RESULT_ROWS)
    conn = _Conn({"ocd-vote/10": "pass", "ocd-vote/11": "fail"})  # vote 11 already fixed underneath
    with pytest.raises(SystemExit, match="nothing written"):
        bmc.write(conn, changes, str(tmp_path / "committed.csv"))
    assert conn.stored == {"ocd-vote/10": "pass", "ocd-vote/11": "fail"}


def test_a_list_without_a_field_column_writes_classifications(tmp_path):
    # OPEN-625's reviewed list predates the "field" column.
    path = tmp_path / "open625.csv"
    path.write_text("id,jurisdiction,bill,date,chamber,motion_text,floor_step,voters,old,new\n"
                    "ocd-vote/1,az,HB 2689,2026-02-11,lower,failed to pass,MOTION,56,passage,\n")
    conn = _Conn({"ocd-vote/1": ["passage"]})
    bmc.write(conn, bmc.read_list(str(path), undo=False), None)
    assert conn.stored == {"ocd-vote/1": []}
    assert "SET motion_classification = %s" in conn.sql[0]


def test_an_unknown_field_in_a_list_is_refused():
    with pytest.raises(ValueError, match="unknown field"):
        bmc.write(_Conn({}), [dict(id="ocd-vote/1", field="updated_at", old="a", new="b")], None)
