"""
Tests for validate_jurisdictions.py (OPEN-221) and, as a live check, the real jurisdictions.yaml
this PR adds. No database, no network, no live scrape -- pure schema validation against fixture
dicts plus the actual checked-in manifest.
"""

import copy
import os
import subprocess
import sys

import pytest
import yaml

from validate_jurisdictions import validate, load_and_validate, DEFAULT_MANIFEST_PATH


def _valid_entry():
    """A minimal, fully-valid single jurisdiction entry -- copy and mutate per test."""
    return {
        "name": "Test State",
        "status": "live",
        "scrape": {
            "allow_duplicates": False,
            "timeout_s": 21600,
            "session_arg": None,
            "votes_scraper": False,
            "start_filter": True,
            "sweep_import": False,
            "full_walk": False,
            "retry": False,
            "cadence_escalation": True,
            "fargate_max_wait_s": None,
        },
        "archive": {
            "enabled": True,
            "timeout_s": 14400,
        },
        "enrollment": {
            "people_refresh": True,
            "search_refresh": True,
            "embedding": True,
            "cloud_path": True,
            "api_smoke_test": True,
            "qa_sweep": True,
            "replica_routing": True,
            "legbot_replica": True,
            "broker_bill_event_signal": False,
        },
        "waf": {
            "profile": "none",
            "fargate_safe": True,
            "scrapebot_fallback": False,
        },
        "quality": {
            "diff_cleaner": "none",
        },
        "api_keys": [],
        "onboarding": {
            "epic": None,
            "evidence": None,
        },
        "actions": {
            "newest_first": False,
        },
        "voatz": {
            "creator_id": None,
            "test_precinct": None,
        },
    }


def test_valid_entry_has_no_errors():
    data = {"ts": _valid_entry()}
    assert validate(data) == []


def test_empty_manifest_is_an_error():
    assert validate(None) != []
    assert validate({}) != []


def test_root_must_be_a_mapping():
    errors = validate(["not", "a", "mapping"])
    assert len(errors) == 1
    assert "mapping" in errors[0]


def test_missing_top_level_field_reported():
    entry = _valid_entry()
    del entry["waf"]
    errors = validate({"ts": entry})
    assert any("ts.waf: missing required field" == e for e in errors)


def test_unknown_top_level_field_reported():
    entry = _valid_entry()
    entry["walk_direction"] = "forward"  # OPEN-34: deliberately obsolete, must not be accepted
    errors = validate({"ts": entry})
    assert any("ts.walk_direction: unknown field" in e for e in errors)


def test_quality_walk_direction_field_rejected():
    """The plan's 2026-08-07 update marks quality.walk_direction obsolete -- confirm the
    validator does not quietly accept it if someone adds it back to a quality block."""
    entry = _valid_entry()
    entry["quality"]["walk_direction"] = "forward"
    errors = validate({"ts": entry})
    assert any("ts.quality.walk_direction: unknown field" in e for e in errors)


def test_missing_enrollment_block_reported():
    entry = _valid_entry()
    del entry["enrollment"]
    assert "ts.enrollment: missing required field" in validate({"ts": entry})


def test_missing_enrollment_flag_reported():
    entry = _valid_entry()
    del entry["enrollment"]["embedding"]
    assert "ts.enrollment.embedding: missing required field" in validate({"ts": entry})


def test_unknown_enrollment_flag_reported():
    entry = _valid_entry()
    entry["enrollment"]["legbot"] = True
    assert any("ts.enrollment.legbot: unknown field" in e for e in validate({"ts": entry}))


def test_enrollment_flags_must_be_booleans():
    entry = _valid_entry()
    entry["enrollment"]["people_refresh"] = "yes"
    assert any("ts.enrollment.people_refresh: expected bool" in e for e in validate({"ts": entry}))


def test_bad_status_enum_reported():
    entry = _valid_entry()
    entry["status"] = "sleeping"
    errors = validate({"ts": entry})
    assert any(e.startswith("ts.status:") for e in errors)


@pytest.mark.parametrize("block, field, value", [(None, "tier", "primary"), (None, "tier", "secondary"),
                                                  ("archive", "scheduled", True), ("archive", "scheduled", False)])
