"""
Tests for cloud_archiver.py (OPEN-192, Phase 3 of the scraper-execution migration).

Reuses `FakeS3Client` from test_cloud_collector.py rather than reimplementing it -- same
in-memory S3 stand-in, same reasoning for why it exists (S3Memory/SourceLock call boto3's
high-level methods, not the raw operations botocore.stub.Stubber matches).
"""

import json
import os
import stat
import sys
import time

import pytest
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.dirname(__file__))
import cloud_archiver as ca
from test_cloud_collector import FakeS3Client


# ── parse_summary_line: the one place this file reads the archiver's own output ────────────

def test_parse_summary_line_extracts_all_counts():
    output = (
        "some log noise\n"
        "fl: 12 bills checked | fetched=8 skipped=4 archived=8 fetch_errors=0 blocked=0 "
        "extract_errors=0 conflicts=0 concurrent_writes=0 s3_verified=8 s3_unverified=0\n"
    )
    counts = ca.parse_summary_line(output)
    assert counts == {
        "state": "fl", "checked": 12, "fetched": 8, "skipped": 4, "archived": 8,
        "fetch_errors": 0, "blocked": 0, "extract_errors": 0, "conflicts": 0,
        "concurrent_writes": 0, "s3_verified": 8, "s3_unverified": 0,
    }


def test_parse_summary_line_returns_none_when_absent():
    # e.g. a crash before the archiver printed anything, or the WAF-abort line, which has a
    # different shape ("fl: aborted -- ...") and is deliberately not matched.
    assert ca.parse_summary_line("fl: aborted -- sustained WAF block\n") is None
    assert ca.parse_summary_line("") is None


def test_parse_summary_line_takes_the_last_match_if_several_appear():
    # Defensive, not expected in practice: `archive()` only ever prints one summary line per
    # invocation, but if output were ever concatenated across runs, the last one is the one
    # that actually describes what THIS process's `os-text-extract archive` call did.
    output = (
        "fl: 1 bills checked | fetched=1 skipped=0 archived=1 fetch_errors=0 blocked=0 "
        "extract_errors=0 conflicts=0 concurrent_writes=0 s3_verified=1 s3_unverified=0\n"
        "fl: 2 bills checked | fetched=2 skipped=0 archived=2 fetch_errors=0 blocked=0 "
        "extract_errors=0 conflicts=0 concurrent_writes=0 s3_verified=2 s3_unverified=0\n"
    )
    assert ca.parse_summary_line(output)["archived"] == 2


# ── main(): the end-to-end paths ────────────────────────────────────────────────────────────

