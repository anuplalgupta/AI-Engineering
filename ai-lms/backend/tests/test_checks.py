"""Build checks that run with the tests: module boundaries and the committed API description."""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_module_boundaries():
    result = subprocess.run(
        ["lint-imports", "--no-cache"], cwd=BACKEND, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_committed_openapi_matches_the_code():
    result = subprocess.run(
        [sys.executable, "-m", "ailms.tools.openapi", "--check"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
