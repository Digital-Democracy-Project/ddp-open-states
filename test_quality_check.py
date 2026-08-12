"""
Tests for quality_check.py's OPEN-32 additions: the per-voter diff that fires inside
compare_bills()'s existing vote-tally-mismatch branch, and the same-date blast-radius
helper that sizes how many other local bills share an identical voter-diff signature.

Greenfield: quality_check.py had no test coverage before this file. psycopg2-binary is
installed in this environment, so the module imports standalone with no real Postgres
connection needed for any test here -- every DB-touching test uses a fake conn/cursor.
"""

from quality_check import (
    diff_voters,
    describe_voter_diff,
    count_shared_date_signature,
    compare_bills,
    split_missing_by_docket_prefix,
    breakdown_by_prefix,
    Report,
    PASS,
    WARN,
)


# ── Fakes ──────────────────────────────────────────────────────────────────────

class FakeCursor:
    def __init__(self, count):
        self.count = count
        self.executed = []

    def execute(self, sql, params):
        self.executed.append((sql, params))

    def fetchone(self):
        return (self.count,)


class FakeConn:
    def __init__(self, count=0):
        self._cursor = FakeCursor(count)

    def cursor(self):
        return self._cursor


# ── Test data builders ─────────────────────────────────────────────────────────

def make_vote_event(date, motion_text, counts, votes):
    """counts: {option: value}. votes: list of (voter_name, option) tuples."""
    return {
        "start_date": f"{date} 14:00:00+00:00",
        "motion_text": motion_text,
        "counts": [{"option": opt, "value": val} for opt, val in counts.items()],
        "votes": [{"voter_name": name, "option": opt} for name, opt in votes],
    }


def make_bill(identifier, votes_events, title="Test Bill", sponsorships=None):
    return {
        "identifier": identifier,
        "title": title,
        "latest_action_description": "Referred to committee",
        "votes": votes_events,
        "sponsorships": sponsorships or [],
    }


def checks_for(report, needle):
    return [c for c in report.checks if needle in c[1]]


# ── diff_voters() ───────────────────────────────────────────────────────────────

def test_diff_voters_identical_votes_yields_no_diff():
    lv = make_vote_event("2026-02-17", "Passed", {"yes": 2}, [("Alice", "yes"), ("Bob", "yes")])
    rv = make_vote_event("2026-02-17", "Passed", {"yes": 2}, [("Bob", "yes"), ("Alice", "yes")])
    local_only, live_only = diff_voters(lv, rv)
    assert local_only == set()
    assert live_only == set()


def test_diff_voters_finds_voter_present_local_only():
    # The exact OPEN-26/Bennett-Parker shape: one extra "yes" voter in local, not live.
    lv = make_vote_event("2026-02-17", "Passed", {"yes": 2, "no": 0},
                          [("Alice", "yes"), ("Bennett-Parker", "yes")])
    rv = make_vote_event("2026-02-17", "Passed", {"yes": 1, "no": 0}, [("Alice", "yes")])
    local_only, live_only = diff_voters(lv, rv)
    assert local_only == {("Bennett-Parker", "yes")}
    assert live_only == set()


def test_diff_voters_finds_voter_present_live_only():
    lv = make_vote_event("2026-07-03", "Passed", {"yes": 1}, [("Alice", "yes")])
    rv = make_vote_event("2026-07-03", "Passed", {"yes": 2}, [("Alice", "yes"), ("Chen", "yes")])
    local_only, live_only = diff_voters(lv, rv)
    assert local_only == set()
    assert live_only == {("Chen", "yes")}


def test_diff_voters_finds_multiple_simultaneous_diffs():
    lv = make_vote_event("2026-02-17", "Passed", {"yes": 2, "no": 1},
                          [("Alice", "yes"), ("Bennett-Parker", "yes"), ("Carl", "no")])
    rv = make_vote_event("2026-02-17", "Passed", {"yes": 1, "no": 0},
                          [("Alice", "yes"), ("Dana", "no")])
    local_only, live_only = diff_voters(lv, rv)
    assert local_only == {("Bennett-Parker", "yes"), ("Carl", "no")}
    assert live_only == {("Dana", "no")}


def test_diff_voters_handles_missing_votes_key_defensively():
    lv = {"start_date": "2026-01-01 00:00:00+00:00", "motion_text": "Passed", "counts": []}
    rv = {"start_date": "2026-01-01 00:00:00+00:00", "motion_text": "Passed", "counts": [],
          "votes": None}
    local_only, live_only = diff_voters(lv, rv)
    assert local_only == set()
    assert live_only == set()


# ── describe_voter_diff() ───────────────────────────────────────────────────────

