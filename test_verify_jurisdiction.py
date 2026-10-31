"""
Tests for verify-jurisdiction (OPEN-222, the onboarding probe). Covers every deterministic,
non-scraper/non-DB piece: module-name/OCD-id mapping, the WAF block-signature matcher, the
production-DB safety guard, extractor-coverage diffing, scrape-order walk-direction
classification, the broker session-code regex, and the gate -> green/yellow/red rollup.

Gates A/D/H's real-scraper/real-DB behavior is exercised live instead (see this PR's description
for the actual command + output against a real, already-onboarded state) -- there is no fake
Jurisdiction/DB fixture here standing in for what a live run already covers.

verify-jurisdiction has no .py extension (matches quality_check.py's own sibling test file's
approach to a script with a stable CLI name) -- imported via importlib from the file directly.
"""

import datetime
import importlib.machinery
import importlib.util
import os
import sys
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOADER = importlib.machinery.SourceFileLoader("verify_jurisdiction", os.path.join(_HERE, "verify-jurisdiction"))
_SPEC = importlib.util.spec_from_loader("verify_jurisdiction", _LOADER)
vj = importlib.util.module_from_spec(_SPEC)
sys.modules["verify_jurisdiction"] = vj
_LOADER.exec_module(vj)


# ── scraper_module_name / ocd_jurisdiction_id ──────────────────────────────────


def test_scraper_module_name_translates_us_to_usa():
    assert vj.scraper_module_name("us") == "usa"


def test_scraper_module_name_passes_through_other_states():
    assert vj.scraper_module_name("fl") == "fl"
    assert vj.scraper_module_name("nc") == "nc"


def test_ocd_jurisdiction_id_us_has_no_state_component():
    assert vj.ocd_jurisdiction_id("us") == "ocd-jurisdiction/country:us/government"


def test_ocd_jurisdiction_id_state_shape():
    assert vj.ocd_jurisdiction_id("fl") == "ocd-jurisdiction/country:us/state:fl/government"


# ── looks_like_unreachable_site ────────────────────────────────────────────────


def test_unreachable_site_detects_waf_block_detected():
    assert vj.looks_like_unreachable_site("WAF block detected on attempt 3") is True


def test_unreachable_site_detects_neither_results_nor_bill_page():
    assert vj.looks_like_unreachable_site("neither a results page nor a usable bill page") is True


def test_unreachable_site_ignores_unrelated_text():
    assert vj.looks_like_unreachable_site("scraped 12 bills successfully") is False


def test_unreachable_site_empty_text_is_false():
    assert vj.looks_like_unreachable_site("") is False
    assert vj.looks_like_unreachable_site(None) is False


def test_unreachable_site_negated_marker_does_not_count():
    """Mirrors import-summary.sh's own negation guard -- 'no WAF block detected' must not
    trip the matcher just because it contains the phrase."""
    assert vj.looks_like_unreachable_site("no WAF block detected this run") is False


def test_unreachable_site_negation_only_suppresses_its_own_line():
    text = "no WAF block detected\nunrecognised block page encountered"
    assert vj.looks_like_unreachable_site(text) is True


def test_unreachable_site_case_insensitive():
    assert vj.looks_like_unreachable_site("CONSECUTIVE WAF BLOCKS seen") is True


# ── is_probably_production_db ──────────────────────────────────────────────────


def test_production_db_flagged_for_plain_openstates_name():
    assert vj.is_probably_production_db("postgresql://u:p@localhost:5433/openstates") is True


def test_dev_db_name_suffix_is_not_flagged():
    assert vj.is_probably_production_db("postgresql://u:p@localhost:5433/openstates_dev") is False


def test_test_db_name_suffix_is_not_flagged():
    assert vj.is_probably_production_db("postgresql://u:p@localhost:5433/openstates_test") is False


def test_name_merely_containing_test_is_flagged_as_production():
    """Round-1 PM review fold: a bare 'test' substring anywhere in the name used to be treated
    as safe -- the reviewer's own example (a real database like contest_prod) shows why that's
    wrong. Only the two suffix conventions this fleet actually uses (_dev/_test) are safe now."""
    assert vj.is_probably_production_db("postgresql://u:p@localhost:5433/v3test_eval5") is True
    assert vj.is_probably_production_db("postgresql://u:p@localhost:5433/contest_prod") is True


def test_empty_or_unparsable_url_defaults_to_production():
    assert vj.is_probably_production_db("") is True
    assert vj.is_probably_production_db("not a url") is True


# ── extract_media_types / missing_extractor_coverage ──────────────────────────


def test_extract_media_types_from_versions_and_documents():
    bill = {
        "versions": [{"links": [{"media_type": "application/pdf"}, {"media_type": "text/html"}]}],
        "documents": [{"links": [{"media_type": "application/pdf"}]}],
    }
    assert vj.extract_media_types(bill) == {"application/pdf", "text/html"}


def test_extract_media_types_handles_missing_keys():
    assert vj.extract_media_types({}) == set()
    assert vj.extract_media_types({"versions": None, "documents": None}) == set()


def test_missing_extractor_coverage_finds_gap():
    present = {"application/pdf", "text/xml"}
    conversion = {"application/pdf": object()}
    assert vj.missing_extractor_coverage(present, conversion) == {"text/xml"}


def test_missing_extractor_coverage_no_gap_when_all_covered():
    present = {"application/pdf"}
    conversion = {"application/pdf": object(), "text/html": object()}
    assert vj.missing_extractor_coverage(present, conversion) == set()


def test_missing_extractor_coverage_handles_state_with_no_registry_entry_at_all():
    assert vj.missing_extractor_coverage({"application/pdf"}, None) == {"application/pdf"}


# ── scraper_signature_has_param ────────────────────────────────────────────────


class _FakeScraperWithStart:
    def scrape(self, session=None, start=None):
        pass


class _FakeScraperWithoutStart:
    def scrape(self, session=None):
        pass


def test_signature_has_param_true_when_present():
    assert vj.scraper_signature_has_param(_FakeScraperWithStart, "start") is True


def test_signature_has_param_false_when_absent():
    assert vj.scraper_signature_has_param(_FakeScraperWithoutStart, "start") is False


def test_signature_has_param_handles_non_introspectable_object():
    assert vj.scraper_signature_has_param(object(), "start") is False


# ── find_env_var_references ────────────────────────────────────────────────────


def test_find_env_var_references_all_three_call_shapes(tmp_path):
    (tmp_path / "bills.py").write_text(
        "import os\n"
        "a = os.environ['VA_API_KEY']\n"
        "b = os.environ.get('OPTIONAL_KEY')\n"
        "c = os.getenv('THIRD_KEY')\n"
        "d = 'not_a_call'\n"
    )
    assert vj.find_env_var_references(str(tmp_path)) == {"VA_API_KEY", "OPTIONAL_KEY", "THIRD_KEY"}


def test_find_env_var_references_empty_dir_returns_empty_set(tmp_path):
    assert vj.find_env_var_references(str(tmp_path)) == set()


def test_find_env_var_references_ignores_lowercase_names(tmp_path):
    (tmp_path / "x.py").write_text("os.environ.get('not_all_caps')\n")
    assert vj.find_env_var_references(str(tmp_path)) == set()


# ── classify_walk_direction ────────────────────────────────────────────────────


def test_walk_direction_forward_when_ten_plus_bills_ascend():
    bills = [["2024-01-01", "2024-01-15"] for _ in range(10)]
    assert vj.classify_walk_direction(bills) == "forward"


def test_walk_direction_backward_when_ten_plus_bills_descend():
    bills = [["2024-01-15", "2024-01-01"] for _ in range(10)]
    assert vj.classify_walk_direction(bills) == "backward"


def test_walk_direction_mixed_when_both_seen():
    bills = [["2024-01-01", "2024-01-15"] for _ in range(6)] + [["2024-01-15", "2024-01-01"] for _ in range(6)]
    assert vj.classify_walk_direction(bills) == "mixed"


def test_walk_direction_unknown_below_threshold():
    bills = [["2024-01-01", "2024-01-15"] for _ in range(9)]
    assert vj.classify_walk_direction(bills) == "unknown"


def test_walk_direction_skips_bills_with_blank_dates():
    bills = [["", ""] for _ in range(20)]
    assert vj.classify_walk_direction(bills) == "unknown"


def test_walk_direction_skips_single_version_bills():
    assert vj.classify_walk_direction([["2024-01-01"]] * 20) == "unknown"


def test_walk_direction_neither_direction_not_counted_either_way():
    # a substitute-heavy shape: dates neither strictly ascend nor descend
    bills = [["2024-01-01", "2024-01-15", "2024-01-05"] for _ in range(15)]
    assert vj.classify_walk_direction(bills) == "unknown"


