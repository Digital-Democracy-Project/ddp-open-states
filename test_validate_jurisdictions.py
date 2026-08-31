"""
Tests for validate_jurisdictions.py (OPEN-221) and, as a live check, the real jurisdictions.yaml
this PR adds. No database, no network, no live scrape -- pure schema validation against fixture
dicts plus the actual checked-in manifest.
"""

import copy

import yaml

from validate_jurisdictions import validate, load_and_validate, DEFAULT_MANIFEST_PATH


def _valid_entry():
    """A minimal, fully-valid single jurisdiction entry -- copy and mutate per test."""
    return {
        "name": "Test State",
        "status": "live",
        "tier": "secondary",
        "scrape": {
            "allow_duplicates": False,
            "timeout_s": 21600,
            "session_arg": None,
            "votes_scraper": False,
            "start_filter": True,
        },
        "archive": {
            "enabled": True,
            "timeout_s": 14400,
        },
        "waf": {
            "profile": "none",
        },
        "quality": {
            "diff_cleaner": "none",
        },
        "api_keys": [],
        "onboarding": {
            "epic": None,
            "evidence": None,
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


def test_bad_status_enum_reported():
    entry = _valid_entry()
    entry["status"] = "sleeping"
    errors = validate({"ts": entry})
    assert any(e.startswith("ts.status:") for e in errors)


def test_bad_tier_enum_reported():
    entry = _valid_entry()
    entry["tier"] = "tertiary"
    errors = validate({"ts": entry})
    assert any(e.startswith("ts.tier:") for e in errors)


def test_bad_waf_profile_enum_reported():
    entry = _valid_entry()
    entry["waf"]["profile"] = "moat"
    errors = validate({"ts": entry})
    assert any(e.startswith("ts.waf.profile:") for e in errors)


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
    entry["tier"] = "bogus"
    del entry["quality"]
    errors = validate({"ts": entry})
    # all three independent problems should show up, not just the first one found
    assert any(e.startswith("ts.status:") for e in errors)
    assert any(e.startswith("ts.tier:") for e in errors)
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
    with open(DEFAULT_MANIFEST_PATH) as f:
        data = yaml.safe_load(f)
    assert set(data.keys()) == {"us", "fl", "wa", "va", "mi", "ut", "az", "ma"}


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
    for code in ("va", "mi", "ut", "az", "ma"):
        assert data[code]["archive"]["timeout_s"] == 4 * 3600

    # activate.sh ARCHIVE_ENABLED_STATES -- all 8 tracked jurisdictions are enabled
    for code in data:
        assert data[code]["archive"]["enabled"] is True

    # run-scrape.sh --allow_duplicates states
    assert data["mi"]["scrape"]["allow_duplicates"] is True
    assert data["fl"]["scrape"]["allow_duplicates"] is True
    assert data["va"]["scrape"]["allow_duplicates"] is True
    for code in ("wa", "ut", "az", "ma", "us"):
        assert data[code]["scrape"]["allow_duplicates"] is False

    # ddp-sync sync_schedule.yaml primary/secondary
    for code in ("fl", "wa", "us"):
        assert data[code]["tier"] == "primary"
    for code in ("va", "mi", "ut", "az", "ma"):
        assert data[code]["tier"] == "secondary"

    # resilience_profiles.py RESILIENCE_PROFILES
    assert data["mi"]["waf"]["profile"] == "cookie_provider"
    assert data["fl"]["waf"]["profile"] == "cookie_provider"
    for code in ("wa", "va", "ut", "az", "ma", "us"):
        assert data[code]["waf"]["profile"] == "none"

    # PRIMITIVES.md per-jurisdiction credentials table
    assert data["va"]["api_keys"] == ["VA_API_KEY"]
    assert data["us"]["api_keys"] == ["CONGRESS_GOV_API_KEY"]

    # OPEN-50: only MA has a live (non-commented) separate votes scraper today
    assert data["ma"]["scrape"]["votes_scraper"] is True
    for code in ("us", "fl", "wa", "va", "mi", "ut", "az"):
        assert data[code]["scrape"]["votes_scraper"] is False

    # OPEN-128: MA's start= filter was deleted 2026-08-25
    assert data["ma"]["scrape"]["start_filter"] is False


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
