"""deploy-scrapers-image.sh's task-definition step (OPEN-633, OPEN-639).

Each image is registered on two families: `ddp-scrapers` (collection and probe tasks) and `ddp-scrapers-db` (load and
archive tasks). Only the DB family may carry the database login (OPEN-639): ECS injects a definition's secrets into
every task started from it, and collection tasks parse outside websites. The secret is added once, when asked, and
every later revision copies it forward.

Runs the script's own embedded Python (the heredoc that turns the current definitions into the ones it registers)
against stand-in task definitions, so no AWS call is made.

OPEN-860: the image is built on the Mac's test Docker VM, never the main one. Those tests run the real script (or its
"0a. Which Docker" block) with stand-in `colima-test.sh`, `docker`, `aws` and `git` commands that only record what they
are asked, so nothing is built, pushed or registered."""

import json
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ARN = "arn:aws:secretsmanager:us-east-1:111122223333:secret:rds!db-example"
NOT_FOUND = ("An error occurred (ClientException) when calling the DescribeTaskDefinition operation: "
             "Unable to describe task definition.")
ADDR = {"TASK_RDS_HOST": "db.example.internal", "TASK_RDS_PORT": "5432", "TASK_RDS_DBNAME": "openstates"}


def _snippet():
    text = open(os.path.join(HERE, "deploy-scrapers-image.sh")).read()
    m = re.search(r"TAG=\"\$TAG\" python3 - <<'EOF'\n(.*?)\nEOF\n", text, re.S)
    assert m, "the register step's embedded Python was not found"
    return m.group(1)


def _register(tmp_path, current, db_current=None, **env):
    """Run the step; returns (process, the ddp-scrapers definition to register, the ddp-scrapers-db one)."""
    paths = {name: str(tmp_path / name) for name in ("cur.json", "db.json", "reg.json", "dbreg.json", "rc", "err")}
    src = (_snippet().replace("/tmp/taskdef-current.json", paths["cur.json"])
           .replace("/tmp/taskdef-db-current.json", paths["db.json"])
           .replace("/tmp/taskdef-db-describe.rc", paths["rc"])
           .replace("/tmp/taskdef-db-describe.err", paths["err"])
           .replace("/tmp/taskdef-register.json", paths["reg.json"])
           .replace("/tmp/taskdef-db-register.json", paths["dbreg.json"]))
    (tmp_path / "cur.json").write_text(json.dumps(current))
    if isinstance(db_current, dict):
        (tmp_path / "db.json").write_text(json.dumps(db_current))
        (tmp_path / "rc").write_text("0\n")
        (tmp_path / "err").write_text("")
    else:  # the describe failed; db_current is its error text (None: the family does not exist yet)
        (tmp_path / "db.json").write_text("")
        (tmp_path / "rc").write_text("254\n")
        (tmp_path / "err").write_text(db_current or NOT_FOUND)
    for name in ("reg.json", "dbreg.json"):
        if os.path.exists(paths[name]):
            os.remove(paths[name])
    run_env = {k: v for k, v in os.environ.items()
               if not k.startswith("TASK_") and k not in ("DB_DROP_PLAIN_ENV", "COLLECTION_PLAIN_TO_SECRET")}
    run_env.update(TAG="v99", **env)
    proc = subprocess.run([sys.executable, "-c", src], env=run_env, capture_output=True, text=True)
    if proc.returncode != 0:
        return proc, None, None
    return proc, json.loads((tmp_path / "reg.json").read_text()), json.loads((tmp_path / "dbreg.json").read_text())


def _current(family="ddp-scrapers", **container):
    return {"family": family, "revision": 72, "executionRoleArn": "arn:role/exec", "taskRoleArn": "arn:role/task",
            "containerDefinitions": [dict({"name": "scraper", "image": "repo/ddp-scrapers:v69",
                                           "environment": [{"name": "KEEP", "value": "1"}]},
                                          **container)]}