# ── session_code_shape_ok ──────────────────────────────────────────────────────


def test_session_code_shape_three_digits_ok():
    assert vj.session_code_shape_ok("119") is True


def test_session_code_shape_four_digits_ok():
    assert vj.session_code_shape_ok("2026") is True


def test_session_code_shape_four_digits_plus_letters_ok():
    assert vj.session_code_shape_ok("2026D") is True


def test_session_code_shape_rejects_arizona_style_identifier():
    """Real, pre-existing finding: AZ's actual session identifiers ("57th-1st-regular") do not
    match the broker's regex -- confirmed live against the dev DB, 2026-08-30."""
    assert vj.session_code_shape_ok("57th-1st-regular") is False


def test_session_code_shape_rejects_empty_and_none():
    assert vj.session_code_shape_ok("") is False
    assert vj.session_code_shape_ok(None) is False


def test_session_code_shape_rejects_two_digits():
    assert vj.session_code_shape_ok("26") is False


# ── classify_probe ──────────────────────────────────────────────────────────


def _gate(gate, blocking, status, block_signature=False):
    return vj.GateResult(gate, blocking, status, "summary", block_signature=block_signature)


def test_exit_code_green_is_zero():
    assert vj.exit_code_for_classification("green") == 0


def test_exit_code_yellow_is_nonzero():
    """Round-1 PM review fold: yellow -- including a blocking gate failure or a refused
    --import -- used to exit 0, indistinguishable from a clean pass to a shell/CI caller."""
    assert vj.exit_code_for_classification("yellow") != 0


def test_exit_code_red_is_nonzero_and_distinct_from_yellow():
    assert vj.exit_code_for_classification("red") != 0
    assert vj.exit_code_for_classification("red") != vj.exit_code_for_classification("yellow")


def test_classify_all_pass_is_green():
    gates = [_gate(g, True, "pass") for g in "ABCDH"] + [_gate(g, False, "pass") for g in "EFG"]
    assert vj.classify_probe(gates) == "green"


def test_classify_advisory_warn_is_yellow():
    gates = [_gate(g, True, "pass") for g in "ABCDH"] + [_gate("E", False, "warn"), _gate("F", False, "skip"), _gate("G", False, "pass")]
    assert vj.classify_probe(gates) == "yellow"


# -- Round-1 PM review fold: a blocking gate that's inconclusive (warn/skip) must not be
# -- rolled up into green -- only a clean "pass" on every blocking gate earns green.


def test_classify_blocking_gate_c_warn_is_not_green():
    """Gate C warns when the dry scrape produced no document links to check coverage against --
    inconclusive, not confirmed-fine."""
    gates = [_gate("A", True, "pass"), _gate("B", True, "pass"), _gate("C", True, "warn"),
             _gate("D", True, "pass"), _gate("H", True, "pass")] + [_gate(g, False, "pass") for g in "EFG"]
    assert vj.classify_probe(gates) == "yellow"


def test_classify_blocking_gate_d_skip_is_not_green():
    """Gate D skips when a real scrape lock is held -- the probe couldn't run at all, not the
    same as confirming the state scrapes cleanly."""
    gates = [_gate("A", True, "pass"), _gate("B", True, "pass"), _gate("C", True, "pass"),
             _gate("D", True, "skip"), _gate("H", True, "pass")] + [_gate(g, False, "pass") for g in "EFG"]
    assert vj.classify_probe(gates) == "yellow"


def test_classify_blocking_gate_h_skip_is_not_green():
    """Gate H skips when no DATABASE_URL is configured -- the probe never actually checked
    whether BillVersionLink rows exist."""
    gates = [_gate("A", True, "pass"), _gate("B", True, "pass"), _gate("C", True, "pass"),
             _gate("D", True, "pass"), _gate("H", True, "skip")] + [_gate(g, False, "pass") for g in "EFG"]
    assert vj.classify_probe(gates) == "yellow"


def test_classify_blocking_gate_h_stale_warn_is_not_green():
    gates = [_gate("A", True, "pass"), _gate("B", True, "pass"), _gate("C", True, "pass"),
             _gate("D", True, "pass"), _gate("H", True, "warn")] + [_gate(g, False, "pass") for g in "EFG"]
    assert vj.classify_probe(gates) == "yellow"


def test_classify_extractor_coverage_failure_is_yellow():
    gates = [_gate("A", True, "pass"), _gate("B", True, "pass"), _gate("C", True, "fail"),
             _gate("D", True, "pass"), _gate("H", True, "pass")]
    assert vj.classify_probe(gates) == "yellow"


def test_classify_zero_links_after_scrape_is_yellow_the_ut_trap():
    gates = [_gate("A", True, "pass"), _gate("B", True, "pass"), _gate("C", True, "pass"),
             _gate("D", True, "pass"), _gate("H", True, "fail")]
    assert vj.classify_probe(gates) == "yellow"


def test_classify_session_list_failure_is_red():
    gates = [_gate("A", True, "fail")]
    assert vj.classify_probe(gates) == "red"


def test_classify_block_signature_on_dry_scrape_is_red():
    gates = [_gate("A", True, "pass"), _gate("D", True, "fail", block_signature=True)]
    assert vj.classify_probe(gates) == "red"


def test_classify_zero_objects_no_block_signature_is_red():
    """Structural failure with no known shape to explain it -- treated as red (needs human
    scoping), distinct from a WAF signature which is also red but for a named reason."""
    gates = [_gate("A", True, "pass"), _gate("D", True, "fail", block_signature=False)]
    assert vj.classify_probe(gates) == "red"


def test_classify_credential_failure_is_yellow_not_red():
    gates = [_gate("A", True, "pass"), _gate("B", True, "fail")]
    assert vj.classify_probe(gates) == "yellow"


# ── render_report (format-only smoke checks) ───────────────────────────────────


def test_render_report_includes_classification_and_every_gate():
    gates = [_gate(g, True, "pass") for g in "ABCDH"] + [_gate(g, False, "pass") for g in "EFG"]
    text = vj.render_report("fl", "Florida", "green", gates, 12.3, datetime.datetime(2026, 8, 30, tzinfo=datetime.timezone.utc))
    assert "**Classification:** GREEN" in text
    for g in "ABCDEFGH":
        assert f"Gate {g}" in text
    assert "fl (Florida)" in text


# ── run_gate_d safety branches (scrape lock / missing bills scraper) ──────────


class _FakeJurisNoBills:
    scrapers = {}


class _FakeJurisWithBills:
    def __init__(self, bills_cls):
        self.scrapers = {"bills": bills_cls}


def test_gate_d_skips_when_scrape_lock_held(tmp_path, monkeypatch):
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()
    (lock_dir / "zz").mkdir()  # a held lock for jurisdiction "zz"
    monkeypatch.setattr(vj, "SCRAPE_LOCK_DIR", str(lock_dir))

    result, bill_files, report = vj.run_gate_d(_FakeJurisNoBills(), "zz", None, 5, str(tmp_path))
    assert result.status == "skip"
    assert bill_files == []
    assert report is None


def test_gate_d_fails_when_no_bills_scraper_registered(tmp_path, monkeypatch):
    monkeypatch.setattr(vj, "SCRAPE_LOCK_DIR", str(tmp_path / "no-such-lock-dir"))
    result, bill_files, report = vj.run_gate_d(_FakeJurisNoBills(), "zz", None, 5, str(tmp_path))
    assert result.status == "fail"
    assert "no 'bills' scraper" in result.summary
    assert bill_files == []


def test_render_report_red_recommendation_mentions_human_scoping():
    gates = [_gate("A", True, "fail")]
    text = vj.render_report("zz", "Zed", "red", gates, 1.0, datetime.datetime(2026, 8, 30, tzinfo=datetime.timezone.utc))
    assert "human scoping" in text


# ── main(): the get_jurisdiction() import crash (round-1 fold) ────────────────


