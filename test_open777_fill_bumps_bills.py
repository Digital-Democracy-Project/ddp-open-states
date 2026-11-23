"""OPEN-777: the blank-voter fill scripts mark the bills of the roll calls they fill as updated (opencivicdata_bill.
updated_at), in the same transaction, so the broker's after-scrape fetch (api-v3 `updated_since`) reads the fills once
the nightly chain stops on 2027-01-01. A dry run marks nothing.

The first tests use stand-in connections that record every statement. The last is opt-in and runs each script's own
SQL on a throwaway PostgreSQL database: set OPEN777_TEST_DB to a libpq connection string for an EMPTY scratch database
(never production, never the replica); it creates two tables there and drops them.
"""
import importlib.util
import os
import sys
from unittest import mock

import psycopg2
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rbv = _load("relink_blank_voters_777", "relink-blank-voters.py")
bvp = _load("backfill_vote_person_777", "backfill-vote-person-resolution.py")


class _RecordingCursor:
    def __init__(self, log, rows=()):
        self.log, self.rows, self.rowcount = log, list(rows), 1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.log.append((sql, params))

    def fetchall(self):
        return self.rows


class _Conn:
    def __init__(self, rows=()):
        self.log, self.rows, self.autocommit, self.committed = [], rows, False, False

    def cursor(self, cursor_factory=None):
        return _RecordingCursor(self.log, self.rows)

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        pass


def _bumps(conn, sql):
    return [params for statement, params in conn.log if statement == sql]


# ── relink-blank-voters.py (states) ─────────────────────────────────────────

FILLED = [
    dict(pv_id=1, vote_event="ocd-vote/a", person_id="ocd-person/p", bill="HB 1", state="wa", session="s",
         date="2025-01-24", motion="m", option="yes", voter_name="Hunt", person_name="Victoria Hunt"),
    dict(pv_id=2, vote_event="ocd-vote/a", person_id="ocd-person/p", bill="HB 1", state="wa", session="s",
         date="2025-01-24", motion="m", option="yes", voter_name="Hunt", person_name="Victoria Hunt"),
    dict(pv_id=3, vote_event="ocd-vote/b", person_id="ocd-person/p", bill="HB 2", state="wa", session="s",
         date="2025-02-01", motion="m", option="no", voter_name="Hunt", person_name="Victoria Hunt"),
]


def _relink(tmp_path, *argv):
    conn = _Conn()
    with mock.patch.object(rbv, "plan_case", return_value=(FILLED, [(9, "left blank")])), mock.patch.object(
        rbv.psycopg2, "connect", return_value=conn
    ), mock.patch.object(rbv, "CASES", [("wa", "lower", "Hunt")]):
        rbv.main(list(argv))
    return conn


def test_a_relink_commit_marks_the_bills_of_the_filled_roll_calls(tmp_path):
    conn = _relink(tmp_path, "--commit", "--list", str(tmp_path / "l.csv"))
    # each roll call once; the left-blank row (pv 9) is not in the plan's fill, so its roll call is not named
    assert _bumps(conn, rbv.BUMP_BILLS_SQL) == [dict(events=["ocd-vote/a", "ocd-vote/b"])]
    # in the same transaction: after the fills, before the commit
    statements = [statement for statement, _ in conn.log]
    assert statements.index(rbv.BUMP_BILLS_SQL) > statements.index(rbv.UPDATE_SQL)
    assert conn.committed


def test_a_relink_dry_run_marks_nothing(tmp_path):
    conn = _relink(tmp_path)
    assert _bumps(conn, rbv.BUMP_BILLS_SQL) == [] and not conn.committed


# ── backfill-vote-person-resolution.py (US) ─────────────────────────────────

NULL_VOTES = [
    dict(id=1, note="W000823", vote_event_id="ocd-vote/a"),  # resolves
    dict(id=2, note="W000823", vote_event_id="ocd-vote/a"),  # resolves, same roll call
    dict(id=3, note="NOBODY01", vote_event_id="ocd-vote/c"),  # does not resolve: its roll call is not marked
]


