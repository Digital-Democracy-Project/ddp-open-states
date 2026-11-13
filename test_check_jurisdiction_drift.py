"""
Tests for check-jurisdiction-drift.py (OPEN-318).

A fixture world (a tiny manifest plus the real SHAPE of every file the checker reads) in which every list
agrees, then one deliberate disagreement per check: each must be caught, named, and reported with both
sides. A checker that cannot fail is worse than none, so most of this file is "break one thing, expect that
exact complaint". No network, no database; the only live check is the real checked-in files in THIS repo.
"""

import copy
import importlib.util
import io
import os

import pytest
import yaml

from test_validate_jurisdictions import _valid_entry

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("check_jurisdiction_drift", os.path.join(HERE, "check-jurisdiction-drift.py"))
drift = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(drift)


# ---------------------------------------------------------------------------------------------------
# the fixture world: fl and us ("usa" in ddp-sync) with their own ddp-sync timing, nc scraped on the defaults
# (no timing entry), al paused (not scraped)
# ---------------------------------------------------------------------------------------------------

def _entry(status="live", archive=True, waf_profile="none", waf_fargate_safe=True, **enrollment):
    e = _valid_entry()
    e["status"] = status
    e["archive"]["enabled"] = archive
    e["enrollment"].update({k: v for k, v in enrollment.items()})
    e["waf"]["profile"] = waf_profile
    e["waf"]["fargate_safe"] = waf_fargate_safe
    return e


def _manifest():
    fl = _entry(waf_profile="cookie_provider", people_refresh=True, search_refresh=True, embedding=True, cloud_path=True, api_smoke_test=True, qa_sweep=True)
    fl["scrape"]["allow_duplicates"] = True
    fl["scrape"]["timeout_s"] = 16 * 3600
    fl["archive"]["timeout_s"] = 16 * 3600
    us = _entry(people_refresh=True, search_refresh=True, embedding=True, cloud_path=True, api_smoke_test=True, qa_sweep=False)
    us["scrape"]["timeout_s"] = 4 * 3600
    us["archive"]["timeout_s"] = 24 * 3600
    nc = _entry(people_refresh=True, search_refresh=True, embedding=False, cloud_path=True, api_smoke_test=False, qa_sweep=False, replica_routing=True)
    # OPEN-462: fl/us keep the default "Test State" name (no branch in CORE_TEXT_EXTRACT_PY below, so
    # their expected diff_cleaner is "none"); nc/al get real display names so the fixture dispatch
    # below (keyed on those exact strings, like the real one) has something to match against.
    nc["name"] = "North Carolina"
    nc["quality"]["diff_cleaner"] = "clean_nc_text"
    al = _entry(status="paused", people_refresh=True, search_refresh=False, embedding=False, cloud_path=False, api_smoke_test=False, qa_sweep=True, replica_routing=False, legbot_replica=False)
    al["name"] = "Alabama"
    al["quality"]["diff_cleaner"] = "clean_al_text"
    return {"fl": fl, "us": us, "nc": nc, "al": al}


# OPEN-327: this repo's scripts derive their lists from the manifest, so the fixture files are the derived shape.
REPO_FILES = {
    "activate.sh": 'ARCHIVE_ENABLED_STATES="$(jurisdiction_codes archive.enabled)"\nexport ARCHIVE_ENABLED_STATES\n',
    "run-people-refresh.sh": 'people_states="$(jurisdiction_codes enrollment.people_refresh)"\nfor state in $(echo "$people_states" | tr "," " "); do\n    echo $state\ndone\n',
    "start-os-api.sh": 'smoke_states="$(jurisdiction_codes enrollment.api_smoke_test)"\nfor j in $(echo "$smoke_states" | tr "," " "); do\n    echo $j\ndone\n',
    "quality_check.py": 'JURISDICTIONS = [c for c, e in _MANIFEST.items() if e["enrollment"]["qa_sweep"]]\n',
    "run-scrape.sh": 'ALLOW_DUPLICATES_STATES="$(jurisdiction_codes scrape.allow_duplicates)"\n',
}

# OPEN-521 (SYNC-152/153): ddp-sync's shape after "one pipeline per state". No list of who is scraped or archived
# (it reads the manifest's status and archive.enabled); openstates_scrape.timing says only WHEN, for some states.
SYNC_YAML = {
    "openstates_archive": {
        "knowledge_base_embedding": {"jurisdictions": ["fl", "us"]},
        "bill_search_refresh": {"jurisdictions": ["us", "fl", "nc"]},
    },
    "openstates_scrape": {
        "defaults": {"floor": "weekly", "day": "sunday", "start_utc": "02:00"},
        "timing": {"fl": {"floor": "weekly", "day": "sunday", "start_utc": "02:00"},
                   "usa": {"floor": "nightly", "start_utc": "03:00",
                           "sessions": ["119 chamber=lower", "119 chamber=upper"]}},
        "cloud_path": {"jurisdictions": ["fl", "usa", "nc"], "memory_backend_jurisdictions": ["fl", "usa", "nc"]},
    },
}