def test_main_reports_red_instead_of_crashing_when_module_import_fails(tmp_path, monkeypatch):
    """Confirmed live against real candidate states: GA needs `suds`, OH needs `cloudscraper`,
    neither installed in this checkout's venv -- the same class of gap OPEN-125 already found
    once for a different five states. Before this fix, that ModuleNotFoundError propagated all
    the way out of main() as a raw traceback and a Python-default exit code that happened to
    collide with "yellow" -- this state was never actually probed, and nothing said so."""
    monkeypatch.setenv("SCRAPED_DATA_DIR", str(tmp_path))

    with patch(
        "openstates.cli.update.get_jurisdiction",
        side_effect=ModuleNotFoundError("No module named 'suds'"),
    ):
        exit_code = vj.main(["ga", "--notes-dir", str(tmp_path)])

    assert exit_code == vj.exit_code_for_classification("red")

    # Round-1 review fold: locate the actual generated report rather than recomputing "today"
    # a second time -- main() computes its own run_at internally, and a test that independently
    # calls datetime.now() again would flake if the two calls straddle UTC midnight.
    reports = list(tmp_path.glob("ga-onboarding-probe-*.md"))
    assert len(reports) == 1
    report = reports[0].read_text()

    assert "RED" in report
    assert "could not import scraper module" in report
    assert "suds" in report
    assert "human scoping" in report
    # Round-1 review fold: assert the Gate A failure row explicitly, not just the surrounding
    # prose -- protects the intended one-gate report contract (exactly Gate A, marked FAIL).
    assert "| A | yes | FAIL |" in report


# ── gate H: people before the first import (OPEN-446, onboarding order rule 1) ─


class _FakeCursor:
    def __init__(self, people, sessions=("2025",)):
        self._people = people
        self._sessions = sessions
        self._row = None
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if "FROM opencivicdata_legislativesession WHERE" in sql:
            self._rows = [(i,) for i in self._sessions]
        elif "opencivicdata_membership" in sql:
            self._row = (self._people,)
        elif "count(*)" in sql:
            self._row = (3,)
        else:
            self._row = (datetime.datetime.now(datetime.timezone.utc),)

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, people, sessions=("2025",)):
        self._people = people
        self._sessions = sessions
        self.cursors = []

    def cursor(self):
        cur = _FakeCursor(self._people, self._sessions)
        self.cursors.append(cur)
        return cur


def test_count_people_loaded_reads_the_jurisdictions_membership_count():
    conn = _FakeConn(508)
    assert vj.count_people_loaded(conn, "nc") == 508
    sql, params = conn.cursors[0].executed[0]
    assert params == ("ocd-jurisdiction/country:us/state:nc/government",)
    assert "opencivicdata_membership" in sql and "o.jurisdiction_id = %s" in sql


def test_gate_h_import_refused_when_no_people_loaded_and_nothing_is_run():
    with patch.object(vj.subprocess, "run", side_effect=AssertionError("os-update must not run")):
        result = vj.run_gate_h(_FakeConn(0), "nc", "2025", [], True, "/venv", "nc", "/data", object())
    assert result.status == "fail"
    assert result.blocking is True
    assert "os-people to-database nc" in result.summary


def test_gate_h_import_runs_when_people_are_loaded():
    done = type("Done", (), {"returncode": 0, "stderr": ""})()
    with patch.object(vj, "scrape_jurisdiction_objects"), patch.object(vj, "stage_import_dir", return_value="/root"), patch.object(vj.subprocess, "run", return_value=done) as run:
        result = vj.run_gate_h(_FakeConn(508), "nc", "2025", [], True, "/venv", "nc", "/data", object())
    assert run.called
    assert result.status == "pass"


def test_gate_h_without_import_does_not_ask_for_people():
    """The people rule is about the first import; a probe run without --import only reads."""
    result = vj.run_gate_h(_FakeConn(0), "nc", "2025", [], False, "/venv", "nc", "/data", object())
    assert result.status == "pass"


# ── gate H: session rows exist after --import (OPEN-456) ───────────────────────


_DONE = type("Done", (), {"returncode": 0, "stderr": ""})()


def test_gate_h_import_writes_the_jurisdiction_objects_before_the_bills_import():
    calls = []
    juris = object()
    with patch.object(vj, "scrape_jurisdiction_objects", side_effect=lambda j, d: calls.append(("objects", j, d))), \
            patch.object(vj, "stage_import_dir", return_value="/root"), \
            patch.object(vj.subprocess, "run", side_effect=lambda cmd, **k: calls.append(("import", cmd[-1])) or _DONE):
        vj.run_gate_h(_FakeConn(508), "nc", "2025", [], True, "/venv", "nc", "/data", juris)
    assert calls == [("objects", juris, "/data"), ("import", "/root")]


def test_stage_import_dir_puts_the_probe_files_where_os_update_reads_them(tmp_path):
    probe = tmp_path / "_probe" / "us"
    probe.mkdir(parents=True)
    (probe / "bill_1.json").write_text("{}")
    stale = tmp_path / "_probe" / "_import" / "usa"
    stale.mkdir(parents=True)
    (stale / "old.json").write_text("{}")
    root = vj.stage_import_dir(str(probe), "usa")
    # os-update reads <--datadir>/<module>: the module is usa even though the probe dir is us
    assert sorted(os.listdir(os.path.join(root, "usa"))) == ["bill_1.json"]


def test_gate_h_import_reports_the_session_rows_it_created():
    with patch.object(vj, "scrape_jurisdiction_objects"), patch.object(vj, "stage_import_dir", return_value="/root"), patch.object(vj.subprocess, "run", return_value=_DONE):
        result = vj.run_gate_h(_FakeConn(508, ("2025", "2025E1")), "nc", "2025", [], True, "/venv", "nc", "/data", object())
    assert result.status == "pass"
    assert any("2 (2025, 2025E1)" in d for d in result.details)


def test_gate_h_import_fails_when_the_probed_session_has_no_row_after_the_import():
    with patch.object(vj, "scrape_jurisdiction_objects"), patch.object(vj, "stage_import_dir", return_value="/root"), patch.object(vj.subprocess, "run", return_value=_DONE):
        result = vj.run_gate_h(_FakeConn(508, ("2024",)), "nc", "2025", [], True, "/venv", "nc", "/data", object())
    assert result.status == "fail"
    assert "2025" in result.summary and "no LegislativeSession row" in result.summary


# ── gate I: vote keys must not repeat across sessions (OPEN-456, OPEN-397) ─────


def _write_vote(path, key, session, bill):
    import json

    path.write_text(json.dumps({"dedupe_key": key, "legislative_session": session, "bill_identifier": bill}))
    return str(path)


def test_vote_key_collision_found_across_sessions(tmp_path):
    a = _write_vote(tmp_path / "vote_event_a.json", "roll-call-7", "2025", "HB 1")
    b = _write_vote(tmp_path / "vote_event_b.json", "roll-call-7", "2025E1", "HB 1")
    collisions, unreadable = vj.find_vote_key_collisions([a, b])
    assert collisions == {"roll-call-7": [("2025", "HB 1"), ("2025E1", "HB 1")]}
    assert unreadable == []


def test_vote_key_collision_found_across_bills_in_one_session(tmp_path):
    a = _write_vote(tmp_path / "vote_event_a.json", "pdf-url", "194th", "S1")
    b = _write_vote(tmp_path / "vote_event_b.json", "pdf-url", "194th", "H2")
    assert list(vj.find_vote_key_collisions([a, b])[0]) == ["pdf-url"]


def test_vote_key_repeated_on_the_same_session_and_bill_is_not_a_collision(tmp_path):
    a = _write_vote(tmp_path / "vote_event_a.json", "k", "2025", "HB 1")
    b = _write_vote(tmp_path / "vote_event_b.json", "k", "2025", "HB 1")
    assert vj.find_vote_key_collisions([a, b]) == ({}, [])


def test_votes_without_a_key_are_ignored_and_unreadable_files_are_reported(tmp_path):
    a = _write_vote(tmp_path / "vote_event_a.json", None, "2025", "HB 1")
    b = _write_vote(tmp_path / "vote_event_b.json", "", "2025E1", "HB 1")
    bad = tmp_path / "vote_event_c.json"
    bad.write_text("{not json")
    missing = str(tmp_path / "missing.json")
    assert vj.find_vote_key_collisions([a, b, str(bad), missing]) == ({}, [str(bad), missing])


def _fake_gate_d(votes_by_session, status="pass"):
    """A run_gate_d stand-in that writes each session's votes into the datadir it is given."""
    def fake(juris, st, session, sample, scraped_data_dir, datadir=None, max_objects=None):
        import os

        os.makedirs(datadir, exist_ok=True)
        for i, (key, bill) in enumerate(votes_by_session.get(session, [])):
            _write_vote(__import__("pathlib").Path(datadir) / f"vote_event_{i}.json", key, session, bill)
        return vj.GateResult("D", True, status, "x"), [], None
    return fake


def _probe_votes(tmp_path, votes):
    import pathlib

    d = pathlib.Path(tmp_path) / "_probe" / "nc"
    d.mkdir(parents=True)
    for i, (key, session, bill) in enumerate(votes):
        _write_vote(d / f"vote_event_{i}.json", key, session, bill)


