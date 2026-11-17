"""Opt-in execution of a distribution outside its original source checkout."""

import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


@pytest.mark.skipif(not os.environ.get("OSDAG_TEST_PACKAGE"), reason="Set OSDAG_TEST_PACKAGE to test an exported ZIP")
def test_exported_package_runs_in_an_unrelated_directory_with_spaces(tmp_path):
    archive = Path(os.environ["OSDAG_TEST_PACKAGE"]).resolve()
    extracted = tmp_path / "Unrelated directory with spaces"
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(extracted)
    result = subprocess.run(
        [sys.executable, str(extracted / "run_report.py"), "--demo", "--no-pdf", "--output", str(extracted / "results")],
        cwd=tmp_path, env=dict(os.environ, PYTHONPATH=""), capture_output=True, text=True, timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    source = (extracted / "results/Report_After.tex").read_text(encoding="utf-8")
    assert "Supplied Girder Design Checks" in source
    assert r"\chapter{Loads and Load Combinations}" in source
    assert (extracted / "PACKAGE_MANIFEST.json").is_file()