def _secrets(td):
    return {s["name"]: s["valueFrom"] for s in td["containerDefinitions"][0].get("secrets", [])}


def _env(td):
    return {e["name"]: e["value"] for e in td["containerDefinitions"][0].get("environment", [])}


def test_the_first_release_creates_the_db_family_from_ddp_scrapers(tmp_path):
    proc, main, db = _register(tmp_path, _current())
    assert proc.returncode == 0, proc.stderr
    assert main["family"] == "ddp-scrapers" and db["family"] == "ddp-scrapers-db"
    for td in (main, db):
        assert td["containerDefinitions"][0]["image"] == "repo/ddp-scrapers:v99"
        assert td["executionRoleArn"] == "arn:role/exec" and "revision" not in td
    assert _secrets(main) == {} and _secrets(db) == {}
    assert "RDS secret in ddp-scrapers: no" in proc.stdout and "RDS secret in ddp-scrapers-db: no" in proc.stdout


def test_the_secret_goes_on_the_db_family_only(tmp_path):
    proc, main, db = _register(tmp_path, _current(), _current("ddp-scrapers-db"), TASK_RDS_SECRET_ARN=ARN, **ADDR)
    assert proc.returncode == 0, proc.stderr
    assert _secrets(db) == {"RDS_USERNAME": ARN + ":username::", "RDS_PASSWORD": ARN + ":password::"}
    assert _env(db) == {"KEEP": "1", "RDS_HOST": "db.example.internal", "RDS_PORT": "5432", "RDS_DBNAME": "openstates"}
    # the collection family gets neither the secret nor the address
    assert _secrets(main) == {}
    assert _env(main) == {"KEEP": "1"}
    assert "RDS secret in ddp-scrapers: no" in proc.stdout and "RDS secret in ddp-scrapers-db: yes" in proc.stdout


def test_a_later_image_copies_the_db_secret_forward_without_being_asked(tmp_path):
    _, _, first_db = _register(tmp_path, _current(), _current("ddp-scrapers-db"), TASK_RDS_SECRET_ARN=ARN, **ADDR)
    proc, main, db = _register(tmp_path, _current(), dict(first_db, revision=73))
    assert proc.returncode == 0, proc.stderr
    assert _secrets(db) == _secrets(first_db) and _env(db) == _env(first_db)
    assert _secrets(main) == {}


def test_asking_again_replaces_rather_than_duplicates(tmp_path):
    _, _, first_db = _register(tmp_path, _current(), _current("ddp-scrapers-db"), TASK_RDS_SECRET_ARN=ARN, **ADDR)
    proc, _, db = _register(tmp_path, _current(), first_db, TASK_RDS_SECRET_ARN=ARN + "-new", **ADDR)
    assert proc.returncode == 0, proc.stderr
    assert sorted(_secrets(db)) == ["RDS_PASSWORD", "RDS_USERNAME"]
    assert all(v.startswith(ARN + "-new:") for v in _secrets(db).values())
    assert len(_env(db)) == 4


@pytest.mark.parametrize("entry", [
    {"secrets": [{"name": "RDS_PASSWORD", "valueFrom": ARN + ":password::"}]},
    {"secrets": [{"name": "RDS_HOST", "valueFrom": ARN + ":host::"}]},
    {"secrets": [{"name": "RDS_ANYTHING", "valueFrom": ARN + ":x::"}]},
    {"secrets": [{"name": "DATABASE_URL", "valueFrom": ARN}]},
    {"environment": [{"name": "RDS_HOST", "value": "db.example.internal"}]},
    {"environment": [{"name": "RDS_USERNAME", "value": "owner"}]},
    {"environment": [{"name": "DATABASE_URL", "value": "postgresql://x"}]},
])
def test_refuses_to_release_while_ddp_scrapers_carries_the_login(tmp_path, entry):
    proc, main, db = _register(tmp_path, _current(**entry), _current("ddp-scrapers-db"))
    assert proc.returncode != 0 and main is None and db is None
    assert "OPEN-639" in proc.stderr
    assert ":password::" not in proc.stderr and "db.example.internal" not in proc.stderr


