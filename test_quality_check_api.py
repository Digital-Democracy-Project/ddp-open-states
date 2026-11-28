"""
Tests for quality_check.py's --api-url mode (OPEN-958): the Stage 3 structural gates and the govbot
coverage check read through api-v3 (HTTP GETs), with no database.

A fake api-v3 stands in for the HTTP layer (quality_check._get_with_retry); psycopg2.connect is made
to explode wherever a test claims "no database". Each rule has a test that a wrong implementation
fails: an unresolved voter or sponsor, a version with no stage (classified by the INJECTED rules,
not whichever core is installed), a missing/extra identifier, a repeated vote key, a missing
dedupe_key field (never a silent pass), paging past page 1, and the core guard.
"""

import os
import subprocess
import sys

import pytest

import quality_check as qc
from quality_check import (
    ApiBills, ApiError, CoreMismatch, Report, PASS, WARN, FAIL, SKIP,
    api_attribution_rates, api_vote_key_collisions, compare_bills,
    load_stage_rules, run_coverage_check_api, run_govbot_coverage_check,
    run_structural_gates_api,
)

JID = qc._ocd_id("ky")


# ── A fake api-v3 ───────────────────────────────────────────────────────────────

def _vote(voter, name="A", option="yes", dedupe_key=None, date="2026-02-01", present_key=True):
    ve = {"identifier": "V", "start_date": date, "organization": {"classification": "lower"},
          "counts": [{"option": option, "value": 1}],
          "votes": [{"voter_name": name, "option": option, "voter": voter}]}
    if present_key:
        ve["dedupe_key"] = dedupe_key
    return ve


def _bill(identifier, session="2026RS", versions=("Introduced",), votes=(), sponsors=()):
    return {"identifier": identifier, "session": session, "title": identifier,
            "versions": [{"note": n} for n in versions], "votes": list(votes),
            "sponsorships": list(sponsors), "actions": []}


def _sponsor(person, entity_type="person"):
    return {"entity_type": entity_type, "person": person, "name": "S"}


class FakeApi:
    """Serves /people and /bills pages like api-v3: `per_page` bills a page, `pagination.max_page`."""

    def __init__(self, bills, people=141, fail=None):
        self.bills, self.people, self.fail = bills, people, fail
        self.calls = []

    def __call__(self, url, params, timeout=15, attempts=4):
        self.calls.append((url, dict(params)))
        if self.fail:
            raise self.fail
        path = url.split("localhost:8002", 1)[1]
        if path == "/people":
            return _Resp({"results": [], "pagination": {"total_items": self.people, "max_page": 1}})
        assert path == "/bills"
        assert params["per_page"] <= 20, "api-v3 caps a page with includes at 20 bills"
        assert set(params["include"]) >= {"versions", "votes", "sponsorships", "actions"}
        size, page = params["per_page"], params["page"]
        pages = max(1, -(-len(self.bills) // size))
        return _Resp({"results": self.bills[(page - 1) * size: page * size],
                      "pagination": {"page": page, "max_page": pages, "total_items": len(self.bills)}})


class _Resp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def _no_database(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("the api-v3 mode must not open a database connection")
    monkeypatch.setattr(qc.psycopg2, "connect", boom)


def _api(monkeypatch, bills, **kw):
    fake = FakeApi(bills, **kw)
    monkeypatch.setattr(qc, "_get_with_retry", fake)
    _no_database(monkeypatch)
    return ApiBills("http://localhost:8002", "KEY", "ky"), fake


def _rules(unknown_notes=("???",)):
    """Stand-in classifier: only the notes named here have no stage."""
    return (lambda note: (-1 if note in unknown_notes else 1, 0)), -1


def _by_label(report):
    return {label: (sym, detail) for sym, label, detail in report.checks}


# ── Crawl ───────────────────────────────────────────────────────────────────────

def test_crawl_reads_every_page_and_sends_the_documented_params(monkeypatch):
    api, fake = _api(monkeypatch, [_bill(f"HB{i}") for i in range(45)])
    assert len(api.bills()) == 45           # a page-1-only crawl would stop at 20
    api.bills()
    bill_calls = [c for c in fake.calls if c[0].endswith("/bills")]
    assert len(bill_calls) == 3             # one crawl, shared: not one per gate
    assert bill_calls[0][1]["jurisdiction"] == JID
    assert bill_calls[0][1]["apikey"] == "KEY"


def test_a_response_without_the_expected_shape_is_an_api_error_not_a_traceback(monkeypatch):
    api, fake = _api(monkeypatch, [])
    monkeypatch.setattr(qc, "_get_with_retry", lambda url, params, timeout=15, attempts=4: _Resp({"oops": 1}))
    with pytest.raises(ApiError):
        api.bills()
    with pytest.raises(ApiError):
        api.people_count()


def test_an_api_failure_is_an_error_with_the_key_redacted_never_a_pass(monkeypatch):
    api, _ = _api(monkeypatch, [], fail=RuntimeError("boom https://x/bills?apikey=SECRET123&a=1"))
    with pytest.raises(ApiError) as e:
        api.bills()
    assert "SECRET123" not in str(e.value)


# ── Gates ───────────────────────────────────────────────────────────────────────

def test_unresolved_voters_fail_and_resolved_pass(monkeypatch):
    bad = [_bill("HB1", votes=[_vote(voter=None)] * 10)]
    api, _ = _api(monkeypatch, bad)
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules())
    sym, detail = _by_label(report)["KY: attribution resolution (votes)"]
    assert sym == FAIL and "10/10 unresolved" in detail

    good = [_bill("HB1", votes=[_vote(voter={"id": "p"})] * 10)]
    api, _ = _api(monkeypatch, good)
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules())
    assert _by_label(report)["KY: attribution resolution (votes)"][0] == PASS


def test_unresolved_sponsors_fail_but_organization_sponsors_are_not_counted():
    rates = api_attribution_rates([_bill("HB1", sponsors=[
        _sponsor(None), _sponsor({"id": "p"}), _sponsor(None, entity_type="organization")])])
    assert rates["sponsorships"] == {"total": 2, "unresolved": 1}


def test_version_with_no_stage_is_judged_by_the_injected_rules_and_the_ceiling(monkeypatch):
    bills = [_bill("HB1", versions=["???", "Introduced", "Enrolled", "Enrolled"] * 5)]  # 5/20 = 25%
    api, _ = _api(monkeypatch, bills)
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules(("???",)))
    sym, detail = _by_label(report)["KY: version stage coverage"]
    assert sym == FAIL and "5/20" in detail and "5.5%" in detail
    # the same crawl with a classifier that knows every note passes: the verdict follows the rules
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules(()))
    assert _by_label(report)["KY: version stage coverage"][0] == PASS


