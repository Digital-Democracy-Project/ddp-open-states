"""OPEN-628: backfill-vote-rollcall-num.py. Each state's number is the one its scraper writes, read from the stored
row; a stored number is never changed; a write applies every planned change or none. No database: rows and the
connection are stand-ins; the plan itself is checked by the dry run on the replica and the apply + undo rehearsal on a
throwaway copy (OPEN-628)."""
import importlib.util
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("backfill_rollcall", os.path.join(HERE, "backfill-vote-rollcall-num.py"))
brn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(brn)

OCD = "ocd-jurisdiction/country:us/state:{}/government"


def row(state, text="", dedupe_key=None, chamber="lower", extras=None, vote_id="ocd-vote/1", bill="HB 1"):
    return dict(id=vote_id, motion_text=text, dedupe_key=dedupe_key, extras=extras or {},
                jurisdiction_id=OCD.format(state), bill=bill, start_date="2026-02-19", chamber=chamber)


def planned(rows, az_times=None, va_times=None):
    changes, counts = brn.plan(rows, az_times, va_times)
    return [(c["id"], c["key"], c["rollcall_num"]) for c in changes], counts


def test_michigan_hb_4079_gets_both_roll_call_numbers():
    # Real stored rows: the House passed HB 4079 as Roll Call #45, reconsidered, then passed it as #47 (2026-02-19).
    rows = [
        row("mi", "passed; given immediate effect Roll Call #45 Yeas 96 Nays 12 Excused 0 Not Voting 2",
            vote_id="ocd-vote/34c0893e"),
        row("mi", "passed Roll Call #47 Yeas 98 Nays 10 Excused 0 Not Voting 2", vote_id="ocd-vote/eb61833d"),
    ]
    assert planned(rows)[0] == [("ocd-vote/34c0893e", "house-rollcall-num", "45"),
                                ("ocd-vote/eb61833d", "house-rollcall-num", "47")]


def test_michigan_senate_spelling_and_key():
    # Real HB 4098 Senate text: "ROLL CALL # 345" (capitals, a space after #).
    rows = [row("mi", "PASSED ROLL CALL # 345 YEAS 27 NAYS 8 EXCUSED 1 NOT VOTING 1", chamber="upper")]
    assert planned(rows)[0] == [("ocd-vote/1", "senate-rollcall-num", "345")]


def test_washington_sequence_number_from_the_motion_text():
    # wa/bills.py writes "{Motion} (#{SequenceNumber})"; HB 1131's House re-vote on 2025-03-07 was #19 after #7.
    rows = [row("wa", "3rd Reading & Final Passage (#7)", vote_id="ocd-vote/a"),
            row("wa", "Final Passage on Reconsideration (#19)", vote_id="ocd-vote/b"),
            row("wa", "1349  Dent  Pg 31 Ln 25 (#1)", chamber="upper", vote_id="ocd-vote/c")]
    assert planned(rows)[0] == [("ocd-vote/a", "house-rollcall-num", "7"), ("ocd-vote/b", "house-rollcall-num", "19"),
                                ("ocd-vote/c", "senate-rollcall-num", "1")]


def test_washington_number_must_end_the_text():
    # An amendment number inside the text is not the roll call's.
    changes, counts = planned([row("wa", "Amendment (#12) adopted"), row("wa", "Final Passage (#)")])
    assert changes == [] and counts["unread"] == 2


def test_virginia_time_comes_from_the_lis_answers_matched_on_the_vote_id():
    # HB 29's House votes on 2026-02-09: the engrossment vote (VoteID 295480) was taken last, at 09:42:58, after
    # 295495 (09:15:42); LIS's VoteIDs are not in vote order, so the number is the time.
    times = {"295480": "094258", "295495": "091542"}
    rows = [row("va", "H VOTE:", dedupe_key="295480-HB29", vote_id="ocd-vote/a"),
            row("va", "H VOTE:", dedupe_key="295495-HB29", vote_id="ocd-vote/b"),
            row("va", "H VOTE:", dedupe_key="295999-HB29", vote_id="ocd-vote/c")]
    changes, counts = planned(rows, va_times=times)
    assert changes == [("ocd-vote/a", "house-rollcall-num", "094258"), ("ocd-vote/b", "house-rollcall-num", "091542")]
    assert counts["unread"] == 1


