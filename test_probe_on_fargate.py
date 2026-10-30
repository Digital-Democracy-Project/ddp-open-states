"""
Tests for probe-on-fargate (OPEN-460): which states are launched, what each task is told to run, how waves and
retries behave, and how the results are read back. No AWS is called: every ECS client here is a fake.
"""

import importlib.machinery
import importlib.util
import json
import os
import sys
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOADER = importlib.machinery.SourceFileLoader("probe_on_fargate", os.path.join(_HERE, "probe-on-fargate"))
_SPEC = importlib.util.spec_from_loader("probe_on_fargate", _LOADER)
pof = importlib.util.module_from_spec(_SPEC)
sys.modules["probe_on_fargate"] = pof
_LOADER.exec_module(pof)


class _FakeEcs:
    def __init__(self, fail_first=(), fail_always=(), raise_for=()):
        self.calls = []
        self.fail_first = set(fail_first)
        self.fail_always = set(fail_always)
        self.raise_for = set(raise_for)
        self.described = []

    def run_task(self, **kw):
        state = kw["overrides"]["containerOverrides"][0]["command"][0]
        self.calls.append(kw)
        if state in self.raise_for:
            raise RuntimeError("ThrottlingException")
        if state in self.fail_always or (state in self.fail_first and sum(
                1 for c in self.calls if c["overrides"]["containerOverrides"][0]["command"][0] == state) == 1):
            return {"tasks": [], "failures": [{"reason": "RESOURCE:CPU"}]}
        return {"tasks": [{"taskArn": f"arn:aws:ecs:us-east-1:000000000000:task/ddp-scrapers/id-{state}",
                           "taskDefinitionArn": "arn:aws:ecs:us-east-1:000000000000:task-definition/ddp-scrapers:42"}], "failures": []}

    def describe_tasks(self, cluster, tasks):
        self.described.append(list(tasks))
        return {"tasks": [
            {"taskArn": f"arn:x:task/ddp-scrapers/{t}", "lastStatus": "STOPPED" if t != "id-ga" else "RUNNING",
             "stoppedReason": "Essential container in task exited",
             "containers": [{"exitCode": {"id-co": 0, "id-in": 2, "id-oh": 4}.get(t, 0)}]}
            for t in tasks
        ], "failures": []}


def _called_states(ecs):
    return [c["overrides"]["containerOverrides"][0]["command"][0] for c in ecs.calls]


# ── which states ─────────────────────────────────────────────────────────────


def test_probeable_states_takes_every_bills_scraper_maps_usa_and_skips_michigan(tmp_path):
    for name, has in {"ak": "file", "usa": "file", "mi": "file", "xx": "dir", "utils": None, "ya": "nothing"}.items():
        d = tmp_path / name
        d.mkdir()
        if has == "file":
            (d / "bills.py").write_text("")
        elif has == "dir":
            (d / "bills").mkdir()
        elif has == "nothing":
            (d / "people.py").write_text("")
    (tmp_path / "stray.txt").write_text("")
    assert pof.probeable_states(str(tmp_path)) == ["ak", "us", "xx"]


def test_refusal_covers_michigan_nothing_to_launch_and_a_prod_prefix():
    assert "mi" in pof.refusal(["co", "mi"], "dev-probe-all-x")
    assert "no states" in pof.refusal([], "dev-probe-all-x")
    for prefix in ("prod", "PROD", "/prod/", "prod/probe"):
        assert "'prod'" in pof.refusal(["co"], prefix)
    assert pof.refusal(["co", "ga"], "dev-probe-all-20261030") is None


# ── what each task is told to run ────────────────────────────────────────────


def test_each_task_runs_the_probe_with_its_own_run_id_prefix_and_limits():
    ecs = _FakeEcs()
    task_id, error, revision = pof.launch_one(ecs, "co", "probe-co-20261030", "dev-probe-all-20261030", 10, 200)
    assert (task_id, error, revision) == ("id-co", None, "42")
    call = ecs.calls[0]
    assert call["cluster"] == "ddp-scrapers" and call["taskDefinition"] == "ddp-scrapers" and call["launchType"] == "FARGATE"
    assert call["networkConfiguration"]["awsvpcConfiguration"]["assignPublicIp"] == "ENABLED"
    override = call["overrides"]["containerOverrides"][0]
    assert override["name"] == "scraper"
    assert override["command"] == ["co", "--fargate", "--sample-bills", "10", "--max-objects", "200"]
    env = {e["name"]: e["value"] for e in override["environment"]}
    assert env == {"RUNNER_SCRIPT": "verify-jurisdiction", "RUN_ID": "probe-co-20261030", "MEMORY_PREFIX": "dev-probe-all-20261030"}


