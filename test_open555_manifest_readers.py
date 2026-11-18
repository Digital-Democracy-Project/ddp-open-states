"""OPEN-555 (PLAN-state-specific-handling Phase 4): this repo's readers of the manifest's `scraper_module` and `ocd_id`.

Each reader takes the field from the manifest and falls back to the table or rule it used before (deleted only at step
4, after both hosts and the scrapers image carry the fields). Each case below checks the reader returns today's value
with the field present, with no manifest, and for a code the manifest has no entry for; and that it really reads the
field (a manifest with a different value changes the answer).
"""
import copy
import importlib.machinery
import importlib.util
import os

import pytest
import yaml

import qa_primitives
from validate_jurisdictions import DEFAULT_MANIFEST_PATH, code_for_scraper_module, scraper_module_for

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_script(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), os.path.join(HERE, name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def manifest():
    with open(DEFAULT_MANIFEST_PATH) as fh:
        return yaml.safe_load(fh)


def _codes(manifest):
    return list(manifest) + ["zz"]  # "zz": a code with no entry (a probe candidate)


# today's rule, written out by hand (the tables each reader keeps as its fallback)
def _module_today(code):
    return "usa" if code == "us" else code


def _code_today(module):
    return "us" if module == "usa" else module


def test_scraper_module_for_is_unchanged_with_without_and_with_no_entry(manifest):
    for code in _codes(manifest):
        assert scraper_module_for(code, manifest, {"us": "usa"}) == _module_today(code)
        assert scraper_module_for(code, None, {"us": "usa"}) == _module_today(code)
        assert scraper_module_for(code, {}, {"us": "usa"}) == _module_today(code)


def test_code_for_scraper_module_is_unchanged_with_without_and_with_no_entry(manifest):
    for module in ["usa", "us", "fl", "pa", "zz"]:
        assert code_for_scraper_module(module, manifest, {"usa": "us"}) == _code_today(module)
        assert code_for_scraper_module(module, None, {"usa": "us"}) == _code_today(module)
        assert code_for_scraper_module(module, {}, {"usa": "us"}) == _code_today(module)


def test_the_module_readers_read_the_manifest(manifest):
    changed = copy.deepcopy(manifest)
    changed["us"]["scraper_module"] = "congress"
    assert scraper_module_for("us", changed, {"us": "usa"}) == "congress"
    assert code_for_scraper_module("congress", changed, {"usa": "us"}) == "us"
    # an entry with no scraper_module (a manifest from before OPEN-555) falls back
    del changed["us"]["scraper_module"]
    assert scraper_module_for("us", changed, {"us": "usa"}) == "usa"
    assert code_for_scraper_module("usa", changed, {"usa": "us"}) == "us"


def _ocd_today(code):
    divisions = {"dc": "district:dc", "pr": "territory:pr"}
    if code == "us":
        return "ocd-jurisdiction/country:us/government"
    return f"ocd-jurisdiction/country:us/{divisions.get(code, f'state:{code}')}/government"


@pytest.fixture
def ocd_from(monkeypatch, tmp_path):
    def use(text):
        path = tmp_path / "jurisdictions.yaml"
        if text is not None:
            path.write_text(text)
        monkeypatch.setattr(qa_primitives, "MANIFEST_PATH", str(path))
        qa_primitives._manifest_ocd_ids.cache_clear()

    yield use
    qa_primitives._manifest_ocd_ids.cache_clear()


def test_ocd_id_is_unchanged_with_without_and_with_no_entry(ocd_from, manifest):
    codes = _codes(manifest) + ["dc", "pr"]
    with open(DEFAULT_MANIFEST_PATH) as fh:
        real = fh.read()
    for text in (real, None, "not: [a, manifest"):  # the real manifest, no file, a file that does not load
        ocd_from(text)
        assert {c: qa_primitives.ocd_jurisdiction_id(c) for c in codes} == {c: _ocd_today(c) for c in codes}


def test_ocd_id_reads_the_manifest(ocd_from, manifest):
    changed = copy.deepcopy(manifest)
    changed["fl"]["ocd_id"] = "ocd-jurisdiction/country:us/state:fx/government"
    ocd_from(yaml.safe_dump(changed))
    assert qa_primitives.ocd_jurisdiction_id("fl") == "ocd-jurisdiction/country:us/state:fx/government"
    assert qa_primitives.ocd_jurisdiction_id("pa") == _ocd_today("pa")


def test_verify_jurisdiction_scraper_module_name(manifest):
    verify = _load_script("verify-jurisdiction")
    for code in _codes(manifest):
        assert verify.scraper_module_name(code, manifest) == _module_today(code)
        assert verify.scraper_module_name(code) == _module_today(code)


def test_probe_on_fargate_maps_module_names_to_codes(manifest):
    probe = _load_script("probe-on-fargate")
    assert probe.normalize_states(["USA", "fl", "us", "Fl"], manifest) == ["us", "fl"]
    assert probe.normalize_states(["USA", "fl", "us", "Fl"]) == ["us", "fl"]


def test_cloud_collector_finds_the_us_entry_for_the_usa_scraper(tmp_path, manifest):
    import cloud_collector

    assert cloud_collector._manifest_scrape_entry("usa") == manifest["us"]["scrape"]
    assert cloud_collector._manifest_scrape_entry("fl") == manifest["fl"]["scrape"]
    assert cloud_collector._manifest_scrape_entry("zz") is None
    changed = copy.deepcopy(manifest)
    changed["us"]["scraper_module"] = "congress"
    path = tmp_path / "jurisdictions.yaml"
    path.write_text(yaml.safe_dump(changed))
    assert cloud_collector._manifest_scrape_entry("congress", str(path)) == manifest["us"]["scrape"]