def test_people_loaded_reads_api_people(monkeypatch):
    api, _ = _api(monkeypatch, [], people=0)
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules())
    assert _by_label(report)["KY: people loaded"][0] == FAIL
    api, _ = _api(monkeypatch, [], people=141)
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules())
    assert _by_label(report)["KY: people loaded"] == (PASS, "141 people loaded")


def test_no_versions_votes_or_sponsors_is_not_applicable_never_a_division_error(monkeypatch):
    api, _ = _api(monkeypatch, [_bill("HB1", versions=())])
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules())
    labels = _by_label(report)
    assert labels["KY: version stage coverage"][0] == SKIP
    assert labels["KY: attribution resolution (votes)"][0] == SKIP
    assert labels["KY: attribution resolution (sponsorships)"][0] == SKIP


# ── Vote-key gate: runs only when api-v3 returns the key ────────────────────────

def test_vote_key_gate_says_not_available_when_the_field_is_missing_never_passes(monkeypatch):
    api, _ = _api(monkeypatch, [_bill("HB1", votes=[_vote({"id": "p"}, present_key=False)])])
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules())
    sym, detail = _by_label(report)["KY: unique vote keys"]
    assert sym == SKIP and "not available through api-v3" in detail
    assert api_vote_key_collisions(api.bills()) is None


def test_vote_key_gate_fails_on_a_key_repeated_across_sessions(monkeypatch):
    bills = [_bill("HB1", "2025RS", votes=[_vote({"id": "p"}, dedupe_key="K")]),
             _bill("HB2", "2026RS", votes=[_vote({"id": "p"}, dedupe_key="K")])]
    api, _ = _api(monkeypatch, bills)
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules())
    sym, detail = _by_label(report)["KY: unique vote keys"]
    assert sym == FAIL and "'K'" in detail and "2 sessions" in detail


