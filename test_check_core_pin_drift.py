"""
Tests for check-core-pin-drift.py (OPEN-579, OPEN-586): the scrapers image's openstates-core and the core installed in
each api-v3 container must be one commit. Both builds take core's main; there is no pin file.

Same discipline as test_check_jurisdiction_drift.py: a world in which everything agrees, then one planted
disagreement per source, each of which must fail and name both commits. Docker is replaced by a stub (no daemon, no
network); refresh-api-v3.sh is run for real against temp directories with stub docker / docker-compose on PATH.
"""

import importlib.util
import io
import json
import os
import re
import shutil
import stat
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("check_core_pin_drift", os.path.join(HERE, "check-core-pin-drift.py"))
drift = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(drift)

A = "96445eb26d7d4c59c592dadc0261c47d985e6d46"
B = "eec94082" + "0" * 32
URL = "https://github.com/Digital-Democracy-Project/openstates-core/archive/{}.tar.gz"
def _direct_url(sha):
    return json.dumps({"archive_info": {}, "url": URL.format(sha)})


@pytest.fixture
def docker(monkeypatch):
    """Stub for drift._run: `docker run ... cat <record>` and `docker exec <container> python -c ...`."""
    state = {"image": {"img:v61": A}, "installed": {"ddp-openstates-api-1": _direct_url(A)}, "calls": []}

    def fake_run(cmd):
        state["calls"].append(cmd)
        assert cmd[0] == "docker"
        if cmd[1] == "run":
            image = cmd[5]
            if image not in state["image"]:
                raise drift.SourceError(f"`{' '.join(cmd)}` exited 1: cat: {drift.IMAGE_RECORD}: No such file")
            return state["image"][image] + "\n"
        if cmd[1] == "exec":
            container = cmd[2]
            if container not in state["installed"]:
                raise drift.SourceError(f"`{' '.join(cmd)}` exited 1: No such container: {container}")
            return state["installed"][container] + "\n"
        raise AssertionError(cmd)

    monkeypatch.setattr(drift, "_run", fake_run)
    return state


def _check(image="img:v61", image_core=None, containers=("ddp-openstates-api-1",)):
    out = io.StringIO()
    rc = drift.run(image, image_core, list(containers), out)
    return rc, out.getvalue()


# --- all agree ---------------------------------------------------------------------------------

def test_passes_when_image_and_container_agree(docker):
    rc, out = _check()
    assert rc == 0, out
    assert f"OK: the scrapers image and 1 api-v3 container(s) all run core {A}" in out


def test_passes_with_image_core_given_and_two_containers(docker):
    docker["installed"]["api-ec2"] = _direct_url(A)
    rc, out = _check(image=None, image_core=A, containers=("ddp-openstates-api-1", "api-ec2"))
    assert rc == 0, out


# --- one planted mismatch per source: exit 1, both commits named -------------------------------------

def test_image_mismatch_fails_naming_both_commits(docker):
    docker["image"]["img:v61"] = B
    rc, out = _check()
    assert rc == 1, out
    drift_lines = [l for l in out.splitlines() if l.startswith("DRIFT")]
    assert len(drift_lines) == 1 and A in drift_lines[0] and B in drift_lines[0], out


def test_image_core_mismatch_fails_naming_both_commits(docker):
    rc, out = _check(image=None, image_core=B)
    assert rc == 1 and re.search(rf"DRIFT .*{A}.*{B}", out), out


def test_installed_mismatch_fails_naming_both_commits(docker):
    """api-v3 rebuilt after a core merge without a new scrapers image (OPEN-586's one real risk)."""
    docker["installed"]["ddp-openstates-api-1"] = _direct_url(B)
    rc, out = _check()
    assert rc == 1 and re.search(rf"DRIFT installed in ddp-openstates-api-1 is {B}, but image img:v61 is {A}", out), out
    assert "ship a scrapers image first" in out and "the image, then any stored recompute, then api-v3" in out, out


def test_two_containers_agreeing_with_each_other_but_not_the_image_both_drift(docker):
    """Both api-v3 copies rebuilt from a newer main than the image: each is compared with the image, not each other."""
    docker["installed"]["ddp-openstates-api-1"] = _direct_url(B)
    docker["installed"]["api-ec2"] = _direct_url(B)
    rc, out = _check(containers=("ddp-openstates-api-1", "api-ec2"))
    assert rc == 1, out
    drift_lines = [l for l in out.splitlines() if l.startswith("DRIFT")]
    assert len(drift_lines) == 2 and all(A in l and B in l for l in drift_lines), out