def test_gate_i_passes_with_a_single_active_session(tmp_path):
    result = vj.run_gate_i(object(), "nc", "2025", ["2025"], 5, str(tmp_path))
    assert result.status == "pass" and result.blocking is True


def test_gate_i_fails_when_a_key_repeats_in_another_session(tmp_path):
    _probe_votes(tmp_path, [("roll-call-7", "2025", "HB 1")])
    fake = _fake_gate_d({"2025E1": [("roll-call-7", "HB 9")]})
    with patch.object(vj, "run_gate_d", side_effect=fake):
        result = vj.run_gate_i(object(), "nc", "2025", ["2025", "2025E1"], 5, str(tmp_path))
    assert result.status == "fail"
    assert any("roll-call-7" in d for d in result.details)


def test_gate_i_passes_when_keys_differ_across_sessions(tmp_path):
    _probe_votes(tmp_path, [("2025-roll-call-7", "2025", "HB 1")])
    fake = _fake_gate_d({"2025E1": [("2025E1-roll-call-7", "HB 9")]})
    with patch.object(vj, "run_gate_d", side_effect=fake):
        result = vj.run_gate_i(object(), "nc", "2025", ["2025", "2025E1"], 5, str(tmp_path))
    assert result.status == "pass"


def test_gate_i_is_inconclusive_when_another_session_cannot_be_sampled(tmp_path):
    _probe_votes(tmp_path, [("k", "2025", "HB 1")])
    with patch.object(vj, "run_gate_d", side_effect=_fake_gate_d({}, status="fail")):
        result = vj.run_gate_i(object(), "nc", "2025", ["2025", "2025E1"], 5, str(tmp_path))
    assert result.status == "warn"


def test_gate_i_is_inconclusive_when_the_sample_has_no_vote_events(tmp_path):
    (__import__("pathlib").Path(tmp_path) / "_probe" / "nc").mkdir(parents=True)
    with patch.object(vj, "run_gate_d", side_effect=_fake_gate_d({})):
        result = vj.run_gate_i(object(), "nc", "2025", ["2025", "2025E1"], 5, str(tmp_path))
    assert result.status == "warn"


def test_gate_i_is_inconclusive_when_a_vote_file_cannot_be_read(tmp_path):
    _probe_votes(tmp_path, [("2025-k", "2025", "HB 1")])
    (__import__("pathlib").Path(tmp_path) / "_probe" / "nc" / "vote_event_bad.json").write_text("{not json")
    fake = _fake_gate_d({"2025E1": [("2025E1-k", "HB 9")]})
    with patch.object(vj, "run_gate_d", side_effect=fake):
        result = vj.run_gate_i(object(), "nc", "2025", ["2025", "2025E1"], 5, str(tmp_path))
    assert result.status == "warn"
    assert any("vote_event_bad.json" in d for d in result.details)


def test_gate_i_samples_at_most_the_capped_number_of_other_sessions(tmp_path):
    _probe_votes(tmp_path, [("k", "2025", "HB 1")])
    seen = []

    def fake(juris, st, session, sample, scraped_data_dir, datadir=None, max_objects=None):
        seen.append(session)
        return vj.GateResult("D", True, "pass", "x"), [], None

    with patch.object(vj, "run_gate_d", side_effect=fake):
        vj.run_gate_i(object(), "nc", "2025", ["2025", "a", "b", "c", "d"], 5, str(tmp_path))
    assert seen == ["a", "b"]


def test_classify_gate_i_failure_is_yellow_and_inconclusive_is_not_green():
    base = [vj.GateResult("A", True, "pass", "x")]
    assert vj.classify_probe(base + [vj.GateResult("I", True, "fail", "x")]) == "yellow"
    assert vj.classify_probe(base + [vj.GateResult("I", True, "warn", "x")]) == "yellow"
    assert vj.classify_probe(base + [vj.GateResult("I", True, "pass", "x")]) == "green"


# ── OPEN-261: gate J, unresolved voter attribution ─────────────────────────────


class _FakeVoterCursor:
    def __init__(self, total, unresolved, top_names=None):
        self.total = total
        self.unresolved = unresolved
        self.top_names = top_names or []
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return (self.total, self.unresolved)

    def fetchall(self):
        return self.top_names


class _FakeVoterConn:
    def __init__(self, total, unresolved, top_names=None):
        self._cursor = _FakeVoterCursor(total, unresolved, top_names)

    def cursor(self):
        return self._cursor


def test_gate_j_is_advisory_and_not_blocking():
    conn = _FakeVoterConn(100, 0)
    result = vj.run_gate_j(conn, "fl", "2026", ["2026"])
    assert result.gate == "J" and result.blocking is False


def test_gate_j_passes_when_nothing_is_unresolved():
    conn = _FakeVoterConn(100, 0)
    result = vj.run_gate_j(conn, "fl", "2026", ["2026"])
    assert result.status == "pass"
    assert "0/100" in result.summary


def test_gate_j_warns_and_lists_top_offending_names_when_unresolved_rows_exist():
    conn = _FakeVoterConn(100, 10, [("Smith", 7), ("Jones", 3)])
    result = vj.run_gate_j(conn, "fl", "2026", ["2026"])
    assert result.status == "warn"
    assert "10/100" in result.summary and "10.0%" in result.summary
    assert any("Smith" in d and "7" in d for d in result.details)
    assert any("Jones" in d and "3" in d for d in result.details)


def test_gate_j_skips_when_the_sample_has_no_personvote_rows():
    conn = _FakeVoterConn(0, 0)
    result = vj.run_gate_j(conn, "fl", "2026", ["2026"])
    assert result.status == "skip"
    assert "nothing to resolve" in result.summary


def test_gate_j_samples_at_most_the_capped_number_of_other_sessions():
    conn = _FakeVoterConn(0, 0)
    vj.run_gate_j(conn, "nc", "2025", ["2025", "a", "b", "c", "d"])
    _sql, params = conn._cursor.executed[0]
    assert params[1] == ["2025", "a", "b"]


def test_gate_j_sorts_after_gate_i_in_gate_order():
    assert vj.GATE_ORDER["J"] > vj.GATE_ORDER["I"]


def test_classify_gate_j_warn_is_yellow_via_advisory_warn_path():
    base = [vj.GateResult("A", True, "pass", "x")]
    assert vj.classify_probe(base + [vj.GateResult("J", False, "warn", "x")]) == "yellow"
    assert vj.classify_probe(base + [vj.GateResult("J", False, "pass", "x")]) == "green"


def test_a_clean_probe_with_no_vote_rows_stays_green():
    # A brand-new state has no imported votes at probe time; that must not turn the probe yellow.
    empty = vj.run_gate_j(_FakeVoterConn(0, 0), "co", "2026A", ["2026A"])
    assert vj.classify_probe([vj.GateResult("A", True, "pass", "x"), empty]) == "green"


def _scratch_postgres():
    """A throwaway database on the dev Postgres server (own database, dropped afterwards), or None."""
    import uuid
    import psycopg2
    try:
        admin = psycopg2.connect("postgresql://openstates:openstates_dev@localhost:5433/postgres", connect_timeout=2)
    except psycopg2.OperationalError:
        return None
    admin.autocommit = True
    name = "gate_j_test_" + uuid.uuid4().hex[:8]
    admin.cursor().execute(f"CREATE DATABASE {name}")
    return admin, name