def test_describe_voter_diff_single_local_only_voter():
    msg = describe_voter_diff({("Bennett-Parker", "yes")}, set())
    assert msg == "Bennett-Parker (yes): local only"


def test_describe_voter_diff_multiple_diffs_both_sides():
    msg = describe_voter_diff({("Alice", "yes")}, {("Bob", "no")})
    assert "Alice (yes): local only" in msg
    assert "Bob (no): live only" in msg


def test_describe_voter_diff_empty_both_sides_still_returns_message():
    msg = describe_voter_diff(set(), set())
    assert msg  # non-empty -- a mismatch with no voter diff is itself informative
    assert "no per-voter difference" in msg


# ── compare_bills(): per-voter diff wired into the existing WARN ───────────────

def test_compare_bills_appends_voter_diff_to_existing_warn_not_a_new_record():
    local = make_bill("HB1030", [
        make_vote_event("2026-02-17", "Passed", {"yes": 2, "no": 0},
                         [("Alice", "yes"), ("Bennett-Parker", "yes")]),
    ])
    live = make_bill("HB1030", [
        make_vote_event("2026-02-17", "Passed", {"yes": 1, "no": 0}, [("Alice", "yes")]),
    ])

    report = Report()
    compare_bills(report, local, live, "VA HB1030 (2026)")

    tally_checks = checks_for(report, "vote tally differs on 2026-02-17")
    assert len(tally_checks) == 1, "voter diff must land on the SAME record, not a new one"
    symbol, _, detail = tally_checks[0]
    assert symbol == WARN
    assert "Bennett-Parker (yes): local only" in detail
    assert "share this signature" not in detail  # no conn/jurisdiction/session supplied


def test_compare_bills_matching_tallies_unchanged_shape():
    """AC #3: jurisdictions that already pass cleanly must see no shape/volume change."""
    identical_votes = [
        make_vote_event("2026-02-17", "Passed", {"yes": 2, "no": 0},
                         [("Alice", "yes"), ("Bob", "yes")]),
    ]
    local = make_bill("HB1", identical_votes)
    live = make_bill("HB1", identical_votes)

    report = Report()
    compare_bills(report, local, live, "VA HB1 (2026)")

    tally_checks = checks_for(report, "vote tally")
    assert len(tally_checks) == 1
    symbol, _, detail = tally_checks[0]
    assert symbol == PASS
    assert "local only" not in detail
    assert "live only" not in detail
    assert "share this signature" not in detail
    # title, latest_action, vote event count, tally, sponsorship -- exactly 5 checks total
    assert len(report.checks) == 5


# ── compare_bills(): blast-radius wiring (mocked conn) ─────────────────────────

def test_compare_bills_includes_blast_radius_count_when_conn_supplied():
    local = make_bill("HB1030", [
        make_vote_event("2026-02-17", "Passed", {"yes": 2, "no": 0},
                         [("Alice", "yes"), ("Bennett-Parker", "yes")]),
    ])
    live = make_bill("HB1030", [
        make_vote_event("2026-02-17", "Passed", {"yes": 1, "no": 0}, [("Alice", "yes")]),
    ])
    conn = FakeConn(count=265)

    report = Report()
    compare_bills(report, local, live, "VA HB1030 (2026)",
                   conn=conn, jurisdiction_code="va", session="2026")

    _, _, detail = checks_for(report, "vote tally differs on 2026-02-17")[0]
    assert "265 other local bill(s) share this signature on 2026-02-17" in detail
    assert len(conn._cursor.executed) == 1


def test_compare_bills_blast_radius_skipped_when_conn_none():
    local = make_bill("HB1030", [
        make_vote_event("2026-02-17", "Passed", {"yes": 2, "no": 0},
                         [("Alice", "yes"), ("Bennett-Parker", "yes")]),
    ])
    live = make_bill("HB1030", [
        make_vote_event("2026-02-17", "Passed", {"yes": 1, "no": 0}, [("Alice", "yes")]),
    ])

    report = Report()
    compare_bills(report, local, live, "VA HB1030 (2026)")  # conn/jurisdiction_code/session omitted

    _, _, detail = checks_for(report, "vote tally differs on 2026-02-17")[0]
    assert "Bennett-Parker (yes): local only" in detail
    assert "share this signature" not in detail


# ── count_shared_date_signature() ───────────────────────────────────────────────

def test_count_shared_date_signature_uses_parameterized_query():
    conn = FakeConn(count=5)
    result = count_shared_date_signature(
        conn, "va", "2026", "2026-02-17", {("Bennett-Parker", "yes")},
        exclude_identifier="HB1030",
    )
    assert result == 5
    sql, params = conn._cursor.executed[0]
    assert "%s" in sql
    assert "Bennett-Parker" not in sql  # no f-string interpolation of voter-sourced data
    assert params[-1] == "HB1030"