@pytest.mark.parametrize("drop", ["TASK_RDS_HOST", "TASK_RDS_PORT", "TASK_RDS_DBNAME"])
def test_refuses_a_secret_without_its_full_address(tmp_path, drop):
    addr = {k: v for k, v in ADDR.items() if k != drop}
    proc, main, db = _register(tmp_path, _current(), _current("ddp-scrapers-db"), TASK_RDS_SECRET_ARN=ARN, **addr)
    assert proc.returncode != 0 and db is None
    assert drop in proc.stderr


def test_refuses_when_the_db_family_has_no_execution_role(tmp_path):
    db = _current("ddp-scrapers-db")
    del db["executionRoleArn"]
    proc, _, out = _register(tmp_path, _current(), db, TASK_RDS_SECRET_ARN=ARN, **ADDR)
    assert proc.returncode != 0 and out is None


@pytest.mark.parametrize("err", [
    "An error occurred (AccessDeniedException) when calling the DescribeTaskDefinition operation: not authorized",
    "An error occurred (ThrottlingException) when calling the DescribeTaskDefinition operation: Rate exceeded",
    "Could not connect to the endpoint URL",
    # the phrase alone is not enough: it must be ECS's own not-found answer, and the whole of it
    "An error occurred (AccessDeniedException) when calling the DescribeTaskDefinition operation: "
    "Unable to describe task definition.",
    NOT_FOUND + " Additionally, the request was throttled",
])
def test_any_other_failure_reading_the_db_family_stops_the_release(tmp_path, err):
    """Only AWS's "does not exist" answer creates ddp-scrapers-db; an access, throttling or network error must not
    rebuild it from ddp-scrapers (that would drop its secret)."""
    proc, main, db = _register(tmp_path, _current(), err, TASK_RDS_SECRET_ARN=ARN, **ADDR)
    assert proc.returncode != 0 and main is None and db is None
    assert "not rebuilt" in proc.stderr


# --- OPEN-880: scraper API keys out of plain settings. The values below are obviously fake; no test may let one reach
# the script's output.
KEYS = ("VA_API_KEY", "CONGRESS_GOV_API_KEY")
ARN_VA = "arn:aws:secretsmanager:us-east-1:111122223333:secret:scrapers-va-example"
ARN_CG = "arn:aws:secretsmanager:us-east-1:111122223333:secret:scrapers-cg-example"
ARNS = {"TASK_VA_API_KEY_SECRET_ARN": ARN_VA, "TASK_CONGRESS_GOV_API_KEY_SECRET_ARN": ARN_CG}
PLAIN = [{"name": "VA_API_KEY", "value": "fake-value-1"}, {"name": "CONGRESS_GOV_API_KEY", "value": "fake-value-2"},
         {"name": "KEEP", "value": "1"}]
TO_SECRET = ",".join(KEYS)


def _no_values(proc):
    assert "fake-value" not in proc.stdout + proc.stderr


def test_the_db_family_loses_the_named_plain_entries_only(tmp_path):
    proc, main, db = _register(tmp_path, _current(environment=PLAIN), _current("ddp-scrapers-db", environment=PLAIN),
                               DB_DROP_PLAIN_ENV=TO_SECRET)
    assert proc.returncode == 0, proc.stderr
    assert _env(db) == {"KEEP": "1"}
    assert set(_env(main)) == {"KEEP", *KEYS}  # the collection family is not touched by this variable
    assert "ddp-scrapers-db: plain entries removed: VA_API_KEY, CONGRESS_GOV_API_KEY" in proc.stdout
    _no_values(proc)