def test_a_launch_failure_or_exception_is_reported_not_raised():
    ecs = _FakeEcs(fail_always={"ga"}, raise_for={"oh"})
    assert pof.launch_one(ecs, "ga", "r", "p", 1, 1) == (None, "RESOURCE:CPU", None)
    task_id, error, _revision = pof.launch_one(ecs, "oh", "r", "p", 1, 1)
    assert task_id is None and "ThrottlingException" in error


# ── waves and retry ──────────────────────────────────────────────────────────


def test_launch_all_launches_in_waves_with_a_pause_between_them():
    ecs, pauses = _FakeEcs(), []
    entries = pof.launch_all(ecs, ["a", "b", "c", "d", "e"], "20261030", "dev-probe-all-20261030", 10, 200, 2, 30, sleep=pauses.append)
    assert _called_states(ecs) == ["a", "b", "c", "d", "e"]
    assert pauses == [30, 30]  # three waves of 2, 2 and 1
    assert all(e["task_id"] and e["error"] is None for e in entries.values())
    assert entries["a"]["run_id"] == "probe-a-20261030"


def test_a_state_that_could_not_be_placed_is_retried_once_after_the_last_wave():
    ecs, pauses = _FakeEcs(fail_first={"b"}), []
    entries = pof.launch_all(ecs, ["a", "b", "c"], "20261030", "p", 1, 1, 2, 30, sleep=pauses.append)
    assert _called_states(ecs) == ["a", "b", "c", "b"]
    assert entries["b"]["task_id"] == "id-b" and entries["b"]["error"] is None


def test_a_state_that_fails_twice_stays_not_launched_with_its_reason():
    ecs = _FakeEcs(fail_always={"b"})
    entries = pof.launch_all(ecs, ["a", "b"], "20261030", "p", 1, 1, 5, 0, sleep=lambda s: None)
    assert _called_states(ecs).count("b") == 2
    assert entries["b"]["task_id"] is None and entries["b"]["error"] == "RESOURCE:CPU"
    assert entries["a"]["task_id"] == "id-a"


# ── reading the results back ─────────────────────────────────────────────────


def test_status_names_what_each_exit_code_means_and_counts_the_outcomes():
    entries = {
        "co": {"run_id": "r", "task_id": "id-co", "error": None},
        "ga": {"run_id": "r", "task_id": "id-ga", "error": None},
        "in": {"run_id": "r", "task_id": "id-in", "error": None},
        "oh": {"run_id": "r", "task_id": "id-oh", "error": None},
        "tx": {"run_id": "r", "task_id": None, "error": "RESOURCE:CPU"},
    }
    ecs = _FakeEcs()
    status = pof.read_status(ecs, entries)
    assert ecs.described == [["id-co", "id-ga", "id-in", "id-oh"]]  # the unlaunched state is not asked about
    text = pof.format_status(entries, status)
    assert "finished, uploaded" in text and "image does not know an option" in text and "upload failed" in text
    assert "NOT LAUNCHED" in text and "RESOURCE:CPU" in text
    assert "5 state(s): 1 finished and uploaded, 2 stopped otherwise, 1 still running, 1 not launched" in text


# ── main ─────────────────────────────────────────────────────────────────────


def test_dry_run_prints_the_plan_and_calls_nothing(tmp_path, capsys):
    with patch.object(pof, "_ecs_client", side_effect=AssertionError("a dry run must not reach AWS")):
        assert pof.main(["co", "ga", "--dry-run", "--date", "20261030", "--out", str(tmp_path / "o")]) == 0
    out = capsys.readouterr().out
    assert "2 state(s)" in out and "dev-probe-all-20261030" in out and not (tmp_path / "o").exists()


def test_main_refuses_michigan_and_a_prod_prefix_before_calling_aws(tmp_path):
    with patch.object(pof, "_ecs_client", side_effect=AssertionError("must not reach AWS")):
        assert pof.main(["mi", "--out", str(tmp_path)]) == 3
        assert pof.main(["co", "--prefix", "prod", "--out", str(tmp_path)]) == 3
        assert pof.main(["--out", str(tmp_path)]) == 3  # nothing to launch