SYNC_SCRAPE_PY = "SCRAPE_TIMEOUT_S: dict[str, int] = {\n    \"fl\": 16 * 3600,\n    \"usa\": 4 * 3600,\n    \"default\": 6 * 3600,\n}\n"
SYNC_ARCHIVE_PY = "ARCHIVE_TIMEOUT_S: dict[str, int] = {\n    \"fl\": 16 * 3600,\n    \"us\": 24 * 3600,\n    \"default\": 4 * 3600,\n}\n"

# OPEN-462: a minimal stand-in for openstates-core's text_extract.py, real dispatch shape (separate
# `if`s, not `elif`) but only the two branches the fixture manifest's nc/al need.
CORE_TEXT_EXTRACT_PY = '''
def apply_prediff_cleaning(prior_text, raw_text, *, jurisdiction_name, is_bill, prior_media_type, cur_media_type):
    if jurisdiction_name == "North Carolina":
        prior_text = _clean_nc_text(prior_text)
        raw_text = _clean_nc_text(raw_text)
    if jurisdiction_name == "Alabama":
        prior_text = _clean_al_text(prior_text)
        raw_text = _clean_al_text(raw_text)
    return prior_text, raw_text
'''

CORE_TEXT_EXTRACT_RELPATH = os.path.join("openstates", "cli", "text_extract.py")

# OPEN-464: a stub of openstates-core's RESILIENCE_PROFILES -- python_dict_keys() never inspects values,
# so these need not be real WafResilienceProfile(...) calls, just a module-level dict with string keys.
RESILIENCE_PROFILES_PY = 'RESILIENCE_PROFILES: dict = {\n    "fl": "stub -- values are never inspected",\n}\n'


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


@pytest.fixture
def world(tmp_path):
    """(repo_root, sync_root, manifest_path, openstates_core_root): every list agrees with the manifest."""
    repo, sync, core = tmp_path / "repo", tmp_path / "ddp-sync", tmp_path / "openstates-core"
    for name, text in REPO_FILES.items():
        _write(str(repo / name), text)
    _write(str(sync / "config" / "sync_schedule.yaml"), yaml.safe_dump(SYNC_YAML))
    _write(str(sync / "src/ddp_sync/pipelines/openstates_scrape.py"), SYNC_SCRAPE_PY)
    _write(str(sync / "src/ddp_sync/pipelines/openstates_archive.py"), SYNC_ARCHIVE_PY)
    _write(str(core / "openstates" / "utils" / "resilience_profiles.py"), RESILIENCE_PROFILES_PY)
    _write(str(core / CORE_TEXT_EXTRACT_RELPATH), CORE_TEXT_EXTRACT_PY)
    manifest = tmp_path / "jurisdictions.yaml"
    manifest.write_text(yaml.safe_dump(_manifest()))
    return str(repo), str(sync), str(manifest), str(core)


@pytest.fixture
def core_root(world):
    """Alias for world's own openstates-core dir (OPEN-462's fixture name, kept for its tests below):
    world already carries both the diff_cleaner dispatch and the RESILIENCE_PROFILES stub, agreeing
    with the fixture manifest's nc/al/fl out of the box."""
    return world[3]


def _run(world, with_sync=True, with_core=True, extra=(), core=None):
    repo, sync, manifest, core_dir = world
    argv = ["check", "--manifest", manifest, "--repo-root", repo, *extra]
    if with_sync:
        argv += ["--ddp-sync-root", sync]
    core_path = core if core is not None else (core_dir if with_core else None)
    if core_path:
        argv += ["--openstates-core-root", core_path]
    out = io.StringIO()
    return drift.main(argv, out), out.getvalue()


def _edit(world, relpath, old, new, root="repo"):
    base = {"repo": world[0], "sync": world[1], "core": world[3]}[root]
    path = os.path.join(base, relpath)
    text = open(path).read()
    assert old in text, (relpath, old)
    _write(path, text.replace(old, new, 1))


def _set_sync_yaml(world, mutate):
    path = os.path.join(world[1], "config", "sync_schedule.yaml")
    data = yaml.safe_load(open(path))
    mutate(data)
    _write(path, yaml.safe_dump(data))