def test_vote_key_gate_passes_unique_keys_and_skips_a_single_session(monkeypatch):
    two = [_bill("HB1", "2025RS", votes=[_vote({"id": "p"}, dedupe_key="A")]),
           _bill("HB2", "2026RS", votes=[_vote({"id": "p"}, dedupe_key="B")])]
    api, _ = _api(monkeypatch, two)
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules())
    assert _by_label(report)["KY: unique vote keys"][0] == PASS
    api, _ = _api(monkeypatch, two[:1])
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules())
    assert _by_label(report)["KY: unique vote keys"][0] == SKIP


def test_a_key_on_some_vote_events_but_not_all_is_not_available_not_a_pass(monkeypatch):
    bills = [_bill("HB1", "2025RS", votes=[_vote({"id": "p"}, dedupe_key="A")]),
             _bill("HB2", "2026RS", votes=[_vote({"id": "p"}, present_key=False)])]
    assert api_vote_key_collisions(bills) is None
    api, _ = _api(monkeypatch, bills)
    report = Report()
    run_structural_gates_api(report, api, "ky", _rules())
    assert _by_label(report)["KY: unique vote keys"][0] == SKIP


def test_a_present_but_null_key_is_not_a_collision():
    bills = [_bill("HB1", "2025RS", votes=[_vote({"id": "p"}, dedupe_key=None)]),
             _bill("HB2", "2026RS", votes=[_vote({"id": "p"}, dedupe_key=None)])]
    assert api_vote_key_collisions(bills) == ({}, 0)


# ── Coverage: Tier 1 identifiers and Tier 2 over the crawl ──────────────────────

def _govbot(*identifiers):
    return {i: {"identifier": i, "title": i, "actions": [], "sponsorships": [], "votes": []}
            for i in identifiers}


def test_tier1_flags_a_missing_and_an_extra_identifier_from_the_crawl(monkeypatch):
    api, _ = _api(monkeypatch, [_bill("HB 1"), _bill("HB 3")])
    report = Report()
    result = run_govbot_coverage_check(report, None, "ky", "2026RS", _govbot("HB 1", "HB 2"),
                                       tier2_limit=0, api_bills=api)
    assert result["missing"] == ["HB 2"] and result["extra"] == ["HB 3"]
    assert any(s == FAIL and "Tier 1" in l for s, l, _ in report.checks)
    assert any(s == WARN and "local-only" in l for s, l, _ in report.checks)


def test_tier1_passes_when_the_sets_match_and_tier2_reads_the_crawled_bill(monkeypatch):
    api, fake = _api(monkeypatch, [_bill("HB 1")])
    report = Report()
    result = run_govbot_coverage_check(report, None, "ky", "2026RS", _govbot("HB 1"), api_bills=api)
    assert result["missing"] == [] and result["tier2_checked"] == 1
    assert not any(s == FAIL for s, _, _ in report.checks)
    assert len([c for c in fake.calls if c[0].endswith("/bills")]) == 1   # no per-bill GET


def test_tier1_uses_only_the_named_sessions_identifiers(monkeypatch):
    api, _ = _api(monkeypatch, [_bill("HB 1", "2025RS"), _bill("HB 2", "2026RS")])
    assert api.identifiers("2026RS") == {"HB 2"}


def test_coverage_without_a_govbot_copy_skips_loudly_instead_of_falling_back_to_the_database(monkeypatch):
    api, _ = _api(monkeypatch, [_bill("HB 1")])
    monkeypatch.setattr(qc, "_ensure_govbot_repo", lambda code: (False, None, "clone failed"))
    report = Report()
    result = run_coverage_check_api(report, api, "ky", "2026RS")
    assert result["source"] == "none"
    sym, label, detail = report.checks[0]
    assert sym == SKIP and "needs" in detail and "database" in detail


def test_blast_radius_counts_other_bills_sharing_a_voter_signature_on_the_date(monkeypatch):
    shared = _vote(None, name="Smith", option="no", date="2026-03-01")
    bills = [_bill("HB 1", votes=[shared]), _bill("HB 2", votes=[shared]), _bill("HB 3", votes=[shared]),
             _bill("HB 4", votes=[_vote(None, name="Smith", option="no", date="2026-03-02")]),
             _bill("HB 5", votes=[_vote(None, name="Jones", option="no", date="2026-03-01")]),
             _bill("HB 6", "2025RS", votes=[shared])]
    api, _ = _api(monkeypatch, bills)
    count = api.shared_date_count("2026RS")
    # HB 2 and HB 3 share it; not HB 1 (excluded), HB 4 (other date), HB 5 (other voter), HB 6 (other session)
    assert count("2026-03-01", {("Smith", "no")}, "HB 1") == 2


