"""deploy-scrapers-image.sh's task-definition step (OPEN-633, OPEN-639).

Each image is registered on two families: `ddp-scrapers` (collection and probe tasks) and `ddp-scrapers-db` (load and
archive tasks). Only the DB family may carry the database login (OPEN-639): ECS injects a definition's secrets into
every task started from it, and collection tasks parse outside websites. The secret is added once, when asked, and
every later revision copies it forward.

Runs the script's own embedded Python (the heredoc that turns the current definitions into the ones it registers)
against stand-in task definitions, so no AWS call is made."""

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
    run_env = {k: v for k, v in os.environ.items() if not k.startswith("TASK_RDS_")}
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