# ---------------------------------------------------------------------------------------------------
# agreement
# ---------------------------------------------------------------------------------------------------

def test_everything_agreeing_passes(world):
    code, out = _run(world)
    assert code == 0, out
    assert "OK" in out and "4 jurisdictions" in out


def test_the_repo_alone_passes_and_says_ddp_sync_was_not_checked(world):
    code, out = _run(world, with_sync=False)
    assert code == 0
    assert "ddp-sync was not checked" in out


def test_require_ddp_sync_without_a_checkout_is_an_error_not_a_pass(world):
    code, out = _run(world, with_sync=False, extra=["--require-ddp-sync"])
    assert code == 2
    assert "--require-ddp-sync" in out


# ---------------------------------------------------------------------------------------------------
# this repo's scripts derive their lists (OPEN-327): break each derivation
# ---------------------------------------------------------------------------------------------------

REPO_SCRIPTS = {
    "activate.sh": ("jurisdiction_codes archive.enabled", 'ARCHIVE_ENABLED_STATES="fl,us"'),
    "run-people-refresh.sh": ("jurisdiction_codes enrollment.people_refresh", "for state in fl us al; do"),
    "start-os-api.sh": ("jurisdiction_codes enrollment.api_smoke_test", "for j in fl us; do"),
    "quality_check.py": ('e["enrollment"]["qa_sweep"]', 'JURISDICTIONS = ["fl", "al"]'),
    "run-scrape.sh": ("jurisdiction_codes scrape.allow_duplicates", 'ALLOW_DUPLICATES_STATES="fl"'),
}


@pytest.mark.parametrize("relpath", sorted(REPO_SCRIPTS))
def test_a_script_that_stops_reading_the_manifest_is_an_error(world, relpath):
    call, _ = REPO_SCRIPTS[relpath]
    _edit(world, relpath, call, "true")
    code, out = _run(world, with_sync=False)
    assert code == 2, out
    assert relpath in out and "must derive this list from jurisdictions.yaml" in out


@pytest.mark.parametrize("relpath", sorted(REPO_SCRIPTS))
def test_a_hand_typed_list_coming_back_is_an_error(world, relpath):
    _, literal = REPO_SCRIPTS[relpath]
    path = os.path.join(world[0], relpath)
    _write(path, open(path).read() + "\n" + literal + "\n")
    code, out = _run(world, with_sync=False)
    assert code == 2, out
    assert relpath in out and "has a hard-coded list again" in out


def test_derived_scripts_pass_even_though_there_is_no_list_to_compare(world):
    code, out = _run(world, with_sync=False)
    assert code == 0, out


def test_a_commented_out_old_list_is_not_a_list(world):
    path = os.path.join(world[0], "activate.sh")
    _write(path, '# ARCHIVE_ENABLED_STATES="fl,ut" -- the old hand-typed list\n' + open(path).read())
    code, out = _run(world, with_sync=False)
    assert code == 0, out


def test_several_disagreements_are_all_reported_in_one_pass(world):
    _set_sync_yaml(world, lambda d: d["openstates_archive"]["bill_search_refresh"]["jurisdictions"].remove("nc"))
    _set_sync_yaml(world, lambda d: d["openstates_scrape"]["cloud_path"]["jurisdictions"].remove("nc"))
    code, out = _run(world)
    assert code == 1
    assert out.count("DRIFT ") == 2 and "2 list(s) disagree" in out


# ---------------------------------------------------------------------------------------------------
# a source that cannot be read is an ERROR, never a pass
# ---------------------------------------------------------------------------------------------------

def test_two_definitions_of_a_timeout_table_are_ambiguous(world):
    _edit(world, "src/ddp_sync/pipelines/openstates_scrape.py", 'SCRAPE_TIMEOUT_S: dict[str, int] = {',
          'SCRAPE_TIMEOUT_S: dict[str, int] = {"default": 1}\nSCRAPE_TIMEOUT_S: dict[str, int] = {', root="sync")
    code, out = _run(world)
    assert code == 2 and "exactly one module-level SCRAPE_TIMEOUT_S" in out


def test_a_duplicate_key_in_the_ddp_sync_yaml_is_an_error_not_last_wins(world):
    path = os.path.join(world[1], "config", "sync_schedule.yaml")
    text = open(path).read()
    _write(path, text + "openstates_archive:\n  jurisdictions: [fl]\n")
    code, out = _run(world)
    assert code == 2 and "duplicate key" in out


def test_a_duplicate_key_in_the_manifest_is_an_error(world):
    text = open(world[2]).read()
    open(world[2], "w").write(text + "fl:\n  name: again\n")
    code, out = _run(world, with_sync=False)
    assert code == 2 and "does not validate" in out