def test_the_fields_open_521_removed_are_rejected_and_the_error_says_why(block, field, value):
    """OPEN-521: tier and archive.scheduled no longer exist (ddp-sync reads only status and archive.enabled; WHEN is
    its openstates_scrape.timing). Any value is an error, and the message names the ticket so nobody adds them back."""
    entry = _valid_entry()
    (entry if block is None else entry[block])[field] = value
    path = f"ts.{field}" if block is None else f"ts.{block}.{field}"
    errors = validate({"ts": entry})
    assert len(errors) == 1, errors
    assert errors[0].startswith(f"{path}: unknown field") and "removed by OPEN-521" in errors[0]


def test_an_ordinary_unknown_field_gets_no_removed_by_note():
    entry = _valid_entry()
    entry["archive"]["cadence"] = "weekly"
    assert validate({"ts": entry}) == ["ts.archive.cadence: unknown field (not in the §4.1 schema)"]


def test_bad_waf_profile_enum_reported():
    entry = _valid_entry()
    entry["waf"]["profile"] = "moat"
    errors = validate({"ts": entry})
    assert any(e.startswith("ts.waf.profile:") for e in errors)


def test_missing_waf_fargate_safe_reported():
    entry = _valid_entry()
    del entry["waf"]["fargate_safe"]
    errors = validate({"ts": entry})
    assert "ts.waf.fargate_safe: missing required field" in errors


def test_waf_fargate_safe_must_be_a_bool():
    entry = _valid_entry()
    entry["waf"]["fargate_safe"] = "false"
    errors = validate({"ts": entry})
    assert any("ts.waf.fargate_safe" in e and "expected bool" in e for e in errors)


def test_wrong_type_reported():
    entry = _valid_entry()
    entry["scrape"]["timeout_s"] = "6h"  # should be an int, not a string
    errors = validate({"ts": entry})
    assert any("ts.scrape.timeout_s" in e and "expected int" in e for e in errors)


def test_bool_rejected_where_int_expected():
    """bool is a subclass of int in Python -- confirm the validator doesn't let `timeout_s: true`
    sneak past a naive isinstance(x, int) check."""
    entry = _valid_entry()
    entry["scrape"]["timeout_s"] = True
    errors = validate({"ts": entry})
    assert any("ts.scrape.timeout_s" in e and "bool" in e for e in errors)


def test_negative_timeout_reported():
    entry = _valid_entry()
    entry["scrape"]["timeout_s"] = -1
    errors = validate({"ts": entry})
    assert any("must be positive" in e for e in errors)


def test_zero_timeout_reported():
    entry = _valid_entry()
    entry["archive"]["timeout_s"] = 0
    errors = validate({"ts": entry})
    assert any("must be positive" in e for e in errors)


def test_null_session_arg_is_allowed():
    """session_arg is nullable -- None must not itself be flagged as a type error."""
    entry = _valid_entry()
    entry["scrape"]["session_arg"] = None
    assert validate({"ts": entry}) == []


def test_string_session_arg_is_allowed():
    entry = _valid_entry()
    entry["scrape"]["session_arg"] = "2026"
    assert validate({"ts": entry}) == []


def test_api_keys_must_be_nonempty_strings():
    entry = _valid_entry()
    entry["api_keys"] = ["VA_API_KEY", "", 5]
    errors = validate({"ts": entry})
    assert any("api_keys[1]" in e for e in errors)
    assert any("api_keys[2]" in e for e in errors)


def test_uppercase_jurisdiction_key_reported():
    entry = _valid_entry()
    errors = validate({"TS": entry})
    assert any("lowercase" in e for e in errors)


def test_multiple_problems_all_reported_in_one_pass():
    entry = _valid_entry()
    entry["status"] = "bogus"
    entry["waf"]["profile"] = "bogus"
    del entry["quality"]
    errors = validate({"ts": entry})
    # all three independent problems should show up, not just the first one found
    assert any(e.startswith("ts.status:") for e in errors)
    assert any(e.startswith("ts.waf.profile:") for e in errors)
    assert any("ts.quality: missing required field" == e for e in errors)


def test_entry_must_be_a_mapping():
    errors = validate({"ts": "not-a-mapping"})
    assert any("must be a mapping" in e for e in errors)


# ── Live check against the real, checked-in manifest ──────────────────────────────────────────


def test_real_manifest_is_valid():
    data, errors = load_and_validate(DEFAULT_MANIFEST_PATH)
    assert errors == [], f"jurisdictions.yaml has schema problems: {errors}"
    assert isinstance(data, dict)


