"""
Tests for deploy/sync-manifest.sh and the compose mounts it serves (OPEN-483). Real bash against temp directories,
no docker. The mount behaviour itself (single-file mount keeps the old inode after a `git pull`, a directory mount
does not) was proven with a real container on native Linux Docker on 2026-11-03 and is recorded in RUNBOOK.md.
"""
import os
import shutil
import subprocess
import time

import pytest
import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(_HERE, "deploy", "sync-manifest.sh")


def _run(src, dest_dir, *args):
    env = dict(os.environ, MANIFEST_SOURCE=str(src), MANIFEST_DEST_DIR=str(dest_dir))
    return subprocess.run(["bash", SCRIPT, *args], env=env, capture_output=True, text=True)


def test_creates_the_directory_and_copies_the_file_with_its_modification_time(tmp_path):
    src = tmp_path / "jurisdictions.yaml"
    src.write_text("nc:\n  name: North Carolina\n")
    old = time.time() - 86400
    os.utime(src, (old, old))
    dest_dir = tmp_path / "deploy" / "manifest"
    r = _run(src, dest_dir)
    assert r.returncode == 0, r.stderr
    dest = dest_dir / "jurisdictions.yaml"
    assert dest.read_text() == src.read_text()
    assert int(dest.stat().st_mtime) == int(src.stat().st_mtime)  # /ddp/enrollment's manifest_mtime equals the checkout's
    assert [p.name for p in dest_dir.iterdir()] == ["jurisdictions.yaml"]  # no temp file left behind


def test_a_changed_source_replaces_the_copy_as_a_new_file(tmp_path):
    """Like `git pull`: the copy is replaced by rename, so a DIRECTORY mount (the whole point) sees the new inode."""
    src = tmp_path / "jurisdictions.yaml"
    dest_dir = tmp_path / "manifest"
    src.write_text("v1\n")
    assert _run(src, dest_dir).returncode == 0
    first = (dest_dir / "jurisdictions.yaml").stat().st_ino
    src.write_text("v2 is longer\n")
    assert _run(src, dest_dir).returncode == 0
    assert (dest_dir / "jurisdictions.yaml").read_text() == "v2 is longer\n"
    assert (dest_dir / "jurisdictions.yaml").stat().st_ino != first


@pytest.mark.parametrize("make_source", ["missing", "empty"])
def test_a_missing_or_empty_source_leaves_the_existing_copy_untouched(tmp_path, make_source):
    dest_dir = tmp_path / "manifest"
    dest_dir.mkdir()
    (dest_dir / "jurisdictions.yaml").write_text("good copy\n")
    src = tmp_path / "jurisdictions.yaml"
    if make_source == "empty":
        src.write_text("")
    r = _run(src, dest_dir)
    assert r.returncode == 1 and "STOP" in r.stderr
    assert (dest_dir / "jurisdictions.yaml").read_text() == "good copy\n"


def test_check_mode_reports_differences_and_changes_nothing(tmp_path):
    src = tmp_path / "jurisdictions.yaml"
    dest_dir = tmp_path / "manifest"
    src.write_text("v1\n")
    r = _run(src, dest_dir, "--check")
    assert r.returncode == 1 and "no copy" in r.stdout and not dest_dir.exists()
    assert _run(src, dest_dir).returncode == 0
    ok = _run(src, dest_dir, "--check")
    assert ok.returncode == 0 and ok.stdout.startswith("OK")
    src.write_text("v2\n")
    stale = _run(src, dest_dir, "--check")
    assert stale.returncode == 1 and stale.stdout.startswith("DIFFERS")
    assert (dest_dir / "jurisdictions.yaml").read_text() == "v1\n"  # --check never repairs


def test_it_touches_nothing_but_its_own_directory(tmp_path):
    src = tmp_path / "jurisdictions.yaml"
    src.write_text("v1\n")
    (tmp_path / ".env").write_text("SECRET=1\n")
    dest_dir = tmp_path / "manifest"
    assert _run(src, dest_dir).returncode == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == [".env", "jurisdictions.yaml", "manifest"]
    assert (tmp_path / ".env").read_text() == "SECRET=1\n"
    assert not any(c in os.listdir(dest_dir) for c in (".env",))


@pytest.mark.parametrize("name", ["ddp", "rds"])
def test_both_compose_files_mount_the_directory_not_the_file_and_never_the_checkout(name):
    api = yaml.safe_load(open(os.path.join(_HERE, "deploy", f"docker-compose.{name}.yml")))["services"]["api"]
    mounts = api["volumes"]
    assert "./manifest:/app/manifest:ro" in mounts
    for m in mounts:
        host = m.split(":")[0]
        assert not host.endswith("jurisdictions.yaml"), f"single-file mount is back: {m}"
        assert host not in ("..", "../", ".", "./"), f"the whole checkout would be mounted: {m}"
    assert api["environment"]["DDP_JURISDICTIONS_MANIFEST"] == "/app/manifest/jurisdictions.yaml"


