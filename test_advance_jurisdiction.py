"""
Tests for advance-jurisdiction: moving a state to `scraping` or `live` in jurisdictions.yaml and setting the
flags that status needs, plus the validator rules that make a forgotten flag impossible to merge
(pilot #2, 2026-11-03: the first scrapes loaded with 0 legislators because people_refresh was still false).
Pure text/schema tests against temporary manifest copies; never the checked-in jurisdictions.yaml.
"""

import copy
import importlib.machinery
import importlib.util
import os
import sys

import pytest
import yaml

from validate_jurisdictions import _DuplicateKeyCheckingLoader, validate

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOADER = importlib.machinery.SourceFileLoader("advance_jurisdiction", os.path.join(_HERE, "advance-jurisdiction"))
_SPEC = importlib.util.spec_from_loader("advance_jurisdiction", _LOADER)
aj = importlib.util.module_from_spec(_SPEC)
sys.modules["advance_jurisdiction"] = aj
_LOADER.exec_module(aj)

# A probing entry as new-jurisdiction writes it (every enrollment flag false, comments kept), then a
# neighbour that must never be touched.
MANIFEST = """# header comment
pa:
  name: Pennsylvania
  status: probing
  scrape:
    allow_duplicates: false
    timeout_s: 21600
    session_arg: null
    votes_scraper: false
    start_filter: false
    sweep_import: false
    full_walk: false
    retry: false
    cadence_escalation: true
    fargate_max_wait_s: null
  archive:
    enabled: false
    timeout_s: 14400               # ARCHIVE_TIMEOUT_S default
  enrollment:
    people_refresh: false
    search_refresh: false
    embedding: false
    cloud_path: false
    api_smoke_test: false
    qa_sweep: false
    replica_routing: false
    legbot_replica: false
    broker_bill_event_signal: false
  waf:
    profile: none
    fargate_safe: true
    scrapebot_fallback: false
  quality:
    diff_cleaner: none  # NEEDS HUMAN REVIEW
  actions:
    newest_first: false  # NEEDS HUMAN REVIEW
  voatz:
    creator_id: null
    test_precinct: null
  api_keys: []
  onboarding:
    epic: OPEN-478
    evidence: notes/probe-pa/report.md

# a neighbour
ne:
  name: Nebraska
  status: probing
  scrape:
    allow_duplicates: false
    timeout_s: 21600
    session_arg: null
    votes_scraper: false
    start_filter: false
    sweep_import: false
    full_walk: false
    retry: false
    cadence_escalation: true
    fargate_max_wait_s: null
  archive:
    enabled: false
    timeout_s: 14400
  enrollment:
    people_refresh: false
    search_refresh: false
    embedding: false
    cloud_path: false
    api_smoke_test: false
    qa_sweep: false
    replica_routing: false
    legbot_replica: false
    broker_bill_event_signal: false
  waf:
    profile: none
    fargate_safe: true
    scrapebot_fallback: false
  quality:
    diff_cleaner: none
  actions:
    newest_first: false
  voatz:
    creator_id: null
    test_precinct: null
  api_keys: []
  onboarding:
    epic: null
    evidence: null
"""


def _load(text):
    return yaml.load(text, Loader=_DuplicateKeyCheckingLoader)


def test_scraping_sets_status_and_the_three_flags_and_nothing_else():
    new, changes, warnings, error = aj.advance(MANIFEST, "pa", "scraping")
    assert error is None and warnings == []
    before, after = _load(MANIFEST)["pa"], _load(new)["pa"]
    assert after["status"] == "scraping"
    assert after["enrollment"]["people_refresh"] is True
    assert after["archive"]["enabled"] is True
    assert after["enrollment"]["cloud_path"] is True
    # Everything else is exactly as it was: the decisions that stay human, and the neighbour.
    for human in ("legbot_replica", "embedding", "replica_routing", "search_refresh", "qa_sweep", "api_smoke_test"):
        assert after["enrollment"][human] is False
    assert after["quality"] == before["quality"] and after["waf"] == before["waf"]
    assert _load(new)["ne"] == _load(MANIFEST)["ne"]
    assert validate(_load(new)) == []


def test_comments_and_layout_survive():
    new, *_ = aj.advance(MANIFEST, "pa", "scraping")
    assert "diff_cleaner: none  # NEEDS HUMAN REVIEW" in new
    assert "timeout_s: 14400               # ARCHIVE_TIMEOUT_S default" in new
    assert new.startswith("# header comment\n") and "# a neighbour\nne:" in new
    assert len(new.split("\n")) == len(MANIFEST.split("\n"))  # line-for-line edits