def test_nothing_is_removed_by_default(tmp_path):
    proc, main, db = _register(tmp_path, _current(environment=PLAIN), _current("ddp-scrapers-db", environment=PLAIN))
    assert proc.returncode == 0, proc.stderr
    assert set(_env(db)) == {"KEEP", *KEYS} and set(_env(main)) == {"KEEP", *KEYS}


def test_a_db_removal_of_a_name_not_present_says_so(tmp_path):
    proc, _, db = _register(tmp_path, _current(), _current("ddp-scrapers-db"), DB_DROP_PLAIN_ENV="VA_API_KEY")
    assert proc.returncode == 0, proc.stderr
    assert "(none were present)" in proc.stdout and _env(db) == {"KEEP": "1"}


def test_refuses_when_the_db_family_still_has_a_name_after_the_removal(tmp_path):
    """A secrets entry is not a plain entry, so the removal cannot clear it: the release stops."""
    db = _current("ddp-scrapers-db", secrets=[{"name": "VA_API_KEY", "valueFrom": ARN_VA}])
    proc, main, out = _register(tmp_path, _current(), db, DB_DROP_PLAIN_ENV="VA_API_KEY")
    assert proc.returncode != 0 and main is None and out is None
    assert "VA_API_KEY" in proc.stderr and "OPEN-880" in proc.stderr


def test_the_collection_family_moves_the_names_to_secrets(tmp_path):
    proc, main, db = _register(tmp_path, _current(environment=PLAIN), _current("ddp-scrapers-db"),
                               COLLECTION_PLAIN_TO_SECRET=TO_SECRET, **ARNS)
    assert proc.returncode == 0, proc.stderr
    assert _secrets(main) == {"VA_API_KEY": ARN_VA, "CONGRESS_GOV_API_KEY": ARN_CG}
    assert _env(main) == {"KEEP": "1"}
    assert _secrets(db) == {} and "KEEP" in _env(db)  # never on the db family
    assert "plain entry removed for: VA_API_KEY, CONGRESS_GOV_API_KEY" in proc.stdout
    _no_values(proc)


def test_each_name_gets_its_own_secret(tmp_path):
    proc, main, _ = _register(tmp_path, _current(environment=PLAIN), _current("ddp-scrapers-db"),
                              COLLECTION_PLAIN_TO_SECRET="VA_API_KEY", TASK_VA_API_KEY_SECRET_ARN=ARN_VA)
    assert proc.returncode == 0, proc.stderr
    assert _secrets(main) == {"VA_API_KEY": ARN_VA}
    assert set(_env(main)) == {"KEEP", "CONGRESS_GOV_API_KEY"}  # only the named entry moves


def test_a_later_release_copies_the_collection_secrets_forward(tmp_path):
    _, first, _ = _register(tmp_path, _current(environment=PLAIN), _current("ddp-scrapers-db"),
                            COLLECTION_PLAIN_TO_SECRET=TO_SECRET, **ARNS)
    proc, main, _ = _register(tmp_path, dict(first, revision=73), _current("ddp-scrapers-db"))
    assert proc.returncode == 0, proc.stderr
    assert _secrets(main) == _secrets(first) and _env(main) == {"KEEP": "1"}


def test_asking_again_replaces_a_collection_secret(tmp_path):
    _, first, _ = _register(tmp_path, _current(environment=PLAIN), _current("ddp-scrapers-db"),
                            COLLECTION_PLAIN_TO_SECRET=TO_SECRET, **ARNS)
    proc, main, _ = _register(tmp_path, first, _current("ddp-scrapers-db"), COLLECTION_PLAIN_TO_SECRET="VA_API_KEY",
                              TASK_VA_API_KEY_SECRET_ARN=ARN_VA + "-new")
    assert proc.returncode == 0, proc.stderr
    assert _secrets(main) == {"VA_API_KEY": ARN_VA + "-new", "CONGRESS_GOV_API_KEY": ARN_CG}
    assert len(main["containerDefinitions"][0]["secrets"]) == 2  # replaced, not appended beside the old one


