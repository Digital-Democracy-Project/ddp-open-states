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

def _entry(tier="secondary", status="live", archive=True, **enrollment):
    e = _valid_entry()
    e["tier"], e["status"] = tier, status
    e["archive"]["enabled"] = archive
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
    nc = _entry("secondary", people_refresh=False, search_refresh=True, embedding=False, cloud_path=True, api_smoke_test=False, qa_sweep=False)
    al = _entry("secondary", status="paused", people_refresh=True, search_refresh=False, embedding=False, cloud_path=False, api_smoke_test=False, qa_sweep=True)
    return {"fl": fl, "us": us, "nc": nc, "al": al}


REPO_FILES = {
    "activate.sh": 'export ARCHIVE_ENABLED_STATES="fl,us,nc,al"\n',
    "run-people-refresh.sh": "for state in fl us al; do\n    echo $state\ndone\n",
    "start-os-api.sh": "for j in fl us; do\n    echo $j\ndone\n",
    "quality_check.py": 'JURISDICTIONS = ["fl", "al"]\n',
    "run-scrape.sh": 'ALLOW_DUPLICATES_STATES="fl"\n',
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


def _run(world, with_sync=True, extra=()):
    repo, sync, manifest = world
    argv = ["check", "--manifest", manifest, "--repo-root", repo, *extra]
    if with_sync:
        argv += ["--ddp-sync-root", sync]
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
# this repo's lists: break each one
# ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "relpath,old,new,field,source,detail",
    [
        ("activate.sh", "fl,us,nc,al", "fl,us,al", "archive.enabled", "activate.sh ARCHIVE_ENABLED_STATES", "in the manifest but not in activate.sh ARCHIVE_ENABLED_STATES: nc"),
        ("run-people-refresh.sh", "fl us al", "fl us al nc", "enrollment.people_refresh", "run-people-refresh.sh", "but not in the manifest: nc"),
        ("start-os-api.sh", "fl us", "fl", "enrollment.api_smoke_test", "start-os-api.sh", "in the manifest but not in start-os-api.sh boot smoke-test `for j in`: us"),
        ("quality_check.py", '["fl", "al"]', '["fl", "al", "nc"]', "enrollment.qa_sweep", "quality_check.py JURISDICTIONS", "but not in the manifest: nc"),
        ("run-scrape.sh", '"fl"', '"fl,nc"', "scrape.allow_duplicates", "run-scrape.sh ALLOW_DUPLICATES_STATES", "but not in the manifest: nc"),
    ],
)
def test_each_repo_list_that_disagrees_is_named_with_both_sides(world, relpath, old, new, field, source, detail):
    _edit(world, relpath, old, new)
    code, out = _run(world, with_sync=False)
    assert code == 1, out
    assert f"DRIFT {field}: {source}" in out
    assert detail in out


def test_several_disagreements_are_all_reported_in_one_pass(world):
    _edit(world, "activate.sh", "fl,us,nc,al", "fl")
    _edit(world, "run-people-refresh.sh", "fl us al", "fl")
    code, out = _run(world, with_sync=False)
    assert code == 1
    assert out.count("DRIFT ") == 2 and "2 list(s) disagree" in out


# ---------------------------------------------------------------------------------------------------
# a source that cannot be read is an ERROR, never a pass
# ---------------------------------------------------------------------------------------------------

def test_a_missing_pattern_is_an_error(world):
    _edit(world, "activate.sh", "ARCHIVE_ENABLED_STATES", "ARCHIVE_ENABLED_STATEZ")
    code, out = _run(world, with_sync=False)
    assert code == 2 and "expected exactly one" in out


def test_an_ambiguous_pattern_is_an_error(world):
    _edit(world, "activate.sh", 'export ARCHIVE_ENABLED_STATES="fl,us,nc,al"\n',
          'export ARCHIVE_ENABLED_STATES="fl,us,nc,al"\nexport ARCHIVE_ENABLED_STATES="fl"\n')
    code, out = _run(world, with_sync=False)
    assert code == 2 and "found 2" in out


def test_a_commented_out_assignment_is_not_the_assignment(world):
    """The real one is on the next line; a commented decoy above it must be ignored, not matched or counted."""
    _edit(world, "activate.sh", 'export ARCHIVE_ENABLED_STATES="fl,us,nc,al"\n',
          '# export ARCHIVE_ENABLED_STATES="fl"\nexport ARCHIVE_ENABLED_STATES="fl,us,nc,al"\n')
    code, out = _run(world, with_sync=False)
    assert code == 0, out


def test_a_similarly_named_variable_is_not_the_assignment(world):
    _edit(world, "activate.sh", 'export ARCHIVE_ENABLED_STATES="fl,us,nc,al"\n',
          'export ARCHIVE_ENABLED_STATES_OLD="fl"\nexport ARCHIVE_ENABLED_STATES="fl,us,nc,al"\n')
    code, out = _run(world, with_sync=False)
    assert code == 0, out


def test_an_indented_or_commented_loop_is_not_the_loop_but_a_second_top_level_one_is_ambiguous(world):
    _edit(world, "run-people-refresh.sh", "for state in fl us al; do",
          "# for state in fl; do\nif true; then\n    for state in nc; do :; done\nfi\nfor state in fl us al; do")
    code, out = _run(world, with_sync=False)
    assert code == 0, out
    _edit(world, "run-people-refresh.sh", "if true; then", "for state in nc; do :; done\nif true; then")
    code, out = _run(world, with_sync=False)
    assert code == 2 and "found 2" in out


