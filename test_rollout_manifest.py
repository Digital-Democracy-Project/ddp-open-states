"""
Tests for deploy/rollout-manifest.sh (OPEN-483): real bash against a temp git repo (origin + clone), a stub `docker`
and a stub `aws` on PATH. Nothing touches a real host, container or the live production checkout.
"""
import hashlib
import os
import shutil
import stat
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
DEPLOY = os.path.join(_HERE, "deploy")

VALID_YAML = "pa:\n  name: Pennsylvania\n  status: scraping\nnc:\n  name: North Carolina\n  status: live\n"

STUB_DOCKER = """#!/usr/bin/env bash
echo "docker $*" >> "$STUB_LOG"
case "$1" in
  inspect)
    case "$*" in
      *Mounts*) echo "${STUB_MOUNTS:-/app/manifest }";;
      *Health*) echo "${STUB_HEALTH:-healthy}";;
    esac;;
  exec) echo "${STUB_EXEC_MD5:-}";;
  compose) echo "recreated (stub)";;
esac
exit 0
"""
STUB_AWS = """#!/usr/bin/env bash
echo "aws $*" >> "$STUB_LOG"
echo "${STUB_ECS_TASKS:-}"
exit ${STUB_ECS_RC:-0}
"""


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


@pytest.fixture
def world(tmp_path):
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    clone = tmp_path / "clone"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(seed)], check=True, capture_output=True)
    for c in (seed,):
        _git(c, "config", "user.email", "t@t"); _git(c, "config", "user.name", "t")
    os.makedirs(seed / "deploy")
    shutil.copy(os.path.join(DEPLOY, "rollout-manifest.sh"), seed / "deploy")
    shutil.copy(os.path.join(DEPLOY, "sync-manifest.sh"), seed / "deploy")
    (seed / "jurisdictions.yaml").write_text(VALID_YAML)
    # Stand-ins for the repo's validator and drift check: real ones need the whole repo; these exit as told.
    (seed / "validate_jurisdictions.py").write_text(
        "import os, sys\nprint('OK: validator stub')\nsys.exit(int(os.environ.get('STUB_VALIDATE_RC', '0')))\n")
    (seed / "check-jurisdiction-drift.py").write_text(
        "import os, sys\nprint('OK: drift stub args=' + ' '.join(sys.argv[1:]))\nsys.exit(int(os.environ.get('STUB_DRIFT_RC', '0')))\n")
    _git(seed, "add", "-A"); _git(seed, "commit", "-q", "-m", "first")
    _git(seed, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True, capture_output=True)
    _git(clone, "config", "user.email", "t@t"); _git(clone, "config", "user.name", "t")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("docker", STUB_DOCKER), ("aws", STUB_AWS)):
        p = bin_dir / name
        p.write_text(body)
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "stub.log"
    log.write_text("")
    return dict(origin=origin, seed=seed, clone=clone, bin=bin_dir, log=log, tmp=tmp_path)


def _push_change(w, text="pa:\n  name: Pennsylvania\n  status: live\nnc:\n  name: North Carolina\n  status: live\n"):
    (w["seed"] / "jurisdictions.yaml").write_text(text)
    _git(w["seed"], "commit", "-q", "-am", "change the list")
    _git(w["seed"], "push", "-q", "origin", "main")


def _run(w, *args, env_extra=None):
    env = dict(
        os.environ,
        PATH=f"{w['bin']}:{os.environ['PATH']}",
        STUB_LOG=str(w["log"]),
        ROLLOUT_PYTHON=sys.executable,
        ROLLOUT_NOW_UTC="14:00",
        ROLLOUT_WAIT="0",
        ROLLOUT_PS_CMD="printf '  101 /sbin/launchd\\n'",
    )
    env.update(env_extra or {})
    return subprocess.run(
        ["bash", str(w["clone"] / "deploy" / "rollout-manifest.sh"), *args],
        env=env, capture_output=True, text=True, cwd=w["clone"],
    )


def _docker_calls(w):
    return [l for l in w["log"].read_text().splitlines() if l.startswith("docker ")]


def test_a_real_rollout_pulls_syncs_checks_and_prints_the_values(world):
    _push_change(world)
    before = _git(world["clone"], "rev-parse", "--short", "HEAD")
    r = _run(world, "--host", "ec2", "--ddp-sync-root", "/opt/ddp-sync",
             env_extra={"STUB_EXEC_MD5": _md5(world["seed"] / "jurisdictions.yaml")})
    assert r.returncode == 0, r.stdout + r.stderr
    after = _git(world["clone"], "rev-parse", "--short", "HEAD")
    assert after != before and f"revision: {before} -> {after}" in r.stdout
    assert (world["clone"] / "deploy" / "manifest" / "jurisdictions.yaml").read_text() == (world["seed"] / "jurisdictions.yaml").read_text()
    assert "drift stub args=--ddp-sync-root /opt/ddp-sync" in r.stdout
    assert "live: nc pa" in r.stdout and "jurisdictions in the list: 2" in r.stdout
    assert "no ddp-sync restart" in r.stdout