def test_refuses_a_name_without_its_secret_arn(tmp_path):
    proc, main, db = _register(tmp_path, _current(environment=PLAIN), _current("ddp-scrapers-db"),
                               COLLECTION_PLAIN_TO_SECRET=TO_SECRET, TASK_VA_API_KEY_SECRET_ARN=ARN_VA)
    assert proc.returncode != 0 and main is None and db is None
    assert "TASK_CONGRESS_GOV_API_KEY_SECRET_ARN" in proc.stderr
    _no_values(proc)


def test_refuses_a_name_whose_secret_arn_is_empty(tmp_path):
    proc, main, _ = _register(tmp_path, _current(environment=PLAIN), _current("ddp-scrapers-db"),
                              COLLECTION_PLAIN_TO_SECRET="VA_API_KEY", TASK_VA_API_KEY_SECRET_ARN="")
    assert proc.returncode != 0 and main is None
    assert "TASK_VA_API_KEY_SECRET_ARN" in proc.stderr


@pytest.mark.parametrize("var", ["COLLECTION_PLAIN_TO_SECRET", "DB_DROP_PLAIN_ENV"])
def test_refuses_an_entry_that_is_not_a_variable_name(tmp_path, var):
    proc, main, _ = _register(tmp_path, _current(), _current("ddp-scrapers-db"), **{var: "VA_API_KEY,fake-value-1"})
    assert proc.returncode != 0 and main is None
    _no_values(proc)


@pytest.mark.parametrize("name", KEYS)
def test_refuses_a_collection_definition_with_a_plain_value_and_a_secret_for_one_name(tmp_path, name):
    """Even with no variable given: a carried-forward secret plus a plain entry someone added back."""
    both = _current(environment=PLAIN, secrets=[{"name": name, "valueFrom": ARN_VA}])
    proc, main, db = _register(tmp_path, both, _current("ddp-scrapers-db"))
    assert proc.returncode != 0 and main is None and db is None
    assert name in proc.stderr and [k for k in KEYS if k != name][0] not in proc.stderr
    _no_values(proc)


def test_a_json_key_of_a_multi_key_secret_is_accepted(tmp_path):
    """valueFrom may name one key of a shared secret: <arn>:<json-key>::"""
    shared = "arn:aws:secretsmanager:us-east-1:111122223333:secret:shared-example"
    proc, main, _ = _register(tmp_path, _current(environment=PLAIN), _current("ddp-scrapers-db"),
                              COLLECTION_PLAIN_TO_SECRET=TO_SECRET, TASK_VA_API_KEY_SECRET_ARN=shared + ":va_api_key::",
                              TASK_CONGRESS_GOV_API_KEY_SECRET_ARN=ARN_CG)
    assert proc.returncode == 0, proc.stderr
    assert _secrets(main) == {"VA_API_KEY": shared + ":va_api_key::", "CONGRESS_GOV_API_KEY": ARN_CG}


@pytest.mark.parametrize("bad", [
    "fake-value-1",
    "arn:aws:ssm:us-east-1:111122223333:parameter/x",
    "arn:aws:secretsmanager:us-east-1:111122223333:secret:",
    "arn:aws:secretsmanager:us-east-1:111122223333:secret:x:a:b",
    "arn:aws:secretsmanager:us-east-1:111122223333:secret:x:::",
    "arn:aws:secretsmanager:us-east-1:111122223333:secret:x:key:stage:id",
    "arn:aws:secretsmanager:us-east-1:111122223333:secret:x fake-value-1",
    " " + ARN_VA,
])
def test_refuses_a_value_that_is_not_a_secrets_manager_arn(tmp_path, bad):
    proc, main, _ = _register(tmp_path, _current(environment=PLAIN), _current("ddp-scrapers-db"),
                              COLLECTION_PLAIN_TO_SECRET="VA_API_KEY", TASK_VA_API_KEY_SECRET_ARN=bad)
    assert proc.returncode != 0 and main is None
    assert "TASK_VA_API_KEY_SECRET_ARN" in proc.stderr
    _no_values(proc)
    assert bad.strip() not in proc.stderr


