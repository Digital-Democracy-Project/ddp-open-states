"""
Tests for new-jurisdiction (OPEN-461): turning an onboarding probe's result.json into
jurisdictions.yaml's Stage 0 `status: probing` entry. No scraper, no database, no network --
pure text/schema tests against temporary manifest copies, never the checked-in jurisdictions.yaml.
"""

import copy
import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys

import pytest
import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOADER = importlib.machinery.SourceFileLoader("new_jurisdiction", os.path.join(_HERE, "new-jurisdiction"))
_SPEC = importlib.util.spec_from_loader("new_jurisdiction", _LOADER)
nj = importlib.util.module_from_spec(_SPEC)
sys.modules["new_jurisdiction"] = nj
_LOADER.exec_module(nj)

from validate_jurisdictions import validate as vj_validate

# The real Colorado onboarding probe result (notes/probe-co-20261030/result.json on this repo's
# notes/ops-handoff branch, fetched 2026-10-30 -- OPEN-461's named acceptance fixture). Trimmed of
# "sample_files" only (a hash manifest of the bounded sample, never read by new-jurisdiction).
CO_RESULT = {
    "state": "co",
    "name": "Colorado",
    "run_id": "probe-co-20261030",
    "run_at": "2026-10-30T19:05:16.448029+00:00",
    "classification": "yellow",
    "session": "2026A",
    "active_sessions": ["2026A"],
    "sample_bills": 20,
    "gates": [
        {"gate": "A", "blocking": True, "status": "pass", "summary": "16 scraped session(s), 1 active",
         "details": ["active: 2026A"], "block_signature": False},
        {"gate": "B", "blocking": True, "status": "pass", "summary": "module shape recorded",
         "details": [
             "votes scraper registered: False",
             "bills scraper accepts start=: False",
             "WAF resilience profile: none",
             "no module-level RPM override found (CO_SCRAPELIB_RPM not set) -- platform default applies",
             "no credential env-var references found in scraper source",
         ], "block_signature": False},
        {"gate": "C", "blocking": True, "status": "fail",
         "summary": "1 media_type(s) with no CONVERSION_FUNCTIONS['co'] entry: text/html",
         "details": [], "block_signature": False},
        {"gate": "D", "blocking": True, "status": "pass", "summary": "dry scrape OK: 1 object(s) in 42.1s",
         "details": ["wall clock: 42.1s", "objects written: 1", "avg per-bill latency: 42.12s"],
         "block_signature": False},
        {"gate": "E", "blocking": False, "status": "warn",
         "summary": "no motion_classification.yaml block for 'co' yet", "details": [], "block_signature": False},
        {"gate": "F", "blocking": False, "status": "skip",
         "summary": "walk direction (informational only, NOT written to the manifest per OPEN-34's "
                     "2026-08-07 correction): unknown (1 classifiable multi-version bill(s) in this "
                     "dry scrape's sample)", "details": [], "block_signature": False},
        {"gate": "G", "blocking": False, "status": "skip",
         "summary": "not run on Fargate: it needs the people checkout and the dev database",
         "details": [], "block_signature": False},
        {"gate": "H", "blocking": True, "status": "skip",
         "summary": "no database on Fargate -- finish with --from-dir on the Mac",
         "details": [], "block_signature": False},
        {"gate": "I", "blocking": True, "status": "pass",
         "summary": "only one active session, so there is no other session to collide with",
         "details": ["probed session 2026A: 19 vote event file(s)"], "block_signature": False},
    ],
}


def _result_with_gate_b_details(details, base=None):
    data = copy.deepcopy(base if base is not None else CO_RESULT)
    for gate in data["gates"]:
        if gate["gate"] == "B":
            gate["details"] = details
    return data


def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)
    return str(path)


@pytest.fixture
def real_manifest_copy(tmp_path):
    """A temporary copy of the actual checked-in jurisdictions.yaml -- never the live file itself."""
    dest = tmp_path / "jurisdictions.yaml"
    shutil.copy(os.path.join(_HERE, "jurisdictions.yaml"), dest)
    return dest


def _run(manifest_path, state, probe_path, extra_args=()):
    return nj.main([state, "--from-probe", str(probe_path), "--manifest", str(manifest_path), *extra_args])


