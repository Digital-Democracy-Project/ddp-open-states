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


def test_arizona_result_reads_counts_when_no_voter_is_recorded():
    # the scraper keeps a roll call with counts but no voter list; so does the fix-up
    counts_only = result_row("ocd-vote/16", "failed to pass", "pass", 28, 25, voters=0)
    changes, unclassified = bmc.plan_results([counts_only])
    assert ([(c["id"], c["new"]) for c in changes], unclassified) == ([("ocd-vote/16", "fail")], 0)


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


# OPEN-712: real 2026 rows from the Mac replica. SB 1175's Senate line returning the bill to the House for
# reconsideration (6/12, a voice vote stored 0-0 with no names); SB 1763's two roll calls are stored with their tallies
# (32-18 House, 29-1 Senate) but no names; HB 2758's third reading has its names.
def empty_row(vote_id, classification, yes=0, no=0, voters=0, text="Passed", jurisdiction=AZ, bill="SB 1175"):
    return dict(row(vote_id, 0, text, classification, jurisdiction=jurisdiction, bill=bill), result="pass", yes=yes,
                no=no, voters=voters)


def test_arizona_empty_votes_labelled_passage_lose_it():
    changes, unclassified = bmc.plan_empty_passage([
        empty_row("ocd-vote/20", ["passage"]),
        empty_row("ocd-vote/21", ["passage", "reading-3"], text="failed to pass", bill="SB 1100"),
    ])
    assert unclassified == 0
    assert [(c["id"], c["field"], c["old"], c["new"]) for c in changes] == [
        ("ocd-vote/20", "motion_classification", "passage", ""),
        ("ocd-vote/21", "motion_classification", "passage,reading-3", "reading-3"),
    ]


def test_a_vote_with_a_tally_or_names_keeps_passage():
    tally_only = empty_row("ocd-vote/22", ["passage"], yes=32, no=18, bill="SB 1763")
    one_nay = empty_row("ocd-vote/23", ["passage"], yes=0, no=1, bill="SB 1763")
    named = empty_row("ocd-vote/24", ["passage"], yes=32, no=24, voters=60, bill="HB 2758")
    names_without_tally = empty_row("ocd-vote/27", ["passage"], voters=60, bill="HB 2758")
    assert bmc.plan_empty_passage([tally_only, one_nay, named, names_without_tally]) == ([], 4)


def test_a_vote_with_no_tally_rows_is_empty_but_one_count_keeps_it():
    # FETCH_SQL's sum() gives NULL when a vote has no count rows; NULL and 0 both mean no tally.
    no_rows = empty_row("ocd-vote/28", ["passage"], yes=None, no=None)
    nays_only = empty_row("ocd-vote/29", ["passage"], yes=None, no=5, bill="SB 1763")
    changes, unclassified = bmc.plan_empty_passage([no_rows, nays_only])
    assert ([c["id"] for c in changes], unclassified) == (["ocd-vote/28"], 1)


def test_empty_votes_without_passage_and_other_states_are_left_alone():
    unlabelled = empty_row("ocd-vote/25", [])
    us = empty_row("ocd-vote/26", ["passage"], jurisdiction="ocd-jurisdiction/country:us/government")
    assert bmc.plan_empty_passage([unlabelled, us]) == ([], 2)


def test_empty_passage_list_writes_and_undoes(tmp_path):
    changes, _ = bmc.plan_empty_passage([empty_row("ocd-vote/20", ["passage"])])
    conn = _Conn({"ocd-vote/20": ["passage"]})
    bmc.write(conn, changes, str(tmp_path / "committed.csv"))
    assert conn.stored == {"ocd-vote/20": []}
    assert all("SET motion_classification = %s WHERE id = %s AND motion_classification = %s" in s for s in conn.sql)
    bmc.write(conn, bmc.read_list(str(tmp_path / "committed.csv"), undo=True), None)
    assert conn.stored == {"ocd-vote/20": ["passage"]}


@pytest.mark.parametrize("argv", [
    ["--az-empty-passage", "--result", "--dry-run"], ["--az-empty-passage", "--apply-list", "x.csv"],
    ["--az-empty-passage", "--jurisdiction", "pa", "--dry-run"], ["--az-empty-passage"],
])
def test_empty_passage_only_plans_arizona(monkeypatch, argv):
    monkeypatch.setattr(bmc.psycopg2, "connect", lambda *a, **k: pytest.fail("connected"))
    with pytest.raises(SystemExit):
        bmc.main(argv)


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


# OPEN-661: the states come from the manifest and the motion rules, not a typed list of eight.
OLD_EIGHT = {
    "ocd-jurisdiction/country:us/government": "us",
    "ocd-jurisdiction/country:us/state:az/government": "az",
    "ocd-jurisdiction/country:us/state:ut/government": "ut",
    "ocd-jurisdiction/country:us/state:fl/government": "fl",
    "ocd-jurisdiction/country:us/state:mi/government": "mi",
    "ocd-jurisdiction/country:us/state:ma/government": "ma",
    "ocd-jurisdiction/country:us/state:wa/government": "wa",
    "ocd-jurisdiction/country:us/state:va/government": "va",
}