@pytest.mark.parametrize("var", ["COLLECTION_PLAIN_TO_SECRET", "DB_DROP_PLAIN_ENV"])
def test_refuses_the_same_name_twice(tmp_path, var):
    proc, main, _ = _register(tmp_path, _current(environment=PLAIN), _current("ddp-scrapers-db"),
                              **{var: "VA_API_KEY,VA_API_KEY"}, **ARNS)
    assert proc.returncode != 0 and main is None


def test_a_refused_release_prints_no_success_line(tmp_path):
    """The collection move is fine but the db family refuses: nothing may claim a change was made."""
    db = _current("ddp-scrapers-db", secrets=[{"name": "VA_API_KEY", "valueFrom": ARN_VA}])
    proc, main, _ = _register(tmp_path, _current(environment=PLAIN), db, COLLECTION_PLAIN_TO_SECRET=TO_SECRET,
                              DB_DROP_PLAIN_ENV="VA_API_KEY", **ARNS)
    assert proc.returncode != 0 and main is None
    assert "secrets entries set" not in proc.stdout and "plain entries removed" not in proc.stdout
    _no_values(proc)


# ---- OPEN-860: the build runs on the test Docker VM, and only there ----------------------------------------------------

TEST_HOST = "unix:///Volumes/DDP-HOT/colima/test/docker.sock"


def _script_text():
    return open(os.path.join(HERE, "deploy-scrapers-image.sh")).read()


def _stand_ins(tmp_path, check_rc=0, check_msg="", info_ok=True, prune_ok=True, host=None):
    """A stand-in colima-test.sh and a bin/ of recording `docker`, `aws`, `git`: every call is appended to calls.log with the
    DOCKER_HOST it saw. Returns (colima script path, bin dir, calls.log path)."""
    log = tmp_path / "calls.log"
    colima = tmp_path / "colima-test.sh"
    colima.write_text(
        '#!/usr/bin/env bash\ncase "$1" in\n'
        f'  check) echo "{check_msg}" >&2; exit {check_rc} ;;\n'
        f'  docker-host) echo "{TEST_HOST if host is None else host}" ;;\n'
        '  *) exit 2 ;;\nesac\n')
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("docker", "aws", "git"):
        rc = "0"
        if name == "docker":
            rc = f'$( [ "$1" = info ] && {"echo 0" if info_ok else "echo 1"} || ([ "$1" = builder ] && {"echo 0" if prune_ok else "echo 1"} || echo 0) )'
        (bin_dir / name).write_text(f'#!/usr/bin/env bash\necho "{name} $* [DOCKER_HOST=${{DOCKER_HOST:-}}]" >> "{log}"\nexit {rc}\n')
        os.chmod(bin_dir / name, 0o755)
    return colima, bin_dir, log


def _run_script(tmp_path, **kw):
    colima, bin_dir, log = _stand_ins(tmp_path, **kw)
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path), "DDP_COLIMA_TEST_SH": str(colima)}
    proc = subprocess.run(["bash", os.path.join(HERE, "deploy-scrapers-image.sh")], env=env, capture_output=True, text=True)
    return proc, (log.read_text() if log.exists() else "")


def _block():
    """The script's own "0a. Which Docker" block and its cleanup trap, run alone."""
    m = re.search(r'(say "0a\. Which Docker.*?\ntrap cleanup EXIT\n)', _script_text(), re.S)
    assert m, "the Which Docker block was not found"
    return m.group(1)