def test_a_missing_timing_map_is_an_error_not_an_empty_pass(world):
    """OPEN-521: ddp-sync before SYNC-152 has no openstates_scrape.timing. That must fail loudly (it is what CI
    does against ddp-sync main until the SYNC-152/153 release merges), never pass as 'no timing, nothing extra'."""
    _set_sync_yaml(world, lambda d: d["openstates_scrape"].pop("timing"))
    code, out = _run(world)
    assert code == 2 and "openstates_scrape.timing (SYNC-152)" in out


def test_a_timing_map_that_is_a_list_is_an_error(world):
    _set_sync_yaml(world, lambda d: d["openstates_scrape"].update({"timing": ["fl", "usa"]}))
    code, out = _run(world)
    assert code == 2 and "openstates_scrape.timing is not a mapping" in out


def test_a_deleted_memory_backend_list_is_skipped_not_an_error(world):
    """SYNC-157: ddp-sync deletes the floor list (its memory backend follows the manifest's cloud_path)."""
    _set_sync_yaml(world, lambda d: d["openstates_scrape"]["cloud_path"].pop("memory_backend_jurisdictions"))
    code, out = _run(world)
    assert code == 0, out


def test_a_memory_backend_floor_still_present_must_contain_the_cloud_path_states(world):
    _set_sync_yaml(world, lambda d: d["openstates_scrape"]["cloud_path"].update(memory_backend_jurisdictions=["fl"]))
    code, out = _run(world)
    assert code == 1 and "memory_backend" in out


def _after_sync_157(d):
    """ddp-sync's shape after SYNC-157: no per-state list anywhere, only timing."""
    d["openstates_archive"]["knowledge_base_embedding"].pop("jurisdictions")
    d["openstates_archive"]["bill_search_refresh"].pop("jurisdictions")
    d["openstates_scrape"]["cloud_path"].pop("jurisdictions")
    d["openstates_scrape"]["cloud_path"].pop("memory_backend_jurisdictions")


def test_after_sync_157_ddp_sync_has_no_list_and_nothing_is_compared_but_timing(world):
    _set_sync_yaml(world, _after_sync_157)
    code, out = _run(world)
    assert code == 0, out


def test_while_ddp_sync_still_lists_a_behaviour_it_must_equal_the_manifest(world):
    """SYNC-157: the values were copied from ddp-sync's lists; until ddp-sync deletes them, they must agree."""
    _set_sync_yaml(world, lambda d: d["openstates_scrape"].update(sweep_import={"enabled": True, "jurisdictions": ["fl"]}))
    code, out = _run(world)
    assert code == 1 and "scrape.sweep_import" in out
    _set_sync_yaml(world, lambda d: d["openstates_scrape"].update(sweep_import={"enabled": True, "jurisdictions": []}))
    code, out = _run(world)
    assert code == 0, out


def test_a_missing_file_is_an_error(world):
    os.remove(os.path.join(world[0], "run-people-refresh.sh"))
    code, out = _run(world, with_sync=False)
    assert code == 2 and "cannot read" in out


# ---------------------------------------------------------------------------------------------------
# OPEN-462: quality.diff_cleaner compared against openstates-core's apply_prediff_cleaning() dispatch
# ---------------------------------------------------------------------------------------------------

def test_diff_cleaner_matching_the_dispatch_passes(world, core_root):
    code, out = _run(world, with_sync=False, core=core_root)
    assert code == 0, out


def test_diff_cleaner_is_not_checked_without_a_core_root(world):
    code, out = _run(world, with_sync=False, with_core=False)
    assert code == 0
    assert "openstates-core was not checked" in out


def test_require_openstates_core_without_a_checkout_is_an_error(world):
    code, out = _run(world, with_sync=False, with_core=False, extra=["--require-openstates-core"])
    assert code == 2
    assert "--require-openstates-core" in out


def test_manifest_says_none_but_code_has_a_cleaner_is_drift(world, core_root):
    """nc's real branch cleans it; a manifest edit back to "none" must be caught."""
    data = yaml.safe_load(open(world[2]))
    data["nc"]["quality"]["diff_cleaner"] = "none"
    _write(world[2], yaml.safe_dump(data))
    code, out = _run(world, with_sync=False, core=core_root)
    assert code == 1, out
    assert "DRIFT quality.diff_cleaner" in out
    assert "nc: code dispatches to 'clean_nc_text', manifest says 'none'" in out