# ── creation + field-derivation rules ───────────────────────────────────────


def test_real_colorado_probe_produces_a_valid_probing_entry(tmp_path, real_manifest_copy, capsys):
    probe_path = _write_json(tmp_path / "result.json", CO_RESULT)
    rc = _run(real_manifest_copy, "co", probe_path)
    assert rc == 0
    data = yaml.safe_load(real_manifest_copy.read_text())
    assert "co" in data
    errors = vj_validate(data)
    assert errors == []
    assert data["co"]["status"] == "probing"


@pytest.mark.parametrize("classification", ["red", "yellow", "green"])
def test_status_is_always_probing_regardless_of_classification(classification):
    data = copy.deepcopy(CO_RESULT)
    data["classification"] = classification
    facts = nj.extract_gate_b_facts(data)
    entry, _ = nj.compose_entry(data, facts)
    assert entry["status"] == "probing"


def test_every_enrollment_field_is_false():
    facts = nj.extract_gate_b_facts(CO_RESULT)
    entry, _ = nj.compose_entry(CO_RESULT, facts)
    assert entry["enrollment"] == {f: False for f in nj.ENROLLMENT_FIELD_ORDER}


@pytest.mark.parametrize("votes,start", [(True, True), (True, False), (False, True), (False, False)])
def test_votes_scraper_and_start_filter_parsed_from_gate_b(votes, start):
    details = [
        f"votes scraper registered: {votes}",
        f"bills scraper accepts start=: {start}",
        "no credential env-var references found in scraper source",
    ]
    data = _result_with_gate_b_details(details)
    facts = nj.extract_gate_b_facts(data)
    assert facts["votes_scraper"] is votes
    assert facts["start_filter"] is start


def test_api_keys_parsed_from_credential_reference_line():
    details = [
        "votes scraper registered: False",
        "bills scraper accepts start=: False",
        "credential env-var references found in source: VA_API_KEY (present: none; absent: VA_API_KEY)",
    ]
    data = _result_with_gate_b_details(details)
    facts = nj.extract_gate_b_facts(data)
    assert facts["api_keys"] == ["VA_API_KEY"]


def test_api_keys_empty_when_gate_b_finds_no_credential_references():
    facts = nj.extract_gate_b_facts(CO_RESULT)  # the real CO fixture has the "no credential..." line
    assert facts["api_keys"] == []


def test_scrape_and_archive_timeouts_use_platform_defaults_not_measured_latency():
    facts = nj.extract_gate_b_facts(CO_RESULT)
    entry, _ = nj.compose_entry(CO_RESULT, facts)
    # The real CO probe's gate D measured "42.1s" wall clock / "42.12s" per-bill latency --
    # neither value may leak into either timeout field.
    assert entry["scrape"]["timeout_s"] == nj.DEFAULT_SCRAPE_TIMEOUT_S == 21600
    assert entry["archive"]["timeout_s"] == nj.DEFAULT_ARCHIVE_TIMEOUT_S == 14400


def test_tier_waf_profile_and_diff_cleaner_are_placeholders_flagged_needs_human():
    facts = nj.extract_gate_b_facts(CO_RESULT)
    entry, needs_human = nj.compose_entry(CO_RESULT, facts)
    assert entry["tier"] == "secondary"
    assert entry["waf"]["profile"] == "none"
    assert entry["quality"]["diff_cleaner"] == "none"
    flagged = {path for path, _reason in needs_human}
    assert {"tier", "waf.profile", "quality.diff_cleaner"} <= flagged


def test_onboarding_epic_always_null_and_evidence_derived_from_run_id():
    facts = nj.extract_gate_b_facts(CO_RESULT)
    entry, needs_human = nj.compose_entry(CO_RESULT, facts)
    assert entry["onboarding"]["epic"] is None
    assert entry["onboarding"]["evidence"] == "notes/probe-co-20261030/report.md"
    assert "onboarding.evidence" not in {path for path, _ in needs_human}


