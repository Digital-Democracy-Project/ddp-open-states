"""OPEN-633 (D2): deploy-scrapers-image.sh's task-definition step gives the ddp-scrapers task
definition the RDS secret once, and every later revision copies it forward.

Runs the script's own embedded Python (the heredoc that turns the current task definition into
the one it registers) against a stand-in task definition, so no AWS call is made."""

import json
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ARN = "arn:aws:secretsmanager:us-east-1:111122223333:secret:rds!db-example"


def _snippet():
    text = open(os.path.join(HERE, "deploy-scrapers-image.sh")).read()
    m = re.search(r"TAG=\"\$TAG\" python3 - <<'EOF'\n(.*?)\nEOF\n", text, re.S)
    assert m, "the register step's embedded Python was not found"
    return m.group(1)


def _register(tmp_path, current, **env):
    src = _snippet().replace("/tmp/taskdef-current.json", str(tmp_path / "cur.json")) \
                    .replace("/tmp/taskdef-register.json", str(tmp_path / "reg.json"))
    (tmp_path / "cur.json").write_text(json.dumps(current))
    run_env = {k: v for k, v in os.environ.items() if not k.startswith("TASK_RDS_")}
    run_env.update(TAG="v99", **env)
    proc = subprocess.run([sys.executable, "-c", src], env=run_env, capture_output=True, text=True)
    out = json.loads((tmp_path / "reg.json").read_text()) if proc.returncode == 0 else None
    return proc, out


def _current(**container):
    return {"family": "ddp-scrapers", "revision": 72, "executionRoleArn": "arn:role/exec",
            "containerDefinitions": [dict({"name": "scraper", "image": "repo/ddp-scrapers:v69",
                                           "environment": [{"name": "KEEP", "value": "1"}]},
                                          **container)]}


ADDR = {"TASK_RDS_HOST": "db.example.internal", "TASK_RDS_PORT": "5432", "TASK_RDS_DBNAME": "openstates"}


def test_adds_the_rds_secret_and_address_when_asked(tmp_path):
    proc, td = _register(tmp_path, _current(), TASK_RDS_SECRET_ARN=ARN, **ADDR)
    assert proc.returncode == 0, proc.stderr
    c = td["containerDefinitions"][0]
    assert c["image"] == "repo/ddp-scrapers:v99"
    assert {s["name"]: s["valueFrom"] for s in c["secrets"]} == {
        "RDS_USERNAME": ARN + ":username::", "RDS_PASSWORD": ARN + ":password::"}
    assert {e["name"]: e["value"] for e in c["environment"]} == {
        "KEEP": "1", "RDS_HOST": "db.example.internal", "RDS_PORT": "5432", "RDS_DBNAME": "openstates"}
    assert "revision" not in td


def test_a_later_image_copies_the_secret_forward_without_being_asked(tmp_path):
    _, first = _register(tmp_path, _current(), TASK_RDS_SECRET_ARN=ARN, **ADDR)
    proc, second = _register(tmp_path, first)
    assert proc.returncode == 0, proc.stderr
    assert second["containerDefinitions"][0]["secrets"] == first["containerDefinitions"][0]["secrets"]
    assert second["containerDefinitions"][0]["environment"] == first["containerDefinitions"][0]["environment"]
    assert "RDS secret in task definition: yes" in proc.stdout


def test_asking_again_replaces_rather_than_duplicates(tmp_path):
    _, first = _register(tmp_path, _current(), TASK_RDS_SECRET_ARN=ARN, **ADDR)
    proc, again = _register(tmp_path, first, TASK_RDS_SECRET_ARN=ARN + "-new", **ADDR)
    assert proc.returncode == 0, proc.stderr
    names = [s["name"] for s in again["containerDefinitions"][0]["secrets"]]
    assert sorted(names) == ["RDS_PASSWORD", "RDS_USERNAME"]
    assert all(s["valueFrom"].startswith(ARN + "-new:") for s in again["containerDefinitions"][0]["secrets"])
    assert len(again["containerDefinitions"][0]["environment"]) == 4


def test_without_being_asked_nothing_is_added(tmp_path):
    proc, td = _register(tmp_path, _current())
    assert proc.returncode == 0, proc.stderr
    assert "secrets" not in td["containerDefinitions"][0]
    assert "RDS secret in task definition: no" in proc.stdout


@pytest.mark.parametrize("drop", ["TASK_RDS_HOST", "TASK_RDS_PORT", "TASK_RDS_DBNAME"])
def test_refuses_a_secret_without_its_full_address(tmp_path, drop):
    addr = {k: v for k, v in ADDR.items() if k != drop}
    proc, td = _register(tmp_path, _current(), TASK_RDS_SECRET_ARN=ARN, **addr)
    assert proc.returncode != 0 and td is None
    assert drop in proc.stderr


def test_refuses_when_the_task_definition_has_no_execution_role(tmp_path):
    cur = _current()
    del cur["executionRoleArn"]
    proc, td = _register(tmp_path, cur, TASK_RDS_SECRET_ARN=ARN, **ADDR)
    assert proc.returncode != 0 and td is None