def test_real_manifest_covers_the_eight_tracked_jurisdictions():
    """The original 8 must always be present; the manifest is allowed to grow beyond them as
    OPEN-230-style pilot candidates get added (e.g. nc, status: probing) -- so this is a subset
    check, not exact-set equality."""
    with open(DEFAULT_MANIFEST_PATH) as f:
        data = yaml.safe_load(f)
    assert {"us", "fl", "wa", "va", "mi", "ut", "az", "ma"} <= set(data.keys())
    assert "al" in data  # OPEN-318: on the archive and people lists, so it belongs in the manifest (status paused)


def test_real_manifest_has_no_walk_direction_field():
    """Confirms the deliberate deviation from the plan's original example schema actually took
    (obsolete per the plan's 2026-08-07 update) -- not just that the validator would catch it if
    reintroduced (covered above), but that today's checked-in file doesn't have it as an actual
    YAML key (the header comment explaining the deviation legitimately mentions the string)."""
    with open(DEFAULT_MANIFEST_PATH) as f:
        data = yaml.safe_load(f)
    for code, entry in data.items():
        assert "walk_direction" not in entry.get("quality", {}), f"{code}.quality still has walk_direction"


def test_real_manifest_matches_known_live_config_values():
    """Spot-check a handful of values against the real config this manifest was seeded from,
    so a future edit that silently drifts the manifest away from ddp-sync/activate.sh's actual
    settings gets caught here rather than discovered live."""
    with open(DEFAULT_MANIFEST_PATH) as f:
        data = yaml.safe_load(f)

    # SCRAPE_TIMEOUT_S (ddp-sync/src/ddp_sync/pipelines/openstates_scrape.py)
    assert data["fl"]["scrape"]["timeout_s"] == 16 * 3600
    assert data["ma"]["scrape"]["timeout_s"] == 16 * 3600
    assert data["mi"]["scrape"]["timeout_s"] == 10 * 3600
    assert data["wa"]["scrape"]["timeout_s"] == 8 * 3600
    assert data["us"]["scrape"]["timeout_s"] == 4 * 3600
    assert data["va"]["scrape"]["timeout_s"] == 6 * 3600
    assert data["ut"]["scrape"]["timeout_s"] == 6 * 3600
    assert data["az"]["scrape"]["timeout_s"] == 6 * 3600

    # ARCHIVE_TIMEOUT_S (ddp-sync/src/ddp_sync/pipelines/openstates_archive.py)
    assert data["fl"]["archive"]["timeout_s"] == 16 * 3600
    assert data["wa"]["archive"]["timeout_s"] == 8 * 3600
    assert data["us"]["archive"]["timeout_s"] == 24 * 3600
    assert data["mi"]["archive"]["timeout_s"] == 24 * 3600  # ARCHIVE_TIMEOUT_S["mi"]; this once pinned the 4h default
    for code in ("va", "ut", "az", "ma"):
        assert data[code]["archive"]["timeout_s"] == 4 * 3600

    # activate.sh ARCHIVE_ENABLED_STATES -- all 8 originally-tracked jurisdictions are enabled.
    # Scoped to just those 8, not `for code in data`: a pilot candidate can be present in the
    # manifest (status: probing) with archive deliberately not yet enabled (Stage 4 gates that),
    # so archive.enabled isn't a blanket invariant across every entry any more.
    for code in ("us", "fl", "wa", "va", "mi", "ut", "az", "ma"):
        assert data[code]["archive"]["enabled"] is True

    # run-scrape.sh --allow_duplicates states
    assert data["mi"]["scrape"]["allow_duplicates"] is True
    assert data["fl"]["scrape"]["allow_duplicates"] is True
    assert data["va"]["scrape"]["allow_duplicates"] is True
    assert data["ma"]["scrape"]["allow_duplicates"] is True  # in run-scrape.sh's list since OPEN-55; this once pinned False
    for code in ("wa", "ut", "az", "us"):
        assert data[code]["scrape"]["allow_duplicates"] is False

    # OPEN-521: no tier and no archive.scheduled anywhere (when a state is scraped is ddp-sync's timing map)
    for code, e in data.items():
        assert "tier" not in e and "scheduled" not in e["archive"], code

    # resilience_profiles.py RESILIENCE_PROFILES
    assert data["mi"]["waf"]["profile"] == "cookie_provider"
    assert data["fl"]["waf"]["profile"] == "cookie_provider"
    for code in ("wa", "va", "ut", "az", "ma", "us"):
        assert data[code]["waf"]["profile"] == "none"

    # OPEN-464: mi and fl share waf.profile: cookie_provider but disagree on fargate_safe -- mi's
    # cookie can only be minted by the Mac, fl's warm-up runs wherever the scraper does
    assert data["mi"]["waf"]["fargate_safe"] is False
    for code in ("us", "fl", "wa", "va", "ut", "az", "ma", "nc", "al"):
        assert data[code]["waf"]["fargate_safe"] is True

    # PRIMITIVES.md per-jurisdiction credentials table
    assert data["va"]["api_keys"] == ["VA_API_KEY"]
    assert data["us"]["api_keys"] == ["CONGRESS_GOV_API_KEY"]

    # OPEN-50: only MA has a live (non-commented) separate votes scraper today
    assert data["ma"]["scrape"]["votes_scraper"] is True
    for code in ("us", "fl", "wa", "va", "mi", "ut", "az"):
        assert data[code]["scrape"]["votes_scraper"] is False

    # OPEN-128: MA's start= filter was deleted 2026-08-25
    assert data["ma"]["scrape"]["start_filter"] is False

    # OPEN-462: openstates-core text_extract.py's apply_prediff_cleaning() dispatch
    # (check-jurisdiction-drift.py --openstates-core-root enforces this against the real code)
    assert data["wa"]["quality"]["diff_cleaner"] == "clean_wa_text"
    assert data["va"]["quality"]["diff_cleaner"] == "clean_virginia_text"
    assert data["mi"]["quality"]["diff_cleaner"] == "clean_michigan_text"
    assert data["az"]["quality"]["diff_cleaner"] == "reflow_paragraphs"
    assert data["al"]["quality"]["diff_cleaner"] == "clean_al_text"  # was "none"; the code already cleaned AL
    assert data["nc"]["quality"]["diff_cleaner"] == "clean_nc_text"  # was "none"; the code already cleaned NC
    assert data["ma"]["quality"]["diff_cleaner"] == "clean_massachusetts_text"  # was "none"; the code already cleaned MA
    for code in ("us", "fl", "ut"):
        assert data[code]["quality"]["diff_cleaner"] == "none"


