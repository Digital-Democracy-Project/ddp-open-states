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


# --- The rules that choose who gets a vote (PM review of #407, comment 21119): plan_case itself. ---------------------


class _PlanCursor:
    """Answers plan_case's three queries from the test's own data: the blank rows, the people the (real) date-anchored
    query would return for each date, and who already voted on each roll call."""

    def __init__(self, blank_rows, candidates_by_day, voters_by_event):
        self.blank_rows, self.candidates_by_day, self.voters_by_event = blank_rows, candidates_by_day, voters_by_event
        self._result = []

    def execute(self, sql, params):
        if sql is rbv.FETCH_BLANK_ROWS_SQL:
            self._result = list(self.blank_rows)
        elif sql is rbv.CANDIDATES_ON_DATE_SQL:
            self._result = list(self.candidates_by_day.get(params["day"], []))
        elif sql is rbv.DUPLICATE_CHECK_SQL:
            event, person = params
            self._result = [(1,)] if person in self.voters_by_event.get(event, ()) else []
        else:
            raise AssertionError(f"unexpected query: {sql[:60]}")

    def fetchall(self):
        return self._result

    def fetchone(self):
        return self._result[0] if self._result else None


HUNT = ("ocd-person/hunt", "Victoria Hunt")
OTHER_HUNT = ("ocd-person/other", "Sam Hunt")


def _blank(pv_id, event, day):
    return (pv_id, event, day, "final passage", "HB 1", "2025-2026", "yes")


def test_plan_fills_only_a_row_with_exactly_one_person_on_that_date():
    cur = _PlanCursor(
        [_blank(1, "e1", "2025-02-01"), _blank(2, "e2", "2025-03-01"), _blank(3, "e3", "2025-04-01")],
        {"2025-02-01": [HUNT], "2025-03-01": [HUNT, OTHER_HUNT], "2025-04-01": []},
        {},
    )
    fill, left = rbv.plan_case(cur, "wa", "lower", "Hunt")
    assert [(r["pv_id"], r["person_id"]) for r in fill] == [(1, HUNT[0])]
    assert sorted(left) == [
        (2, "2 people of that name held a seat on 2025-03-01"),
        (3, "0 people of that name held a seat on 2025-04-01"),
    ]


def test_plan_never_fills_a_person_already_on_that_roll_call():
    cur = _PlanCursor(
        [_blank(1, "e1", "2025-02-01"), _blank(2, "e2", "2025-02-01")],
        {"2025-02-01": [HUNT]},
        {"e2": {HUNT[0]}},
    )
    fill, left = rbv.plan_case(cur, "wa", "lower", "Hunt")
    assert [r["pv_id"] for r in fill] == [1]
    assert left == [(2, "Victoria Hunt is already a voter on that roll call")]


def test_plan_asks_for_the_people_on_each_vote_s_own_date_in_that_state_and_chamber():
    cur = _PlanCursor([_blank(1, "e1", "2025-02-01")], {"2025-02-01": [HUNT]}, {})
    asked = []
    real = cur.execute

    def spy(sql, params):
        if sql is rbv.CANDIDATES_ON_DATE_SQL:
            asked.append(params)
        real(sql, params)

    cur.execute = spy
    rbv.plan_case(cur, "wa", "lower", "Hunt")
    assert asked == [
        dict(name="Hunt", chamber="lower", jid="ocd-jurisdiction/country:us/state:wa/government", day="2025-02-01")
    ]


# --- The date-anchored query itself, on a real Postgres (set RELINK_TEST_DATABASE_URL to a throwaway database). -----

