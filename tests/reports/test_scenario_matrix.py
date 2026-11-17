"""Quick checks for the real-compiler matrix harness, without compiling here."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


@pytest.fixture
def matrix():
    path = Path(__file__).resolve().parents[2] / "scripts" / "run_report_matrix.py"
    specification = importlib.util.spec_from_file_location("report_scenario_matrix", path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def test_matrix_has_at_least_thirty_distinct_purposes_and_inputs(matrix):
    cases = matrix.build_scenarios()
    assert len(cases) >= 30
    assert len({case.name for case in cases}) == len(cases)
    assert len({case.purpose for case in cases}) == len(cases)
    signatures = {
        json.dumps([case.data, case.sections, case.figures, case.toc, sorted(case.figure_bytes)], sort_keys=True)
        for case in cases
    }
    assert len(signatures) == len(cases)


def test_scenario_input_changes_never_leak_to_another_case_or_future_build(matrix):
    cases = matrix.build_scenarios()
    original_name = cases[1].data["metadata"]["project_name"]
    cases[0].data["metadata"]["project_name"] = "mutation should stay local"
    cases[0].data["outputs"]["design_results"]["per_girder"]["G1"]["checks"][0]["demand"] = -400
    assert cases[1].data["metadata"]["project_name"] == original_name
    assert matrix.build_scenarios()[0].data["metadata"]["project_name"] != "mutation should stay local"
    assert matrix.build_scenarios()[0].data["outputs"]["design_results"]["per_girder"]["G1"]["checks"][0]["demand"] >= 0


def test_renderer_failure_is_evidence_of_failure_and_keeps_case_data_private(matrix, monkeypatch, tmp_path):
    monkeypatch.setattr(matrix, "generate_report", lambda *args, **kwargs:
                        SimpleNamespace(error="Compiler failed at " + str(tmp_path / "private.tex"), pdf_path=None, tex_path=None))
    result = matrix.run_scenario(matrix.build_scenarios()[0], tmp_path)
    assert result["passed"] is False
    assert "Compiler failed" in result["errors"][0]
    assert "pdf" not in result
    assert str(tmp_path) not in result["errors"][0]


def test_matrix_summary_counts_failures_instead_of_claiming_all_passed(matrix, monkeypatch, tmp_path):
    cases = matrix.build_scenarios()[:2]
    monkeypatch.setattr(matrix, "build_scenarios", lambda: cases)
    monkeypatch.setattr(matrix, "run_scenario", lambda case, *args:
                        {"name": case.name, "passed": case is cases[0], "errors": [] if case is cases[0] else ["controlled unit failure"]})
    summary = matrix.run_matrix(tmp_path)
    assert (summary["total"], summary["passed"], summary["failed"]) == (2, 1, 1)
    saved = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert saved == summary
    assert "no bridge analysis" in summary["scope"]


@pytest.mark.parametrize("arguments", [["--limit", "0"], ["--limit", "-1"], ["--case", "not-a-real-case"]])
def test_matrix_cli_rejects_invalid_selection_before_running(matrix, arguments):
    with pytest.raises(SystemExit) as error:
        matrix.main(arguments)
    assert error.value.code == 2