def test_dry_run_changes_nothing_but_prints_what_it_would_do(world):
    _push_change(world)
    before = _git(world["clone"], "rev-parse", "HEAD")
    r = _run(world, "--host", "mac", "--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _git(world["clone"], "rev-parse", "HEAD") == before
    assert not (world["clone"] / "deploy" / "manifest").exists()
    assert "would: git merge --ff-only origin/main" in r.stdout and "DRY RUN" in r.stdout


def test_a_real_scrape_process_stops_it_before_anything_changes(world):
    _push_change(world)
    before = _git(world["clone"], "rev-parse", "HEAD")
    r = _run(world, "--host", "ec2", env_extra={
        "ROLLOUT_PS_CMD": "printf '  4242 bash /opt/ddp-open-states/run-scrape.sh nc\\n'"})
    assert r.returncode == 1 and "real run-scrape.sh process" in r.stderr and "4242" in r.stderr
    assert _git(world["clone"], "rev-parse", "HEAD") == before


@pytest.mark.parametrize("line", [
    # The 2026-11-03 near-miss: a shell whose command line merely CONTAINS the text is not a scrape.
    "  14772 /bin/zsh -c source snapshot.sh && ps aux | grep -c run-scrape",
    "  14773 grep run-scrape",
    "  14774 bash deploy/rollout-manifest.sh --host mac  # run-scrape",
    "  14775 vim run-scrape.sh.bak",
])
def test_a_process_that_only_mentions_run_scrape_is_not_a_scrape(world, line):
    r = _run(world, "--host", "ec2", "--dry-run", env_extra={"ROLLOUT_PS_CMD": f"printf '%s\\n' '{line}'"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "real run-scrape.sh processes: 0" in r.stdout


def test_run_scrape_started_directly_by_its_path_is_a_scrape(world):
    r = _run(world, "--host", "ec2", "--dry-run", env_extra={
        "ROLLOUT_PS_CMD": "printf '  77 /Users/x/ddp-open-states/run-scrape.sh va\\n'"})
    assert r.returncode == 1 and "run-scrape.sh process" in r.stderr


@pytest.mark.parametrize("now", ["02:00", "02:08", "01:51", "02:30", "03:09"])
def test_it_refuses_near_the_02_02_30_and_03_utc_jobs(world, now):
    r = _run(world, "--host", "ec2", "--dry-run", env_extra={"ROLLOUT_NOW_UTC": now})
    assert r.returncode == 1 and "job; try later" in r.stderr


def test_it_runs_just_outside_the_window(world):
    assert _run(world, "--host", "ec2", "--dry-run", env_extra={"ROLLOUT_NOW_UTC": "02:11"}).returncode == 0


def test_running_cloud_scrape_tasks_stop_it(world):
    r = _run(world, "--host", "ec2", env_extra={"STUB_ECS_TASKS": "arn:aws:ecs:us-east-1:1:task/x/abc"})
    assert r.returncode == 1 and "cloud scrape tasks are running" in r.stderr


def test_an_unlistable_task_gate_stops_unless_skipped_on_purpose(world):
    r = _run(world, "--host", "ec2", "--dry-run", env_extra={"STUB_ECS_RC": "1", "STUB_ECS_TASKS": "AccessDenied"})
    assert r.returncode == 1 and "--skip-ecs-check" in r.stderr
    ok = _run(world, "--host", "ec2", "--dry-run", "--skip-ecs-check", env_extra={"STUB_ECS_RC": "1"})
    assert ok.returncode == 0 and "NOT CHECKED" in ok.stdout


def test_modified_tracked_files_or_another_branch_stop_it(world):
    (world["clone"] / "jurisdictions.yaml").write_text("pa:\n  status: live\n")
    r = _run(world, "--host", "ec2", "--dry-run")
    assert r.returncode == 1 and "modified" in r.stderr
    _git(world["clone"], "checkout", "-q", "--", "jurisdictions.yaml")
    _git(world["clone"], "checkout", "-q", "-b", "side")
    r = _run(world, "--host", "ec2", "--dry-run")
    assert r.returncode == 1 and "not main" in r.stderr


def test_a_failed_drift_check_stops_before_the_container_is_looked_at(world):
    r = _run(world, "--host", "ec2", "--ddp-sync-root", "/opt/ddp-sync", env_extra={"STUB_DRIFT_RC": "1"})
    assert r.returncode == 1 and "drift check failed" in r.stderr
    assert _docker_calls(world) == []


def test_a_failed_validator_stops_it(world):
    r = _run(world, "--host", "ec2", env_extra={"STUB_VALIDATE_RC": "1"})
    assert r.returncode == 1 and "does not validate" in r.stderr


def test_the_old_single_file_mount_exits_3_and_recreates_nothing(world):
    r = _run(world, "--host", "ec2", env_extra={"STUB_MOUNTS": "/app/jurisdictions.yaml "})
    assert r.returncode == 3 and "ONE-TIME SWITCH NEEDED" in r.stderr
    assert not any(" compose " in c for c in _docker_calls(world))


def test_recreate_runs_exactly_the_one_allowed_command_and_nothing_else(world):
    r = _run(world, "--host", "ec2", "--recreate", env_extra={
        "STUB_MOUNTS": "/app/jurisdictions.yaml ", "STUB_EXEC_MD5": _md5(world["seed"] / "jurisdictions.yaml")})
    assert r.returncode == 0, r.stdout + r.stderr
    compose = [c for c in _docker_calls(world) if c.startswith("docker compose")]
    assert compose == ["docker compose -p ddp-openstates -f docker-compose.rds.yml up -d --no-deps --force-recreate api"]


def test_the_script_can_only_touch_the_api_service(world):
    """Whatever the path through the script, no docker call names ddp-sync, the broker or the database."""
    _push_change(world)
    _run(world, "--host", "ec2", "--recreate", env_extra={"STUB_MOUNTS": "/app/jurisdictions.yaml "})
    allowed = ("docker inspect", "docker exec", "docker compose -p ddp-openstates -f docker-compose.rds.yml up -d --no-deps --force-recreate api")
    for call in _docker_calls(world):
        assert call.startswith(allowed), call
        assert not any(w in call for w in ("ddp-sync", "broker", "postgres", "celery", ".env"))


def test_a_container_whose_copy_differs_from_the_checkout_stops_it(world):
    r = _run(world, "--host", "ec2", env_extra={"STUB_EXEC_MD5": "deadbeef"})
    assert r.returncode == 1 and "does not match the checkout" in r.stderr


@pytest.mark.parametrize("line", [
    "  51 bash -x /opt/ddp-open-states/run-scrape.sh nc",
    "  52 bash -e -x /opt/ddp-open-states/run-scrape.sh nc",
    "  53 /usr/bin/env bash /opt/ddp-open-states/run-scrape.sh nc",
    "  54 env FOO=1 BAR=2 bash /opt/ddp-open-states/run-scrape.sh nc",
    "  55 /bin/sh /opt/ddp-open-states/run-scrape.sh nc",
    "  56 /usr/bin/env /opt/ddp-open-states/run-scrape.sh nc",
])
def test_run_scrape_started_through_interpreter_flags_or_env_is_still_a_scrape(world, line):
    r = _run(world, "--host", "ec2", "--dry-run", env_extra={"ROLLOUT_PS_CMD": f"printf '%s\\n' '{line}'"})
    assert r.returncode == 1 and "real run-scrape.sh process" in r.stderr, line


@pytest.mark.parametrize("line", [
    "  61 /bin/bash -c /opt/ddp-open-states/run-scrape.sh nc",   # carries text; its child shows up on its own line
    "  62 bash -lc cd /x && ./run-scrape.sh nc",
    "  63 /usr/bin/env FOO=1 grep run-scrape.sh",
    "  64 bash -x /opt/some-other-script.sh run-scrape.sh",      # the script is not the first non-option argument
])
def test_wrappers_that_only_carry_the_text_are_not_scrapes(world, line):
    r = _run(world, "--host", "ec2", "--dry-run", env_extra={"ROLLOUT_PS_CMD": f"printf '%s\\n' '{line}'"})
    assert r.returncode == 0, line + r.stderr


def test_a_clean_local_main_that_is_ahead_of_origin_is_refused_before_anything_else(world):
    (world["clone"] / "local-only.txt").write_text("not merged\n")
    _git(world["clone"], "add", "local-only.txt")
    _git(world["clone"], "commit", "-q", "-m", "unpushed local commit")
    before = _git(world["clone"], "rev-parse", "HEAD")
    r = _run(world, "--host", "ec2")
    assert r.returncode == 1 and "not on origin/main" in r.stderr
    assert _git(world["clone"], "rev-parse", "HEAD") == before
    assert not (world["clone"] / "deploy" / "manifest").exists() and _docker_calls(world) == []
    assert _run(world, "--host", "ec2", "--dry-run").returncode == 1  # dry run refuses too