def test_gate_j_query_against_a_real_postgres_counts_only_named_unresolved_rows():
    # The fake-cursor tests above never run the SQL; this one does, so a changed WHERE/FILTER fails.
    psycopg2 = __import__("pytest").importorskip("psycopg2")
    made = _scratch_postgres()
    if made is None:
        __import__("pytest").skip("dev Postgres on :5433 is not reachable")
    admin, name = made
    try:
        conn = psycopg2.connect(f"postgresql://openstates:openstates_dev@localhost:5433/{name}")
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE opencivicdata_jurisdiction (id text PRIMARY KEY);
            CREATE TABLE opencivicdata_legislativesession (id int PRIMARY KEY, jurisdiction_id text, identifier text);
            CREATE TABLE opencivicdata_bill (id text PRIMARY KEY, legislative_session_id int);
            CREATE TABLE opencivicdata_voteevent (id text PRIMARY KEY, bill_id text);
            CREATE TABLE opencivicdata_personvote (id serial PRIMARY KEY, vote_event_id text, voter_name text, voter_id text);
        """)
        jid = vj.ocd_jurisdiction_id("co")
        cur.execute("INSERT INTO opencivicdata_jurisdiction VALUES (%s)", (jid,))
        cur.execute("INSERT INTO opencivicdata_legislativesession VALUES (1, %s, '2026A'), (2, %s, '2025A')", (jid, jid))
        cur.execute("INSERT INTO opencivicdata_bill VALUES ('b1', 1), ('b2', 2)")
        cur.execute("INSERT INTO opencivicdata_voteevent VALUES ('v1', 'b1'), ('v2', 'b2')")
        cur.execute("""INSERT INTO opencivicdata_personvote (vote_event_id, voter_name, voter_id) VALUES
            ('v1', 'Resolved Rep', 'p1'),
            ('v1', 'Garcia', NULL), ('v1', 'Garcia', NULL), ('v1', 'Smith', NULL),
            ('v1', NULL, NULL),
            ('v2', 'Other Session', NULL)""")
        result = vj.run_gate_j(conn, "co", "2026A", ["2026A"])
        # 5 rows in 2026A; 3 have a name and no voter_id (the nameless row and the resolved row do not count);
        # the 2025A row is outside the sample.
        assert result.status == "warn"
        assert "3/5" in result.summary
        assert any("Garcia" in d and "2" in d for d in result.details)
        assert not any("Other Session" in d for d in result.details)
        # A session with no rows is the empty case.
        assert vj.run_gate_j(conn, "co", "2027A", ["2027A"]).status == "skip"
        conn.close()
    finally:
        admin.cursor().execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
        admin.close()


# ── OPEN-458: the probe on Fargate, and finishing its output on the Mac ───────


class _Args:
    def __init__(self, do_import=False, force_import=False):
        self.do_import = do_import
        self.force_import = force_import


_FARGATE_ENV = {"MEMORY_BUCKET": "bucket", "MEMORY_PREFIX": "dev-probe-co-20261030"}


def test_gate_result_round_trips_through_a_dict():
    g = vj.GateResult("D", True, "fail", "blocked", details=["x"], block_signature=True)
    back = vj.GateResult.from_dict(g.to_dict())
    assert (back.gate, back.blocking, back.status, back.summary, back.details, back.block_signature) == (
        "D", True, "fail", "blocked", ["x"], True,
    )


def test_fargate_refusal_allows_a_plain_probe_run():
    """"co" is not a tracked jurisdiction -- a brand-new onboarding candidate has no manifest
    entry yet, and that is exactly the case this probe exists to run against."""
    assert vj.fargate_refusal("co", _Args(), _FARGATE_ENV) is None


def test_fargate_refusal_refuses_michigan():
    """Against the real, checked-in jurisdictions.yaml: mi.waf.fargate_safe is false."""
    assert "mi" in vj.fargate_refusal("mi", _Args(), _FARGATE_ENV)


def test_fargate_refusal_does_not_refuse_florida_despite_sharing_the_cookie_provider_profile():
    """AC: the probe's refusal and the manifest agree for every state -- specifically, mi and fl
    share waf.profile: cookie_provider but must disagree on the Fargate refusal, because only mi's
    cookie requires the Mac's mint."""
    assert vj.fargate_refusal("fl", _Args(), _FARGATE_ENV) is None


def test_fargate_refusal_agrees_with_waf_fargate_safe_for_every_state_in_the_real_manifest():
    from validate_jurisdictions import load_and_validate

    manifest, problems = load_and_validate(vj.MANIFEST_PATH)
    assert not problems, problems
    for code, entry in manifest.items():
        refused = vj.fargate_refusal(code, _Args(), _FARGATE_ENV) is not None
        assert refused == (not entry["waf"]["fargate_safe"]), code


def test_fargate_refusal_fails_closed_when_the_manifest_is_missing(tmp_path, monkeypatch):
    """No manifest means fargate_safe cannot be checked for ANYONE, so every state is refused --
    not silently allowed. A quiet pass here is the exact "measured zero" failure class OPEN-188/
    OPEN-152/OPEN-153 already found once."""
    monkeypatch.setattr(vj, "MANIFEST_PATH", str(tmp_path / "does-not-exist.yaml"))
    refusal = vj.fargate_refusal("co", _Args(), _FARGATE_ENV)
    assert refusal is not None and "does not validate" in refusal


def test_fargate_refusal_fails_closed_when_the_manifest_does_not_validate(tmp_path, monkeypatch):
    import yaml

    from test_validate_jurisdictions import _valid_entry

    bad = _valid_entry()
    del bad["waf"]["fargate_safe"]  # schema-invalid: fargate_safe is required
    manifest_path = tmp_path / "jurisdictions.yaml"
    manifest_path.write_text(yaml.safe_dump({"mi": bad}))
    monkeypatch.setattr(vj, "MANIFEST_PATH", str(manifest_path))

    refusal = vj.fargate_refusal("mi", _Args(), _FARGATE_ENV)
    assert refusal is not None and "does not validate" in refusal


def test_fargate_refusal_refuses_import_and_force_import():
    assert "--import" in vj.fargate_refusal("co", _Args(do_import=True), _FARGATE_ENV)
    assert "--import" in vj.fargate_refusal("co", _Args(force_import=True), _FARGATE_ENV)


def test_fargate_refusal_needs_a_bucket_and_a_non_prod_prefix():
    assert "MEMORY_BUCKET" in vj.fargate_refusal("co", _Args(), {"MEMORY_PREFIX": "dev-x"})
    assert "MEMORY_PREFIX" in vj.fargate_refusal("co", _Args(), {"MEMORY_BUCKET": "b"})
    for prod in ("prod", "PROD", "/prod/", " prod ", "prod/probe", "Prod/dev-x"):
        assert "'prod'" in vj.fargate_refusal("co", _Args(), {"MEMORY_BUCKET": "b", "MEMORY_PREFIX": prod})


def test_main_refuses_a_bad_fargate_run_before_touching_the_scraper(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "prod")
    with patch("openstates.cli.update.get_jurisdiction", side_effect=AssertionError("must not load a scraper")):
        assert vj.main(["co", "--fargate"]) == vj.EXIT_REFUSED
        assert vj.main(["mi", "--fargate"]) == vj.EXIT_REFUSED


class _FakeS3:
    def __init__(self, fail=False):
        self.objects = {}
        self.fail = fail

    def put_object(self, Bucket, Key, Body):
        if self.fail:
            raise RuntimeError("AccessDenied")
        self.objects[(Bucket, Key)] = Body


def test_upload_probe_output_writes_the_report_result_and_sample_under_the_probe_prefix(tmp_path):
    import io
    import tarfile

    sample = tmp_path / "_probe" / "co"
    sample.mkdir(parents=True)
    (sample / "bill_1.json").write_text("{}")
    s3 = _FakeS3()
    keys = vj.upload_probe_output(s3, "bucket", "/dev-probe-co/", "co", "run1", "# report", {"a": 1}, str(tmp_path))
    assert keys == [
        "dev-probe-co/probe/co/run1/sample.tar.gz",
        "dev-probe-co/probe/co/run1/report.md",
        "dev-probe-co/probe/co/run1/result.json",
    ]
    assert s3.objects[("bucket", keys[1])] == b"# report"
    with tarfile.open(fileobj=io.BytesIO(s3.objects[("bucket", keys[0])]), mode="r:gz") as tar:
        assert "_probe/co/bill_1.json" in tar.getnames()


class _FailsOnSecondPut(_FakeS3):
    def put_object(self, Bucket, Key, Body):
        if len(self.objects) >= 1:
            raise RuntimeError("AccessDenied")
        super().put_object(Bucket, Key, Body)


def test_a_failed_upload_never_leaves_a_result_json_behind(tmp_path):
    """result.json is the sign that a run's upload finished; --from-dir will not start without it."""
    (tmp_path / "_probe" / "co").mkdir(parents=True)
    s3 = _FailsOnSecondPut()
    try:
        vj.upload_probe_output(s3, "bucket", "dev", "co", "run1", "r", {}, str(tmp_path))
    except RuntimeError:
        pass
    assert not any(key.endswith("result.json") for _bucket, key in s3.objects)


def test_upload_probe_output_skips_the_sample_when_nothing_was_scraped(tmp_path):
    s3 = _FakeS3()
    keys = vj.upload_probe_output(s3, "bucket", "dev", "co", "run1", "r", {}, str(tmp_path))
    assert [k.rsplit("/", 1)[1] for k in keys] == ["report.md", "result.json"]


def _fargate_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-probe-co-20261030")
    monkeypatch.setenv("RUN_ID", "run1")
    monkeypatch.delenv("DATABASE_URL", raising=False)


