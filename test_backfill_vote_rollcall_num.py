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


def row(state, text="", dedupe_key=None, chamber="lower", extras=None, vote_id="ocd-vote/1", bill="HB 1",
        identifier=""):
    return dict(id=vote_id, motion_text=text, dedupe_key=dedupe_key, extras=extras or {}, identifier=identifier,
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
    assert all("NOT (extras ?| array['house-rollcall-num', 'senate-rollcall-num', 'legislature-rollcall-num'])" in sql
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


# --- OPEN-685: Nebraska, Louisiana, New Mexico ----------------------------------------------------------------------


def test_nebraska_lb48_key_ids_from_the_dedupe_key():
    # Real stored rows: LB 48 on 2025-05-30, failed with the emergency clause (KeyID 12956), then passed with it
    # stricken (12957). Nebraska's one chamber is stored as "legislature".
    rows = [row("ne", "Failed on Final Reading with Emergency Clause 26-22*-1", dedupe_key="12956",
                chamber="legislature", vote_id="ocd-vote/a"),
            row("ne", "Passed on Final Reading with Emergency Clause stricken 27-21*-1", dedupe_key="12957",
                chamber="legislature", vote_id="ocd-vote/b")]
    assert planned(rows)[0] == [("ocd-vote/a", "legislature-rollcall-num", "12956"),
                                ("ocd-vote/b", "legislature-rollcall-num", "12957")]


def test_nebraska_dedupe_key_must_be_plain_digits():
    changes, counts = planned([row("ne", "x", dedupe_key="KeyID=12956", chamber="legislature"),
                               row("ne", "x", dedupe_key=None, chamber="legislature")])
    assert changes == [] and counts["unread"] == 2


def test_louisiana_sb487_numbers_from_the_motion_text():
    rows = [row("la", "FINAL PASSAGE (#1393)", vote_id="ocd-vote/a"), row("la", "FINAL PASSAGE (#1400)", vote_id="ocd-vote/b"),
            row("la", "CONCUR (#1432)", chamber="upper", vote_id="ocd-vote/c")]
    assert planned(rows)[0] == [("ocd-vote/a", "house-rollcall-num", "1393"), ("ocd-vote/b", "house-rollcall-num", "1400"),
                                ("ocd-vote/c", "senate-rollcall-num", "1432")]


NM_URL = "https://www.nmlegis.gov/Sessions/26%20Regular/votes/HB0253SVOTE{}.PDF"


def test_new_mexico_hb253_rcs_from_the_saved_pdf_text(tmp_path):
    from urllib.parse import quote

    # pdftotext -layout of nmlegis.gov's two HB 253 Senate roll calls (2026-02-18): the number sits far right.
    (tmp_path / (quote(NM_URL.format(""), safe="") + ".txt")).write_text("LEGISLATIVE DAY 16   DATE: 02/18/26\n   RCS#            158\n")
    (tmp_path / (quote(NM_URL.format("2"), safe="") + ".txt")).write_text("LEGISLATIVE DAY 17   DATE: 02/18/26\n   RCS#            173\n")
    (tmp_path / "unrelated.json").write_text("{}")
    numbers = brn.nm_vote_rcs(tmp_path)
    assert numbers == {NM_URL.format(""): "158", NM_URL.format("2"): "173"}
    rows = [row("nm", "senate passage", dedupe_key=NM_URL.format(""), chamber="upper", vote_id="ocd-vote/a"),
            row("nm", "senate passage", dedupe_key=NM_URL.format("2"), chamber="upper", vote_id="ocd-vote/b")]
    changes, _ = brn.plan(rows, None, None, numbers)
    assert [(c["id"], c["key"], c["rollcall_num"]) for c in changes] == [
        ("ocd-vote/a", "senate-rollcall-num", "158"), ("ocd-vote/b", "senate-rollcall-num", "173")]


def test_new_mexico_is_left_alone_without_the_pdf_text():
    changes, counts = planned([row("nm", "senate passage", dedupe_key=NM_URL.format(""), chamber="upper")])
    assert changes == [] and counts["unread"] == 1


def test_a_nebraska_number_already_stored_is_never_changed():
    changes, counts = planned([row("ne", "x", dedupe_key="12956", chamber="legislature",
                                   extras={"legislature-rollcall-num": "12956"})])
    assert changes == [] and counts["already"] == 1


def test_a_nebraska_vote_outside_its_one_chamber_is_left_alone():
    changes, counts = planned([row("ne", "x", dedupe_key="12956", chamber="upper")])
    assert changes == [] and counts["unread"] == 1


def test_the_new_states_are_in_the_jurisdiction_map():
    assert {brn.JURISDICTIONS[OCD.format(st)] for st in ("ne", "la", "nm")} == {"ne", "la", "nm"}


def test_georgia_2026_ss_ties_come_out_in_voting_order():
    # Real stored rows (Mac replica, 2026_ss): SB 3's Senate on 2026-06-23 (#27 failed 19-32, #28 passed 36-16) and
    # HB 80's House the same day (#13 and #15, both "Local Calendar"). The numbers are the ones the scraper now writes.
    rows = [
        row("ga", "AGREE TO HOUSE SUBSTITUTE AS AMENDED", chamber="upper", vote_id="ocd-vote/s27",
            identifier="Senate Vote #27 - 2026 Special Session"),
        row("ga", "AGREE TO HOUSE SUBSTITUTE", chamber="upper", vote_id="ocd-vote/s28",
            identifier="Senate Vote #28 - 2026 Special Session"),
        row("ga", "Local Calendar", chamber="lower", vote_id="ocd-vote/h13",
            identifier="House Vote #13 - 2026 Special Session"),
        row("ga", "Local Calendar", chamber="lower", vote_id="ocd-vote/h15",
            identifier="House Vote #15 - 2026 Special Session"),
    ]
    assert planned(rows)[0] == [
        ("ocd-vote/s27", "senate-rollcall-num", "27"),
        ("ocd-vote/s28", "senate-rollcall-num", "28"),
        ("ocd-vote/h13", "house-rollcall-num", "13"),
        ("ocd-vote/h15", "house-rollcall-num", "15"),
    ]


@pytest.mark.parametrize("identifier,chamber", [
    ("Senate Vote #28 - 2026 Special Session", "lower"),  # the identifier names the other chamber
    ("House Vote #5 - 2026 Special Session", "upper"),
    ("1234", "lower"),  # no roll call in it (the scraper falls back to the VoteId when Description is empty)
    ("House Vote # - 2026 Special Session", "lower"),
])
def test_a_georgia_vote_whose_identifier_does_not_say_its_number_is_left_alone(identifier, chamber):
    changes, counts = brn.plan([row("ga", chamber=chamber, identifier=identifier)], None)
    assert changes == [] and counts["unread"] == 1


def test_a_georgia_number_already_stored_is_never_changed():
    rows = [row("ga", chamber="upper", extras={"senate-rollcall-num": "99"},
                identifier="Senate Vote #28 - 2026 Special Session")]
    changes, counts = brn.plan(rows, None)
    assert changes == [] and counts["already"] == 1


def test_alabama_same_day_ties_come_out_in_voting_order():
    # Real stored dedupe keys (Mac replica, 2026 RS): HB 460's House 520/521 (2026-02-24), HB 605's Senate 1316/1317 and
    # SB 146's Senate 813/814, each a same-day pair of passage votes.
    rows = [
        row("al", chamber="lower", vote_id="ocd-vote/h520", dedupe_key="2026RS#House#520#HB460", bill="HB 460"),
        row("al", chamber="lower", vote_id="ocd-vote/h521", dedupe_key="2026RS#House#521#HB460", bill="HB 460"),
        row("al", chamber="upper", vote_id="ocd-vote/s1316", dedupe_key="2026RS#Senate#1316#HB605", bill="HB 605"),
        row("al", chamber="upper", vote_id="ocd-vote/s1317", dedupe_key="2026RS#Senate#1317#HB605", bill="HB 605"),
        row("al", chamber="upper", vote_id="ocd-vote/s813", dedupe_key="2026RS#Senate#813#SB146", bill="SB 146"),
        row("al", chamber="upper", vote_id="ocd-vote/s814", dedupe_key="2026RS#Senate#814#SB146", bill="SB 146"),
    ]
    assert planned(rows)[0] == [
        ("ocd-vote/h520", "house-rollcall-num", "520"),
        ("ocd-vote/h521", "house-rollcall-num", "521"),
        ("ocd-vote/s1316", "senate-rollcall-num", "1316"),
        ("ocd-vote/s1317", "senate-rollcall-num", "1317"),
        ("ocd-vote/s813", "senate-rollcall-num", "813"),
        ("ocd-vote/s814", "senate-rollcall-num", "814"),
    ]


@pytest.mark.parametrize("dedupe_key,chamber", [
    ("2026RS#Senate#1317#HB605", "lower"),  # the key names the other chamber
    ("2026RS#House#520#HB460", "upper"),
    ("2026RS#House#HB460", "lower"),  # no roll call in it
    (None, "lower"),
])
def test_an_alabama_vote_whose_key_does_not_say_its_number_is_left_alone(dedupe_key, chamber):
    changes, counts = brn.plan([row("al", chamber=chamber, dedupe_key=dedupe_key)], None)
    assert changes == [] and counts["unread"] == 1


def test_an_alabama_number_already_stored_is_never_changed():
    rows = [row("al", chamber="lower", extras={"house-rollcall-num": "999"}, dedupe_key="2026RS#House#521#HB460")]
    changes, counts = brn.plan(rows, None)
    assert changes == [] and counts["already"] == 1