def test_one_of_two_containers_drifting_fails(docker):
    docker["installed"]["api-ec2"] = _direct_url(B)
    rc, out = _check(containers=("ddp-openstates-api-1", "api-ec2"))
    assert rc == 1 and "DRIFT installed in api-ec2" in out and "ddp-openstates-api-1 is" not in out, out


def test_pypi_openstates_in_the_container_is_drift(docker):
    """PyPI's openstates says 6.26.5 too; no direct_url.json means it is not the fork at a commit."""
    docker["installed"]["ddp-openstates-api-1"] = ""
    rc, out = _check()
    assert rc == 1 and "not an archive install of the fork" in out, out


def test_a_non_fork_archive_url_is_drift(docker):
    docker["installed"]["ddp-openstates-api-1"] = json.dumps(
        {"url": f"https://github.com/openstates/openstates-core/archive/{A}.tar.gz"})
    rc, out = _check()
    assert rc == 1, out


@pytest.mark.parametrize("url", [
    f"https://example.invalid/?next=https://github.com/Digital-Democracy-Project/openstates-core/archive/{A}.tar.gz",
    URL.format(A) + ".evil",
    URL.format(A).replace("https://", "http://"),
    None, 123, ["x"],
])
def test_an_installed_url_that_is_not_exactly_the_fork_archive_is_drift(docker, url):
    docker["installed"]["ddp-openstates-api-1"] = json.dumps({"url": url})
    rc, out = _check()
    assert rc == 1 and "not an archive install of the fork" in out, out


@pytest.mark.parametrize("payload", ["[]", "null", '"text"', "not json"])
def test_installed_metadata_of_the_wrong_shape_is_an_error_not_a_crash(docker, payload):
    docker["installed"]["ddp-openstates-api-1"] = payload
    rc, out = _check()
    assert rc == 2 and "ERROR installed:" in out, out


# --- unreadable sources: exit 2, never a pass -------------------------------------------------------

def test_image_without_a_record_is_an_error_not_a_pass(docker):
    rc, out = _check(image="img:v60")
    assert rc == 2 and "has no readable /opt/openstates-core/DDP_CORE_COMMIT" in out and "--image-core" in out, out


def test_image_record_that_is_not_a_full_sha_is_an_error(docker):
    docker["image"]["img:v61"] = A[:9]
    rc, out = _check()
    assert rc == 2, out


@pytest.mark.parametrize("image,image_core", [(None, None), ("img:v61", A), (None, A[:9])])
def test_image_source_must_be_exactly_one_full_commit(docker, image, image_core):
    rc, out = _check(image=image, image_core=image_core)
    assert rc == 2, out


@pytest.mark.parametrize("image,image_core", [("img:v61", None), (None, A)])
def test_an_image_with_no_container_to_compare_is_an_error_not_a_pass(docker, image, image_core):
    rc, out = _check(image=image, image_core=image_core, containers=())
    assert rc == 2 and "no api-v3 container given" in out, out


def test_container_not_running_is_an_error(docker):
    rc, out = _check(containers=("ddp-openstates-api-1", "gone"))
    assert rc == 2 and "No such container: gone" in out, out


# --- the real files ---------------------------------------------------------------------------------

def test_the_dockerfile_records_the_core_commit_where_the_checker_and_deploy_script_read_it():
    dockerfile = open(os.path.join(HERE, "Dockerfile")).read()
    write = dockerfile.index(f"git -C /opt/openstates-core rev-parse HEAD > {drift.IMAGE_RECORD}")
    assert write < dockerfile.index("rm -rf /opt/openstates-core/.git"), "the record must be written before .git is deleted"
    assert drift.IMAGE_RECORD in open(os.path.join(HERE, "deploy-scrapers-image.sh")).read()


def test_the_api_v3_build_installs_core_main_at_a_commit_the_checker_can_read():
    """deploy/Dockerfile.ddp (the build both api-v3 copies use) resolves main to a commit with a remote ADD (re-fetched
    every build, so the cache never keeps an old core) and installs the fork archive at that commit, whose URL is what
    pip records in direct_url.json. An install of `archive/main.tar.gz` would record no commit."""
    dockerfile = open(os.path.join(HERE, "deploy", "Dockerfile.ddp")).read()
    add = re.search(r"^ADD https://api\.github\.com/repos/Digital-Democracy-Project/openstates-core/git/ref/heads/main "
                    r"(/tmp/\S+)$", dockerfile, re.M)
    assert add and f"json.load(open('{add.group(1)}'))['object']['sha']" in dockerfile, "main must be resolved by an ADD"
    add = add.start()
    m = re.search(r'"openstates @ (https://\S+/archive/)\$\{sha\}(\.tar\.gz)"', dockerfile)
    assert m and add < m.start(), "the archive must be installed at the commit resolved from main"
    assert drift._fork_sha(m.group(1) + A + m.group(2)) == A
    assert "--no-deps --ignore-requires-python" in dockerfile
    assert "ddp-openstates-core.txt" not in dockerfile