def test_main_fargate_uploads_a_red_report_and_exits_zero_when_the_module_cannot_load(tmp_path, monkeypatch):
    """A failed scraper import is still a finding worth reading, and a task that exits non-zero
    would show up in ECS as a failure for what is a perfectly good probe result."""
    import json

    _fargate_env(monkeypatch, tmp_path)
    s3 = _FakeS3()
    with patch("openstates.cli.update.get_jurisdiction", side_effect=ModuleNotFoundError("No module named 'suds'")), \
            patch.object(vj, "_s3_client", return_value=s3):
        assert vj.main(["ga", "--fargate"]) == 0
    result = json.loads(s3.objects[("bucket", "dev-probe-co-20261030/probe/ga/run1/result.json")])
    assert result["classification"] == "red" and result["gates"][0]["gate"] == "A"
    assert "suds" in s3.objects[("bucket", "dev-probe-co-20261030/probe/ga/run1/report.md")].decode()


def test_main_fargate_exits_with_the_upload_code_when_the_upload_fails(tmp_path, monkeypatch):
    _fargate_env(monkeypatch, tmp_path)
    with patch("openstates.cli.update.get_jurisdiction", side_effect=ModuleNotFoundError("x")), \
            patch.object(vj, "_s3_client", return_value=_FakeS3(fail=True)):
        assert vj.main(["ga", "--fargate"]) == vj.EXIT_UPLOAD_FAILED


def _passing(gate, blocking=True):
    return vj.GateResult(gate, blocking, "pass", f"{gate} ok")