SCHEMA = """
CREATE TABLE opencivicdata_person (id text PRIMARY KEY, name text, family_name text);
CREATE TABLE opencivicdata_personname (id serial PRIMARY KEY, person_id text, name text);
CREATE TABLE opencivicdata_organization (id text PRIMARY KEY, classification text, jurisdiction_id text);
CREATE TABLE opencivicdata_membership (id serial PRIMARY KEY, person_id text, organization_id text,
    start_date text DEFAULT '', end_date text DEFAULT '');
CREATE TABLE opencivicdata_legislativesession (id text PRIMARY KEY, identifier text, jurisdiction_id text);
CREATE TABLE opencivicdata_bill (id text PRIMARY KEY, identifier text);
CREATE TABLE opencivicdata_voteevent (id text PRIMARY KEY, organization_id text, legislative_session_id text,
    bill_id text, start_date text, motion_text text);
CREATE TABLE opencivicdata_personvote (id serial PRIMARY KEY, vote_event_id text, voter_id text, voter_name text,
    option text);
"""


@pytest.fixture
def db():
    url = os.environ.get("RELINK_TEST_DATABASE_URL")
    if not url:
        pytest.skip("RELINK_TEST_DATABASE_URL not set (a throwaway Postgres)")
    conn = rbv.psycopg2.connect(url)
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS relink_test CASCADE; CREATE SCHEMA relink_test")
        cur.execute("SET search_path TO relink_test")
        cur.execute(SCHEMA)
    yield conn
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS relink_test CASCADE")
    conn.commit()
    conn.close()


def _seed_washington(cur):
    """Washington's real shape (production replica, 2026-11-17): Victoria Hunt in the House from 2025-01-13 to
    2025-06-03 (other name "Hunt"), two earlier House Hunts, and a Senate Hunt."""
    wa = "ocd-jurisdiction/country:us/state:wa/government"
    cur.execute(
        "INSERT INTO opencivicdata_organization VALUES ('house', 'lower', %s), ('senate', 'upper', %s)", (wa, wa)
    )
    cur.execute(
        "INSERT INTO opencivicdata_person VALUES ('victoria', 'Victoria Hunt', 'Hunt'), ('sam', 'Sam Hunt', 'Hunt'),"
        " ('graham', 'Graham Hunt', 'Hunt'), ('sen', 'Senator Hunt', 'Hunt')"
    )
    cur.execute("INSERT INTO opencivicdata_personname (person_id, name) VALUES ('victoria', 'Hunt')")
    cur.execute(
        "INSERT INTO opencivicdata_membership (person_id, organization_id, start_date, end_date) VALUES"
        " ('victoria', 'house', '2025-01-13', '2025-06-03'), ('sam', 'house', '2011-01-01', '2018-12-31'),"
        " ('graham', 'house', '2013-01-01', '2016-12-31'), ('sen', 'senate', '2020-01-01', '')"
    )
    cur.execute("INSERT INTO opencivicdata_legislativesession VALUES ('s', '2025-2026', %s)", (wa,))
    cur.execute("INSERT INTO opencivicdata_bill VALUES ('b', 'HB 1')")
    for event, day in (("e1", "2025-02-01"), ("e2", "2025-09-01"), ("e3", "2025-02-02")):
        cur.execute("INSERT INTO opencivicdata_voteevent VALUES (%s, 'house', 's', 'b', %s, 'passage')", (event, day))
    cur.execute(
        "INSERT INTO opencivicdata_personvote (vote_event_id, voter_id, voter_name, option) VALUES"
        " ('e1', NULL, 'Hunt', 'yes'),"  # 2025-02-01: only Victoria Hunt held a House seat -> filled
        " ('e2', NULL, 'Hunt', 'no'),"  # 2025-09-01: she had left the House; no Hunt held one -> blank
        " ('e3', NULL, 'Hunt', 'yes'), ('e3', 'victoria', 'Victoria Hunt', 'yes')"  # already on that roll call -> blank
    )


def test_the_real_query_fills_by_the_vote_s_date_and_never_twice(db):
    with db.cursor() as cur:
        _seed_washington(cur)
        fill, left = rbv.plan_case(cur, "wa", "lower", "Hunt")
    assert [(r["vote_event"], r["person_id"]) for r in fill] == [("e1", "victoria")]
    assert sorted(why for _, why in left) == [
        "0 people of that name held a seat on 2025-09-01",
        "Victoria Hunt is already a voter on that roll call",
    ]