def test_count_shared_date_signature_us_jurisdiction_branch():
    conn = FakeConn(count=3)
    result = count_shared_date_signature(
        conn, "us", "119", "2026-07-03", {("Chen", "yes")}, exclude_identifier="HR1",
    )
    assert result == 3
    sql, _ = conn._cursor.executed[0]
    assert "ocd-jurisdiction/country:us/government" in sql


def test_count_shared_date_signature_empty_signature_skips_query():
    conn = FakeConn(count=999)
    result = count_shared_date_signature(conn, "va", "2026", "2026-02-17", set(), "HB1030")
    assert result == 0
    assert conn._cursor.executed == []


def test_count_shared_date_signature_memoizes_within_cache():
    conn = FakeConn(count=3)
    cache = {}
    signature = {("Bennett-Parker", "yes")}

    r1 = count_shared_date_signature(conn, "va", "2026", "2026-02-17", signature,
                                      exclude_identifier="HB1030", cache=cache)
    r2 = count_shared_date_signature(conn, "va", "2026", "2026-02-17", signature,
                                      exclude_identifier="HB973", cache=cache)

    assert r1 == 3 and r2 == 3
    assert len(conn._cursor.executed) == 1  # second call served from cache, not re-queried


def test_count_shared_date_signature_different_signature_not_cached():
    conn = FakeConn(count=1)
    cache = {}

    count_shared_date_signature(conn, "va", "2026", "2026-02-17", {("A", "yes")}, "HB1",
                                 cache=cache)
    count_shared_date_signature(conn, "va", "2026", "2026-02-17", {("B", "no")}, "HB2",
                                 cache=cache)

    assert len(conn._cursor.executed) == 2


# ── OPEN-42: docket/bill-number normalization ───────────────────────────────────
# MA gives every bill two permanent, separate upstream identifiers over its life
# (docket number at filing, bill number once read in); our scraper deliberately
# keeps only the bill number, so a naive Tier 1 diff overstates the real gap by
# counting live's permanent docket-stage record as "missing." See
# PLAN-coverage-completeness-check.md §10.

def test_split_missing_by_docket_prefix_splits_ma_shaped_input():
    missing = {"H3444", "S1200", "HD2050", "HD9999", "SD1111"}

    result = split_missing_by_docket_prefix(missing, "ma")

    assert result["real"] == {"H3444", "S1200"}
    assert result["docket_duplicate"] == {"HD2050", "HD9999", "SD1111"}


def test_split_missing_by_docket_prefix_splits_fl_shaped_input():
    # FL: SPB/HPB (Senate/House Proposed Bill, a temporary pre-filing docket
    # number) get replaced in place by a permanent SB/HB number once formally
    # read in -- live's API keeps the frozen SPB/HPB record permanently as its
    # own entity even though the site itself now only shows the new number
    # (OPEN-63; confirmed live against flsenate.gov/Session/Bill/2026/7000).
    missing = {"SB 7000", "HB 30", "SPB 7000", "SPB 7042", "HPB 9001"}

    result = split_missing_by_docket_prefix(missing, "fl")

    assert result["real"] == {"SB 7000", "HB 30"}
    assert result["docket_duplicate"] == {"SPB 7000", "SPB 7042", "HPB 9001"}


def test_split_missing_by_docket_prefix_unmapped_jurisdiction_passes_through_unchanged():
    missing = {"HB30", "SB12", "HD2050"}  # HD-shaped identifier, but az has no docket lifecycle

    result = split_missing_by_docket_prefix(missing, "az")

    assert result["real"] == missing
    assert result["docket_duplicate"] == set()


def test_split_missing_by_docket_prefix_unrecognized_identifier_shape_stays_real():
    # A malformed/unexpected identifier for a mapped jurisdiction must not be
    # silently dropped -- anything that isn't a registered docket prefix counts
    # as a real gap by default.
    missing = {"HD2050", "XYZ123", ""}

    result = split_missing_by_docket_prefix(missing, "ma")

    assert result["real"] == {"XYZ123", ""}
    assert result["docket_duplicate"] == {"HD2050"}


def test_breakdown_by_prefix_counts_by_leading_alpha_chars():
    identifiers = ["H1", "H2", "S1", "HD1", "HD2", "HD3", "SD1"]

    assert breakdown_by_prefix(identifiers) == {"H": 2, "S": 1, "HD": 3, "SD": 1}


def test_breakdown_by_prefix_handles_no_alpha_prefix():
    assert breakdown_by_prefix(["123", ""]) == {"123": 1, "": 1}