def test_main_fargate_never_connects_to_a_database_and_skips_the_database_gates(tmp_path, monkeypatch):
    import json

    _fargate_env(monkeypatch, tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/openstates_dev")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    s3 = _FakeS3()
    juris = type("J", (), {"name": "Colorado"})()
    gate_a = vj.GateResult("A", True, "pass", "ok", details=["active: 2026A"])
    def load_scraper(module_name):
        assert "DATABASE_URL" not in os.environ, "scraper code must not be able to read the database URL on Fargate"
        return juris, None

    def scrape_one_bill(juris, st, session, sample, scraped_data_dir, datadir=None, max_objects=None):
        import pathlib

        d = pathlib.Path(scraped_data_dir) / "_probe" / st
        d.mkdir(parents=True)
        (d / "bill_1.json").write_text("{}")
        return _passing("D"), [], None

    with patch("openstates.cli.update.get_jurisdiction", side_effect=load_scraper), \
            patch.object(vj, "run_gate_a", return_value=gate_a), \
            patch.object(vj, "run_gate_b", return_value=_passing("B")), \
            patch.object(vj, "run_gate_d", side_effect=scrape_one_bill), \
            patch.object(vj, "run_gate_i", return_value=_passing("I")), \
            patch("psycopg2.connect", side_effect=AssertionError("Fargate must not connect to a database")), \
            patch.object(vj, "_s3_client", return_value=s3):
        assert vj.main(["co", "--fargate"]) == 0
    result = json.loads(s3.objects[("bucket", "dev-probe-co-20261030/probe/co/run1/result.json")])
    by_gate = {g["gate"]: g for g in result["gates"]}
    assert by_gate["H"]["status"] == "skip" and by_gate["G"]["status"] == "skip"
    assert by_gate["J"]["status"] == "skip"
    assert result["session"] == "2026A" and result["active_sessions"] == ["2026A"]
    assert list(result["sample_files"]) == [os.path.join("_probe", "co", "bill_1.json")]
    assert ("bucket", "dev-probe-co-20261030/probe/co/run1/sample.tar.gz") in s3.objects
    report = s3.objects[("bucket", "dev-probe-co-20261030/probe/co/run1/report.md")].decode()
    assert "Ran on Fargate" in report and "--from-dir" in report


# ── --from-dir: the Mac-side half ────────────────────────────────────────────


def _downloaded_folder(tmp_path, st="nc", gates=None, session="2025", active=("2025", "2025E1")):
    import json
    import pathlib

    root = pathlib.Path(tmp_path)
    (root / "_probe" / st).mkdir(parents=True)
    gates = gates if gates is not None else [
        vj.GateResult("A", True, "pass", "fargate A", details=["active: 2025, 2025E1"]),
        vj.GateResult("B", True, "pass", "fargate B"),
        vj.GateResult("D", True, "pass", "fargate D"),
    ]
    (root / "result.json").write_text(json.dumps({
        "state": st, "run_id": "run1", "run_at": "2026-10-30T16:00:00+00:00", "session": session,
        "active_sessions": list(active), "sample_files": vj.sample_manifest(str(root)),
        "gates": [g.to_dict() for g in gates],
    }))
    return root


def _seal(root):
    """Record the sample as it now stands, as a finished Fargate run would have."""
    import json

    payload = json.loads((root / "result.json").read_text())
    payload["sample_files"] = vj.sample_manifest(str(root))
    (root / "result.json").write_text(json.dumps(payload))


def test_load_fargate_payload_reads_the_gates_back(tmp_path):
    root = _downloaded_folder(tmp_path)
    payload = vj.load_fargate_payload(str(root), "nc")
    assert [g.gate for g in payload["gates"]] == ["A", "B", "D"]
    assert payload["session"] == "2025"


def test_load_fargate_payload_explains_each_missing_piece(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="result.json"):
        vj.load_fargate_payload(str(tmp_path), "nc")
    root = _downloaded_folder(tmp_path / "x")
    with pytest.raises(ValueError, match="not 'co'"):
        vj.load_fargate_payload(str(root), "co")
    import shutil

    shutil.rmtree(root / "_probe")
    with pytest.raises(ValueError, match="un-tar"):
        vj.load_fargate_payload(str(root), "nc")


def _sample_session(root, name, votes, with_bill=True):
    d = root / "_probe" / name
    d.mkdir(parents=True, exist_ok=True)
    if with_bill:
        (d / "bill_1.json").write_text("{}")
    for i, (key, session, bill) in enumerate(votes):
        _write_vote(d / f"vote_event_{i}.json", key, session, bill)


def test_load_fargate_payload_refuses_a_sample_that_is_not_the_one_the_run_produced(tmp_path):
    """Two probes of the same state un-tarred into one folder would leave the first run's files
    beside the second's: the gates would then judge a mix under the second run's A, B and D."""
    import pytest

    root = _downloaded_folder(tmp_path)
    _sample_session(root, "nc", [("k", "2025", "HB 1")])
    _seal(root)
    vj.load_fargate_payload(str(root), "nc")  # untouched: accepted

    (root / "_probe" / "nc" / "bill_old_run.json").write_text("{}")
    with pytest.raises(ValueError, match="1 unexpected"):
        vj.load_fargate_payload(str(root), "nc")
    (root / "_probe" / "nc" / "bill_old_run.json").unlink()

    (root / "_probe" / "nc" / "vote_event_0.json").write_text('{"dedupe_key": "changed"}')
    with pytest.raises(ValueError, match="1 changed"):
        vj.load_fargate_payload(str(root), "nc")
    _write_vote(root / "_probe" / "nc" / "vote_event_0.json", "k", "2025", "HB 1")

    (root / "_probe" / "nc" / "bill_1.json").unlink()
    with pytest.raises(ValueError, match="1 file\\(s\\) missing"):
        vj.load_fargate_payload(str(root), "nc")


def test_load_fargate_payload_ignores_the_files_a_mac_import_writes_into_the_folder(tmp_path):
    root = _downloaded_folder(tmp_path)
    _sample_session(root, "nc", [("k", "2025", "HB 1")])
    _seal(root)
    (root / "_probe" / "nc" / "jurisdiction_x.json").write_text("{}")
    (root / "_probe" / "_import" / "nc").mkdir(parents=True)
    (root / "_probe" / "_import" / "nc" / "bill_1.json").write_text("{}")
    vj.load_fargate_payload(str(root), "nc")  # a second --from-dir --import run on the same folder


def test_load_fargate_payload_refuses_a_result_with_no_sample_list_or_bad_gates(tmp_path):
    import json
    import pytest

    root = _downloaded_folder(tmp_path)
    good = json.loads((root / "result.json").read_text())

    def write(**changes):
        (root / "result.json").write_text(json.dumps({**good, **changes}))

    write(sample_files=None)
    with pytest.raises(ValueError, match="lists no sample files"):
        vj.load_fargate_payload(str(root), "nc")
    write(gates=good["gates"][:2])
    with pytest.raises(ValueError, match="exactly one gate D"):
        vj.load_fargate_payload(str(root), "nc")
    write(gates=good["gates"] + [good["gates"][0]])
    with pytest.raises(ValueError, match="exactly one gate A"):
        vj.load_fargate_payload(str(root), "nc")
    write(gates=[{**good["gates"][0], "status": "great"}] + good["gates"][1:])
    with pytest.raises(ValueError, match="malformed gate result"):
        vj.load_fargate_payload(str(root), "nc")
    write(gates=[{"gate": "A"}] + good["gates"][1:])
    with pytest.raises(ValueError, match="malformed gate result"):
        vj.load_fargate_payload(str(root), "nc")


def test_gate_i_from_dir_fails_when_a_key_repeats_across_downloaded_sessions(tmp_path):
    root = _downloaded_folder(tmp_path)
    _sample_session(root, "nc", [("roll-call-7", "2025", "HB 1")])
    _sample_session(root, "nc-session-2025E1", [("roll-call-7", "2025E1", "HB 9")])
    result = vj.run_gate_i_from_dir("nc", "2025", ["2025", "2025E1"], str(root))
    assert result.status == "fail" and any("roll-call-7" in d for d in result.details)


def test_gate_i_from_dir_passes_when_keys_differ_and_does_not_scrape(tmp_path):
    root = _downloaded_folder(tmp_path)
    _sample_session(root, "nc", [("2025-k", "2025", "HB 1")])
    _sample_session(root, "nc-session-2025E1", [("2025E1-k", "2025E1", "HB 9")])
    with patch.object(vj, "run_gate_d", side_effect=AssertionError("must not scrape")):
        assert vj.run_gate_i_from_dir("nc", "2025", ["2025", "2025E1"], str(root)).status == "pass"


def test_gate_i_from_dir_is_inconclusive_when_another_session_was_not_sampled(tmp_path):
    root = _downloaded_folder(tmp_path)
    _sample_session(root, "nc", [("k", "2025", "HB 1")])
    assert vj.run_gate_i_from_dir("nc", "2025", ["2025", "2025E1"], str(root)).status == "warn"
    _sample_session(root, "nc-session-2025E1", [], with_bill=False)  # a folder with no bills is not a sample
    assert vj.run_gate_i_from_dir("nc", "2025", ["2025", "2025E1"], str(root)).status == "warn"


def test_gate_i_from_dir_passes_with_a_single_active_session(tmp_path):
    root = _downloaded_folder(tmp_path, active=("2025",))
    assert vj.run_gate_i_from_dir("nc", "2025", ["2025"], str(root)).status == "pass"


def test_gate_i_from_dir_compares_at_most_the_capped_number_of_other_sessions(tmp_path):
    root = _downloaded_folder(tmp_path)
    _sample_session(root, "nc", [("k", "2025", "HB 1")])
    _sample_session(root, "nc-session-a", [("a", "a", "HB 1")])
    _sample_session(root, "nc-session-b", [("b", "b", "HB 1")])
    _sample_session(root, "nc-session-c", [("k", "c", "HB 1")])  # would collide, but is past the cap
    result = vj.run_gate_i_from_dir("nc", "2025", ["2025", "a", "b", "c"], str(root))
    assert result.status == "pass"


def test_main_from_dir_reads_gates_a_b_d_from_the_fargate_run_and_runs_the_rest_here(tmp_path, monkeypatch):
    root = _downloaded_folder(tmp_path / "dl")
    _sample_session(root, "nc", [("roll-call-7", "2025", "HB 1")])
    _sample_session(root, "nc-session-2025E1", [("roll-call-7", "2025E1", "HB 9")])
    _seal(root)
    notes = tmp_path / "notes"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    never = AssertionError("a --from-dir run must not scrape or re-run a Fargate gate")
    with patch("openstates.cli.update.get_jurisdiction", return_value=(type("J", (), {"name": "NC"})(), None)), \
            patch.object(vj, "run_gate_a", side_effect=never), patch.object(vj, "run_gate_b", side_effect=never), \
            patch.object(vj, "run_gate_d", side_effect=never), patch.object(vj, "run_gate_i", side_effect=never):
        code = vj.main(["nc", "--from-dir", str(root), "--notes-dir", str(notes), "--people-dir", str(tmp_path)])
    report = next(notes.glob("nc-onboarding-probe-*.md")).read_text()
    assert "| A | yes | PASS | fargate A |" in report and "| D | yes | PASS | fargate D |" in report
    assert "| I | yes | FAIL |" in report and "roll-call-7" in report
    assert "| J | no | SKIP |" in report  # no DATABASE_URL in this test
    assert "come from the Fargate run run1" in report
    assert code == vj.exit_code_for_classification("yellow")


def test_main_from_dir_refuses_a_folder_that_is_not_a_probe_download(tmp_path):
    assert vj.main(["nc", "--from-dir", str(tmp_path)]) == vj.EXIT_REFUSED


def test_gate_h_import_fails_plainly_when_the_scraper_module_could_not_be_loaded_here():
    result = vj.run_gate_h(_FakeConn(people=3), "nc", "2025", [], True, "/venv", "nc", "/tmp/x", None)
    assert result.status == "fail" and "could not be loaded on this machine" in result.summary


def test_dockerfile_copies_the_probe_into_the_scrapers_image():
    """The probe runs on Fargate only if the image carries it; a file missing from this COPY
    line is a runtime 'No such file' on the task, found only after a deploy."""
    text = open(os.path.join(_HERE, "Dockerfile")).read()
    copy_line = next(line for line in text.splitlines() if line.startswith("COPY cloud_collector.py"))
    assert "verify-jurisdiction" in copy_line.split()


# ── OPEN-459: the sample limit counts bills, with a cap on everything ────────


class _Obj:
    def __init__(self, kind, name):
        self._type = kind
        self.name = name


def _scrape_of(*groups):
    """A scraper's output the way the real ones yield it: each bill's votes first, then the bill."""
    for votes, bill in groups:
        for i in range(votes):
            yield _Obj("vote_event", f"{bill}-v{i}")
        yield _Obj("bill", bill)


def _capped(groups, max_bills, max_objects):
    tally = {}
    kept = list(vj.cap_scrape_output(_scrape_of(*groups), max_bills, max_objects, tally))
    return kept, tally


def test_the_limit_counts_bills_not_objects():
    """Colorado's 20 objects were 1 bill and 19 votes; the limit must be 20 bills."""
    kept, tally = _capped([(5, f"HB{i}") for i in range(30)], max_bills=3, max_objects=1000)
    assert [o.name for o in kept if o._type == "bill"] == ["HB0", "HB1", "HB2"]
    assert (tally["bills"], tally["votes"], tally["objects"]) == (3, 15, 18)
    assert tally["stopped_by"] == "bill limit"


def test_each_kept_bill_keeps_all_its_votes_and_no_later_bill_leaks_votes():
    kept, _tally = _capped([(2, "HB1"), (3, "HB2"), (4, "HB3")], max_bills=2, max_objects=1000)
    assert [o.name for o in kept] == ["HB1-v0", "HB1-v1", "HB1", "HB2-v0", "HB2-v1", "HB2-v2", "HB2"]


def test_a_bill_group_that_would_pass_the_object_cap_is_dropped_whole():
    kept, tally = _capped([(2, "HB1"), (50, "HB2"), (1, "HB3")], max_bills=10, max_objects=10)
    assert [o.name for o in kept] == ["HB1-v0", "HB1-v1", "HB1"]
    assert tally["stopped_by"] == "object cap" and tally["bills"] == 1
    assert not any(o.name.startswith("HB2") for o in kept)  # no orphaned votes of a bill that is not there




def test_a_scraper_that_finishes_early_is_reported_as_finished():
    kept, tally = _capped([(1, "HB1"), (1, "HB2")], max_bills=20, max_objects=1000)
    assert len(kept) == 4 and tally["stopped_by"] == "scraper finished" and tally["bills"] == 2




class _FakeBillScraper:
    """Stands in for a bills scraper: writes what it is handed, the way do_scrape does."""

    output = []

    def __init__(self, juris, datadir, strict_validation=False):
        self.datadir = datadir
        self.scrape = lambda session=None: iter(_FakeBillScraper.output)

    def do_scrape(self, **kwargs):
        import json
        import os

        for i, obj in enumerate(self.scrape(**kwargs)):
            with open(os.path.join(self.datadir, f"{obj._type}_{i}.json"), "w") as f:
                json.dump({"name": obj.name}, f)
        return {}


def _gate_d(tmp_path, output, sample_bills, max_objects):
    _FakeBillScraper.output = output
    juris = type("J", (), {"scrapers": {"bills": _FakeBillScraper}})()
    return vj.run_gate_d(juris, "zz", "2026", sample_bills, str(tmp_path), max_objects=max_objects)


def test_gate_d_stops_after_the_bill_limit_and_reports_bills_and_votes(tmp_path):
    result, files, _report = _gate_d(tmp_path, list(_scrape_of(*[(3, f"HB{i}") for i in range(10)])), 4, 1000)
    assert result.status == "pass" and len(files) == 4
    assert "dry scrape OK: 4 bill(s)" in result.summary  # the headline counts bills, as the limit does
    sample_line = next(d for d in result.details if d.startswith("sample:"))
    assert "4 bill(s) and 12 vote event(s)" in sample_line and "stopped by: bill limit" in sample_line


def test_gate_d_stops_at_the_object_cap_and_says_so(tmp_path):
    result, files, _report = _gate_d(tmp_path, list(_scrape_of(*[(20, f"HB{i}") for i in range(10)])), 10, 50)
    assert len(files) == 2
    assert any("stopped by: object cap" in d for d in result.details)




def test_gate_i_hands_the_object_cap_to_each_session_it_samples(tmp_path):
    _probe_votes(tmp_path, [("k", "2025", "HB 1")])
    seen = []

    def fake(juris, st, session, sample, scraped_data_dir, datadir=None, max_objects=None):
        seen.append((session, sample, max_objects))
        return vj.GateResult("D", True, "pass", "x"), [], None

    with patch.object(vj, "run_gate_d", side_effect=fake):
        vj.run_gate_i(object(), "nc", "2025", ["2025", "2025E1"], 7, str(tmp_path), max_objects=123)
    assert seen == [("2025E1", 7, 123)]


def test_main_hands_the_sample_limits_to_gate_d_and_records_them(tmp_path, monkeypatch):
    import json

    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-probe-x")
    monkeypatch.setenv("RUN_ID", "run1")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    s3 = _FakeS3()
    seen = {}

    def fake_d(juris, st, session, sample, scraped_data_dir, datadir=None, max_objects=None):
        seen.update(sample=sample, max_objects=max_objects)
        return _passing("D"), [], None

    gate_a = vj.GateResult("A", True, "pass", "ok", details=["active: 2026A"])
    with patch("openstates.cli.update.get_jurisdiction", return_value=(type("J", (), {"name": "X"})(), None)), \
            patch.object(vj, "run_gate_a", return_value=gate_a), patch.object(vj, "run_gate_b", return_value=_passing("B")), \
            patch.object(vj, "run_gate_d", side_effect=fake_d), patch.object(vj, "run_gate_i", return_value=_passing("I")), \
            patch.object(vj, "_s3_client", return_value=s3):
        assert vj.main(["co", "--fargate", "--sample-bills", "7", "--max-objects", "150"]) == 0
    assert seen == {"sample": 7, "max_objects": 150}
    result = json.loads(s3.objects[("bucket", "dev-probe-x/probe/co/run1/result.json")])
    assert result["sample_bills"] == 7 and result["max_objects"] == 150


class _Pulled:
    """An iterator that counts how many objects were asked of it: the cap must bound this, not only the output."""

    def __init__(self, objects):
        self._it = iter(objects)
        self.pulled = 0

    def __iter__(self):
        return self

    def __next__(self):
        self.pulled += 1
        return next(self._it)


def _endless_votes():
    i = 0
    while True:
        yield _Obj("vote_event", f"v{i}")
        i += 1


def test_a_stream_of_votes_with_no_bill_stops_at_the_cap_instead_of_running_on():
    source, tally = _Pulled(_endless_votes()), {}
    assert list(vj.cap_scrape_output(source, 5, 50, tally)) == []
    assert source.pulled <= 51 and tally["stopped_by"] == "object cap"


def test_a_bill_whose_votes_alone_pass_the_cap_is_not_pulled_in_full():
    source, tally = _Pulled(_scrape_of((500, "HB1"))), {}
    assert list(vj.cap_scrape_output(source, 5, 20, tally)) == []
    assert source.pulled <= 21 and tally["bills"] == 0


def test_a_later_group_over_the_cap_is_cut_off_after_the_cap_and_earlier_bills_are_kept():
    source, tally = _Pulled(_scrape_of((2, "HB1"), (500, "HB2"))), {}
    kept = list(vj.cap_scrape_output(source, 5, 10, tally))
    assert [o.name for o in kept] == ["HB1-v0", "HB1-v1", "HB1"]
    assert source.pulled <= 11 and tally["stopped_by"] == "object cap"


def test_gate_d_warns_plainly_when_the_cap_is_reached_before_the_first_bill(tmp_path):
    result, files, _report = _gate_d(tmp_path, list(_scrape_of((100, "HB1"))), 5, 10)
    assert files == [] and result.status == "warn"
    assert "raise --max-objects" in result.summary and "before the first bill" in result.summary
    assert vj.classify_probe([result]) == "yellow"  # inconclusive, not the red of a state that cannot be scraped


def test_every_repo_module_the_probe_imports_is_copied_into_the_image():
    # The probe runs on Fargate from the Dockerfile's COPY line; a module it imports that is not copied
    # there makes the next image's probe fail to start (OPEN-445's qa_primitives.py nearly did).
    import ast
    import re
    with open(os.path.join(_HERE, "verify-jurisdiction")) as f:
        tree = ast.parse(f.read())
    imported = {n.split(".")[0] for node in ast.walk(tree)
                for n in ([a.name for a in node.names] if isinstance(node, ast.Import)
                          else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])}
    local = {m for m in imported if os.path.exists(os.path.join(_HERE, m + ".py"))}
    with open(os.path.join(_HERE, "Dockerfile")) as f:
        copy_lines = [l for l in f.read().splitlines() if l.startswith("COPY ") and "verify-jurisdiction" in l.split()]
    assert len(copy_lines) == 1
    copied = set(copy_lines[0].split()[1:-1])
    assert {m + ".py" for m in local} <= copied, sorted({m + ".py" for m in local} - copied)