def test_all_reads_the_scrapers_directory(tmp_path, capsys):
    for name in ("ak", "mi", "usa"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "bills.py").write_text("")
    assert pof.main(["--all", "--dry-run", "--scrapers-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "2 state(s)" in out and out.rstrip().endswith("ak us")  # Michigan is left out, usa becomes us


def test_a_launch_is_recorded_and_status_reads_it_back(tmp_path, capsys):
    ecs = _FakeEcs()
    with patch.object(pof, "_ecs_client", return_value=ecs), patch.object(pof.time, "sleep", lambda s: None):
        assert pof.main(["co", "in", "--date", "20261030", "--out", str(tmp_path)]) == 0
        record = json.loads((tmp_path / "launched.json").read_text())
        assert record["prefix"] == "dev-probe-all-20261030" and set(record["entries"]) == {"co", "in"}
        assert pof.main(["--status", "--out", str(tmp_path)]) == 0
    assert "image does not know an option" in capsys.readouterr().out


def test_a_launch_with_a_state_that_never_started_exits_nonzero(tmp_path):
    with patch.object(pof, "_ecs_client", return_value=_FakeEcs(fail_always={"ga"})), patch.object(pof.time, "sleep", lambda s: None):
        assert pof.main(["co", "ga", "--out", str(tmp_path), "--wave-pause", "0"]) == 1
    assert json.loads((tmp_path / "launched.json").read_text())["entries"]["ga"]["task_id"] is None


def test_status_without_a_launch_record_says_so(tmp_path):
    assert pof.main(["--status", "--out", str(tmp_path)]) == 3


# ── review fixes: duplicates, idempotent retries, checkpoints, reruns, revisions ──


def test_states_are_normalised_and_deduplicated_before_anything_is_launched():
    assert pof.normalize_states(["CO", "usa", "us", "co", "ga"]) == ["co", "us", "ga"]


def test_main_launches_one_task_per_state_however_it_is_spelled(tmp_path):
    ecs = _FakeEcs()
    with patch.object(pof, "_ecs_client", return_value=ecs), patch.object(pof.time, "sleep", lambda s: None):
        assert pof.main(["co", "CO", "usa", "us", "--out", str(tmp_path)]) == 0
    assert _called_states(ecs) == ["co", "us"]
    assert set(json.loads((tmp_path / "launched.json").read_text())["entries"]) == {"co", "us"}


def test_the_idempotency_token_is_stable_per_state_and_differs_between_states_and_prefixes():
    a = pof.client_token("dev-probe-all-20261030", "probe-co-20261030")
    assert a == pof.client_token("dev-probe-all-20261030", "probe-co-20261030")
    assert a != pof.client_token("dev-probe-all-20261030", "probe-ga-20261030")
    assert a != pof.client_token("dev-probe-all-20261101", "probe-co-20261030")
    assert len(a) <= 64 and a.isalnum()


class _AcceptsThenTimesOut:
    """ECS accepted the first request but the answer never arrived; a repeat with the same token returns the same task."""

    def __init__(self):
        self.started = {}
        self.timed_out = False

    def run_task(self, **kw):
        token = kw["clientToken"]
        if token not in self.started:
            self.started[token] = f"arn:x:task/ddp-scrapers/t{len(self.started)}"
            if not self.timed_out:
                self.timed_out = True
                raise TimeoutError("read timeout")
        return {"tasks": [{"taskArn": self.started[token], "taskDefinitionArn": "arn:x:task-definition/ddp-scrapers:42"}], "failures": []}


def test_a_retry_after_a_timeout_that_hid_a_success_does_not_start_a_second_task():
    ecs = _AcceptsThenTimesOut()
    entries = pof.launch_all(ecs, ["co"], "20261030", "p", 1, 1, 5, 0, sleep=lambda s: None)
    assert len(ecs.started) == 1 and entries["co"]["task_id"] == "t0"


def test_every_launch_is_checkpointed_so_an_interruption_leaves_the_task_ids(tmp_path):
    class Interrupted(_FakeEcs):
        def run_task(self, **kw):
            if len(self.calls) == 2:
                raise KeyboardInterrupt
            return super().run_task(**kw)

    import pytest

    with patch.object(pof, "_ecs_client", return_value=Interrupted()), patch.object(pof.time, "sleep", lambda s: None):
        with pytest.raises(KeyboardInterrupt):
            pof.main(["a", "b", "c", "d", "--out", str(tmp_path)])
    entries = json.loads((tmp_path / "launched.json").read_text())["entries"]
    assert [s for s, e in entries.items() if e["task_id"]] == ["a", "b"]


def test_the_checkpoint_is_written_before_the_first_launch_and_after_each(tmp_path):
    seen = []
    pof.launch_all(_FakeEcs(), ["a", "b"], "20261030", "p", 1, 1, 5, 0, sleep=lambda s: None,
                   checkpoint=lambda e: seen.append(sum(1 for v in e.values() if v["task_id"])))
    assert seen == [0, 1, 2]


def test_a_rerun_into_an_existing_record_is_refused_before_aws_and_leaves_it_alone(tmp_path):
    (tmp_path / "launched.json").write_text('{"entries": {"co": {"task_id": "keep-me"}}}')
    with patch.object(pof, "_ecs_client", side_effect=AssertionError("must not reach AWS")):
        assert pof.main(["co", "--out", str(tmp_path)]) == 3
    assert "keep-me" in (tmp_path / "launched.json").read_text()


def test_the_task_definition_revision_is_recorded_and_a_mixed_batch_is_flagged():
    ecs = _FakeEcs()
    entries = pof.launch_all(ecs, ["co", "ga"], "20261030", "p", 1, 1, 5, 0, sleep=lambda s: None)
    assert entries["co"]["revision"] == "42"
    status = {"co": ("STOPPED", 0, None), "ga": ("STOPPED", 0, None)}
    assert "revision(s) used: 42" in pof.format_status(entries, status) and "MIXED" not in pof.format_status(entries, status)
    entries["ga"]["revision"] = "43"
    assert "MIXED" in pof.format_status(entries, status)


def test_the_record_is_claimed_before_any_aws_call(tmp_path):
    seen = []

    class Watching(_FakeEcs):
        def run_task(self, **kw):
            seen.append((tmp_path / "launched.json").exists())
            return super().run_task(**kw)

    with patch.object(pof, "_ecs_client", return_value=Watching()), patch.object(pof.time, "sleep", lambda s: None):
        assert pof.main(["co", "--out", str(tmp_path)]) == 0
    assert seen == [True]


def test_the_final_state_list_is_deduplicated_for_all_as_well(tmp_path, capsys):
    for name in ("us", "usa", "ak"):  # a hypothetical tree with both spellings of one jurisdiction
        (tmp_path / name).mkdir()
        (tmp_path / name / "bills.py").write_text("")
    assert pof.main(["--all", "--dry-run", "--scrapers-dir", str(tmp_path)]) == 0
    assert capsys.readouterr().out.rstrip().endswith("ak us")


class _IdempotentEcs:
    """ECS as far as launching goes: one task per idempotency token; can be interrupted right after accepting a request."""

    def __init__(self, interrupt_after_accepting=None):
        self.tasks = {}
        self.interrupt_after_accepting = interrupt_after_accepting

    def run_task(self, **kw):
        token = kw["clientToken"]
        state = kw["overrides"]["containerOverrides"][0]["command"][0]
        fresh = token not in self.tasks
        self.tasks.setdefault(token, f"t-{state}")
        if fresh and state == self.interrupt_after_accepting:
            self.interrupt_after_accepting = None
            raise KeyboardInterrupt  # ECS has the task, the launcher never saw the answer
        return {"tasks": [{"taskArn": f"arn:x:task/ddp-scrapers/{self.tasks[token]}",
                           "taskDefinitionArn": "arn:x:task-definition/ddp-scrapers:42"}], "failures": []}


def test_an_interrupted_launch_is_recovered_by_rerunning_with_the_same_date_and_a_new_folder(tmp_path):
    import pytest

    ecs = _IdempotentEcs(interrupt_after_accepting="c")
    with patch.object(pof, "_ecs_client", return_value=ecs), patch.object(pof.time, "sleep", lambda s: None):
        with pytest.raises(KeyboardInterrupt):
            pof.main(["a", "b", "c", "d", "--date", "20261030", "--out", str(tmp_path / "first")])
        first = json.loads((tmp_path / "first" / "launched.json").read_text())["entries"]
        assert [s for s, e in first.items() if e["task_id"]] == ["a", "b"]  # c was accepted but its id was lost
        assert pof.main(["a", "b", "c", "d", "--date", "20261030", "--out", str(tmp_path / "second")]) == 0
    second = json.loads((tmp_path / "second" / "launched.json").read_text())["entries"]
    assert {s: e["task_id"] for s, e in second.items()} == {"a": "t-a", "b": "t-b", "c": "t-c", "d": "t-d"}
    assert len(ecs.tasks) == 4  # four tasks in all: nothing was started twice