def test_virginia_is_left_alone_without_the_lis_answers():
    changes, counts = planned([row("va", "H VOTE:", dedupe_key="295480-HB29")])
    assert changes == [] and counts["unread"] == 1


def test_virginia_vote_times_are_read_from_saved_answers(tmp_path):
    answer = {"Votes": [{"VoteID": 296925, "VoteDate": "2026-02-12T08:49:55"},
                        {"VoteID": 296925, "VoteDate": "2026-02-12T08:49:55"},
                        {"VoteID": 299056, "VoteDate": "2026-02-25T00:00:00"},
                        {"VoteID": 1, "VoteDate": None}]}
    (tmp_path / "2026_HB1441.json").write_text(json.dumps(answer))
    (tmp_path / "notes.txt").write_text("not an answer")
    assert brn.va_vote_times(str(tmp_path)) == {"296925": "084955", "299056": "000000"}


AZ_KEY = "https://apps.azleg.gov/api/BillStatusFloorAction?billStatusId=83546&billStatusActionId={}&includeVotes=true{}"


def test_arizona_time_comes_from_the_cache_matched_on_action_and_referral():
    times = {("83546", "245992", "1"): "161649", ("83546", "245992", "2"): "170102"}
    rows = [row("az", "Passed", AZ_KEY.format(245992, 1), vote_id="ocd-vote/a"),
            row("az", "Passed", AZ_KEY.format(245992, 2), vote_id="ocd-vote/b"),
            row("az", "Passed", AZ_KEY.format(999999, 1), vote_id="ocd-vote/c")]
    changes, counts = planned(rows, times)
    assert changes == [("ocd-vote/a", "house-rollcall-num", "161649"), ("ocd-vote/b", "house-rollcall-num", "170102")]
    assert counts["unread"] == 1


def test_arizona_is_left_alone_without_the_cache():
    changes, counts = planned([row("az", "Passed", AZ_KEY.format(245992, 1))], None)
    assert changes == [] and counts["unread"] == 1


def test_a_stored_number_is_never_changed():
    # MI HB 4518's Senate votes already carry the scraper's number; either key counts as numbered.
    rows = [row("mi", "PASSED ROLL CALL # 183", chamber="upper", extras={"senate-rollcall-num": "183"}),
            row("wa", "Final Passage (#4)", extras={"house-rollcall-num": "9"})]
    changes, counts = planned(rows)
    assert changes == [] and counts["already"] == 2


def test_arizona_report_times_are_read_from_cached_floor_actions(tmp_path):
    answer = [{"ReferralNumber": 1, "ReportDate": "2026-06-09T16:16:49.000"},
              {"ReferralNumber": 2, "ReportDate": "2026-06-09T16:13:35"},
              {"ReferralNumber": 3, "ReportDate": None}]
    (tmp_path / "apps.azleg.gov,api,BillStatusFloorAction,billStatusId=83546&billStatusActionId=245992"
                "&includeVotes=true,ab12").write_bytes(
        b"status: 200\nContent-Type: application/json\n\n" + json.dumps(answer).encode())
    (tmp_path / "apps.azleg.gov,api,Bill,billNumber=HB2013,cd34").write_bytes(b"{}")
    assert brn.az_report_times(str(tmp_path)) == {("83546", "245992", "1"): "161649",
                                                  ("83546", "245992", "2"): "161335"}


class Cursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params):
        self.conn.executed.append((sql, params))
        vote_id = params[1] if "extras -" in sql else params[2]
        self.rowcount = 0 if vote_id in self.conn.misses else 1