# ── a crashing gate still gives a report (OPEN-470) ───────────────────────────


class _GeneratorSessions:
    """Vermont's scraper returns its session list as a generator (OPEN-470)."""

    def __init__(self, sessions):
        self._sessions = sessions

    def get_session_list(self):
        return (s for s in self._sessions)


def test_gate_a_counts_a_generator_session_list_instead_of_crashing():
    with patch("openstates.cli.update.check_session_list", return_value=["2026"]):
        result = vj.run_gate_a(_GeneratorSessions(["2025", "2026"]), "vt")
    assert result.status == "pass"
    assert result.summary == "2 scraped session(s), 1 active"


def test_gate_a_fails_on_an_empty_generator_session_list():
    # A generator is always truthy, so before list() an empty one skipped the "no sessions" failure.
    result = vj.run_gate_a(_GeneratorSessions([]), "vt")
    assert result.status == "fail"
    assert "no sessions" in result.summary


def test_guarded_turns_a_raising_gate_into_a_failed_gate_that_names_the_error():
    def boom():
        raise ModuleNotFoundError("No module named 'MySQLdb'")

    result = vj.guarded("D", True, boom)
    assert (result.gate, result.blocking, result.status) == ("D", True, "fail")
    assert "gate D crashed" in result.summary and "MySQLdb" in result.summary
    assert vj.guarded("F", False, lambda: "fine") == "fine"


def test_main_still_writes_the_report_when_gate_d_crashes(tmp_path, monkeypatch):
    """California's scraper builds a MySQL connection when it is created: gate D raised out of
    main() and the Fargate task wrote no result.json at all."""
    import json

    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-probe-x")
    monkeypatch.setenv("RUN_ID", "run1")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    s3 = _FakeS3()
    gate_a = vj.GateResult("A", True, "pass", "ok", details=["active: 2026"])
    with patch("openstates.cli.update.get_jurisdiction", return_value=(type("J", (), {"name": "X"})(), None)), \
            patch.object(vj, "run_gate_a", return_value=gate_a), patch.object(vj, "run_gate_b", return_value=_passing("B")), \
            patch.object(vj, "run_gate_d", side_effect=ModuleNotFoundError("No module named 'MySQLdb'")), \
            patch.object(vj, "_s3_client", return_value=s3):
        code = vj.main(["ca", "--fargate"])
    assert code == 0  # a Fargate task exits 0 once its output is uploaded, whatever the colour
    result = json.loads(s3.objects[("bucket", "dev-probe-x/probe/ca/run1/result.json")])
    d = next(g for g in result["gates"] if g["gate"] == "D")
    assert d["status"] == "fail" and "MySQLdb" in d["summary"]
    assert ("bucket", "dev-probe-x/probe/ca/run1/report.md") in s3.objects  # the readable report is uploaded too