def _run_block(tmp_path, tail="exit 0", **kw):
    colima, bin_dir, log = _stand_ins(tmp_path, **kw)
    prelude = ('say() { printf "\\n==> %s\\n" "$*"; }\ndie() { printf "\\nSTOP: %s\\n" "$*" >&2; exit 1; }\n'
               f'WORK={tmp_path}/work\nset -euo pipefail\n')
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path), "DDP_COLIMA_TEST_SH": str(colima)}
    proc = subprocess.run(["bash", "-c", prelude + _block() + tail], env=env, capture_output=True, text=True)
    return proc, (log.read_text() if log.exists() else "")


def test_test_vm_down_stops_the_script_before_any_docker_aws_or_git_call(tmp_path):
    proc, calls = _run_script(tmp_path, check_rc=3, check_msg="DDP-HOT is not mounted")
    assert proc.returncode != 0
    assert "the test Docker VM is not available" in proc.stderr and "Nothing was built" in proc.stderr
    assert "DDP-HOT is not mounted" in proc.stderr          # the colima-test.sh reason is passed on
    assert calls == ""                                       # no docker, no aws, no git: no build started, nothing pushed


def test_a_missing_colima_test_script_stops_it_too_and_never_falls_back(tmp_path):
    colima, bin_dir, log = _stand_ins(tmp_path)
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path), "DDP_COLIMA_TEST_SH": str(tmp_path / "nope.sh")}
    proc = subprocess.run(["bash", os.path.join(HERE, "deploy-scrapers-image.sh")], env=env, capture_output=True, text=True)
    assert proc.returncode != 0 and "cannot be used" in proc.stderr
    assert not log.exists()
    # an empty override is not "off": it falls back to the default path under HOME, which does not exist here either
    env["DDP_COLIMA_TEST_SH"] = ""
    proc = subprocess.run(["bash", os.path.join(HERE, "deploy-scrapers-image.sh")], env=env, capture_output=True, text=True)
    assert proc.returncode != 0 and "cannot be used" in proc.stderr and not log.exists()


def test_a_test_vm_that_is_set_up_but_not_running_stops_it(tmp_path):
    proc, calls = _run_script(tmp_path, info_ok=False)
    assert proc.returncode != 0 and "set up but not running" in proc.stderr and "colima start" in proc.stderr
    # it asked the TEST VM and stopped there: nothing was built, pushed or cloned, and there was no AWS call
    assert calls.splitlines() == [f"docker info [DOCKER_HOST={TEST_HOST}]"]