def test_onboarding_evidence_null_and_flagged_when_run_id_absent():
    data = copy.deepcopy(CO_RESULT)
    del data["run_id"]
    facts = nj.extract_gate_b_facts(data)
    entry, needs_human = nj.compose_entry(data, facts)
    assert entry["onboarding"]["evidence"] is None
    assert "onboarding.evidence" in {path for path, _ in needs_human}


def test_from_probe_accepts_both_a_direct_file_and_its_containing_folder(tmp_path, real_manifest_copy):
    folder = tmp_path / "probe-co-folder"
    folder.mkdir()
    _write_json(folder / "result.json", CO_RESULT)

    rc = _run(real_manifest_copy, "co", folder, extra_args=("--dry-run",))
    assert rc == 0
    folder_output = real_manifest_copy.read_text()

    manifest2 = tmp_path / "jurisdictions2.yaml"
    shutil.copy(os.path.join(_HERE, "jurisdictions.yaml"), manifest2)
    file_path = tmp_path / "result-standalone.json"
    _write_json(file_path, CO_RESULT)
    rc2 = _run(manifest2, "co", file_path, extra_args=("--dry-run",))
    assert rc2 == 0
    # dry-run never writes, so both manifests must still be byte-identical to the original
    assert folder_output == manifest2.read_text()


# ── mutation checks: refuses invalid input, never touches another state ────


def test_refuses_when_probe_state_does_not_match_cli_argument(tmp_path, real_manifest_copy):
    before = real_manifest_copy.read_text()
    probe_path = _write_json(tmp_path / "result.json", CO_RESULT)  # probe says "co"
    rc = _run(real_manifest_copy, "ga", probe_path)  # asked for "ga"
    assert rc != 0
    assert real_manifest_copy.read_text() == before


def test_refuses_missing_gate_b(tmp_path, real_manifest_copy):
    before = real_manifest_copy.read_text()
    data = copy.deepcopy(CO_RESULT)
    data["gates"] = [g for g in data["gates"] if g["gate"] != "B"]
    probe_path = _write_json(tmp_path / "result.json", data)
    rc = _run(real_manifest_copy, "co", probe_path)
    assert rc != 0
    assert real_manifest_copy.read_text() == before


@pytest.mark.parametrize("details", [
    [],  # no lines at all
    ["votes scraper registered: maybe"],  # unrecognized wording -- must not be guessed as False
    ["bills scraper accepts start=: False"],  # votes line entirely absent
    ["votes scraper registered: True", "bills scraper accepts start=: True"],  # credential line absent
])
def test_refuses_contradictory_or_unrecognized_gate_b_wording(tmp_path, real_manifest_copy, details):
    before = real_manifest_copy.read_text()
    data = _result_with_gate_b_details(details)
    probe_path = _write_json(tmp_path / "result.json", data)
    rc = _run(real_manifest_copy, "co", probe_path)
    assert rc != 0
    assert real_manifest_copy.read_text() == before


def test_refuses_malformed_json(tmp_path, real_manifest_copy):
    before = real_manifest_copy.read_text()
    bad = tmp_path / "result.json"
    bad.write_text("{not valid json")
    rc = _run(real_manifest_copy, "co", bad)
    assert rc != 0
    assert real_manifest_copy.read_text() == before


@pytest.mark.parametrize("missing_key", ["state", "gates"])
def test_refuses_probe_result_missing_a_required_field(tmp_path, real_manifest_copy, missing_key):
    before = real_manifest_copy.read_text()
    data = copy.deepcopy(CO_RESULT)
    del data[missing_key]
    probe_path = _write_json(tmp_path / "result.json", data)
    rc = _run(real_manifest_copy, "co", probe_path)
    assert rc != 0
    assert real_manifest_copy.read_text() == before


def test_refuses_candidate_that_the_validator_rejects(tmp_path, real_manifest_copy, monkeypatch):
    """compose_entry() is schema-correct by construction -- to prove the validator gate actually
    runs (not just that compose_entry happens to be right), force an invalid composed entry and
    confirm the write is refused and the file is untouched."""
    before = real_manifest_copy.read_text()
    real_compose_entry = nj.compose_entry

    def bad_compose_entry(data, gate_b_facts):
        entry, needs_human = real_compose_entry(data, gate_b_facts)
        entry["tier"] = "not-a-real-tier"  # violates validate_jurisdictions.py's TIER_VALUES enum
        return entry, needs_human

    monkeypatch.setattr(nj, "compose_entry", bad_compose_entry)
    probe_path = _write_json(tmp_path / "result.json", CO_RESULT)
    rc = _run(real_manifest_copy, "co", probe_path)
    assert rc != 0
    assert real_manifest_copy.read_text() == before