def test_deepcopy_of_valid_entry_is_still_valid():
    # sanity check on the fixture itself
    entry = copy.deepcopy(_valid_entry())
    assert validate({"ts": entry}) == []


def test_load_and_validate_missing_file():
    data, errors = load_and_validate("/nonexistent/path/jurisdictions.yaml")
    assert data is None
    assert len(errors) == 1
    assert "cannot read" in errors[0]


def test_load_and_validate_invalid_yaml(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("fl: [this is not: valid: yaml")
    data, errors = load_and_validate(str(bad))
    assert data is None
    assert len(errors) == 1
    assert "not valid YAML" in errors[0]


# -- PM-review round 1 fold: duplicate-key detection --


def test_load_and_validate_rejects_duplicate_top_level_jurisdiction_key(tmp_path):
    """PyYAML's default loader silently accepts duplicate mapping keys (last value wins) -- a
    real gap for a file meant to be this fleet's authoritative source of truth. A duplicated
    jurisdiction code must be rejected, not silently resolved to whichever copy came last."""
    dup = tmp_path / "dup.yaml"
    dup.write_text(
        "fl:\n  name: Florida\n  status: live\nfl:\n  name: Florida Again\n  status: live\n"
    )
    data, errors = load_and_validate(str(dup))
    assert data is None
    assert len(errors) == 1
    assert "duplicate key" in errors[0]


def test_load_and_validate_rejects_duplicate_nested_field(tmp_path):
    """Same gap, one level deeper -- two timeout_s: lines under one jurisdiction's scrape block."""
    dup = tmp_path / "dup.yaml"
    dup.write_text(
        "fl:\n  name: Florida\n  status: live\n  scrape:\n    timeout_s: 100\n    timeout_s: 200\n"
    )
    data, errors = load_and_validate(str(dup))
    assert data is None
    assert len(errors) == 1
    assert "duplicate key" in errors[0]


# -- PM-review round 1 fold: exercise the actual CLI entry point as a subprocess, not just by
# -- importing and calling functions, so a broken/missing __main__ block would actually fail here.


def test_cli_exits_zero_on_the_real_manifest():
    result = subprocess.run(
        [sys.executable, "validate_jurisdictions.py", DEFAULT_MANIFEST_PATH],
        capture_output=True,
        text=True,
    )
    with open(DEFAULT_MANIFEST_PATH) as f:
        real_count = len(yaml.safe_load(f))

    assert result.returncode == 0
    # Not hardcoded to 8: the manifest is expected to grow as pilot candidates get added
    # (OPEN-230+), so this checks the CLI's reported count against the real manifest instead.
    assert result.stdout.startswith(f"OK: {real_count} jurisdiction(s) valid")


def test_cli_exits_nonzero_and_reports_problems_on_invalid_input(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("fl:\n  name: Florida\n")  # missing every other required field
    result = subprocess.run(
        [sys.executable, "validate_jurisdictions.py", str(bad)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "problem(s)" in result.stderr
    assert "missing required field" in result.stderr


def test_the_two_env_list_fields_are_required_booleans():
    for field in ("replica_routing", "legbot_replica"):
        entry = _valid_entry()
        del entry["enrollment"][field]
        assert any(field in e for e in validate({"ts": entry})), field
        entry = _valid_entry()
        entry["enrollment"][field] = "yes"
        assert any(f"ts.enrollment.{field}: expected bool" in e for e in validate({"ts": entry})), field


# ---------------------------------------------------------------------------------------------------
# OPEN-521: archive.enabled is the one archive flag ("this state's scrape is followed by its archive"); the
# pilot #2 rule that every state past probing has it is unchanged, and `live` asks for nothing more.
# ---------------------------------------------------------------------------------------------------


def _with(status="live", enabled=True):
    entry = _valid_entry()
    entry["status"] = status
    entry["archive"]["enabled"] = enabled
    return {"ts": entry}


@pytest.mark.parametrize("status", ["scraping", "validating", "archived", "live"])
def test_a_scraped_state_must_have_archive_enabled(status):
    errors = validate(_with(status=status, enabled=False))
    assert len(errors) == 1 and errors[0].startswith("ts.archive.enabled: must be true") and repr(status) in errors[0]


@pytest.mark.parametrize("status", ["probing", "paused"])
def test_a_probing_or_paused_state_may_have_archive_off(status):
    assert validate(_with(status=status, enabled=False)) == []


@pytest.mark.parametrize("status", ["probing", "scraping", "validating", "archived", "live", "paused"])
def test_archive_enabled_alone_is_valid_at_every_status(status):
    """There is no second archive flag for `live` to need (the old archive.scheduled)."""
    assert validate(_with(status=status, enabled=True)) == []


# --- BROKER-368: actions.newest_first and the voatz block -------------------------------------------------------

def test_actions_and_voatz_are_required_blocks():
    for block in ("actions", "voatz"):
        entry = _valid_entry()
        del entry[block]
        assert validate({"ts": entry}) == [f"ts.{block}: missing required field"]


def test_newest_first_must_be_a_bool():
    entry = _valid_entry()
    entry["actions"]["newest_first"] = "yes"
    assert any("ts.actions.newest_first: expected bool" in e for e in validate({"ts": entry}))
    entry["actions"] = {}
    assert validate({"ts": entry}) == ["ts.actions.newest_first: missing required field"]


def test_voatz_values_take_an_id_and_a_name_or_null():
    entry = _valid_entry()
    entry["voatz"] = {"creator_id": 900000837, "test_precinct": "FLORIDA-TEST"}
    assert validate({"ts": entry}) == []


@pytest.mark.parametrize("field,bad,why", [
    ("creator_id", "900000837", "expected int or NoneType"),
    ("creator_id", True, "expected int or null, got bool"),
    ("creator_id", 0, "must be a positive id"),
    ("creator_id", -5, "must be a positive id"),
    ("test_precinct", 7, "expected str or NoneType"),
    ("test_precinct", "  ", "must be null or a non-empty name"),
])
def test_a_wrong_voatz_value_is_rejected(field, bad, why):
    entry = _valid_entry()
    entry["voatz"][field] = bad
    errors = validate({"ts": entry})
    assert any(f"ts.voatz.{field}" in e and why in e for e in errors), errors


def test_an_unknown_field_in_the_new_blocks_is_rejected():
    entry = _valid_entry()
    entry["voatz"]["organization_id"] = "800000075"
    assert any("ts.voatz.organization_id: unknown field" in e for e in validate({"ts": entry}))


def test_the_real_manifest_keeps_the_broker_values_it_replaces():
    """The values the broker kept in code until BROKER-368, copied exactly: newest-first us and nc; creator ids fl, us,
    va (CREATOR_IDS was keyed by Voatz organization id: 800000075 fl, 800000097 us, 800000115 va); test precincts fl, us."""
    import yaml
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "jurisdictions.yaml")) as fh:
        data = yaml.safe_load(fh)
    assert sorted(c for c, e in data.items() if e["actions"]["newest_first"]) == ["nc", "us"]
    assert {c: e["voatz"]["creator_id"] for c, e in data.items() if e["voatz"]["creator_id"] is not None} == {
        "fl": 900000837, "us": 900000912, "va": 900000977}
    assert {c: e["voatz"]["test_precinct"] for c, e in data.items() if e["voatz"]["test_precinct"] is not None} == {
        "fl": "FLORIDA-TEST", "us": "FEDERAL-TEST"}


# --- SYNC-157: ddp-sync's per-state behaviour fields ---------------------------------------------------------------


@pytest.mark.parametrize("dotted,value", [
    ("scrape.sweep_import", "yes"), ("scrape.full_walk", 1), ("scrape.retry", None), ("scrape.cadence_escalation", "true"),
    ("scrape.fargate_max_wait_s", "86400"), ("enrollment.broker_bill_event_signal", None), ("waf.scrapebot_fallback", "mi"),
])
def test_sync_157_fields_reject_a_wrong_type(dotted, value):
    entry = _valid_entry()
    section, key = dotted.split(".")
    entry[section][key] = value
    assert any(f"xx.{dotted}" in e for e in validate({"xx": entry}))


@pytest.mark.parametrize("dotted", ["scrape.sweep_import", "scrape.retry", "scrape.fargate_max_wait_s",
                                    "enrollment.broker_bill_event_signal", "waf.scrapebot_fallback"])
def test_sync_157_fields_are_required(dotted):
    entry = _valid_entry()
    section, key = dotted.split(".")
    del entry[section][key]
    assert any(f"xx.{dotted}: missing required field" in e for e in validate({"xx": entry}))


@pytest.mark.parametrize("value", [0, -1, True])
def test_fargate_max_wait_must_be_positive_seconds_or_null(value):
    entry = _valid_entry()
    entry["scrape"]["fargate_max_wait_s"] = value
    assert any("xx.scrape.fargate_max_wait_s" in e for e in validate({"xx": entry}))
    entry["scrape"]["fargate_max_wait_s"] = 86400
    assert validate({"xx": entry}) == []


def test_retry_is_refused_for_a_state_with_a_waf():
    """Was ddp-sync's scrape_retry.jurisdictions_excluded: ["mi"] (OPEN-53): retrying against a WAF worsens a block."""
    entry = _valid_entry()
    entry["scrape"]["retry"] = True
    assert validate({"xx": entry}) == []          # no WAF: fine
    entry["waf"]["profile"] = "cookie_provider"
    assert any("xx.scrape.retry" in e and "OPEN-53" in e for e in validate({"xx": entry}))


def test_the_real_manifest_keeps_the_values_ddp_sync_had():
    """SYNC-157: the values copied from ddp-sync's sync_schedule.yaml on 2026-11-12."""
    import yaml as _yaml
    with open(DEFAULT_MANIFEST_PATH) as fh:
        data = _yaml.safe_load(fh)
    on = lambda path: sorted(c for c, e in data.items() if e[path[0]][path[1]])  # noqa: E731
    assert on(("scrape", "sweep_import")) == ["fl", "ma", "mi", "va"]
    assert on(("scrape", "full_walk")) == ["mi"]
    assert on(("scrape", "retry")) == ["ma"]
    assert on(("waf", "scrapebot_fallback")) == ["mi"]
    assert on(("enrollment", "broker_bill_event_signal")) == []
    assert all(e["scrape"]["cadence_escalation"] for e in data.values())
    assert {c: e["scrape"]["fargate_max_wait_s"] for c, e in data.items() if e["scrape"]["fargate_max_wait_s"]} == {"ma": 86400}