def test_two_definitions_of_a_python_list_are_ambiguous_not_last_wins(world):
    _edit(world, "quality_check.py", 'JURISDICTIONS = ["fl", "al"]\n', 'JURISDICTIONS = ["fl", "al"]\nJURISDICTIONS = ["fl"]\n')
    code, out = _run(world, with_sync=False)
    assert code == 2 and "exactly one module-level JURISDICTIONS" in out


def test_a_decoy_name_in_a_python_file_is_not_the_list(world):
    _edit(world, "quality_check.py", 'JURISDICTIONS = ["fl", "al"]\n', 'JURISDICTIONS_LEGACY = ["fl"]\nJURISDICTIONS = ["fl", "al"]\n')
    code, out = _run(world, with_sync=False)
    assert code == 0, out


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


def test_a_non_literal_python_list_is_an_error(world):
    _edit(world, "quality_check.py", '["fl", "al"]', "load_list()")
    code, out = _run(world, with_sync=False)
    assert code == 2 and "quality_check.py" in out


def test_an_invalid_manifest_is_an_error_not_a_pass(world):
    open(world[2], "w").write("fl: {name: x}\n")
    code, out = _run(world, with_sync=False)
    assert code == 2 and "does not validate" in out


# ---------------------------------------------------------------------------------------------------
# ddp-sync's lists
# ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "mutate,field,source",
    [
        (lambda d: d["openstates_archive"]["jurisdictions"].remove("nc"), "archive.enabled", "ddp-sync openstates_archive.jurisdictions"),
        (lambda d: d["openstates_archive"]["schedule"].pop("al"), "archive.enabled", "ddp-sync openstates_archive.schedule (keys)"),
        (lambda d: d["openstates_archive"]["knowledge_base_embedding"]["jurisdictions"].append("nc"), "enrollment.embedding", "ddp-sync ...knowledge_base_embedding.jurisdictions"),
        (lambda d: d["openstates_archive"]["bill_search_refresh"]["jurisdictions"].remove("nc"), "enrollment.search_refresh", "ddp-sync ...bill_search_refresh.jurisdictions"),
        (lambda d: d["openstates_scrape"]["secondary"]["jurisdictions"].append("al"), "tier: secondary", "ddp-sync openstates_scrape.secondary.jurisdictions"),
        (lambda d: d["openstates_scrape"]["primary"].pop("fl"), "tier: primary", "ddp-sync openstates_scrape.primary (enabled)"),
        (lambda d: d["openstates_scrape"]["cloud_path"]["jurisdictions"].remove("nc"), "enrollment.cloud_path", "ddp-sync openstates_scrape.cloud_path.jurisdictions"),
    ],
)
def test_each_ddp_sync_list_that_disagrees_is_named(world, mutate, field, source):
    _set_sync_yaml(world, mutate)
    code, out = _run(world)
    assert code == 1, out
    assert f"DRIFT {field}: {source}" in out


def test_us_is_usa_in_ddp_sync_and_that_is_not_drift(world):
    """The fixture's cloud_path and primary lists say \"usa\" for the manifest's \"us\": it must map, not flag."""
    code, out = _run(world)
    assert code == 0 and "usa" not in out


def test_a_paused_jurisdiction_is_expected_on_no_scrape_list(world):
    """al is paused with tier secondary: it must NOT be required on ddp-sync's secondary list."""
    code, out = _run(world)
    assert code == 0, out


def test_the_memory_backend_floor_must_contain_the_cloud_path_set(world):
    _set_sync_yaml(world, lambda d: d["openstates_scrape"]["cloud_path"]["memory_backend_jurisdictions"].remove("nc"))
    code, out = _run(world)
    assert code == 1
    assert "missing from the memory_backend floor: nc" in out


def test_a_memory_backend_floor_larger_than_cloud_path_is_fine(world):
    """The floor never shrinks on rollback (its own comment): a jurisdiction rolled back to the Mac stays on it."""
    _set_sync_yaml(world, lambda d: d["openstates_scrape"]["cloud_path"]["memory_backend_jurisdictions"].append("al"))
    code, out = _run(world)
    assert code == 0, out


def test_a_manifest_timeout_that_differs_from_ddp_sync_is_named_per_jurisdiction(world):
    _edit(world, "src/ddp_sync/pipelines/openstates_archive.py", '"us": 24 * 3600', '"us": 12 * 3600', root="sync")
    code, out = _run(world)
    assert code == 1
    assert "DRIFT archive.timeout_s" in out
    assert "us: manifest 86400s, ddp-sync ARCHIVE_TIMEOUT_S 43200s" in out


def test_a_jurisdiction_with_no_timeout_entry_gets_ddp_syncs_default_so_the_manifest_must_say_so(world):
    """nc has no entry in either table: ddp-sync gives it the default, and the manifest has to agree."""
    m = _manifest()
    m["nc"]["scrape"]["timeout_s"] = 99
    open(world[2], "w").write(yaml.safe_dump(m))
    code, out = _run(world)
    assert code == 1
    assert "nc: manifest 99s, ddp-sync SCRAPE_TIMEOUT_S 21600s" in out


def test_a_timeout_table_with_no_default_is_an_error(world):
    _edit(world, "src/ddp_sync/pipelines/openstates_scrape.py", '    "default": 6 * 3600,\n', "", root="sync")
    code, out = _run(world)
    assert code == 2 and 'no "default"' in out


def test_a_missing_ddp_sync_yaml_key_is_an_error(world):
    _set_sync_yaml(world, lambda d: d["openstates_archive"].pop("bill_search_refresh"))
    code, out = _run(world)
    assert code == 2 and "bill_search_refresh" in out


# ---------------------------------------------------------------------------------------------------
# the matrix, and the real files
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