def _fake_os_text_extract(tmp_path, *, exit_code=0, state="fl", archived=3,
                           expect_env_var=None, env_var_file=None):
    """A stand-in for the real os-text-extract binary, matching cloud_collector.py's own
    OS_UPDATE_OVERRIDE-style convention (here, OS_TEXT_EXTRACT) for driving this script
    without the real toolchain.

    `expect_env_var`/`env_var_file`, when given, records that environment variable's value as
    the fake process actually saw it -- so a test can assert cloud_archiver.py really set
    ARCHIVE_S3_MODE=direct in the subprocess's own environment, not just intended to.
    """
    script = tmp_path / "fake_os_text_extract.sh"
    lines = ["#!/usr/bin/env bash", "set -e"]
    if expect_env_var and env_var_file:
        lines.append(f'printf "%s" "${expect_env_var}" > {str(env_var_file)!r}')
    lines.append(
        f'echo "{state}: 5 bills checked | fetched={archived} skipped=2 archived={archived} '
        f'fetch_errors=0 blocked=0 extract_errors=0 conflicts=0 concurrent_writes=0 '
        f's3_verified={archived} s3_unverified=0"'
    )
    lines.append(f"exit {exit_code}")
    script.write_text("\n".join(lines) + "\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


def test_main_requires_working_tier_bucket_and_never_touches_s3_or_the_lock(
    tmp_path, monkeypatch, capsys
):
    """The one thing this test file exists to prove above all the others -- mirrors the same
    priority test in test_upload_and_verify_s3_modes.py, one layer up: OPEN-192's own bucket
    decision gates the whole runner, not just the eventual S3 write inside openstates-core."""
    monkeypatch.delenv("WORKING_TIER_S3_BUCKET", raising=False)
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open192")
    client = FakeS3Client()

    rc = ca.main(["fl"], s3_client=client)

    assert rc == 1
    assert client.put_calls == []  # no lock was ever attempted
    out = capsys.readouterr().out
    record = json.loads(out.strip().splitlines()[-1])
    assert record["status"] == "failed"


def test_main_full_run_ok(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open192")
    monkeypatch.setenv("WORKING_TIER_S3_BUCKET", "ddp-openstates-scraper-memory")
    env_var_file = tmp_path / "seen_mode.txt"
    monkeypatch.setenv(
        "OS_TEXT_EXTRACT",
        _fake_os_text_extract(tmp_path, archived=3, expect_env_var="ARCHIVE_S3_MODE",
                               env_var_file=env_var_file),
    )
    client = FakeS3Client()

    rc = ca.main(["fl", "session=2026E"], s3_client=client)

    assert rc == 0
    assert env_var_file.read_text() == "direct"  # the subprocess really saw it, not just us
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "ok"
    assert record["source"] == "fl"
    assert record["session"] == "2026E"
    assert record["archived"] == 3
    assert "run_id" in record


def test_main_zero_exit_with_no_parseable_summary_is_not_reported_as_plain_ok(
    tmp_path, monkeypatch, capsys
):
    """The concrete deploy-ordering failure mode this file's own module docstring warns about:
    if cloud_archiver is deployed ahead of the openstates-core change it depends on (PR #34),
    ARCHIVE_S3_MODE is set but silently ignored by old code, and the archive command can still
    exit 0 with output that doesn't match the expected summary line shape. A plain "ok" status
    would hide that from anything reading these completion records; "ok_unparsed" says the
    command didn't signal failure but its outcome couldn't be confirmed."""
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open192")
    monkeypatch.setenv("WORKING_TIER_S3_BUCKET", "ddp-openstates-scraper-memory")
    script = tmp_path / "fake_os_text_extract_no_summary.sh"
    script.write_text("#!/usr/bin/env bash\necho 'some unrelated output'\nexit 0\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("OS_TEXT_EXTRACT", str(script))
    client = FakeS3Client()

    rc = ca.main(["fl"], s3_client=client)

    assert rc == 0
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "ok_unparsed"
    assert "archived" not in record  # no counts were parsed at all


def test_main_lock_held_by_another_run_refuses(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open192")
    monkeypatch.setenv("WORKING_TIER_S3_BUCKET", "ddp-openstates-scraper-memory")
    monkeypatch.setenv("OS_TEXT_EXTRACT", _fake_os_text_extract(tmp_path))
    client = FakeS3Client()
    # Pre-seed a live lock, exactly as test_cloud_collector.py's own equivalent test does.
    other = ca.SourceLock(client, "bucket", "dev-open192", holder="someone-else",
                           suffix="_archive_lock")
    assert other.acquire("fl") is True

    rc = ca.main(["fl"], s3_client=client)

    assert rc == ca.EXIT_DO_NOT_RETRY
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"


def test_main_archive_lock_and_collection_lock_are_independent_keys(tmp_path, monkeypatch):
    """The exact hazard this third lock exists to name: an archive run and a collection run of
    the SAME jurisdiction must not exclude each other -- only two archive runs (or two
    collection runs) of the same jurisdiction should."""
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open192")
    monkeypatch.setenv("WORKING_TIER_S3_BUCKET", "ddp-openstates-scraper-memory")
    monkeypatch.setenv("OS_TEXT_EXTRACT", _fake_os_text_extract(tmp_path))
    client = FakeS3Client()
    collection_lock = ca.SourceLock(client, "bucket", "dev-open192", holder="collector",
                                     suffix="_lock")
    assert collection_lock.acquire("fl") is True  # collection is running fl right now

    rc = ca.main(["fl"], s3_client=client)  # archiving fl should not be blocked by that

    assert rc == 0


def test_main_archive_failure_still_emits_a_completion_record_with_parsed_counts(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open192")
    monkeypatch.setenv("WORKING_TIER_S3_BUCKET", "ddp-openstates-scraper-memory")
    monkeypatch.setenv(
        "OS_TEXT_EXTRACT", _fake_os_text_extract(tmp_path, exit_code=1, archived=0)
    )
    client = FakeS3Client()

    rc = ca.main(["fl"], s3_client=client)

    assert rc == 1
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"
    assert record["archived"] == 0  # the summary line was still parsed even on failure


def test_main_michigan_refuses_without_a_fresh_published_cookie(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open192")
    monkeypatch.setenv("WORKING_TIER_S3_BUCKET", "ddp-openstates-scraper-memory")
    monkeypatch.setenv("OS_TEXT_EXTRACT", _fake_os_text_extract(tmp_path, state="mi"))
    client = FakeS3Client()  # no cookie ever published to it

    rc = ca.main(["mi"], s3_client=client)

    assert rc == 1  # retryable -- not EXIT_DO_NOT_RETRY, self-heals at the next publish tick
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"


def test_main_michigan_proceeds_with_a_fresh_published_cookie(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open192")
    monkeypatch.setenv("WORKING_TIER_S3_BUCKET", "ddp-openstates-scraper-memory")
    monkeypatch.setenv("OS_TEXT_EXTRACT", _fake_os_text_extract(tmp_path, state="mi"))
    client = FakeS3Client()
    fresh_cookie = {
        "x-bni-fpc": {"value": "abc", "expires": time.time() + 3600},
        "_meta": {"minted_at": time.time()},
    }
    client.objects["dev-open192/mi/_cache/mi_waf_cookies.json"] = json.dumps(
        fresh_cookie
    ).encode()

    rc = ca.main(["mi"], s3_client=client)

    assert rc == 0
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "ok"


def test_main_non_michigan_state_never_checks_for_a_cookie(tmp_path, monkeypatch):
    """Confirms the cookie gate really is Michigan-only -- a state with no cookie in the store
    at all must archive successfully, unlike mi in the test above."""
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open192")
    monkeypatch.setenv("WORKING_TIER_S3_BUCKET", "ddp-openstates-scraper-memory")
    monkeypatch.setenv("OS_TEXT_EXTRACT", _fake_os_text_extract(tmp_path, state="va"))
    client = FakeS3Client()

    rc = ca.main(["va"], s3_client=client)

    assert rc == 0


def test_main_unhandled_exception_still_releases_the_lock(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BUCKET", "bucket")
    monkeypatch.setenv("MEMORY_PREFIX", "dev-open192")
    monkeypatch.setenv("WORKING_TIER_S3_BUCKET", "ddp-openstates-scraper-memory")
    # A binary that does not exist at all -- Popen itself raises, exercising main()'s bare
    # `except Exception` path (contract: still emit a record, still release the lock, then
    # re-raise so the real exit code reflects the crash).
    monkeypatch.setenv("OS_TEXT_EXTRACT", str(tmp_path / "does-not-exist"))
    client = FakeS3Client()

    with pytest.raises(FileNotFoundError):
        ca.main(["fl"], s3_client=client)

    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["status"] == "failed"
    # The lock must have been released, not left held -- a fresh attempt should succeed.
    lock = ca.SourceLock(client, "bucket", "dev-open192", holder="next-attempt",
                          suffix="_archive_lock")
    assert lock.acquire("fl") is True
