"""
AGENTS-250: test-structure-sync.sh starts its throwaway Postgres pair on the Mac's TEST Docker VM, never on the
production VM that holds the real replica. ddp-agents' colima-test.sh says where that VM is; a test VM that is not
available skips the run before any docker call.

Real bash, a stub `docker` that records DOCKER_HOST and answers "not available" (so the real test body never runs),
and a stub colima-test.sh.
"""
import os
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(_HERE, "test-structure-sync.sh")
TEST_SOCK = "unix:///Volumes/DDP-HOT/colima/test/docker.sock"


@pytest.fixture
def run(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text('#!/bin/bash\necho "$DOCKER_HOST $*" >> "$STUB_LOG"\nexit 1\n')   # "docker is not available"
    docker.chmod(0o755)
    helper = tmp_path / "colima-test.sh"
    helper.write_text('case "$1" in\n  check) [ "${STUB_DOWN:-0}" = 1 ] && { echo "DDP-HOT is not mounted" >&2; exit 3; }; exit 0;;\n'
                      f'  docker-host) echo "{TEST_SOCK}";;\nesac\n')
    log = tmp_path / "docker.log"

    def go(**extra):
        env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path), "STUB_LOG": str(log),
               "DDP_COLIMA_TEST_SH": str(helper), "DOCKER_HOST": "unix:///production.sock", **extra}
        proc = subprocess.run(["bash", SCRIPT], env=env, capture_output=True, text=True, timeout=30)
        return proc, (log.read_text().splitlines() if log.exists() else [])
    return go


def test_docker_is_asked_on_the_test_vm_not_production(run):
    proc, calls = run()
    assert proc.returncode == 0 and "SKIPPED: docker is not available" in proc.stdout
    assert calls and all(c.startswith(TEST_SOCK + " ") for c in calls)


def test_a_test_vm_that_is_down_skips_before_any_docker_call(run):
    proc, calls = run(STUB_DOWN="1")
    assert proc.returncode == 0 and "SKIPPED: the test Docker VM is not available: DDP-HOT is not mounted" in proc.stdout
    assert calls == []


def test_without_the_helper_docker_host_is_left_alone(run):
    proc, calls = run(DDP_COLIMA_TEST_SH="")
    assert calls and all(c.startswith("unix:///production.sock ") for c in calls)