def test_compare_bills_folds_the_api_blast_radius_into_the_tally_warning(monkeypatch):
    shared = _vote(None, name="Smith", option="yes", date="2026-03-01")
    api, _ = _api(monkeypatch, [_bill("HB 1", votes=[shared]), _bill("HB 2", votes=[shared])])
    live = _bill("HB 1")
    live["votes"] = [dict(shared, votes=[], counts=[{"option": "yes", "value": 2}])]
    local = api.bill("2026RS", "HB 1")
    report = Report()
    compare_bills(report, local, live, "KY HB 1", session="2026RS",
                  shared_count_fn=api.shared_date_count("2026RS"))
    warn = [d for s, l, d in report.checks if s == WARN and "tally differs" in l]
    assert warn and "1 other local bill(s) share this signature" in warn[0]


# ── The core guard (OPEN-579) ───────────────────────────────────────────────────

def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}).stdout.strip()


def _fake_core(root, marker):
    pkg = root / "openstates" / "utils"
    pkg.mkdir(parents=True)
    (root / "openstates" / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / "version_ordering.py").write_text(
        f"STAGE_UNKNOWN = -1\nMARK = {marker!r}\ndef note_stage(note):\n    return (STAGE_UNKNOWN, 0)\n")


@pytest.fixture
def clean_imports(monkeypatch):
    saved = {k: v for k, v in sys.modules.items() if k == "openstates" or k.startswith("openstates.")}
    for k in saved:
        monkeypatch.delitem(sys.modules, k)
    monkeypatch.setattr(sys, "path", list(sys.path))
    yield
    for k in [k for k in sys.modules if k == "openstates" or k.startswith("openstates.")]:
        del sys.modules[k]
    sys.modules.update(saved)


def test_guard_refuses_without_the_core_root_or_the_commit():
    with pytest.raises(CoreMismatch, match="--openstates-core-root"):
        load_stage_rules(None, None)
    with pytest.raises(CoreMismatch, match="--openstates-core-root"):
        load_stage_rules("/x", None)


def test_guard_refuses_a_short_or_unreadable_commit(tmp_path, clean_imports):
    _fake_core(tmp_path, "x")
    with pytest.raises(CoreMismatch, match="40-character"):
        load_stage_rules(str(tmp_path), "abc123")
    with pytest.raises(CoreMismatch, match="cannot tell which commit"):
        load_stage_rules(str(tmp_path), "a" * 40)   # no record file, not a git checkout


def test_guard_accepts_the_same_commit_by_record_file_and_uses_that_core(tmp_path, clean_imports):
    _fake_core(tmp_path, "from-the-checked-core")
    (tmp_path / "DDP_CORE_COMMIT").write_text("b" * 40 + "\n")
    note_stage, unknown = load_stage_rules(str(tmp_path), "b" * 40)
    import openstates.utils.version_ordering as vo
    assert vo.MARK == "from-the-checked-core" and note_stage is vo.note_stage and unknown == -1


def test_guard_refuses_a_record_file_for_a_different_commit_it_cannot_compare(tmp_path, clean_imports):
    _fake_core(tmp_path, "x")
    (tmp_path / "DDP_CORE_COMMIT").write_text("b" * 40)
    with pytest.raises(CoreMismatch, match="not at or after"):
        load_stage_rules(str(tmp_path), "c" * 40)


def test_guard_with_git_history_accepts_newer_and_refuses_older(tmp_path, clean_imports):
    _fake_core(tmp_path, "x")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "old")
    old = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "later.txt").write_text("1")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "new")
    new = _git(tmp_path, "rev-parse", "HEAD")
    assert load_stage_rules(str(tmp_path), old)               # core is newer than api-v3's: fine
    _git(tmp_path, "checkout", "-q", old)                      # core is OLDER than api-v3's: refuse
    with pytest.raises(CoreMismatch, match="not at or after"):
        load_stage_rules(str(tmp_path), new)


def test_guard_refuses_a_git_checkout_with_uncommitted_changes_under_openstates(tmp_path, clean_imports):
    _fake_core(tmp_path, "x")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "c")
    head = _git(tmp_path, "rev-parse", "HEAD")
    assert load_stage_rules(str(tmp_path), head)               # clean: fine
    (tmp_path / "openstates" / "utils" / "version_ordering.py").write_text("STAGE_UNKNOWN = -1\n")
    with pytest.raises(CoreMismatch, match="uncommitted"):
        load_stage_rules(str(tmp_path), head)