def test_live_changes_only_the_status_and_adds_no_archive_field():
    """OPEN-521: the archive follows every scrape, so `live` records the human decision and sets nothing more."""
    scraping, *_ = aj.advance(MANIFEST, "pa", "scraping")
    live, changes, _, error = aj.advance(scraping, "pa", "live")
    assert error is None and changes == ["status: scraping -> live"]
    assert _load(live)["pa"] == dict(_load(scraping)["pa"], status="live")
    assert "scheduled" not in _load(live)["pa"]["archive"] and validate(_load(live)) == []


def test_rerun_changes_nothing():
    once, *_ = aj.advance(MANIFEST, "pa", "scraping")
    twice, changes, _, error = aj.advance(once, "pa", "scraping")
    assert error is None and changes == [] and twice == once


@pytest.mark.parametrize("target", ["live"])
def test_a_probing_state_cannot_skip_to_live(target):
    new, changes, _, error = aj.advance(MANIFEST, "pa", target)
    assert new == MANIFEST and changes == [] and "probing" in error


def test_unknown_state_and_bad_target_are_refused():
    assert "not in the manifest" in aj.advance(MANIFEST, "zz", "scraping")[3]
    assert "must be one of" in aj.advance(MANIFEST, "pa", "paused")[3]


def test_a_state_whose_site_needs_the_mac_keeps_cloud_path_and_warns():
    mac_only = MANIFEST.replace("fargate_safe: true", "fargate_safe: false", 1)
    new, changes, warnings, error = aj.advance(mac_only, "pa", "scraping")
    assert error is None and _load(new)["pa"]["enrollment"]["cloud_path"] is False
    assert warnings and "fargate_safe" in warnings[0]
    assert not any("cloud_path" in c for c in changes)


def test_a_missing_field_is_an_error_not_a_silent_skip():
    broken = MANIFEST.replace("    people_refresh: false\n", "", 1)
    with pytest.raises(KeyError):
        aj.advance(broken, "pa", "scraping")


def test_main_writes_validated_result_and_dry_run_writes_nothing(tmp_path):
    path = tmp_path / "jurisdictions.yaml"
    path.write_text(MANIFEST)
    assert aj.main(["pa", "scraping", "--manifest", str(path), "--dry-run"]) == 0
    assert path.read_text() == MANIFEST
    assert aj.main(["pa", "scraping", "--manifest", str(path)]) == 0
    assert _load(path.read_text())["pa"]["status"] == "scraping"


# --- the validator rules behind it ---------------------------------------------------------------


def _entry(status, **overrides):
    entry = copy.deepcopy(_load(MANIFEST)["pa"])
    entry["status"] = status
    for dotted, value in overrides.items():
        section, key = dotted.split("__")
        entry[section][key] = value
    return {"pa": entry}


@pytest.mark.parametrize("status", ["scraping", "validating", "archived", "live"])
def test_a_state_past_probing_must_refresh_people_and_allow_archive(status):
    errors = validate(_entry(status))
    assert any("pa.enrollment.people_refresh" in e and repr(status) in e for e in errors)
    assert any("pa.archive.enabled" in e for e in errors)
    ok = validate(_entry(status, enrollment__people_refresh=True, archive__enabled=True))
    assert ok == []


def test_a_probing_or_paused_state_may_leave_them_off():
    assert validate(_entry("probing")) == []
    assert validate(_entry("paused")) == []


def test_legbot_embedding_and_routing_are_never_required():
    only_the_required = _entry("live", enrollment__people_refresh=True, archive__enabled=True)
    for human in ("legbot_replica", "embedding", "replica_routing"):
        assert only_the_required["pa"]["enrollment"][human] is False
    assert validate(only_the_required) == []


@pytest.mark.parametrize("flag", ["enrollment__people_refresh", "archive__enabled"])
@pytest.mark.parametrize("bad", ["missing", None, "yes", 1])
def test_a_live_state_cannot_get_past_the_validator_with_a_missing_null_or_mistyped_required_flag(flag, bad):
    """The new lifecycle rules reject an explicit false; the existing block check rejects a missing, null or
    non-boolean value. Together a live state cannot carry anything but a real true in these two places."""
    data = _entry("live", enrollment__people_refresh=True, archive__enabled=True)
    section, key = flag.split("__")
    if bad == "missing":
        del data["pa"][section][key]
    else:
        data["pa"][section][key] = bad
    errors = validate(data)
    assert errors, f"{flag}={bad!r} was accepted for a live state"
    assert any(f"pa.{section}.{key}" in e for e in errors)
