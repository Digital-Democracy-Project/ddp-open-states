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
# the fixture world: fl (primary), us (primary, "usa" in ddp-sync), nc (secondary), al (paused)
# ---------------------------------------------------------------------------------------------------

def _entry(tier="secondary", status="live", archive=True, scheduled=None, **enrollment):
    e = _valid_entry()
    e["tier"], e["status"] = tier, status
    e["archive"]["enabled"] = archive
    e["archive"]["scheduled"] = archive if scheduled is None else scheduled
    e["enrollment"].update({k: v for k, v in enrollment.items()})
    return e


def _manifest():
    fl = _entry("primary", people_refresh=True, search_refresh=True, embedding=True, cloud_path=True, api_smoke_test=True, qa_sweep=True)
    fl["scrape"]["allow_duplicates"] = True
    fl["scrape"]["timeout_s"] = 16 * 3600
    fl["archive"]["timeout_s"] = 16 * 3600
    us = _entry("primary", people_refresh=True, search_refresh=True, embedding=True, cloud_path=True, api_smoke_test=True, qa_sweep=False)
    us["scrape"]["timeout_s"] = 4 * 3600
    us["archive"]["timeout_s"] = 24 * 3600
    nc = _entry("secondary", people_refresh=False, search_refresh=True, embedding=False, cloud_path=True, api_smoke_test=False, qa_sweep=False, replica_routing=True)
    # OPEN-462: fl/us keep the default "Test State" name (no branch in CORE_TEXT_EXTRACT_PY below, so
    # their expected diff_cleaner is "none"); nc/al get real display names so the fixture dispatch
    # below (keyed on those exact strings, like the real one) has something to match against.
    nc["name"] = "North Carolina"
    nc["quality"]["diff_cleaner"] = "clean_nc_text"
    al = _entry("secondary", status="paused", people_refresh=True, search_refresh=False, embedding=False, cloud_path=False, api_smoke_test=False, qa_sweep=True, replica_routing=False, legbot_replica=False)
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