def test_the_pin_option_is_gone():
    with pytest.raises(SystemExit):
        drift.main(["check-core-pin-drift.py", "--pin", "x", "--image-core", A], out=io.StringIO())


def test_commits_sharing_a_short_prefix_still_differ(docker):
    """The whole SHA is compared, not the 9-character form the ops notes use."""
    near = A[:-1] + ("0" if A[-1] != "0" else "1")
    docker["image"]["img:v61"] = near
    rc, out = _check()
    assert rc == 1 and near in out and A in out, out


# --- refresh-api-v3.sh ends with the check ----------------------------------------------------------

STUB_DOCKER = """#!/usr/bin/env bash
case "$1" in
  exec) [ "$STUB_INSTALLED" = none ] && echo "" || echo "{\\"url\\": \\"https://github.com/Digital-Democracy-Project/openstates-core/archive/$STUB_INSTALLED.tar.gz\\"}"; exit 0;;
  run) echo "$STUB_IMAGE"; exit 0;;
esac
case "$*" in
  *StartedAt*) echo "2026-11-03T00:00:00Z";;
  *Health.Status*) echo "healthy";;
esac
exit 0
"""


@pytest.fixture
def refresh_host(tmp_path):
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "sync-manifest.sh").write_text("exit 0\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("docker", STUB_DOCKER), ("docker-compose", "#!/usr/bin/env bash\nexit 0\n")):
        p = bin_dir / name
        p.write_text(body)
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
    origin, api_v3 = tmp_path / "origin.git", tmp_path / "api-v3"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(api_v3)], check=True, capture_output=True)
    for cmd in (["git", "config", "user.email", "t@t"], ["git", "config", "user.name", "t"]):
        subprocess.run(cmd, cwd=api_v3, check=True)
    (api_v3 / "README.md").write_text("api-v3 (no pin file since OPEN-586)\n")
    subprocess.run(["git", "add", "."], cwd=api_v3, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=api_v3, check=True)
    subprocess.run(["git", "push", "-q", "origin", "main"], cwd=api_v3, check=True, capture_output=True)
    script = tmp_path / "refresh-api-v3.sh"
    shutil.copy(os.path.join(HERE, "refresh-api-v3.sh"), script)
    return dict(tmp=tmp_path, deploy=deploy, bin=bin_dir, api_v3=api_v3, script=script)


def _refresh(h, **env):
    e = dict(os.environ, PATH=f"{h['bin']}:{os.environ['PATH']}", COMPOSE_DIR=str(h["deploy"]),
             LOG=str(h["tmp"] / "os-api.log"), API_V3_DIR=str(h["api_v3"]), REPO_DIR=HERE,
             STUB_INSTALLED=A, STUB_IMAGE=A)
    e.pop("SCRAPERS_IMAGE", None)
    e.pop("SCRAPERS_IMAGE_CORE", None)
    e.update(env)
    return subprocess.run(["bash", str(h["script"])], env=e, capture_output=True, text=True, timeout=60)


def test_refresh_passes_when_all_agree(refresh_host):
    r = _refresh(refresh_host, SCRAPERS_IMAGE="img:v61")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"all run core {A}" in r.stdout


def test_refresh_fails_on_a_planted_image_mismatch(refresh_host):
    r = _refresh(refresh_host, SCRAPERS_IMAGE_CORE=B)
    assert r.returncode == 1, r.stdout + r.stderr
    assert A in r.stdout and B in r.stdout and "FATAL: core pin drift check exited 1" in r.stdout


def test_refresh_fails_on_a_planted_container_mismatch(refresh_host):
    r = _refresh(refresh_host, SCRAPERS_IMAGE="img:v61", STUB_INSTALLED=B)
    assert r.returncode == 1, r.stdout + r.stderr


def test_refresh_without_an_image_fails_rather_than_passing_unchecked(refresh_host):
    r = _refresh(refresh_host)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "no scrapers image given" in r.stdout