def test_guard_refuses_when_git_status_of_the_checkout_cannot_be_read(tmp_path, clean_imports, monkeypatch):
    _fake_core(tmp_path, "x")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "c")
    head = _git(tmp_path, "rev-parse", "HEAD")
    real = qc._run_git
    monkeypatch.setattr(qc, "_run_git", lambda args, cwd=None, timeout=300:
                        (False, "TimeoutExpired") if args[0] == "status" else real(args, cwd, timeout))
    with pytest.raises(CoreMismatch, match="cannot tell whether"):
        load_stage_rules(str(tmp_path), head)


def test_guard_ignores_the_status_of_an_enclosing_repo_for_an_unpacked_export(tmp_path, clean_imports):
    _git(tmp_path, "init", "-q")                      # an enclosing repo that has not tracked the export
    export = tmp_path / "export"
    export.mkdir()
    _fake_core(export, "x")
    (export / "DDP_CORE_COMMIT").write_text("9" * 40)
    assert load_stage_rules(str(export), "9" * 40)


def test_guard_refuses_when_another_core_was_already_imported(tmp_path, clean_imports):
    other = tmp_path / "other"
    other.mkdir()
    _fake_core(other, "other")
    sys.path.insert(0, str(other))
    import openstates  # noqa: F401  (now loaded from `other`, ahead of any later sys.path insert)
    mine = tmp_path / "mine"
    mine.mkdir()
    _fake_core(mine, "mine")
    (mine / "DDP_CORE_COMMIT").write_text("d" * 40)
    with pytest.raises(CoreMismatch, match="already loaded"):
        load_stage_rules(str(mine), "d" * 40)


# ── The command line ────────────────────────────────────────────────────────────

def _run_main(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["quality_check.py"] + argv)
    with pytest.raises(SystemExit) as e:
        qc.main()
    return e.value.code


def test_cli_structural_via_api_runs_with_no_database_and_no_live_key(monkeypatch, tmp_path, clean_imports, capsys):
    _fake_core(tmp_path, "x")
    (tmp_path / "DDP_CORE_COMMIT").write_text("e" * 40)
    monkeypatch.setattr(qc, "LIVE_KEY", "")
    _api(monkeypatch, [_bill("HB1", versions=["a"])])
    code = _run_main(monkeypatch, ["--structural", "ky", "--api-url", "--openstates-core-root", str(tmp_path),
                                   "--core-commit", "e" * 40])
    out = capsys.readouterr().out
    # the fake core calls every note unstaged (1/1): the gate FAILs, so the run exits 1 -- proving the
    # verdict reaches the exit code, through the checked core
    assert code == 1 and "version stage coverage" in out and "via api-v3" in out


def test_cli_refuses_to_classify_without_a_checked_core(monkeypatch, capsys):
    _no_database(monkeypatch)
    assert _run_main(monkeypatch, ["--structural", "ky", "--api-url"]) == 2
    assert "--openstates-core-root" in capsys.readouterr().out


def test_cli_api_url_needs_structural_or_coverage(monkeypatch):
    assert _run_main(monkeypatch, ["--api-url", "--tier2", "ky", "2026RS"]) == 2
    assert _run_main(monkeypatch, ["--structural", "ky", "--core-commit", "a" * 40]) == 2


def test_cli_without_api_url_still_uses_the_database(monkeypatch):
    class Reached(Exception):
        pass

    def connect(url):
        raise Reached
    monkeypatch.setattr(qc.psycopg2, "connect", connect)
    monkeypatch.setattr(sys, "argv", ["quality_check.py", "--structural", "ky"])
    with pytest.raises(Reached):
        qc.main()


def test_cli_api_failure_exits_2_not_a_pass(monkeypatch, tmp_path, clean_imports, capsys):
    _fake_core(tmp_path, "x")
    (tmp_path / "DDP_CORE_COMMIT").write_text("f" * 40)
    _api(monkeypatch, [], fail=RuntimeError("connection refused"))
    code = _run_main(monkeypatch, ["--structural", "ky", "--api-url", "--openstates-core-root", str(tmp_path),
                                   "--core-commit", "f" * 40])
    assert code == 2 and "ERROR" in capsys.readouterr().out