def test_manifest_names_a_cleaner_the_code_does_not_have_is_drift(world, core_root):
    data = yaml.safe_load(open(world[2]))
    data["al"]["quality"]["diff_cleaner"] = "clean_al_text_v2"
    _write(world[2], yaml.safe_dump(data))
    code, out = _run(world, with_sync=False, core=core_root)
    assert code == 1, out
    assert "DRIFT quality.diff_cleaner" in out
    assert "al: code dispatches to 'clean_al_text', manifest says 'clean_al_text_v2'" in out


def test_a_renamed_cleaner_in_the_dispatch_is_caught_as_drift(world, core_root):
    """Mutation check (OPEN-462 AC): the manifest's old value now disagrees with the parsed table once
    the code's dispatch calls a differently-named function for the same jurisdiction."""
    path = os.path.join(core_root, CORE_TEXT_EXTRACT_RELPATH)
    _write(path, open(path).read().replace("_clean_al_text", "_clean_alabama_text_v2"))
    code, out = _run(world, with_sync=False, core=core_root)
    assert code == 1, out
    assert "al: code dispatches to 'clean_alabama_text_v2', manifest says 'clean_al_text'" in out


def test_a_removed_dispatch_branch_is_caught_as_drift(world, core_root):
    """If the code stops cleaning a jurisdiction, the manifest's non-"none" value is now stale."""
    path = os.path.join(core_root, CORE_TEXT_EXTRACT_RELPATH)
    text = open(path).read().replace(
        '    if jurisdiction_name == "North Carolina":\n'
        "        prior_text = _clean_nc_text(prior_text)\n"
        "        raw_text = _clean_nc_text(raw_text)\n",
        "",
    )
    assert "North Carolina" not in text
    _write(path, text)
    code, out = _run(world, with_sync=False, core=core_root)
    assert code == 1, out
    assert "nc: code dispatches to 'none', manifest says 'clean_nc_text'" in out


def test_an_unparseable_if_shape_is_an_error_not_a_pass(world, core_root):
    path = os.path.join(core_root, CORE_TEXT_EXTRACT_RELPATH)
    _write(path, open(path).read().replace(
        'if jurisdiction_name == "Alabama":', 'if jurisdiction_name in ("Alabama",):'
    ))
    code, out = _run(world, with_sync=False, core=core_root)
    assert code == 2, out
    assert "text_extract.py" in out and "this checker cannot parse" in out


def test_a_branch_calling_two_distinct_cleaners_is_an_error(world, core_root):
    path = os.path.join(core_root, CORE_TEXT_EXTRACT_RELPATH)
    _write(path, open(path).read().replace(
        "raw_text = _clean_al_text(raw_text)", "raw_text = _clean_other_text(raw_text)"
    ))
    code, out = _run(world, with_sync=False, core=core_root)
    assert code == 2, out
    assert "2 distinct cleaner" in out


def test_a_missing_apply_prediff_cleaning_function_is_an_error(world, core_root):
    path = os.path.join(core_root, CORE_TEXT_EXTRACT_RELPATH)
    _write(path, "def some_other_function():\n    pass\n")
    code, out = _run(world, with_sync=False, core=core_root)
    assert code == 2, out
    assert "no apply_prediff_cleaning() function found" in out


def test_a_missing_openstates_core_file_is_an_error(world, core_root):
    os.remove(os.path.join(core_root, CORE_TEXT_EXTRACT_RELPATH))
    code, out = _run(world, with_sync=False, core=core_root)
    assert code == 2 and "cannot read" in out


def test_the_real_text_extract_dispatch_agrees_with_the_real_manifest():
    """The real openstates-core checkout this workspace keeps locally (gitignored, same checkout
    text_extract.py's own cleaners live in) agrees with the real jurisdictions.yaml -- the exact
    comparison OPEN-462 found failing for ma/nc/al before this change. Skipped where that checkout
    isn't present (e.g. a CI pytest step, which doesn't check it out -- only the final drift-check
    shell step in validate-jurisdictions.yml does, with --require-openstates-core)."""
    core_path = os.path.join(HERE, "openstates-core")
    if not os.path.isdir(core_path):
        pytest.skip("no local openstates-core checkout (expected: this repo's own CI pytest step doesn't check it out)")
    out = io.StringIO()
    code = drift.main(["check", "--openstates-core-root", core_path], out)
    assert code == 0, out.getvalue()


# ---------------------------------------------------------------------------------------------------
# waf.profile vs. openstates-core's RESILIENCE_PROFILES (OPEN-464)
# ---------------------------------------------------------------------------------------------------

def test_waf_profile_agrees_with_resilience_profiles(world):
    code, out = _run(world, with_sync=False)
    assert code == 0, out


