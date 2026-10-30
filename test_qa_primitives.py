"""
Tests for qa_primitives.py (OPEN-445) -- the shared DB queries verify-jurisdiction and
quality_check.py both call, scoped by jurisdiction. No real Postgres connection needed: every
DB-touching test uses a fake conn/cursor, same convention as test_quality_check.py.
"""

from qa_primitives import (
    ocd_jurisdiction_id,
    count_people_loaded,
    find_db_vote_key_collisions,
    attribution_resolution_rates,
)


# ── Fakes ──────────────────────────────────────────────────────────────────────

class FakeCursor:
    """fetchone_results / fetchall_results are consumed in call order -- one entry per
    cursor.execute() the function under test performs, in the order it performs them."""
    def __init__(self, fetchone_results=None, fetchall_results=None):
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self.executed = []

    def execute(self, sql, params):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._fetchone_results.pop(0)

    def fetchall(self):
        return self._fetchall_results.pop(0)


class FakeConn:
    def __init__(self, fetchone_results=None, fetchall_results=None):
        self._cursor = FakeCursor(fetchone_results, fetchall_results)

    def cursor(self):
        return self._cursor


# ── ocd_jurisdiction_id() ───────────────────────────────────────────────────────

def test_ocd_jurisdiction_id_us_branch():
    assert ocd_jurisdiction_id("us") == "ocd-jurisdiction/country:us/government"


def test_ocd_jurisdiction_id_state_branch():
    assert ocd_jurisdiction_id("nc") == "ocd-jurisdiction/country:us/state:nc/government"
    assert ocd_jurisdiction_id("fl") == "ocd-jurisdiction/country:us/state:fl/government"


# ── count_people_loaded() ───────────────────────────────────────────────────────

def test_count_people_loaded_zero():
    conn = FakeConn(fetchone_results=[(0,)])
    assert count_people_loaded(conn, "nc") == 0


def test_count_people_loaded_positive():
    conn = FakeConn(fetchone_results=[(508,)])
    assert count_people_loaded(conn, "nc") == 508


def test_count_people_loaded_scopes_by_jurisdiction_id():
    conn = FakeConn(fetchone_results=[(1,)])
    count_people_loaded(conn, "nc")
    sql, params = conn._cursor.executed[0]
    assert params == ("ocd-jurisdiction/country:us/state:nc/government",)
    assert "opencivicdata_membership" in sql
    assert "opencivicdata_organization" in sql


# ── find_db_vote_key_collisions() ───────────────────────────────────────────────

def test_find_db_vote_key_collisions_no_collision():
    rows = [
        ("key-a", "2025", "HB1"),
        ("key-b", "2025", "HB2"),
    ]
    conn = FakeConn(fetchall_results=[rows])
    collisions, n_sessions = find_db_vote_key_collisions(conn, "nc")
    assert collisions == {}
    assert n_sessions == 1


def test_find_db_vote_key_collisions_detects_cross_session_repeat():
    rows = [
        ("key-a", "2025", "HB1"),
        ("key-a", "2025E1", "HB1"),  # OPEN-397 shape: same key, different session
    ]
    conn = FakeConn(fetchall_results=[rows])
    collisions, n_sessions = find_db_vote_key_collisions(conn, "nc")
    assert collisions == {"key-a": [("2025", "HB1"), ("2025E1", "HB1")]}
    assert n_sessions == 2


def test_find_db_vote_key_collisions_detects_cross_bill_repeat_same_session():
    rows = [
        ("key-a", "2025", "HB1"),
        ("key-a", "2025", "HB2"),
    ]
    conn = FakeConn(fetchall_results=[rows])
    collisions, n_sessions = find_db_vote_key_collisions(conn, "nc")
    assert collisions == {"key-a": [("2025", "HB1"), ("2025", "HB2")]}
    assert n_sessions == 1


def test_find_db_vote_key_collisions_same_session_and_bill_is_not_a_collision():
    # A key re-yielded for the same (session, bill) -- e.g. two PersonVote-adjacent rows for one
    # VoteEvent that both carry its dedupe_key -- is one vote, not a collision.
    rows = [
        ("key-a", "2025", "HB1"),
        ("key-a", "2025", "HB1"),
    ]
    conn = FakeConn(fetchall_results=[rows])
    collisions, n_sessions = find_db_vote_key_collisions(conn, "nc")
    assert collisions == {}
    assert n_sessions == 1


def test_find_db_vote_key_collisions_no_votes_at_all():
    conn = FakeConn(fetchall_results=[[]])
    collisions, n_sessions = find_db_vote_key_collisions(conn, "nc")
    assert collisions == {}
    assert n_sessions == 0


def test_find_db_vote_key_collisions_scopes_by_jurisdiction_id():
    conn = FakeConn(fetchall_results=[[]])
    find_db_vote_key_collisions(conn, "fl")
    sql, params = conn._cursor.executed[0]
    assert params == ("ocd-jurisdiction/country:us/state:fl/government",)
    assert "opencivicdata_voteevent" in sql
    assert "dedupe_key IS NOT NULL" in sql


# ── attribution_resolution_rates() ──────────────────────────────────────────────

def test_attribution_resolution_rates_counts_null_voter_id_as_unresolved():
    # (votes_total, votes_unresolved), (sponsorships_total, sponsorships_unresolved)
    conn = FakeConn(fetchone_results=[(72058, 611), (26095, 898)])
    rates = attribution_resolution_rates(conn, "nc")
    assert rates["votes"] == {"total": 72058, "unresolved": 611}
    assert rates["sponsorships"] == {"total": 26095, "unresolved": 898}


def test_attribution_resolution_rates_handles_zero_population():
    conn = FakeConn(fetchone_results=[(0, 0), (0, 0)])
    rates = attribution_resolution_rates(conn, "nc")
    assert rates["votes"] == {"total": 0, "unresolved": 0}
    assert rates["sponsorships"] == {"total": 0, "unresolved": 0}


def test_attribution_resolution_rates_votes_query_scopes_by_jurisdiction_and_voter_id_null():
    conn = FakeConn(fetchone_results=[(1, 0), (1, 0)])
    attribution_resolution_rates(conn, "va")
    votes_sql, votes_params = conn._cursor.executed[0]
    assert votes_params == ("ocd-jurisdiction/country:us/state:va/government",)
    assert "opencivicdata_personvote" in votes_sql
    assert "voter_id IS NULL" in votes_sql


def test_attribution_resolution_rates_sponsorships_query_filters_entity_type_person():
    # Regression test for the denominator-ambiguity risk flagged during planning: organization-type
    # sponsorships must not dilute the measured person-attribution rate.
    conn = FakeConn(fetchone_results=[(1, 0), (1, 0)])
    attribution_resolution_rates(conn, "va")
    sponsorships_sql, sponsorships_params = conn._cursor.executed[1]
    assert sponsorships_params == ("ocd-jurisdiction/country:us/state:va/government",)
    assert "opencivicdata_billsponsorship" in sponsorships_sql
    assert "entity_type = 'person'" in sponsorships_sql
    assert "person_id IS NULL" in sponsorships_sql