SYNC_YAML = {
    "openstates_archive": {
        "jurisdictions": ["fl", "us", "nc", "al"],
        "schedule": {"fl": "monday", "us": "sunday", "nc": "thursday", "al": "saturday"},
        "knowledge_base_embedding": {"jurisdictions": ["fl", "us"]},
        "bill_search_refresh": {"jurisdictions": ["us", "fl", "nc"]},
    },
    "openstates_scrape": {
        "primary": {"fl": {"enabled": True}, "usa": {"enabled": True}},
        "secondary": {"jurisdictions": ["nc"]},
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


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


@pytest.fixture
def world(tmp_path):
    """(repo_root, sync_root, manifest_path): every list agrees with the manifest."""
    repo, sync = tmp_path / "repo", tmp_path / "ddp-sync"
    for name, text in REPO_FILES.items():
        _write(str(repo / name), text)
    _write(str(sync / "config" / "sync_schedule.yaml"), yaml.safe_dump(SYNC_YAML))
    _write(str(sync / "src/ddp_sync/pipelines/openstates_scrape.py"), SYNC_SCRAPE_PY)
    _write(str(sync / "src/ddp_sync/pipelines/openstates_archive.py"), SYNC_ARCHIVE_PY)
    manifest = tmp_path / "jurisdictions.yaml"
    manifest.write_text(yaml.safe_dump(_manifest()))
    return str(repo), str(sync), str(manifest)


@pytest.fixture
def core_root(tmp_path):
    """openstates-core stand-in: agrees with the fixture manifest's nc/al out of the box."""
    core = tmp_path / "openstates-core"
    _write(str(core / CORE_TEXT_EXTRACT_RELPATH), CORE_TEXT_EXTRACT_PY)
    return str(core)


def _run(world, with_sync=True, extra=(), core=None):
    repo, sync, manifest = world
    argv = ["check", "--manifest", manifest, "--repo-root", repo, *extra]
    if with_sync:
        argv += ["--ddp-sync-root", sync]
    if core:
        argv += ["--openstates-core-root", core]
    out = io.StringIO()
    return drift.main(argv, out), out.getvalue()


def _edit(world, relpath, old, new, root="repo"):
    base = world[0] if root == "repo" else world[1]
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
    _set_sync_yaml(world, lambda d: d["openstates_archive"]["jurisdictions"].remove("nc"))
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


def test_a_primary_entry_that_is_not_a_mapping_with_enabled_is_an_error(world):
    _set_sync_yaml(world, lambda d: d["openstates_scrape"]["primary"].update({"usa": True}))
    code, out = _run(world)
    assert code == 2 and "openstates_scrape.primary.usa" in out


def test_a_missing_memory_backend_list_is_an_error_not_an_empty_floor(world):
    _set_sync_yaml(world, lambda d: d["openstates_scrape"]["cloud_path"].pop("memory_backend_jurisdictions"))
    code, out = _run(world)
    assert code == 2 and "memory_backend_jurisdictions" in out


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
    code, out = _run(world, with_sync=False)
    assert code == 0
    assert "openstates-core was not checked" in out


def test_require_openstates_core_without_a_checkout_is_an_error(world):
    code, out = _run(world, with_sync=False, extra=["--require-openstates-core"])
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

def test_matrix_lists_every_jurisdiction_and_feature(world):
    code, out = _run(world, with_sync=False, extra=["--matrix"])
    assert code == 0
    lines = out.strip().splitlines()
    assert lines[0].split()[0] == "code" and "embedding" in lines[0]
    rows = {l.split()[0]: l.split() for l in lines[1:]}  # by code: yaml.safe_dump sorts the fixture's keys
    assert set(rows) == {"fl", "us", "nc", "al"}
    assert rows["nc"][:3] == ["nc", "live", "secondary"]
    assert rows["al"][1] == "paused"


def test_the_real_checked_in_files_agree_with_the_real_manifest():
    """This repo's own lists against its own manifest, today. (ddp-sync is checked in CI, where its checkout exists.)"""
    out = io.StringIO()
    code = drift.main(["check"], out)
    assert code == 0, out.getvalue()


def test_the_real_manifest_enrolls_every_archived_jurisdiction_somewhere_visible():
    """The matrix is how today's gaps (NC on 2 of 6 feature lists, MA on 3, AL on 2) stay visible: it must
    cover every manifest entry, including paused al."""
    out = io.StringIO()
    assert drift.main(["check", "--matrix"], out) == 0
    codes = [l.split()[0] for l in out.getvalue().strip().splitlines()[1:]]
    assert {"us", "fl", "wa", "va", "mi", "ut", "az", "ma", "nc", "al"} == set(codes)


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
# OPEN-418: ddp-sync's recurring archive list is compared with archive.scheduled, not archive.enabled
# ---------------------------------------------------------------------------------------------------

def _make_nc_stage_4(world):
    """nc is mid-pilot: enabled for the manual validation run, validating, NOT on the recurring schedule."""
    manifest_path = world[2]
    data = yaml.safe_load(open(manifest_path))
    data["nc"]["status"] = "validating"
    data["nc"]["archive"]["scheduled"] = False
    _write(manifest_path, yaml.safe_dump(data))


def test_a_stage_4_state_enabled_but_not_scheduled_passes_when_it_is_off_the_ddp_sync_list(world):
    _make_nc_stage_4(world)
    _set_sync_yaml(world, lambda d: (d["openstates_archive"]["jurisdictions"].remove("nc"),
                                     d["openstates_archive"]["schedule"].pop("nc")))
    code, out = _run(world)
    assert code == 0, out


def test_a_stage_4_state_that_is_on_the_ddp_sync_archive_list_is_drift(world):
    """The whole point of OPEN-418: being on the recurring schedule before `live` is now reported."""
    _make_nc_stage_4(world)
    code, out = _run(world)
    assert code == 1, out
    assert "DRIFT archive.scheduled: ddp-sync openstates_archive.jurisdictions" in out
    assert "in ddp-sync openstates_archive.jurisdictions but not in the manifest: nc" in out
    assert "DRIFT archive.scheduled: ddp-sync openstates_archive.schedule (keys)" in out


def test_the_shell_gate_still_follows_archive_enabled_not_scheduled(world):
    """activate.sh's list derives from archive.enabled, so the Stage 4 state is still in it."""
    _make_nc_stage_4(world)
    _set_sync_yaml(world, lambda d: (d["openstates_archive"]["jurisdictions"].remove("nc"),
                                     d["openstates_archive"]["schedule"].pop("nc")))
    manifest = yaml.safe_load(open(world[2]))
    assert manifest["nc"]["archive"]["enabled"] is True
    assert drift.project(manifest)["archive"] >= {"nc"} and "nc" not in drift.project(manifest)["archive_scheduled"]


def test_the_matrix_shows_the_scheduled_column(world):
    code, out = _run(world, with_sync=False, extra=["--matrix"])
    assert code == 0
    header = out.strip().splitlines()[0].split()
    assert "archive" in header and "scheduled" in header
