"""
Tests for fix-open433-az-stale-empty-vote-events.py.

The breakdown tests are pure. The SQL cross-check is opt-in and read-only: set
OPEN433_TEST_DB to a database that holds Arizona rows (a copy, not production) and it
recomputes the script's predicate in Python from the raw tables and compares.
"""
import importlib.util
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "fix_open433", os.path.join(HERE, "fix-open433-az-stale-empty-vote-events.py")
)
fix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fix)


def row(vid, bill, cls, date, chamber="lower", session="57th-2nd-regular", shape="all-zero counts"):
    return (vid, bill, cls, date, chamber, session, shape)


def test_breakdown_splits_passage_rows_by_whether_a_real_passage_vote_exists():
    stale = [
        row("v1", "b1", ["passage"], "2026-03-10"),  # after the real vote
        row("v2", "b1", ["passage"], "2026-03-01"),  # before it
        row("v3", "b2", ["passage"], "2026-03-10"),  # no real vote at all in that chamber
        row("v4", "b3", ["passage"], "2026-03-10", "upper"),  # real vote only in the other chamber
        row("v5", "b1", ["committee-passage"], "2026-03-02"),
        row("v6", "b1", [], "2026-03-02"),
        row("v7", "b1", None, "2026-03-02"),
    ]
    real = {("b1", "lower"): ["2026-03-05"], ("b3", "lower"): ["2026-03-05"]}
    out = fix.breakdown(stale, real, {"b1": 9, "b2": 1, "b3": 4})
    assert out["passage-tagged"] == 4
    assert out["  passage-tagged, dated after a real passage vote"] == 1
    assert out["  passage-tagged, same day or before a real passage vote"] == 1
    assert out["  passage-tagged, no real passage vote in that chamber"] == 2
    assert out["committee-passage-tagged"] == 1
    assert out["untagged"] == 2


def test_breakdown_counts_bills_left_with_no_vote_event():
    stale = [row("v1", "b1", [], "2026-03-01"), row("v2", "b1", [], "2026-03-02"), row("v3", "b2", [], "2026-03-01")]
    # b1 has exactly its two stale events; b2 has a real vote besides its stale one
    out = fix.breakdown(stale, {}, {"b1": 2, "b2": 2})
    assert out["bills touched"] == 2
    assert out["bills left with no vote event at all"] == 1


def test_breakdown_reports_sessions_and_count_row_shapes():
    stale = [row("v1", "b1", [], "2026-03-01"), row("v2", "b2", [], "2026-03-01", session="56th", shape="no count rows")]
    out = fix.breakdown(stale, {}, {})
    assert out["session 57th-2nd-regular"] == 1 and out["session 56th"] == 1
    assert out["count rows: all-zero counts"] == 1 and out["count rows: no count rows"] == 1


@pytest.mark.parametrize(
    "argv",
    [
        [],  # nothing
        ["--save-dir", "x", "--session", "s"],  # no --expect-events
        ["--save-dir", "x", "--expect-events", "1"],  # no --session
        ["--session", "s", "--expect-events", "1"],  # no --save-dir
    ],
)
def test_a_real_run_refuses_to_start_without_all_three_guards(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", ["fix"] + argv)
    monkeypatch.setattr(fix.psycopg2, "connect", lambda **kw: pytest.fail("must not connect"))
    with pytest.raises(SystemExit):
        fix.main()


def test_predicate_only_matches_what_the_scraper_would_skip():
    sql = " ".join(fix.STALE_SQL.split())
    for clause in (
        "vc.value <> 0",  # any non-zero count protects the event
        "opencivicdata_personvote",  # any voter protects it
        "opencivicdata_eventrelatedentity",
        "src.url LIKE",  # only events the azleg floor-action feed produced
    ):
        assert clause in sql
    assert fix.JURISDICTION_ID.endswith("state:az/government")


@pytest.mark.skipif(not os.getenv("OPEN433_TEST_DB"), reason="set OPEN433_TEST_DB to a copy that holds Arizona rows")
def test_sql_predicate_matches_an_independent_python_derivation():
    import psycopg2

    cfg = dict(fix.DB_CONFIG, dbname=os.environ["OPEN433_TEST_DB"])
    conn = psycopg2.connect(**cfg)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    cur.execute(
        fix.STALE_SQL,
        {"jurisdiction": fix.JURISDICTION_ID, "source": fix.FLOOR_ACTION_SOURCE, "sessions": None},
    )
    from_sql = {r[0] for r in cur.fetchall()}

    cur.execute(
        "SELECT ve.id FROM opencivicdata_voteevent ve JOIN opencivicdata_legislativesession s "
        "ON s.id = ve.legislative_session_id WHERE s.jurisdiction_id = %s",
        (fix.JURISDICTION_ID,),
    )
    all_ids = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT vote_event_id, value FROM opencivicdata_votecount")
    nonzero = {v for v, n in cur.fetchall() if n != 0}
    cur.execute("SELECT DISTINCT vote_event_id FROM opencivicdata_personvote")
    voters = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT DISTINCT vote_event_id FROM opencivicdata_eventrelatedentity WHERE vote_event_id IS NOT NULL")
    related = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT vote_event_id, url FROM opencivicdata_votesource")
    prefix = "https://apps.azleg.gov/api/BillStatusFloorAction?"
    floor = {v for v, u in cur.fetchall() if u.startswith(prefix) and "includeVotes=true" in u}
    expected = {i for i in all_ids if i not in nonzero and i not in voters and i not in related and i in floor}
    conn.rollback()
    conn.close()

    assert from_sql == expected
    assert from_sql, "the copy should hold stale Arizona rows, otherwise this proves nothing"
    assert not (from_sql & nonzero) and not (from_sql & voters)
