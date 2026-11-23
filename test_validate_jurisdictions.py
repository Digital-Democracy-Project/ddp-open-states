"""
Tests for validate_jurisdictions.py (OPEN-221) and, as a live check, the real jurisdictions.yaml
this PR adds. No database, no network, no live scrape -- pure schema validation against fixture
dicts plus the actual checked-in manifest.
"""

import copy
import datetime
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
        "scraper_module": "ts",
        "ocd_id": "ocd-jurisdiction/country:us/state:ts/government",
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
            "load_on_fargate": False,
            "session_list_attempts": None,
            "session_list_backoff_s": None,
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
            "requests_per_minute": None,
            "max_consecutive_blocks": None,
            "max_attempts": None,
            "cooldown_after_failures": None,
            "cooldown_s": None,
        },
        "quality": {
            "diff_cleaner": "none",
        },
        "chambers": {
            "unicameral": False,
            "upper": "Senate",
            "lower": "House of Representatives",
        },
        "votes": {
            "house_speaker_by_session": None,
            "senate_president_by_session": None,
            "bare_key_session": None,
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

    # OPEN-50/OPEN-592: MA registers a separate votes scraper but stays false on purpose (its votes
    # come from ma/bills.py; Ramon, 2026-11-16: MAVoteScraper stays off)
    for code in ("us", "fl", "wa", "va", "mi", "ut", "az", "ma"):
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


# --- OPEN-544: no actions block (was BROKER-368's actions.newest_first); BROKER-482/494: no voatz block ---------------

@pytest.mark.parametrize("actions", [{"newest_first": False}, {"newest_first": True}, {}, None])
def test_an_actions_block_is_rejected_whatever_it_holds(actions):
    """OPEN-544: every state's bill actions are stored oldest first (fixed in the scrapers), so actions.newest_first was
    false everywhere and nothing reads it. A state found storing them newest first is fixed in its scraper, so the
    block, even `newest_first: false` or empty, is refused with the reason."""
    entry = _valid_entry()
    entry["actions"] = actions
    errors = validate({"ts": entry})
    assert errors == [errors[0]] and errors[0].startswith("ts.actions: unknown field"), errors
    assert "OPEN-544" in errors[0] and "scraper" in errors[0], errors


@pytest.mark.parametrize("voatz", [
    {"test_precinct": "FLORIDA-TEST"}, {"test_precinct": None}, {"creator_id": 999000001}, {"creator_id": None}, {}, None,
])
def test_a_voatz_block_is_rejected_whatever_it_holds(voatz):
    """BROKER-494 (Ramon, 2026-11-13: api-v3 serves only OpenStates data): Voatz's test precinct and its private poll
    creator id (BROKER-482) live in each state's Voatz entry in AWS Secrets Manager, read by the broker. The public
    manifest never carries a voatz block, not even an empty one, so nothing Voatz can be added back by accident."""
    entry = _valid_entry()
    entry["voatz"] = voatz
    errors = validate({"ts": entry})
    assert errors == [errors[0]] and errors[0].startswith("ts.voatz: unknown field"), errors
    assert "BROKER-494" in errors[0] and "Secrets Manager" in errors[0], errors


def test_the_real_manifest_has_no_actions_block_and_nothing_voatz():
    """No actions block (OPEN-544: actions.newest_first is gone, every state stores its actions oldest first). No voatz
    block (BROKER-494: the test precincts moved to Secrets Manager) and no Voatz creator id anywhere in the file
    (BROKER-482: private), not even a number that looks like one."""
    import re
    import yaml
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jurisdictions.yaml")
    with open(path) as fh:
        text = fh.read()
    data = yaml.safe_load(text)
    assert [c for c, e in data.items() if "actions" in e] == []
    assert "newest_first:" not in text
    assert [c for c, e in data.items() if "voatz" in e] == []
    assert "test_precinct" not in text and "creator_id" not in text
    # Voatz ids are nine digits starting 9 (creator) or 8 (organization, not secret); no 9-prefixed one may appear
    assert not re.search(r"(?<!\d)9\d{8}(?!\d)", text)


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


# --- OPEN-556: chamber names and the one-house flag ----------------------------------------------------------------


@pytest.mark.parametrize("dotted", [None, "chambers.unicameral", "chambers.upper", "chambers.lower"])
def test_chambers_are_required_on_every_entry(dotted):
    entry = _valid_entry()
    if dotted is None:
        del entry["chambers"]
        assert "xx.chambers: missing required field" in validate({"xx": entry})
    else:
        del entry["chambers"][dotted.split(".")[1]]
        assert f"xx.{dotted}: missing required field" in validate({"xx": entry})


@pytest.mark.parametrize("field,value", [("unicameral", "no"), ("unicameral", None), ("upper", None), ("upper", 1),
                                         ("lower", 1), ("upper", ""), ("lower", "  ")])
def test_chambers_reject_a_wrong_type_or_an_empty_name(field, value):
    entry = _valid_entry()
    entry["chambers"][field] = value
    assert any(e.startswith(f"xx.chambers.{field}:") for e in validate({"xx": entry}))


def test_chambers_reject_an_unknown_field():
    entry = _valid_entry()
    entry["chambers"]["legislature"] = "Legislature"
    assert validate({"xx": entry}) == ["xx.chambers.legislature: unknown field (not in the §4.1 schema)"]


def test_a_one_house_legislature_has_no_lower_chamber_and_a_two_house_one_needs_it():
    entry = _valid_entry()
    entry["chambers"] = {"unicameral": True, "upper": "Legislature", "lower": None}
    assert validate({"xx": entry}) == []
    entry["chambers"]["lower"] = "House of Representatives"
    assert any(e.startswith("xx.chambers.lower: must be null for a one-house") for e in validate({"xx": entry}))
    entry["chambers"] = {"unicameral": False, "upper": "Senate", "lower": None}
    assert any(e.startswith("xx.chambers.lower: a two-house legislature") for e in validate({"xx": entry}))


def test_the_real_manifest_names_each_legislatures_chambers():
    """OPEN-556: the values checked against each legislature's own site (see the PR). Pinned so a wrong edit is seen."""
    with open(DEFAULT_MANIFEST_PATH) as fh:
        data = yaml.safe_load(fh)
    names = {c: (e["chambers"]["upper"], e["chambers"]["lower"]) for c, e in data.items()}
    assert [c for c, e in data.items() if e["chambers"]["unicameral"]] == ["ne"]
    assert names["ne"] == ("Legislature", None)
    assert names["va"] == ("Senate", "House of Delegates")
    assert names["md"] == ("Senate", "House of Delegates")  # OPEN-674: Maryland Manual, mgaleg.maryland.gov
    assert names["nv"] == ("Senate", "Assembly")
    house = {c for c, (upper, lower) in names.items() if (upper, lower) == ("Senate", "House of Representatives")}
    assert house == set(data) - {"ne", "va", "nv", "md"}


# --- OPEN-555: per-state values moved out of code (scraper_module, ocd_id, fetch limits, vote-reading values) ---------

OPEN555_FIELDS = ["scraper_module", "ocd_id", "votes", "scrape.session_list_attempts", "scrape.session_list_backoff_s",
                  "waf.requests_per_minute", "waf.max_consecutive_blocks", "waf.max_attempts",
                  "waf.cooldown_after_failures", "waf.cooldown_s", "votes.house_speaker_by_session",
                  "votes.senate_president_by_session", "votes.bare_key_session"]


# OPEN-764: Louisiana's sessions of the 2024-2028 term, as scrapers/la/__init__.py names them
LA_2024_TERM = ("2024", "2024s1", "2024s2", "2024s3", "2025", "2025s1", "2026")


@pytest.mark.parametrize("dotted", OPEN555_FIELDS)
def test_open555_fields_are_required_on_every_entry(dotted):
    entry = _valid_entry()
    *blocks, leaf = dotted.split(".")
    node = entry
    for block in blocks:
        node = node[block]
    del node[leaf]
    assert f"xx.{dotted}: missing required field" in validate({"xx": entry})


@pytest.mark.parametrize("dotted,value", [
    ("scraper_module", 1), ("scraper_module", "US"), ("scraper_module", "scrapers.fl"), ("scraper_module", ""),
    ("ocd_id", None), ("ocd_id", "ocd-jurisdiction/country:us/state:ts"), ("ocd_id", "state:ts"),
    ("scrape.session_list_attempts", 0), ("scrape.session_list_attempts", "3"), ("scrape.session_list_backoff_s", -1),
    ("scrape.session_list_backoff_s", True),
    ("votes.bare_key_session", 2025), ("votes.bare_key_session", " "), ("votes.house_speaker_by_session", []),
    ("votes.house_speaker_by_session", {"194th": ""}), ("votes.house_speaker_by_session", {"194th": None}),
    ("votes.senate_president_by_session", []), ("votes.senate_president_by_session", "Cameron Henry"),
    ("votes.senate_president_by_session", {"2026": " "}), ("votes.senate_president_by_session", {"2026": None}),
    ("votes.senate_president_by_session", {2026: "Cameron Henry"}),
    # OPEN-785: a dated session needs quoted 'YYYY-MM-DD' days, each with a name
    ("votes.house_speaker_by_session", {"2026": {}}),
    ("votes.house_speaker_by_session", {"2026": {datetime.date(2026, 5, 7): "Chris Blazejewski"}}),
    ("votes.house_speaker_by_session", {"2026": {"May 7": "Chris Blazejewski"}}),
    ("votes.house_speaker_by_session", {"2026": {"2026-01-06": "Joe Shekarchi", "2026-05-07": " "}}),
    ("votes.senate_president_by_session", {"2026": {"2026-05-07": None}}),
])
def test_open555_fields_reject_a_wrong_value(dotted, value):
    entry = _valid_entry()
    *blocks, leaf = dotted.split(".")
    node = entry
    for block in blocks:
        node = node[block]
    node[leaf] = value
    assert any(e.startswith(f"xx.{dotted}") for e in validate({"xx": entry})), validate({"xx": entry})


@pytest.mark.parametrize("field", ["house_speaker_by_session", "senate_president_by_session"])
def test_open785_a_session_whose_officer_changed_maps_first_days_to_names(field):
    entry = _valid_entry()
    entry["votes"][field] = {"2025": "Joe Shekarchi",
                             "2026": {"2026-01-06": "Joe Shekarchi", "2026-05-07": "Chris Blazejewski"}}
    assert validate({"xx": entry}) == []


@pytest.mark.parametrize("value", ["ocd-jurisdiction/country:us/government",
                                   "ocd-jurisdiction/country:us/district:dc/government",
                                   "ocd-jurisdiction/country:us/territory:pr/government"])
def test_open555_ocd_id_accepts_us_districts_and_territories(value):
    entry = _valid_entry()
    entry["ocd_id"] = value
    assert validate({"xx": entry}) == []


@pytest.mark.parametrize("field", ["requests_per_minute", "max_consecutive_blocks", "max_attempts",
                                   "cooldown_after_failures", "cooldown_s"])
def test_open555_fetch_limits_are_null_without_a_waf_profile(field):
    entry = _valid_entry()
    entry["waf"][field] = 3
    assert any(e.startswith(f"xx.waf.{field}: must be null for a state with no WAF profile")
               for e in validate({"xx": entry}))
    entry["waf"]["profile"] = "cookie_provider"
    entry["waf"]["requests_per_minute"] = entry["waf"]["requests_per_minute"] or 10
    entry["waf"]["max_consecutive_blocks"] = entry["waf"]["max_consecutive_blocks"] or 3
    assert validate({"xx": entry}) == []
    entry["waf"][field] = 0
    assert any(e.startswith(f"xx.waf.{field}: must be null or a positive whole number") for e in validate({"xx": entry}))


@pytest.mark.parametrize("field", ["requests_per_minute", "max_consecutive_blocks"])
def test_open555_a_waf_profile_needs_its_rate_and_block_limit(field):
    """openstates-core's resilience profile reads these two; the other three are optional (mi has none of them)."""
    entry = _valid_entry()
    entry["waf"].update(profile="cookie_provider", requests_per_minute=10, max_consecutive_blocks=3)
    assert validate({"xx": entry}) == []
    entry["waf"][field] = None
    assert any(e.startswith(f"xx.waf.{field}: a state with a WAF profile") for e in validate({"xx": entry}))


def test_open555_the_real_manifest_carries_todays_constants():
    """The values written out by hand from the constants each reader keeps as its fallback (openstates-core
    resilience_profiles.py, openstates-scrapers mi/fl/ut/ma/nc, qa_primitives.ocd_jurisdiction_id's rule), so the
    manifest and the fallbacks agree until step 4 deletes the constants."""
    with open(DEFAULT_MANIFEST_PATH) as fh:
        data = yaml.safe_load(fh)
    limits = ("requests_per_minute", "max_consecutive_blocks", "max_attempts", "cooldown_after_failures", "cooldown_s")
    assert {c: tuple(e["waf"][f] for f in limits) for c, e in data.items() if e["waf"]["profile"] != "none"} == {
        "mi": (10, 3, None, None, None),
        "fl": (10, 3, 3, 3, 300),
    }
    assert all(all(e["waf"][f] is None for f in limits) for e in data.values() if e["waf"]["profile"] == "none")
    retries = {c: (e["scrape"]["session_list_attempts"], e["scrape"]["session_list_backoff_s"]) for c, e in data.items()}
    assert {c: v for c, v in retries.items() if v != (None, None)} == {"ut": (3, 2)}
    speakers = {c: e["votes"]["house_speaker_by_session"] for c, e in data.items()}
    assert {c: v for c, v in speakers.items() if v is not None} == {
        "ma": {"192nd": "Ronald Mariano", "193rd": "Ronald Mariano", "194th": "Ronald Mariano"},
        "id": {"2026": "Mike Moyle"},  # OPEN-664: scrapers/id/voter_names.py
        "ms": {s: "Jason White" for s in ("2024", "20241E", "20242E", "2025", "20251E", "2026", "20261E")},  # OPEN-731
        "mo": {"2023": "Dean Plocher", "2024": "Dean Plocher",  # OPEN-738: scrapers/mo/voter_names.py
               **{s: "Jonathan Patterson" for s in ("2025", "2025S1", "2025S2", "2026")}},
        "la": {s: "Phillip DeVillier" for s in LA_2024_TERM},  # OPEN-764: scrapers/la/voter_names.py
        # OPEN-785: Speaker Shekarchi until the House elected Blazejewski on 2026-05-07 (House Journal of that day)
        "ri": {"2026": {"2026-01-06": "Joe Shekarchi", "2026-05-07": "Chris Blazejewski"}}}
    presidents = {c: e["votes"]["senate_president_by_session"] for c, e in data.items()}
    assert {c: v for c, v in presidents.items() if v is not None} == {
        "la": {s: "Cameron Henry" for s in LA_2024_TERM},  # OPEN-764
        "ri": {"2026": "Val Lawson"}}  # OPEN-785
    bare = {c: e["votes"]["bare_key_session"] for c, e in data.items()}
    assert {c: v for c, v in bare.items() if v is not None} == {"nc": "2025"}
    assert {c: e["scraper_module"] for c, e in data.items() if e["scraper_module"] != c} == {"us": "usa"}
    for code, entry in data.items():
        expected = ("ocd-jurisdiction/country:us/government" if code == "us"
                    else f"ocd-jurisdiction/country:us/state:{code}/government")
        assert entry["ocd_id"] == expected, code


def test_open555_two_entries_may_not_share_a_scraper_module():
    """code_for_scraper_module() maps a module back to one entry; a shared one would route by file order."""
    a, b = _valid_entry(), _valid_entry()
    b["ocd_id"] = "ocd-jurisdiction/country:us/state:tt/government"
    assert validate({"ts": a, "tt": b}) == ["ts, tt: scraper_module 'ts' is used by more than one entry; each "
                                            "jurisdiction has its own scraper module"]
    b["scraper_module"] = "tt"
    assert validate({"ts": a, "tt": b}) == []