def test_a_cookie_provider_state_with_no_code_handler_is_drift(world):
    """AC: a state declared waf.profile: cookie_provider that no code handles fails the drift check."""
    text = open(world[2]).read()
    _write(world[2], text.replace("profile: none\n", "profile: cookie_provider\n", 1))
    code, out = _run(world, with_sync=False)
    assert code == 1
    assert "DRIFT waf.profile: openstates-core RESILIENCE_PROFILES" in out
    assert "in the manifest but not in openstates-core RESILIENCE_PROFILES" in out


def test_a_resilience_profile_the_manifest_does_not_declare_is_drift(world):
    """The reverse direction: code handles a state the manifest says has no WAF profile."""
    _edit(world, "openstates/utils/resilience_profiles.py", '"fl": "stub -- values are never inspected",',
          '"fl": "stub -- values are never inspected",\n    "us": "stub",', root="core")
    code, out = _run(world, with_sync=False)
    assert code == 1
    assert "in openstates-core RESILIENCE_PROFILES but not in the manifest: us" in out


def test_openstates_core_root_absent_prints_a_note_and_passes(world):
    code, out = _run(world, with_sync=False, with_core=False)
    assert code == 0, out
    assert "NOTE: openstates-core was not checked" in out


def test_two_definitions_of_resilience_profiles_are_ambiguous(world):
    _edit(world, "openstates/utils/resilience_profiles.py", 'RESILIENCE_PROFILES: dict = {',
          'RESILIENCE_PROFILES: dict = {"default": 1}\nRESILIENCE_PROFILES: dict = {', root="core")
    code, out = _run(world, with_sync=False)
    assert code == 2 and "exactly one module-level RESILIENCE_PROFILES" in out


def test_a_duplicate_key_in_resilience_profiles_is_an_error(world):
    _edit(world, "openstates/utils/resilience_profiles.py", '"fl": "stub -- values are never inspected",',
          '"fl": "stub -- values are never inspected",\n    "fl": "again",', root="core")
    code, out = _run(world, with_sync=False)
    assert code == 2 and "RESILIENCE_PROFILES has a duplicate key" in out


def test_a_non_string_key_in_resilience_profiles_is_an_error(world):
    _edit(world, "openstates/utils/resilience_profiles.py", '"fl": "stub -- values are never inspected",',
          '"fl": "stub -- values are never inspected",\n    1: "bad key",', root="core")
    code, out = _run(world, with_sync=False)
    assert code == 2 and "RESILIENCE_PROFILES has a key that is not a string literal" in out


def test_a_missing_resilience_profiles_file_is_an_error(world):
    os.remove(os.path.join(world[3], "openstates", "utils", "resilience_profiles.py"))
    code, out = _run(world, with_sync=False)
    assert code == 2 and "cannot read" in out


# ---------------------------------------------------------------------------------------------------

def test_matrix_lists_every_jurisdiction_and_feature(world):
    code, out = _run(world, with_sync=False, extra=["--matrix"])
    assert code == 0
    lines = out.strip().splitlines()
    assert lines[0].split()[0] == "code" and "embedding" in lines[0]
    rows = {l.split()[0]: l.split() for l in lines[1:]}  # by code: yaml.safe_dump sorts the fixture's keys
    assert set(rows) == {"fl", "us", "nc", "al"}
    assert rows["nc"][:3] == ["nc", "live", "yes"]  # code, status, archive
    assert rows["al"][1] == "paused"


def test_the_real_checked_in_files_agree_with_the_real_manifest():
    """This repo's own lists against its own manifest, today. (ddp-sync is checked in CI, where its checkout exists.)"""
    out = io.StringIO()
    code = drift.main(["check"], out)
    assert code == 0, out.getvalue()


@pytest.mark.skipif(
    not os.path.isfile(os.path.join(HERE, "openstates-core", "openstates", "utils", "resilience_profiles.py")),
    reason="openstates-core is a local dev checkout (private repo, not fetched by CI) -- OPEN-464",
)
def test_the_real_openstates_core_agrees_with_the_real_manifests_waf_profile():
    """waf.profile vs. RESILIENCE_PROFILES, when a real openstates-core checkout sits next to this repo
    (as it does on both dev checkouts per CLAUDE.md). Not run in CI today -- see check-jurisdiction-drift.py's
    module docstring and PRIMITIVES.md's WAF-decision catalog (OPEN-464)."""
    out = io.StringIO()
    code = drift.main(["check", "--openstates-core-root", os.path.join(HERE, "openstates-core")], out)
    assert code == 0, out.getvalue()


