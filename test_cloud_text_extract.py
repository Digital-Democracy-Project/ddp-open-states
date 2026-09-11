"""
Tests for cloud_text_extract.py (OPEN-268).

There is exactly one behavior to prove: this file passes its own argv straight through to
os-text-extract via os.execvp, unmodified. No subprocess capture, no summary parsing, no S3/DB
of its own -- that's all still os-text-extract's and the calling pipeline's job.
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
import cloud_text_extract as cte


def test_execs_os_text_extract_with_argv_passed_through():
    with patch.object(sys, "argv", ["cloud_text_extract.py", "recompute-diff-order", "fl", "--dry-run"]), \
         patch.object(cte.os, "execvp") as mock_execvp:
        cte.main()

    mock_execvp.assert_called_once_with(
        "os-text-extract", ["os-text-extract", "recompute-diff-order", "fl", "--dry-run"]
    )


def test_execs_os_text_extract_with_no_extra_args():
    with patch.object(sys, "argv", ["cloud_text_extract.py"]), \
         patch.object(cte.os, "execvp") as mock_execvp:
        cte.main()

    mock_execvp.assert_called_once_with("os-text-extract", ["os-text-extract"])