def test_every_docker_call_goes_to_the_test_vm_and_the_build_cache_is_emptied_there_on_exit(tmp_path):
    proc, calls = _run_block(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert f"Docker: the test VM ({TEST_HOST})" in proc.stdout
    lines = calls.splitlines()
    assert lines == [f"docker info [DOCKER_HOST={TEST_HOST}]", f"docker builder prune -af [DOCKER_HOST={TEST_HOST}]"]
    assert "build cache on the test VM emptied" in proc.stdout


def test_the_build_cache_is_emptied_on_a_failure_too_and_a_failed_prune_only_says_so(tmp_path):
    proc, calls = _run_block(tmp_path, tail="die 'a later check failed'")
    assert proc.returncode == 1 and "a later check failed" in proc.stderr
    assert calls.splitlines()[-1] == f"docker builder prune -af [DOCKER_HOST={TEST_HOST}]"
    (tmp_path / "second").mkdir()
    proc, calls = _run_block(tmp_path / "second", prune_ok=False)
    assert proc.returncode == 0 and "could not empty the build cache on the test VM" in proc.stdout
    assert f"DOCKER_HOST={TEST_HOST} docker builder prune -af" in proc.stdout


def test_no_docker_command_runs_before_the_test_vm_is_chosen_and_the_default_host_is_never_set():
    text = _script_text()
    before = text.split('say "0a. Which Docker', 1)[0]
    assert not re.search(r"^\s*(docker|DOCKER_BUILDKIT=1 docker)\s", before, re.M)
    assert "unix:///var/run/docker.sock" not in text and ".colima/default" not in text
    assert "TEST_DOCKER_HOST=$(bash" in text and "export DOCKER_HOST" in text
    # the build line itself is unchanged: same flags, no cache
    assert "docker build --no-cache --platform linux/arm64" in text and "--secret id=github_token,env=GITHUB_PERSONAL_ACCESS_TOKEN" in text


def test_the_core_check_it_prints_runs_against_the_test_vm():
    assert "DOCKER_HOST=$TEST_DOCKER_HOST python3 check-core-pin-drift.py --image $IMG" in _script_text()


def test_a_docker_host_in_the_dev_env_file_never_moves_the_build_or_the_cleanup_to_another_vm(tmp_path):
    """The script sources the dev .env after choosing the test VM. If that file ever sets DOCKER_HOST (it does not today), the
    build and the cache cleanup must still go to the test VM. The stand-in .env has no GitHub token, so the script stops at
    that check, before it clones or removes anything."""
    colima, bin_dir, log = _stand_ins(tmp_path)
    env_dir = tmp_path / "Developer" / "repos" / "ddp-open-states-dev"
    env_dir.mkdir(parents=True)
    (env_dir / ".env").write_text("DOCKER_HOST=unix:///Users/x/.colima/default/docker.sock\n")
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path), "DDP_COLIMA_TEST_SH": str(colima)}
    proc = subprocess.run(["bash", os.path.join(HERE, "deploy-scrapers-image.sh")], env=env, capture_output=True, text=True)
    assert proc.returncode != 0 and "GITHUB_PERSONAL_ACCESS_TOKEN not set" in proc.stderr
    docker_calls = [l for l in log.read_text().splitlines() if l.startswith("docker ")]
    assert docker_calls == [f"docker info [DOCKER_HOST={TEST_HOST}]", f"docker builder prune -af [DOCKER_HOST={TEST_HOST}]"]


def test_the_test_host_is_restored_right_after_the_dev_env_file_is_sourced_and_the_cleanup_names_it_itself():
    """Two independent guards, each pinned on its own (the run above only sees them together): the test host is put back
    straight after `source "$DEV_ENV"`, before any docker call, and the cache cleanup names the test host in its own command."""
    text = _script_text()
    src = text.index('set -a; source "$DEV_ENV"; set +a\n')
    restore = text.index("DOCKER_HOST=$TEST_DOCKER_HOST; export DOCKER_HOST", src)
    first_docker_after = re.search(r"^\s*(DOCKER_BUILDKIT=1 )?docker\s|\|\s*docker\s", text[src:], re.M)
    assert first_docker_after and src + first_docker_after.start() > restore
    assert "if DOCKER_HOST=$TEST_DOCKER_HOST docker builder prune -af" in text


@pytest.mark.parametrize("host", ["", "tcp://main.example:2375", "/Volumes/DDP-HOT/colima/test/docker.sock", "unix://"])
def test_a_missing_or_odd_socket_from_the_helper_stops_it_before_any_docker_call(tmp_path, host):
    """An empty DOCKER_HOST means Docker's default daemon, the main VM, and `docker info` would succeed there: so only a real
    unix:// socket address passes."""
    proc, calls = _run_script(tmp_path, host=host)
    assert proc.returncode != 0 and "Nothing was built" in proc.stderr and "unix:// address" in proc.stderr
    assert calls == ""


def test_the_runbooks_manual_steps_stop_unless_the_test_host_is_really_set():
    runbook = open(os.path.join(HERE, "RUNBOOK.md")).read()
    manual = runbook.split("cd /tmp/ddp-open-states-deploy", 1)[1].split("set -a && source .env", 1)[0]
    assert 'check && export DOCKER_HOST="$(bash "$CT" docker-host)" && [ -n "$DOCKER_HOST" ] && docker info' in manual
    assert 'eval "$(bash' not in manual
