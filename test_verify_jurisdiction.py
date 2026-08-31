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