def test_the_old_eight_keep_their_ids():
    for ocd_id, code in OLD_EIGHT.items():
        assert bmc.JURISDICTION_MAP[ocd_id] == code


def test_pennsylvania_and_louisiana_are_covered():
    assert bmc.JURISDICTION_MAP["ocd-jurisdiction/country:us/state:pa/government"] == "pa"
    assert bmc.JURISDICTION_MAP["ocd-jurisdiction/country:us/state:la/government"] == "la"


def test_a_manifest_state_without_motion_rules_is_left_out():
    # New Mexico is in the manifest but has no motion rules: classify_motion() would return [] and wipe its labels
    from classify_motion import _config

    assert "nm" not in _config["jurisdictions"]
    assert "nm" not in bmc.JURISDICTION_MAP.values()


def test_every_covered_state_is_in_the_manifest_and_has_rules():
    from classify_motion import _config
    from validate_jurisdictions import load_and_validate

    manifest, errors = load_and_validate(os.path.join(HERE, "jurisdictions.yaml"))
    assert not errors
    assert set(bmc.JURISDICTION_MAP.values()) == set(manifest) & set(_config["jurisdictions"])


@pytest.mark.parametrize("key", ["nm", "xx"])
def test_an_uncovered_jurisdiction_is_refused(key):
    with pytest.raises(SystemExit):
        bmc.main(["--jurisdiction", key, "--dry-run"])


@pytest.mark.parametrize("argv", [[], ["--jurisdiction", "la"], ["--jurisdiction", "pa"], ["--result"]])
def test_a_run_that_classifies_never_writes(monkeypatch, argv):
    # OPEN-661: refused before any database connection; Louisiana's dry run plans 31 removals of the `amendment`
    # labels Ramon decided to keep, so a classifying run may only plan, and a write is a reviewed list
    monkeypatch.setattr(bmc.psycopg2, "connect", lambda *a, **k: pytest.fail("connected"))
    with pytest.raises(SystemExit):
        bmc.main(argv)


@pytest.mark.parametrize("argv", [
    ["--jurisdiction", "la", "--dry-run"], ["--apply-list", "reviewed.csv"], ["--undo", "committed.csv"],
])
def test_dry_runs_and_reviewed_lists_still_reach_the_database(monkeypatch, argv):
    class Reached(Exception):
        pass

    def connect(*a, **k):
        raise Reached

    monkeypatch.setattr(bmc.psycopg2, "connect", connect)
    with pytest.raises(Reached):
        bmc.main(argv)


# OPEN-865: Nevada's stored votes against NELIS's own outcome. test_fixtures/nv_open865/ holds NELIS's real "Final
# Passage" vote lists (GetBillVotes?billKey=K&voteTypeId=3, fetched 2026-11-24) of AB 4 (12994), AB 5 (12997) and SB 10
# (13008) of 2025Special36; the rows are the Mac replica's, stored as the old scraper wrote them (yeas > nays).
NV = "ocd-jurisdiction/country:us/state:nv/government"
NV_PAGES = os.path.join(HERE, "test_fixtures", "nv_open865")
NV_SOURCE = "https://www.leg.state.nv.us/App/NELIS/REL/36th2025Special/Bill/FillSelectedBillTab?selectedTab=Votes&billKey={}&_=1"


def nv_row(vote_id, bill, key, text, date, yes, no, extras=None):
    return dict(
        id=vote_id, motion_text=text, motion_classification=["passage"], bill_action=None, nelis_outcome=extras,
        jurisdiction_id=NV, bill=bill, start_date=f"{date}T08:00:00+00:00", chamber="upper", result="pass",
        source=NV_SOURCE.format(key), voters=21, yes=yes, no=no,
    )


NV_ROWS = [
    nv_row("ocd-vote/ab4-asm", "AB 4", 12994, "Assembly (1st Reprint)", "2025-11-16", 31, 11),
    nv_row("ocd-vote/ab4-3rd", "AB 4", 12994, "Senate (3rd Reprint)", "2025-11-18", 16, 2),
    nv_row("ocd-vote/ab4-4th", "AB 4", 12994, "Senate (4th Reprint)", "2025-11-19", 16, 2),
    nv_row("ocd-vote/ab5-asm", "AB 5", 12997, "Assembly (1st Reprint)", "2025-11-16", 22, 20),
    nv_row("ocd-vote/ab5-sen", "AB 5", 12997, "Senate (2nd Reprint)", "2025-11-19", 10, 8),
    nv_row("ocd-vote/sb10-sen", "SB 10", 13008, "Senate (1st Reprint)", "2025-11-19", 18, 0),
    nv_row("ocd-vote/sb10-asm", "SB 10", 13008, "Assembly (1st Reprint)", "2025-11-19", 27, 10),
]