def test_the_real_manifest_enrolls_every_archived_jurisdiction_somewhere_visible():
    """The matrix is how today's gaps (NC on 2 of 6 feature lists, MA on 3, AL on 2) stay visible: it must
    cover every manifest entry, including paused al. Not pinned to today's exact code count -- adding a
    state to the manifest must not break this (OPEN-465) -- but the original eight (OPEN-318) must never
    silently drop off the matrix."""
    with open(os.path.join(HERE, "jurisdictions.yaml")) as f:
        manifest = yaml.safe_load(f)
    out = io.StringIO()
    assert drift.main(["check", "--matrix"], out) == 0
    codes = [l.split()[0] for l in out.getvalue().strip().splitlines()[1:]]
    assert set(manifest.keys()) == set(codes)
    assert {"us", "fl", "wa", "va", "mi", "ut", "az", "ma"} <= set(codes)


def test_deepcopy_of_the_fixture_manifest_still_agrees(world):
    assert copy.deepcopy(_manifest()) == _manifest()


# ---------------------------------------------------------------------------------------------------
# live values read from a host's environment (OPEN-330)
# ---------------------------------------------------------------------------------------------------

def test_a_live_value_that_agrees_passes_and_is_case_insensitive(world):
    code, out = _run(world, with_sync=False, extra=["--live", "broker-prod:DDP_OPENSTATES_JURISDICTIONS=FL, US ,nc"])
    assert code == 0, out


def test_a_live_value_missing_a_jurisdiction_is_drift_naming_where_it_was_read(world):
    code, out = _run(world, with_sync=False, extra=["--live", "broker-prod:DDP_OPENSTATES_JURISDICTIONS=FL,US"])
    assert code == 1, out
    assert "DRIFT enrollment.replica_routing: DDP_OPENSTATES_JURISDICTIONS on broker-prod" in out
    assert "in the manifest but not in DDP_OPENSTATES_JURISDICTIONS on broker-prod: nc" in out


def test_a_live_value_with_an_extra_jurisdiction_is_drift(world):
    code, out = _run(world, with_sync=False, extra=["--live", "broker-prod:DDP_OPENSTATES_JURISDICTIONS=FL,US,NC,AL"])
    assert code == 1
    assert "in DDP_OPENSTATES_JURISDICTIONS on broker-prod but not in the manifest: al" in out


def test_the_legbot_allowlist_is_checked_against_its_own_field(world):
    # al is paused and not on the legbot list; the fixture's other three are
    code, out = _run(world, with_sync=False, extra=["--live", "mac:LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST=fl,us,nc"])
    assert code == 0, out
    code, out = _run(world, with_sync=False, extra=["--live", "mac:LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST=fl,us"])
    assert code == 1 and "enrollment.legbot_replica" in out


def test_several_live_values_are_all_reported(world):
    code, out = _run(world, with_sync=False, extra=[
        "--live", "broker-prod:DDP_OPENSTATES_JURISDICTIONS=FL",
        "--live", "sync-ec2:DDP_OPENSTATES_JURISDICTIONS=US",
    ])
    assert code == 1 and out.count("DRIFT ") == 2


@pytest.mark.parametrize("bad", ["no-colon", "x:UNKNOWN_VAR=a", "x:DDP_OPENSTATES_JURISDICTIONS", ":DDP_OPENSTATES_JURISDICTIONS=a"])
def test_a_malformed_live_argument_is_an_error_not_a_pass(world, bad):
    code, out = _run(world, with_sync=False, extra=["--live", bad])
    assert code == 2 and "--live" in out


def test_an_empty_live_value_is_a_real_empty_list_and_drifts(world):
    code, out = _run(world, with_sync=False, extra=["--live", "broker-prod:DDP_OPENSTATES_JURISDICTIONS="])
    assert code == 1 and "in the manifest but not in DDP_OPENSTATES_JURISDICTIONS on broker-prod: fl, nc, us" in out


# ---------------------------------------------------------------------------------------------------
# OPEN-521: ddp-sync keeps no list of who is scraped; its openstates_scrape.timing may only name scraped states
# ---------------------------------------------------------------------------------------------------

def _set_status(world, code, status):
    data = yaml.safe_load(open(world[2]))
    data[code]["status"] = status
    _write(world[2], yaml.safe_dump(data))


def _add_timing(world, sync_code):
    _set_sync_yaml(world, lambda d: d["openstates_scrape"]["timing"].update({sync_code: {"floor": "nightly", "start_utc": "04:00"}}))


def test_timing_for_a_paused_state_is_drift(world):
    _add_timing(world, "al")
    code, out = _run(world)
    assert code == 1, out
    assert "DRIFT status: ddp-sync openstates_scrape.timing" in out and "does not scrape" in out and ": al" in out


