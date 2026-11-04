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

FULL_STATE = (
    "  name: {name}\n  status: {status}\n  tier: secondary\n"
    "  archive:\n    enabled: true\n    scheduled: {sched}\n"
    "  enrollment:\n    people_refresh: true\n    legbot_replica: false\n"
)
VALID_YAML = "pa:\n" + FULL_STATE.format(name="Pennsylvania", status="scraping", sched="false") + \
             "nc:\n" + FULL_STATE.format(name="North Carolina", status="live", sched="true")
CHANGED_YAML = VALID_YAML.replace("status: scraping", "status: live").replace("scheduled: false", "scheduled: true")

STUB_DOCKER = """#!/usr/bin/env bash
echo "docker $*" >> "$STUB_LOG"
case "$1" in
  inspect)
    case "$*" in
      *"{{.Id}}"*) if [ -e "${STUB_MARKER:-/nonexistent}" ]; then echo newcontainerid0000; else echo oldcontainerid0000; fi;;
      *Mounts*) if [ -e "${STUB_MARKER:-/nonexistent}" ] && [ -n "${STUB_MOUNTS_AFTER:-}" ]; then echo "$STUB_MOUNTS_AFTER"; else echo "${STUB_MOUNTS-/app/manifest }"; fi;;
      *Health*) echo "${STUB_HEALTH:-healthy}";;
    esac;;
  exec) echo "${STUB_EXEC_MD5-anymd5}";;
  compose) touch "${STUB_MARKER:-/dev/null}"; echo "recreated (stub)";;
esac
exit 0
"""
# Lets ONE test reach `git merge --ff-only` on a diverged branch by answering the ahead-count question with 0
# (a test harness shim on PATH; the script itself has no switch for this).
STUB_GIT = """#!/usr/bin/env bash
if [ -n "${STUB_GIT_AHEAD_ZERO:-}" ] && [ "$1 $2 $3" = "rev-list --count origin/main..HEAD" ]; then echo 0; exit 0; fi
exec "$REAL_GIT" "$@"
"""
STUB_AWS = """#!/usr/bin/env bash
echo "aws $*" >> "$STUB_LOG"
echo "${STUB_ECS_TASKS:-}"
exit ${STUB_ECS_RC:-0}
"""
# Stand-ins for the repo's validator and drift check: they read the file they are given (like the real ones) and fail on
# the word BROKEN, or as told by an env var.
STUB_VALIDATE = """import os, sys
path = sys.argv[1] if len(sys.argv) > 1 else "jurisdictions.yaml"
text = open(path).read()
print("OK: validator stub", os.path.basename(path))
sys.exit(1 if "BROKEN" in text or os.environ.get("STUB_VALIDATE_RC") else 0)
"""
STUB_DRIFT = """import os, sys
args = sys.argv[1:]
manifest = args[args.index("--manifest") + 1] if "--manifest" in args else "jurisdictions.yaml"
print("OK: drift stub args=" + " ".join(a if not a.startswith("/") or "sync" in a else "<file>" for a in args))
sys.exit(1 if os.environ.get("STUB_DRIFT_RC") else 0)
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
    _git(seed, "config", "user.email", "t@t"); _git(seed, "config", "user.name", "t")
    os.makedirs(seed / "deploy")
    shutil.copy(os.path.join(DEPLOY, "rollout-manifest.sh"), seed / "deploy")
    shutil.copy(os.path.join(DEPLOY, "sync-manifest.sh"), seed / "deploy")
    (seed / "jurisdictions.yaml").write_text(VALID_YAML)
    (seed / "validate_jurisdictions.py").write_text(STUB_VALIDATE)
    (seed / "check-jurisdiction-drift.py").write_text(STUB_DRIFT)
    _git(seed, "add", "-A"); _git(seed, "commit", "-q", "-m", "first")
    _git(seed, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True, capture_output=True)
    _git(clone, "config", "user.email", "t@t"); _git(clone, "config", "user.name", "t")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("docker", STUB_DOCKER), ("aws", STUB_AWS), ("git", STUB_GIT)):
        p = bin_dir / name
        p.write_text(body)
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "stub.log"
    log.write_text("")
    ps = tmp_path / "ps.txt"
    ps.write_text("  101 /sbin/launchd\n")
    return dict(origin=origin, seed=seed, clone=clone, bin=bin_dir, log=log, ps=ps, tmp=tmp_path)


def _push(w, text=CHANGED_YAML, msg="change the list"):
    (w["seed"] / "jurisdictions.yaml").write_text(text)
    _git(w["seed"], "commit", "-q", "-am", msg)
    _git(w["seed"], "push", "-q", "origin", "main")


def _set_ps(w, *lines):
    w["ps"].write_text("\n".join(lines) + "\n")


def _run(w, *args, env_extra=None, sync=True):
    args = list(args)
    if sync and "--dry-run" not in args and "--ddp-sync-root" not in args:
        args += ["--ddp-sync-root", "/opt/ddp-sync"]
    env = dict(
        os.environ,
        PATH=f"{w['bin']}:{os.environ['PATH']}",
        STUB_LOG=str(w["log"]),
        ROLLOUT_PYTHON=sys.executable,
        ROLLOUT_NOW_UTC="14:00",
        ROLLOUT_WAIT="0",
        ROLLOUT_HEALTH_TRIES="3",
        ROLLOUT_PS_FILE=str(w["ps"]),
        REAL_GIT=shutil.which("git"),
        STUB_MARKER=str(w["tmp"] / "recreated.marker"),
    )
    env.update(env_extra or {})
    return subprocess.run(
        ["bash", str(w["clone"] / "deploy" / "rollout-manifest.sh"), *args],
        env=env, capture_output=True, text=True, cwd=w["clone"],
    )


def _docker_calls(w):
    return [l for l in w["log"].read_text().splitlines() if l.startswith("docker ")]


def _same_md5(w):
    return {"STUB_EXEC_MD5": _md5(w["seed"] / "jurisdictions.yaml")}


# --- the main path ---------------------------------------------------------------------------------------------


def test_a_real_rollout_pulls_checks_then_syncs_and_prints_the_values(world):
    _push(world)
    before = _git(world["clone"], "rev-parse", "--short", "HEAD")
    r = _run(world, "--host", "ec2", "--state", "pa", env_extra=_same_md5(world))
    assert r.returncode == 0, r.stdout + r.stderr
    after = _git(world["clone"], "rev-parse", "--short", "HEAD")
    assert after != before and f"revision: {before} -> {after}" in r.stdout
    assert (world["clone"] / "deploy" / "manifest" / "jurisdictions.yaml").read_text() == CHANGED_YAML
    assert "drift stub args=--manifest" in r.stdout and "--ddp-sync-root /opt/ddp-sync" in r.stdout
    assert "live: nc pa" in r.stdout and "jurisdictions in the list: 2" in r.stdout
    assert "state pa: status=live" in r.stdout and "archive.scheduled=True" in r.stdout and "legbot_replica=False" in r.stdout
    assert "container health: healthy" in r.stdout and "no ddp-sync restart" in r.stdout


def test_dry_run_changes_nothing_but_prints_what_it_would_do(world):
    _push(world)
    before = _git(world["clone"], "rev-parse", "HEAD")
    r = _run(world, "--host", "mac", "--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _git(world["clone"], "rev-parse", "HEAD") == before
    assert not (world["clone"] / "deploy" / "manifest").exists()
    assert "would: git merge --ff-only origin/main" in r.stdout and "DRY RUN" in r.stdout
    assert "still runs git fetch" in r.stdout and "INCOMING file" in r.stdout


def test_dry_run_validates_the_incoming_file_not_the_current_one(world):
    _push(world, "BROKEN list\n")
    before = _git(world["clone"], "rev-parse", "HEAD")
    r = _run(world, "--host", "ec2", "--dry-run")
    assert r.returncode == 1 and "does not validate" in r.stderr and "nothing was changed" in r.stderr
    assert _git(world["clone"], "rev-parse", "HEAD") == before


def test_a_real_run_needs_the_ddp_sync_root_and_a_dry_run_says_unchecked(world):
    r = _run(world, "--host", "ec2", sync=False)
    assert r.returncode == 2 and "--ddp-sync-root" in r.stderr and "Nothing was changed" in r.stderr
    assert not (world["clone"] / "deploy" / "manifest").exists() and _docker_calls(world) == []
    d = _run(world, "--host", "ec2", "--dry-run", sync=False)
    assert d.returncode == 0 and "UNCHECKED" in d.stdout


# --- the process gate ---------------------------------------------------------------------------------------------


def test_a_real_scrape_process_stops_it_before_anything_changes(world):
    _push(world)
    before = _git(world["clone"], "rev-parse", "HEAD")
    _set_ps(world, "  4242 bash /opt/ddp-open-states/run-scrape.sh nc")
    r = _run(world, "--host", "ec2")
    assert r.returncode == 1 and "real scrape, archive or people-refresh job" in r.stderr and "4242" in r.stderr
    assert _git(world["clone"], "rev-parse", "HEAD") == before


@pytest.mark.parametrize("line", [
    # The 2026-11-03 near-miss: a shell whose command line merely CONTAINS the text is not a scrape.
    "  14772 /bin/zsh -c source snapshot.sh && ps aux | grep -c run-scrape",
    "  14773 grep run-scrape",
    "  14774 bash deploy/rollout-manifest.sh --host mac  # run-scrape",
    "  14775 vim run-scrape.sh.bak",
    "  61 /bin/bash -c /opt/ddp-open-states/run-scrape.sh nc",   # carries text; its child shows up on its own line
    "  62 bash -lc cd /x && ./run-scrape.sh nc",
    "  63 /usr/bin/env FOO=1 grep run-scrape.sh",
    "  64 bash -x /opt/some-other-script.sh run-scrape.sh",      # the script is not the first non-option argument
    "  66 vim run-scrape.sh",                                    # an editor is not a job, even behind a wrapper
    "  67 sudo vim /opt/ddp-open-states/run-scrape.sh",
    "  68 nohup grep run-archive.sh logs.txt",
    "  69 sudo -u u bash -c /opt/ddp-open-states/run-scrape.sh nc",   # -c carries text; the child shows on its own line
    "  70 caffeinate -i sleep 900",
    "  71 nohup echo run-scrape.sh",                             # the wrapper runs echo; the job name is data
    "  72 sudo -u u printf run-scrape.sh",
    "  73 timeout 60 grep run-archive.sh x",
    "  65 sleep 900",                                            # a sleep alone (no wrapper alive) is not a job
])
def test_a_process_that_only_mentions_a_job_is_not_a_job(world, line):
    _set_ps(world, line)
    r = _run(world, "--host", "ec2", "--dry-run")
    assert r.returncode == 0, line + r.stderr
    assert "processes: 0" in r.stdout


@pytest.mark.parametrize("line", [
    "  77 /Users/x/ddp-open-states/run-scrape.sh va",
    "  51 bash -x /opt/ddp-open-states/run-scrape.sh nc",
    "  52 bash -e -x /opt/ddp-open-states/run-scrape.sh nc",
    "  53 /usr/bin/env bash /opt/ddp-open-states/run-scrape.sh nc",
    "  54 env FOO=1 BAR=2 bash /opt/ddp-open-states/run-scrape.sh nc",
    "  55 /bin/sh /opt/ddp-open-states/run-scrape.sh nc",
    "  56 /usr/bin/env /opt/ddp-open-states/run-scrape.sh nc",
    # run-scrape-retrying.sh is alive THROUGH its sleep between attempts (up to 900 s) with no run-scrape.sh running
    "  81 bash /opt/ddp-open-states/run-scrape-retrying.sh nc",
    "  82 /bin/bash -x /opt/ddp-open-states/run-scrape-retrying.sh va",
    # the archive and the people refresh read this checkout too
    "  83 bash /opt/ddp-open-states/run-archive.sh va",
    "  84 /opt/ddp-open-states/run-people-refresh.sh",
    # OPEN-488: a wrapper the gate used not to know, and an option whose value is not the script
    "  91 nohup bash /opt/ddp-open-states/run-scrape.sh nc",
    "  92 caffeinate -i /opt/ddp-open-states/run-scrape.sh nc",
    "  93 /usr/bin/time -p /opt/ddp-open-states/run-archive.sh va",
    "  94 sudo -u u /opt/ddp-open-states/run-people-refresh.sh",
    "  95 bash -o pipefail /opt/ddp-open-states/run-scrape.sh nc",
    "  96 nohup caffeinate -i bash -x /opt/ddp-open-states/run-scrape-retrying.sh nc",
    "  97 sudo -u u bash -eo pipefail run-scrape.sh nc",
    "  98 sudo -u git bash /opt/ddp-open-states/run-scrape.sh nc",   # the user name is an option value, not the command
    "  99 timeout 3600 env FOO=1 /opt/ddp-open-states/run-archive.sh va",
])
def test_every_wrapper_that_reads_the_checkout_is_a_job(world, line):
    _set_ps(world, line)
    r = _run(world, "--host", "ec2", "--dry-run")
    assert r.returncode == 1 and "real scrape, archive or people-refresh job" in r.stderr, line


def test_a_retry_wrapper_asleep_between_attempts_still_blocks_the_rollout(world):
    """Only the wrapper and its `sleep 900` are alive: no run-scrape.sh process exists in this window."""
    _set_ps(world, "  81 bash /opt/ddp-open-states/run-scrape-retrying.sh nc", "  82 sleep 900")
    r = _run(world, "--host", "ec2", env_extra=_same_md5(world))
    assert r.returncode == 1 and "run-scrape-retrying.sh" in r.stderr


def test_the_process_listing_hook_is_a_file_and_is_never_executed(world):
    marker = world["tmp"] / "executed"
    r = _run(world, "--host", "ec2", "--dry-run", env_extra={"ROLLOUT_PS_CMD": f"touch {marker}"})
    assert r.returncode == 0 and not marker.exists()


# --- the other gates -----------------------------------------------------------------------------------------------


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


def test_the_pull_is_fast_forward_only_a_diverged_branch_is_never_merged(world):
    """The ahead gate normally stops a diverged checkout first; a git shim on PATH (the script has no switch for this)
    answers its question with 0 so the pull itself is reached and must still refuse: plain `git merge` would succeed here
    (the two sides touch different files) and create a merge commit."""
    (world["clone"] / "local-only.txt").write_text("local\n")
    _git(world["clone"], "add", "local-only.txt")
    _git(world["clone"], "commit", "-q", "-m", "local commit")
    (world["seed"] / "remote-only.txt").write_text("remote\n")
    _git(world["seed"], "add", "remote-only.txt")
    _git(world["seed"], "commit", "-q", "-m", "remote commit")
    _git(world["seed"], "push", "-q", "origin", "main")
    before = _git(world["clone"], "rev-parse", "HEAD")
    r = _run(world, "--host", "ec2", env_extra={"STUB_GIT_AHEAD_ZERO": "1", **_same_md5(world)})
    assert r.returncode == 1 and "not a fast-forward" in r.stderr
    assert _git(world["clone"], "rev-parse", "HEAD") == before and not (world["clone"] / "remote-only.txt").exists()


# --- order: checks before the copy goes live ------------------------------------------------------------------------


def test_a_failed_validator_stops_before_the_copy_is_made_and_says_what_it_left_behind(world):
    _push(world, "BROKEN list\n")
    r = _run(world, "--host", "ec2")
    assert r.returncode == 1 and "does not validate" in r.stderr
    assert "api-v3's copy of the list was NOT changed" in r.stderr
    assert not (world["clone"] / "deploy" / "manifest").exists()          # the copy was never made
    assert _git(world["clone"], "show", "HEAD:jurisdictions.yaml") == "BROKEN list"   # the pulled checkout stays
    assert _docker_calls(world) == []


def test_a_failed_drift_check_stops_before_the_copy_and_before_docker(world):
    _push(world)
    r = _run(world, "--host", "ec2", env_extra={"STUB_DRIFT_RC": "1"})
    assert r.returncode == 1 and "drift check failed" in r.stderr and "was NOT changed" in r.stderr
    assert not (world["clone"] / "deploy" / "manifest").exists() and _docker_calls(world) == []


def test_a_good_existing_copy_keeps_serving_when_a_check_fails(world):
    assert _run(world, "--host", "ec2", env_extra=_same_md5(world)).returncode == 0
    old = (world["clone"] / "deploy" / "manifest" / "jurisdictions.yaml").read_text()
    _push(world, "BROKEN list\n")
    assert _run(world, "--host", "ec2").returncode == 1
    assert (world["clone"] / "deploy" / "manifest" / "jurisdictions.yaml").read_text() == old


# --- the container -----------------------------------------------------------------------------------------------


def test_an_unhealthy_container_fails_the_run_after_a_bounded_wait(world):
    r = _run(world, "--host", "ec2", env_extra={"STUB_HEALTH": "starting", **_same_md5(world)})
    assert r.returncode == 1 and "is not healthy (status: starting)" in r.stderr
    inspects = [c for c in _docker_calls(world) if "Health" in c]
    assert len(inspects) == 3                                          # ROLLOUT_HEALTH_TRIES=3: bounded, not forever


def test_a_container_that_becomes_healthy_within_the_wait_passes(world, tmp_path):
    flaky = world["bin"] / "docker"
    flaky.write_text(STUB_DOCKER.replace(
        '*Health*) echo "${STUB_HEALTH:-healthy}";;',
        '*Health*) n=$(grep -c Health "$STUB_LOG"); if [ "$n" -ge 2 ]; then echo healthy; else echo starting; fi;;'))
    r = _run(world, "--host", "ec2", env_extra=_same_md5(world))
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("dry", [False, True])
def test_an_empty_container_checksum_on_a_directory_mount_fails_the_run(world, dry):
    args = ["--host", "ec2"] + (["--dry-run"] if dry else [])
    r = _run(world, *args, env_extra={"STUB_EXEC_MD5": ""})
    assert r.returncode == 1 and "cannot read jurisdictions.yaml" in r.stderr and "EMPTY" in r.stdout


def test_a_container_copy_that_differs_from_the_checkout_stops_it(world):
    r = _run(world, "--host", "ec2", env_extra={"STUB_EXEC_MD5": "deadbeef"})
    assert r.returncode == 1 and "does not match the checkout" in r.stderr


def test_the_old_single_file_mount_exits_3_and_recreates_nothing(world):
    r = _run(world, "--host", "ec2", env_extra={"STUB_MOUNTS": "/app/jurisdictions.yaml "})
    assert r.returncode == 3 and "ONE-TIME SWITCH NEEDED" in r.stderr
    assert not any(" compose " in c for c in _docker_calls(world))


def test_recreate_runs_exactly_the_one_allowed_command_and_nothing_else(world):
    r = _run(world, "--host", "ec2", "--recreate", env_extra={"STUB_MOUNTS": "/app/jurisdictions.yaml ", **_same_md5(world)})
    # the stub reports the old mount both before and after, so only the command itself is asserted here
    compose = [c for c in _docker_calls(world) if c.startswith("docker compose")]
    assert compose == ["docker compose -p ddp-openstates -f docker-compose.rds.yml up -d --no-build --no-deps --force-recreate api"]


def test_the_script_can_only_touch_the_api_service(world):
    """Whatever the path through the script, no docker call names ddp-sync, the broker or the database."""
    _push(world)
    _run(world, "--host", "ec2", "--recreate", env_extra={"STUB_MOUNTS": "/app/jurisdictions.yaml "})
    allowed = ("docker inspect", "docker exec",
               "docker compose -p ddp-openstates -f docker-compose.rds.yml up -d --no-build --no-deps --force-recreate api")
    for call in _docker_calls(world):
        assert call.startswith(allowed), call
        assert not any(w in call for w in ("ddp-sync", "broker", "postgres", "celery", ".env"))


def test_state_argument_for_an_unknown_state_says_so(world):
    r = _run(world, "--host", "ec2", "--state", "zz", env_extra=_same_md5(world))
    assert r.returncode == 0 and "state zz: not in the list" in r.stdout


def test_there_is_no_way_to_switch_the_ahead_gate_off_from_the_environment(world):
    """An ahead-only checkout would pass `git merge --ff-only` as already up to date and deploy unreviewed local commits."""
    (world["clone"] / "local-only.txt").write_text("not merged\n")
    _git(world["clone"], "add", "local-only.txt")
    _git(world["clone"], "commit", "-q", "-m", "unpushed local commit")
    for name in ("ROLLOUT_TEST_SKIP_AHEAD_GATE", "ROLLOUT_SKIP_AHEAD_GATE", "ROLLOUT_FORCE"):
        r = _run(world, "--host", "ec2", env_extra={name: "1", **_same_md5(world)})
        assert r.returncode == 1 and "not on origin/main" in r.stderr, name
    assert not (world["clone"] / "deploy" / "manifest").exists()
    assert "SKIP_AHEAD" not in open(os.path.join(DEPLOY, "rollout-manifest.sh")).read()


def test_health_mounts_and_checksum_are_read_from_the_container_id_after_a_recreate(world):
    r = _run(world, "--host", "ec2", "--recreate", env_extra={
        "STUB_MOUNTS": "/app/jurisdictions.yaml ", "STUB_MOUNTS_AFTER": "/app/manifest ", **_same_md5(world)})
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _docker_calls(world)
    recreate = next(i for i, c in enumerate(calls) if c.startswith("docker compose"))
    after = [c for c in calls[recreate + 1:] if c.startswith(("docker inspect", "docker exec"))]
    assert any("Health" in c for c in after) and any(c.startswith("docker exec") for c in after)
    for c in after:
        if "{{.Id}}" in c:
            continue                                   # the one lookup of the new id, by name
        assert "newcontainerid0000" in c, c           # everything else targets the NEW id,
        assert "ddp-openstates-api-1" not in c, c      # never the name
    before = [c for c in calls[:recreate] if "Mounts" in c]
    assert before and all("oldcontainerid0000" in c for c in before)