@pytest.fixture(scope="module")
def nelis():
    return bmc.nv_nelis_votes(NV_PAGES)


def test_nevada_failed_votes_change_the_result_only_and_a_rescinded_vote_ends_as_the_scraper_stores_it(nelis):
    changes, unclassified = bmc.plan_nv_results(NV_ROWS, nelis)
    assert unclassified == 0
    assert [(c["id"], c["field"], c["old"], c["new"]) for c in changes] == [
        ("ocd-vote/ab4-3rd", "result", "pass", "fail"),
        ("ocd-vote/ab4-3rd", "motion_classification", "passage", ""),
        ("ocd-vote/ab4-3rd", "nelis_outcome", "", "Rescinded"),
        ("ocd-vote/ab5-sen", "result", "pass", "fail"),  # 10-8 of 21: 11 are needed
        ("ocd-vote/sb10-asm", "result", "pass", "fail"),  # 27-10 of 42: two thirds is 28
    ]
    assert len({c["id"] for c in changes}) == 3


def test_nevada_votes_nelis_passed_and_votes_without_a_nelis_page_are_left_alone(nelis):
    other = nv_row("ocd-vote/x", "AB 9", 99999, "Senate (1st Reprint)", "2025-11-19", 1, 0)
    az = dict(NV_ROWS[0], id="ocd-vote/az", jurisdiction_id=AZ)
    changes, unclassified = bmc.plan_nv_results([NV_ROWS[0], NV_ROWS[2], NV_ROWS[3], NV_ROWS[5], other, az], nelis)
    assert (changes, unclassified) == ([], 2)


def test_a_planned_nevada_vote_is_not_planned_again(nelis):
    fixed = dict(NV_ROWS[1], result="fail", motion_classification=[], nelis_outcome="Rescinded")
    assert bmc.plan_nv_results([fixed], nelis) == ([], 0)


class _ExtrasCursor(_Cursor):
    def execute(self, sql, params):
        new, vote_id, old = params
        self.conn.sql.append(" ".join(sql.split()))
        key = (vote_id, "classification" if "motion_classification" in sql else "outcome" if "nelis_outcome" in sql else "result")
        self.rowcount = 1 if self.conn.stored.get(key) == old else 0
        if self.rowcount:
            self.conn.pending[key] = new


class _ExtrasConn(_Conn):
    def cursor(self):
        return _ExtrasCursor(self)


def test_the_nevada_list_writes_each_column_and_undoes(tmp_path, nelis):
    changes, _ = bmc.plan_nv_results(NV_ROWS, nelis)
    conn = _ExtrasConn({
        ("ocd-vote/ab4-3rd", "result"): "pass", ("ocd-vote/ab4-3rd", "classification"): ["passage"],
        ("ocd-vote/ab4-3rd", "outcome"): "", ("ocd-vote/ab5-sen", "result"): "pass",
        ("ocd-vote/sb10-asm", "result"): "pass",
    })
    before = dict(conn.stored)
    bmc.write(conn, changes, str(tmp_path / "committed.csv"))
    assert conn.stored[("ocd-vote/ab4-3rd", "outcome")] == "Rescinded"
    assert conn.stored[("ocd-vote/ab4-3rd", "classification")] == []
    assert [conn.stored[(v, "result")] for v in ("ocd-vote/ab4-3rd", "ocd-vote/ab5-sen", "ocd-vote/sb10-asm")] == ["fail"] * 3
    assert sum("SET extras" in sql and "WHERE id = %s AND coalesce(extras->>'nelis_outcome', '') = %s" in sql
               for sql in conn.sql) == 1
    bmc.write(conn, bmc.read_list(str(tmp_path / "committed.csv"), undo=True), None)
    assert conn.stored == before


def test_a_stale_nevada_row_aborts_the_whole_write(tmp_path, nelis):
    changes, _ = bmc.plan_nv_results(NV_ROWS, nelis)
    conn = _ExtrasConn({
        ("ocd-vote/ab4-3rd", "result"): "pass", ("ocd-vote/ab4-3rd", "classification"): ["passage"],
        ("ocd-vote/ab4-3rd", "outcome"): "", ("ocd-vote/ab5-sen", "result"): "fail",  # already fixed underneath
        ("ocd-vote/sb10-asm", "result"): "pass",
    })
    with pytest.raises(SystemExit, match="nothing written"):
        bmc.write(conn, changes, str(tmp_path / "committed.csv"))
    assert conn.stored[("ocd-vote/ab4-3rd", "result")] == "pass"


def test_nv_result_needs_the_pages_and_plans_nevada_only():
    for argv in (["--nv-result", "--dry-run"], ["--nv-result", "--nv-cache", "x", "--jurisdiction", "az", "--dry-run"],
                 ["--nv-cache", "x", "--dry-run"], ["--nv-result", "--nv-cache", "x", "--result", "--dry-run"]):
        with pytest.raises(SystemExit):
            bmc.main(argv)