def _backfill(*argv):
    conn = _Conn(rows=NULL_VOTES)
    with mock.patch.object(bvp.psycopg2, "connect", return_value=conn), mock.patch.object(
        bvp, "build_identifier_map", return_value={"W000823": [("ocd-person/w", True)]}
    ), mock.patch.object(bvp.psycopg2.extras, "execute_batch"), mock.patch.object(
        sys, "argv", ["backfill-vote-person-resolution.py", *argv]
    ):
        bvp.main()
    return conn


def test_a_backfill_commit_marks_only_the_bills_of_resolved_votes():
    conn = _backfill()
    assert _bumps(conn, bvp.BUMP_BILLS_SQL) == [dict(events=["ocd-vote/a"])]
    assert conn.committed


def test_a_backfill_dry_run_marks_nothing():
    conn = _backfill("--dry-run")
    assert _bumps(conn, bvp.BUMP_BILLS_SQL) == [] and not conn.committed


# ── both scripts' SQL on a real database (opt-in) ───────────────────────────


@pytest.mark.skipif(not os.getenv("OPEN777_TEST_DB"), reason="set OPEN777_TEST_DB to an empty scratch database")
@pytest.mark.parametrize("module", [rbv, bvp], ids=["relink", "backfill"])
def test_only_the_filled_roll_calls_bills_move(module):
    conn = psycopg2.connect(os.environ["OPEN777_TEST_DB"])
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE opencivicdata_bill (id text PRIMARY KEY, updated_at timestamptz NOT NULL);"
                "CREATE TABLE opencivicdata_voteevent (id text PRIMARY KEY, bill_id text NOT NULL);"
                "INSERT INTO opencivicdata_bill VALUES ('bill-1', '2026-01-01'), ('bill-2', '2026-01-01'),"
                " ('bill-3', '2026-01-01');"
                "INSERT INTO opencivicdata_voteevent VALUES ('ocd-vote/a', 'bill-1'), ('ocd-vote/b', 'bill-1'),"
                " ('ocd-vote/c', 'bill-2'), ('ocd-vote/d', 'bill-3');"
            )
            cur.execute(module.BUMP_BILLS_SQL, dict(events=["ocd-vote/a", "ocd-vote/b", "ocd-vote/c"]))
            assert cur.rowcount == 2  # two bills, each once
            cur.execute("SELECT id FROM opencivicdata_bill WHERE updated_at > '2026-01-01' ORDER BY id")
            assert [r[0] for r in cur.fetchall()] == ["bill-1", "bill-2"]
            cur.execute(module.BUMP_BILLS_SQL, dict(events=[]))
            assert cur.rowcount == 0  # nothing filled, nothing marked
    finally:
        conn.rollback()  # the tables were made inside this transaction: nothing stays
        conn.close()


@pytest.mark.skipif(not os.getenv("OPEN777_TEST_DB"), reason="set OPEN777_TEST_DB to an empty scratch database")
@pytest.mark.parametrize("module", [rbv, bvp], ids=["relink", "backfill"])
def test_the_mark_is_later_than_a_broker_cutoff_taken_while_the_run_was_planning(module):
    # pm-review: the scripts hold one transaction from planning to commit. A broker fetch that starts meanwhile records
    # its cutoff then; the bill's new timestamp must be after it, not the transaction's start (now()).
    conn = psycopg2.connect(os.environ["OPEN777_TEST_DB"])
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE opencivicdata_bill (id text PRIMARY KEY, updated_at timestamptz NOT NULL);"
                "CREATE TABLE opencivicdata_voteevent (id text PRIMARY KEY, bill_id text NOT NULL);"
                "INSERT INTO opencivicdata_bill VALUES ('bill-1', '2026-01-01');"
                "INSERT INTO opencivicdata_voteevent VALUES ('ocd-vote/a', 'bill-1');"
            )
            cur.execute("SELECT pg_sleep(0.2), clock_timestamp()")  # the planning; a broker cutoff taken during it
            cutoff = cur.fetchone()[1]
            cur.execute(module.BUMP_BILLS_SQL, dict(events=["ocd-vote/a"]))
            cur.execute("SELECT updated_at FROM opencivicdata_bill WHERE id = 'bill-1'")
            assert cur.fetchone()[0] > cutoff
    finally:
        conn.rollback()
        conn.close()
