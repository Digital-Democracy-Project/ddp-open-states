"""
OPEN-483: start-os-api.sh (run by the LaunchDaemon at boot) and refresh-api-v3.sh must refresh api-v3's copy of
jurisdictions.yaml (deploy/sync-manifest.sh) BEFORE any docker-compose call, and must stop before docker-compose when
the sync fails. Otherwise a host that pulls and then reboots (or runs refresh-api-v3.sh) lets Docker create an empty
deploy/manifest directory and api-v3 answers 503 on /ddp/enrollment.

Real bash against temp directories, a stub `docker` and a stub `docker-compose` on PATH. The scripts are copied WITHOUT
their lib/ directory so no Slack alert can be sent from a test (start-os-api.sh falls back to a stderr message).
"""
import os
import shutil
import stat
import subprocess

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))

STUB_DOCKER = """#!/usr/bin/env bash
echo "docker $*" >> "$STUB_LOG"
case "$*" in
  *StartedAt*) echo "2026-11-03T00:00:00Z";;
  *Health.Status*) echo "healthy";;
esac
exit 0
"""
# Records, at the moment docker-compose is called, whether the copy exists, then aborts so nothing after `up` runs.
STUB_COMPOSE = """#!/usr/bin/env bash
if [ -s "$PWD/manifest/jurisdictions.yaml" ]; then present=yes; else present=no; fi
echo "docker-compose $* | copy_present=$present | manifest_dir_exists=$([ -d "$PWD/manifest" ] && echo yes || echo no)" >> "$STUB_LOG"
exit 99
"""


@pytest.fixture
def host(tmp_path):
    deploy = tmp_path / "ddp-open-states" / "deploy"
    deploy.mkdir(parents=True)
    shutil.copy(os.path.join(_HERE, "deploy", "sync-manifest.sh"), deploy)
    (tmp_path / "ddp-open-states" / "jurisdictions.yaml").write_text("nc:\n  name: North Carolina\n  status: live\n")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("start-os-api.sh", "refresh-api-v3.sh"):
        shutil.copy(os.path.join(_HERE, name), scripts)  # no lib/: no Slack
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("docker", STUB_DOCKER), ("docker-compose", STUB_COMPOSE)):
        p = bin_dir / name
        p.write_text(body)
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
    # refresh-api-v3.sh pulls api-v3's own checkout first: a temp repo with an origin
    origin = tmp_path / "api-v3-origin.git"
    api_v3 = tmp_path / "api-v3"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(api_v3)], check=True, capture_output=True)
    for cmd in (["git", "config", "user.email", "t@t"], ["git", "config", "user.name", "t"]):
        subprocess.run(cmd, cwd=api_v3, check=True)
    (api_v3 / "x").write_text("x")
    subprocess.run(["git", "add", "x"], cwd=api_v3, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "x"], cwd=api_v3, check=True)
    subprocess.run(["git", "push", "-q", "origin", "main"], cwd=api_v3, check=True, capture_output=True)
    log = tmp_path / "stub.log"
    log.write_text("")
    return dict(tmp=tmp_path, deploy=deploy, scripts=scripts, bin=bin_dir, log=log, api_v3=api_v3)


def _run(host, script):
    env = dict(
        os.environ,
        PATH=f"{host['bin']}:{os.environ['PATH']}",
        STUB_LOG=str(host["log"]),
        COMPOSE_DIR=str(host["deploy"]),
        LOG=str(host["tmp"] / "os-api.log"),
        API_V3_DIR=str(host["api_v3"]),
        DOCKER_HOST="unix:///nonexistent",
    )
    return subprocess.run(["bash", str(host["scripts"] / script)], env=env, capture_output=True, text=True, timeout=60)


def _compose_calls(host):
    return [l for l in host["log"].read_text().splitlines() if l.startswith("docker-compose")]


@pytest.mark.parametrize("script", ["start-os-api.sh", "refresh-api-v3.sh"])
def test_the_copy_exists_before_the_first_docker_compose_call(host, script):
    _run(host, script)  # the stub aborts at the first docker-compose call, which is all we need
    calls = _compose_calls(host)
    assert calls, "docker-compose was never reached"
    assert "copy_present=yes" in calls[0], calls[0]
    assert (host["deploy"] / "manifest" / "jurisdictions.yaml").read_text().startswith("nc:")


@pytest.mark.parametrize("script", ["start-os-api.sh", "refresh-api-v3.sh"])
@pytest.mark.parametrize("break_source", ["missing", "empty"])
def test_a_failed_sync_stops_before_any_docker_compose_call(host, script, break_source):
    src = host["tmp"] / "ddp-open-states" / "jurisdictions.yaml"
    if break_source == "missing":
        src.unlink()
    else:
        src.write_text("")
    r = _run(host, script)
    assert r.returncode != 0
    assert _compose_calls(host) == [], f"docker-compose ran although the sync failed:\n{r.stdout}{r.stderr}"
    assert not (host["deploy"] / "manifest").exists(), "an empty manifest directory was left behind"


@pytest.mark.parametrize("script", ["start-os-api.sh", "refresh-api-v3.sh"])
def test_a_good_existing_copy_survives_a_failed_sync(host, script):
    assert subprocess.run(["bash", str(host["deploy"] / "sync-manifest.sh")], capture_output=True).returncode == 0
    (host["tmp"] / "ddp-open-states" / "jurisdictions.yaml").write_text("")
    _run(host, script)
    assert (host["deploy"] / "manifest" / "jurisdictions.yaml").read_text().startswith("nc:")
    assert _compose_calls(host) == []


@pytest.mark.parametrize("script", ["start-os-api.sh", "refresh-api-v3.sh"])
def test_the_sync_call_precedes_every_docker_compose_command_line_in_the_source(script):
    """Command lines only (comments mention docker-compose too)."""
    lines = [l.strip() for l in open(os.path.join(_HERE, script)).read().splitlines() if not l.strip().startswith("#")]
    sync = next(i for i, l in enumerate(lines) if "sync-manifest.sh" in l)
    compose = [i for i, l in enumerate(lines) if l.startswith("docker-compose ")]
    assert compose and all(sync < i for i in compose), (sync, compose)


def _alerts(result):
    return result.stderr.count("alert not sent")  # the no-lib fallback prints this instead of posting to Slack


def test_a_persistent_sync_failure_alerts_once_per_streak_not_on_every_relaunch(host):
    """launchd relaunches the boot script every ~30 s: one alert per failure streak, and a success re-arms it."""
    src = host["tmp"] / "ddp-open-states" / "jurisdictions.yaml"
    good = src.read_text()
    src.write_text("")
    first = _run(host, "start-os-api.sh")
    second = _run(host, "start-os-api.sh")
    third = _run(host, "start-os-api.sh")
    assert [_alerts(first), _alerts(second), _alerts(third)] == [1, 0, 0]
    src.write_text(good)
    ok = _run(host, "start-os-api.sh")  # the sync works; the stub docker-compose aborts afterwards
    assert _compose_calls(host) and "copy_present=yes" in _compose_calls(host)[0]
    src.write_text("")
    again = _run(host, "start-os-api.sh")
    assert _alerts(again) == 1  # a new streak alerts again