class Conn:
    def __init__(self, misses=()):
        self.misses, self.executed, self.committed, self.rolled_back = set(misses), [], False, False

    def cursor(self):
        return Cursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


CHANGES = [dict(id="ocd-vote/a", key="house-rollcall-num", rollcall_num="45"),
           dict(id="ocd-vote/b", key="house-rollcall-num", rollcall_num="47")]


def test_write_applies_every_change_with_its_guard(tmp_path):
    conn = Conn()
    brn.write(conn, CHANGES, undo=False, list_path=str(tmp_path / "committed.csv"))
    assert conn.committed and not conn.rolled_back
    assert [p for _, p in conn.executed] == [("house-rollcall-num", "45", "ocd-vote/a"),
                                             ("house-rollcall-num", "47", "ocd-vote/b")]
    assert all("NOT (extras ? 'house-rollcall-num') AND NOT (extras ? 'senate-rollcall-num')" in sql
               for sql, _ in conn.executed)
    assert (tmp_path / "committed.csv").exists()


def test_a_guard_miss_rolls_the_whole_run_back(tmp_path):
    conn = Conn(misses={"ocd-vote/b"})
    with pytest.raises(SystemExit):
        brn.write(conn, CHANGES, undo=False, list_path=str(tmp_path / "committed.csv"))
    assert conn.rolled_back and not conn.committed
    assert not (tmp_path / "committed.csv").exists()


def test_undo_takes_off_only_the_value_written(tmp_path):
    conn = Conn()
    brn.write(conn, CHANGES, undo=True, list_path=None)
    assert conn.committed
    assert all("SET extras = extras - %s::text" in sql and "AND extras->>%s::text = %s" in sql
               for sql, _ in conn.executed)
    assert [p for _, p in conn.executed] == [("house-rollcall-num", "ocd-vote/a", "house-rollcall-num", "45"),
                                             ("house-rollcall-num", "ocd-vote/b", "house-rollcall-num", "47")]


def test_an_undo_guard_miss_rolls_the_whole_run_back():
    # The second vote no longer holds the value the backfill wrote (a scrape changed it): nothing is taken off.
    conn = Conn(misses={"ocd-vote/b"})
    with pytest.raises(SystemExit):
        brn.write(conn, CHANGES, undo=True, list_path=None)
    assert conn.rolled_back and not conn.committed


@pytest.mark.parametrize("bad", [
    dict(id="ocd-vote/c", key="bill_action", rollcall_num="1"),
    dict(id="ocd-vote/c", key="house-rollcall-num", rollcall_num="#47"),
    dict(id="ocd-vote/c", key="house-rollcall-num", rollcall_num="\u0664\u0667"),  # Arabic-Indic 47
    dict(id="", key="house-rollcall-num", rollcall_num="47"),
    dict(id="ocd-vote/a", key="house-rollcall-num", rollcall_num="47"),
])
def test_a_list_with_a_bad_row_writes_nothing(bad):
    conn = Conn()
    with pytest.raises(SystemExit):
        brn.write(conn, CHANGES + [bad], undo=False, list_path=None)
    assert conn.executed == [] and not conn.committed


def test_a_vote_of_neither_chamber_is_left_alone():
    changes, counts = planned([row("mi", "passed Roll Call #47", chamber="legislature")])
    assert changes == [] and counts["unread"] == 1


def test_every_write_needs_expect(capsys):
    with pytest.raises(SystemExit):
        brn.main(["--apply-list", "list.csv"])
    assert "--expect" in capsys.readouterr().err


def test_list_round_trip(tmp_path):
    path = tmp_path / "list.csv"
    brn._write_list(str(path), [dict(CHANGES[0], jurisdiction="mi", bill="HB 4079", date="2026-02-19",
                                     chamber="lower", motion_text="passed Roll Call #45")])
    (back,) = brn.read_list(str(path))
    assert (back["id"], back["key"], back["rollcall_num"]) == ("ocd-vote/a", "house-rollcall-num", "45")