def test_never_touches_another_states_block(tmp_path, real_manifest_copy):
    before = real_manifest_copy.read_text()
    probe_path = _write_json(tmp_path / "result.json", CO_RESULT)
    rc = _run(real_manifest_copy, "co", probe_path)
    assert rc == 0
    after = real_manifest_copy.read_text()
    # the entire original file must survive, byte-for-byte, as a prefix of the new one -- only
    # bytes were ever appended, nothing upstream of them was rewritten.
    assert after.startswith(before.rstrip("\n"))
    # and every other state's parsed entry is unchanged too (belt and suspenders on the above)
    before_data = yaml.safe_load(before)
    after_data = yaml.safe_load(after)
    for code, entry in before_data.items():
        assert after_data[code] == entry


@pytest.mark.parametrize("state_arg", ["ga", None])  # None == gate-B-missing refusal path
def test_dry_run_never_writes_on_any_refusal_or_conflict_path(tmp_path, real_manifest_copy, state_arg):
    before = real_manifest_copy.read_text()
    if state_arg is None:
        data = copy.deepcopy(CO_RESULT)
        data["gates"] = [g for g in data["gates"] if g["gate"] != "B"]
        probe_path = _write_json(tmp_path / "result.json", data)
        state = "co"
    else:
        probe_path = _write_json(tmp_path / "result.json", CO_RESULT)
        state = state_arg
    _run(real_manifest_copy, state, probe_path, extra_args=("--dry-run",))
    assert real_manifest_copy.read_text() == before


def test_dry_run_never_writes_for_a_valid_new_entry(tmp_path, real_manifest_copy):
    before = real_manifest_copy.read_text()
    probe_path = _write_json(tmp_path / "result.json", CO_RESULT)
    rc = _run(real_manifest_copy, "co", probe_path, extra_args=("--dry-run",))
    assert rc == 0
    assert real_manifest_copy.read_text() == before


def test_a_valid_new_state_appends_exactly_one_block(tmp_path, real_manifest_copy):
    before_data = yaml.safe_load(real_manifest_copy.read_text())
    probe_path = _write_json(tmp_path / "result.json", CO_RESULT)
    rc = _run(real_manifest_copy, "co", probe_path)
    assert rc == 0
    after_data = yaml.safe_load(real_manifest_copy.read_text())
    assert set(after_data) - set(before_data) == {"co"}


# ── idempotency: no-op or a reported conflict, never a silent overwrite ────


def test_second_identical_run_is_a_noop(tmp_path, real_manifest_copy):
    probe_path = _write_json(tmp_path / "result.json", CO_RESULT)
    assert _run(real_manifest_copy, "co", probe_path) == 0
    after_first = real_manifest_copy.read_text()
    rc = _run(real_manifest_copy, "co", probe_path)
    assert rc == 0
    assert real_manifest_copy.read_text() == after_first


def test_existing_differing_entry_reports_conflict_and_is_not_overwritten(tmp_path, real_manifest_copy, capsys):
    probe_path = _write_json(tmp_path / "result.json", CO_RESULT)
    assert _run(real_manifest_copy, "co", probe_path) == 0
    capsys.readouterr()

    # simulate a human hand-editing the field this script deliberately never guesses
    text = real_manifest_copy.read_text()
    text = text.replace("diff_cleaner: none  # NEEDS HUMAN REVIEW", "diff_cleaner: clean_co_text")
    real_manifest_copy.write_text(text)
    before_conflict = real_manifest_copy.read_text()

    rc = _run(real_manifest_copy, "co", probe_path)
    out = capsys.readouterr().out
    assert rc == 0
    assert "quality.diff_cleaner" in out
    assert "clean_co_text" in out
    # the human's edit must survive untouched
    assert real_manifest_copy.read_text() == before_conflict
