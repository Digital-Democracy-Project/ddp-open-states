"""OPEN-622: fix-ut-passage-chamber.py. A stored Utah passage line moves to the chamber its text names (the scraper's
own rule), nothing else moves, and a write either applies every planned change or none. No database: rows and the
connection are stand-ins; the plan itself is checked by the dry run on the replica and the commit + undo rehearsal on
a throwaway copy (OPEN-622)."""
import csv
import importlib.util
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("fix_ut_passage_chamber", os.path.join(HERE, "fix-ut-passage-chamber.py"))
fix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fix)

HOUSE, SENATE = "ocd-organization/house", "ocd-organization/senate"
ORGS = {"lower": HOUSE, "upper": SENATE}


def row(action_id, description, chamber, bill="HB 209"):
    return dict(
        id=action_id, bill_id=f"ocd-bill/{bill}", bill=bill, session="2026", order=1, date="2026-01-26",
        description=description, organization_id=ORGS[chamber], chamber=chamber,
    )


# HB 209 (2026) as stored on the replica: the House's passage under the Senate, the Senate's suspension passage under
# the House; SB 98's House passage already under the House.
ROWS = [
    row("a1", "House/ passed 3rd reading", "upper"),
    row("a2", "House/ to Senate", "upper"),
    row("a3", "Senate/ passed 2nd reading", "upper"),
    row("a4", "Senate/ passed 2nd & 3rd readings/ suspension", "lower"),
    row("a5", "House/ concurs with Senate amendment", "upper"),
    row("a6", "Senate/ signed by President/ returned to House", "lower"),
    row("a7", "House/ passed 3rd reading", "lower", bill="SB 98"),
    row("a8", "Senate/ passed 3rd reading", "lower", bill="SB 98"),
]


def test_passage_lines_move_to_the_chamber_that_voted_and_nothing_else_moves():
    changes = fix.plan(ROWS, ORGS)
    assert [(c["id"], c["old_chamber"], c["new_chamber"], c["old_org"], c["new_org"]) for c in changes] == [
        ("a1", "upper", "lower", SENATE, HOUSE),
        ("a4", "lower", "upper", HOUSE, SENATE),
        ("a8", "lower", "upper", HOUSE, SENATE),
    ]


def test_a_second_run_finds_nothing():
    moved = {c["id"]: c["new_chamber"] for c in fix.plan(ROWS, ORGS)}
    after = [dict(r, chamber=moved.get(r["id"], r["chamber"]), organization_id=ORGS[moved.get(r["id"], r["chamber"])])
             for r in ROWS]
    assert fix.plan(after, ORGS) == []


class _Cursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params):
        if sql == fix.TOUCH_SQL:
            self.conn.pending_touched |= set(params[0])
            return
        new, action_id, old, description = params
        stored = self.conn.stored.get(action_id)
        self.rowcount = 1 if stored == (old, description) else 0
        if self.rowcount:
            self.conn.pending[action_id] = (new, description)


class _Conn:
    def __init__(self, stored):
        self.stored = dict(stored)
        self.pending, self.pending_touched, self.touched = {}, set(), set()

    def cursor(self):
        return _Cursor(self)

    def commit(self):
        self.stored.update(self.pending)
        self.touched |= self.pending_touched

    def rollback(self):
        self.pending, self.pending_touched = {}, set()


def stored(rows):
    return {r["id"]: (r["organization_id"], r["description"]) for r in rows}


def test_a_stale_action_aborts_the_whole_write(tmp_path):
    changes = fix.plan(ROWS, ORGS)
    before = stored(ROWS)
    before["a8"] = (SENATE, "Senate/ passed 3rd reading")  # already moved underneath (a re-scrape)
    conn = _Conn(before)
    with pytest.raises(SystemExit, match="nothing written"):
        fix.write(conn, changes, str(tmp_path / "committed.csv"))
    assert conn.stored == before and conn.touched == set()
    assert os.listdir(tmp_path) == []


def test_changed_text_aborts_the_whole_write(tmp_path):
    changes = fix.plan(ROWS, ORGS)
    before = stored(ROWS)
    before["a1"] = (SENATE, "House/ passed 3rd reading/ reconsidered")
    conn = _Conn(before)
    with pytest.raises(SystemExit, match="nothing written"):
        fix.write(conn, changes, None)
    assert conn.stored == before


def test_commit_moves_updated_at_and_undo_round_trips(tmp_path):
    changes = fix.plan(ROWS, ORGS)
    conn = _Conn(stored(ROWS))
    fix.write(conn, changes, str(tmp_path / "committed.csv"))
    assert conn.stored["a1"][0] == HOUSE and conn.stored["a4"][0] == SENATE and conn.stored["a8"][0] == SENATE
    assert conn.stored["a2"][0] == SENATE  # untouched
    assert conn.touched == {"ocd-bill/HB 209", "ocd-bill/SB 98"}
    with open(tmp_path / "committed.csv", newline="") as f:
        assert [r["id"] for r in csv.DictReader(f)] == ["a1", "a4", "a8"]
    fix.write(conn, fix.read_list(str(tmp_path / "committed.csv"), undo=True), None)
    assert conn.stored == stored(ROWS)


def test_a_list_from_another_script_is_refused(tmp_path):
    other = tmp_path / "other.csv"
    other.write_text("id,jurisdiction,bill,date,chamber,motion_text,floor_step,voters,old,new\n")
    with pytest.raises(SystemExit, match="not a change list"):
        fix.read_list(str(other), undo=False)