@pytest.mark.parametrize("status", ["probing", "paused"])
def test_pausing_a_state_that_still_has_timing_is_drift(world, status):
    """The manifest change that stops a state being scraped must remove its timing in ddp-sync too: fl has an entry."""
    _set_status(world, "fl", status)
    code, out = _run(world)
    assert code == 1, out
    assert "does not scrape" in out and ": fl" in out


def test_timing_for_a_state_not_in_the_manifest_is_drift(world):
    _add_timing(world, "ca")
    code, out = _run(world)
    assert code == 1 and ": ca" in out


def test_ddp_sync_usa_timing_is_the_manifests_us(world):
    """The fixture's timing names "usa"; it must match the manifest's "us", not be reported as an unknown state."""
    code, out = _run(world)
    assert code == 0, out
    _set_status(world, "us", "paused")
    code, out = _run(world)
    assert code == 1 and ": us" in out


@pytest.mark.parametrize("status", ["scraping", "validating", "archived", "live"])
def test_a_scraped_state_with_no_timing_entry_needs_no_ddp_sync_edit(world, status):
    """nc has no timing entry (ddp-sync's defaults apply); moving it through every scraped status is no drift."""
    _set_status(world, "nc", status)
    code, out = _run(world)
    assert code == 0, out


def test_the_projection_scrapes_every_status_but_probing_and_paused():
    manifest = {code: _entry(status=status) for code, status in
                [("a", "probing"), ("b", "scraping"), ("c", "validating"), ("d", "archived"), ("e", "live"), ("f", "paused")]}
    assert drift.project(manifest)["scraped"] == {"b", "c", "d", "e"}


# ---------------------------------------------------------------------------------------------------
# OPEN-478/479/480: a probing state (Stage 0) is not scraped yet; from Stage 2 (`scraping`) it is, with no ddp-sync edit
# ---------------------------------------------------------------------------------------------------

def _add_pilot_state(world, status):
    """A brand-new state as `new-jurisdiction` writes it: every enrollment flag off, archive off."""
    manifest_path = world[2]
    data = yaml.safe_load(open(manifest_path))
    # Past probing the validator requires people_refresh and archive.enabled: advance-jurisdiction sets them.
    # Everything else is still off, as `new-jurisdiction` writes it.
    past_probing = status != "probing"
    e = _entry(status=status, archive=past_probing, people_refresh=past_probing,
               search_refresh=False, embedding=False, cloud_path=False, api_smoke_test=False, qa_sweep=False,
               replica_routing=False, legbot_replica=False)
    e["name"] = "Pennsylvania"
    data["pa"] = e
    _write(manifest_path, yaml.safe_dump(data))


@pytest.mark.parametrize("status", ["probing", "scraping", "live"])
def test_a_new_state_needs_no_ddp_sync_list_at_any_status(world, status):
    _add_pilot_state(world, status)
    code, out = _run(world)
    assert code == 0, out


def test_a_new_state_with_its_own_timing_passes_once_scraped_and_drifts_while_probing(world):
    _add_pilot_state(world, "scraping")
    _add_timing(world, "pa")
    assert _run(world)[0] == 0
    _set_status(world, "pa", "probing")
    code, out = _run(world)
    assert code == 1 and ": pa" in out


def test_the_matrix_has_no_tier_or_scheduled_column(world):
    code, out = _run(world, with_sync=False, extra=["--matrix"])
    assert code == 0
    header = out.strip().splitlines()[0].split()
    assert "archive" in header and "tier" not in header and "scheduled" not in header


def test_the_matrix_shows_newest_first_and_no_creator_id(world):
    # BROKER-368: newest_first is visible in the matrix; BROKER-482: the Voatz creator id is private, not in the manifest.
    code, out = _run(world, with_sync=False, extra=["--matrix"])
    assert code == 0
    header = out.strip().splitlines()[0].split()
    assert header[-1] == "newest_first" and "voatz_creator" not in header


def test_after_sync_157_the_deleted_timeout_tables_are_skipped(world):
    """SYNC-157: ddp-sync reads scrape/archive.timeout_s from the manifest and deletes SCRAPE_/ARCHIVE_TIMEOUT_S."""
    _set_sync_yaml(world, _after_sync_157)
    for rel in ("scrape", "archive"):
        _write(os.path.join(world[1], "src", "ddp_sync", "pipelines", f"openstates_{rel}.py"),
               "DEFAULT_TIMEOUT_S = 6 * 3600  # the per-state ceilings are the manifest's\n")
    code, out = _run(world)
    assert code == 0, out