def test_the_copy_directory_is_not_committed():
    assert "deploy/manifest/" in open(os.path.join(_HERE, ".gitignore")).read()


def test_changed_content_with_the_same_modification_time_still_gets_a_new_one(tmp_path):
    """api-v3 reloads only when the copy's mtime changes: a changed file must never keep the old copy's time."""
    src = tmp_path / "jurisdictions.yaml"
    dest_dir = tmp_path / "manifest"
    src.write_text("v1\n")
    pinned = time.time() - 86400
    os.utime(src, (pinned, pinned))
    assert _run(src, dest_dir).returncode == 0
    before = (dest_dir / "jurisdictions.yaml").stat().st_mtime
    src.write_text("v2 different content\n")
    os.utime(src, (pinned, pinned))  # same time as the copy it replaces
    assert _run(src, dest_dir).returncode == 0
    after = (dest_dir / "jurisdictions.yaml").stat().st_mtime
    assert (dest_dir / "jurisdictions.yaml").read_text() == "v2 different content\n"
    assert after != before


def test_identical_content_keeps_the_source_time(tmp_path):
    src = tmp_path / "jurisdictions.yaml"
    dest_dir = tmp_path / "manifest"
    src.write_text("v1\n")
    pinned = time.time() - 86400
    os.utime(src, (pinned, pinned))
    assert _run(src, dest_dir).returncode == 0
    assert _run(src, dest_dir).returncode == 0
    assert int((dest_dir / "jurisdictions.yaml").stat().st_mtime) == int(pinned)


def test_refuses_a_symlinked_directory_and_a_destination_that_is_a_directory(tmp_path):
    src = tmp_path / "jurisdictions.yaml"
    src.write_text("v1\n")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    link = tmp_path / "manifest"
    link.symlink_to(elsewhere)
    r = _run(src, link)
    assert r.returncode == 1 and "symlink" in r.stderr and list(elsewhere.iterdir()) == []
    dest_dir = tmp_path / "manifest2"
    (dest_dir / "jurisdictions.yaml").mkdir(parents=True)  # what docker makes for a missing bind-mount source
    r = _run(src, dest_dir)
    assert r.returncode == 1 and "directory" in r.stderr


def test_an_unwritable_directory_gives_the_root_owned_hint(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root can write anywhere")
    src = tmp_path / "jurisdictions.yaml"
    src.write_text("v1\n")
    dest_dir = tmp_path / "manifest"
    dest_dir.mkdir()
    dest_dir.chmod(0o555)
    try:
        r = _run(src, dest_dir)
    finally:
        dest_dir.chmod(0o755)
    assert r.returncode == 1 and "created it as root" in r.stderr


@pytest.mark.parametrize("failing", ["cp", "mv"])
def test_a_failure_while_publishing_leaves_the_served_copy_intact_and_no_partial_file(tmp_path, failing):
    """api-v3 reads deploy/manifest/jurisdictions.yaml directly, so it must never see a partial file, and a failed sync
    must keep the previous copy. The copy is written to a temp file in the same directory and published by rename; here
    `cp` dies halfway (leaving a partial temp file) or `mv` fails, and the served file must be untouched."""
    src = tmp_path / "jurisdictions.yaml"
    dest_dir = tmp_path / "manifest"
    src.write_text("v1\n")
    assert _run(src, dest_dir).returncode == 0
    served = dest_dir / "jurisdictions.yaml"
    before = (served.read_text(), served.stat().st_ino, served.stat().st_mtime)
    src.write_text("v2 is a much longer document\n" * 50)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    real = shutil.which(failing)
    stub = bin_dir / failing
    if failing == "cp":   # writes half the content to the destination argument, then dies
        stub.write_text(f'#!/usr/bin/env bash\nfor last; do :; done\nhead -c 20 "${{@: -2:1}}" > "$last"\nexit 1\n')
    else:
        stub.write_text("#!/usr/bin/env bash\nexit 1\n")
    stub.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}", MANIFEST_SOURCE=str(src), MANIFEST_DEST_DIR=str(dest_dir))
    r = subprocess.run(["bash", SCRIPT], env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert (served.read_text(), served.stat().st_ino, served.stat().st_mtime) == before   # same content, same file
    assert [p.name for p in dest_dir.iterdir()] == ["jurisdictions.yaml"]                  # no partial temp file left
