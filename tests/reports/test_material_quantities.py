"""Keep supplied quantities consistent across Chapter 7, charts and exports."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from osdagbridge.core.reports import charts, report_generator as reports
from osdagbridge.core.reports.chap7 import ch7_quantities
from osdagbridge.core.reports.compilation import ReportCompilationError
from osdagbridge.core.reports.demo import demonstration_data


def diaphragm_cell(source):
    row = next(line for line in source.splitlines() if "2(d) & End Diaphragms &" in line)
    return row.split("&")[-1].split(r"\\", 1)[0].strip()


@pytest.mark.parametrize("value,expected_number,expected_text", [
    (2.5, 2.5, "2.5"), ("2.500", 2.5, "2.500"),
    (0, 0, "0"), ("0.00", 0, "0.00"),
    (None, None, "N/A"), (float("nan"), None, "N/A"),
    (float("inf"), None, "N/A"), ("-Infinity", None, "N/A"),
    (-2, None, "N/A"), ("-2.0", None, "N/A"),
    (True, None, "N/A"), (False, None, "N/A"),
    ("", None, "N/A"), ("N.A.", None, "N/A"),
    ("2 & 3", None, "N/A"),
])
def test_supplied_diaphragm_quantity_agrees_between_table_and_chart(value, expected_number, expected_text):
    quantities = {"end_diaphragm_wt_total": value}
    before = json.dumps(quantities, sort_keys=True)
    assert diaphragm_cell(ch7_quantities(quantities)) == expected_text
    assert charts.material_series(quantities)["Structural steel (MT)"]["End diaphragms"] == expected_number
    assert json.dumps(quantities, sort_keys=True) == before


def test_absent_diaphragm_quantity_stays_unavailable_instead_of_becoming_zero():
    assert diaphragm_cell(ch7_quantities({})) == "N/A"
    assert charts.material_series({})["Structural steel (MT)"]["End diaphragms"] is None


def test_all_numeric_quantity_columns_hide_invalid_values_without_erasing_real_zero():
    prefixes = ("steel_girders", "bracing_top", "bracing_bot", "bracing_diag", "concrete_deck", "rebar_deck", "shear_studs", "crash_barrier")
    quantities = {prefix + suffix: value for prefix in prefixes for suffix, value in (
        ("_qty", 0), ("_vol_total", float("nan")), ("_wt_single", -1), ("_wt_total", None),
    )}
    source = ch7_quantities(quantities)
    rows = [line for line in source.splitlines() if any(label in line for label in (
        "Structural Steel for Girders &", "Cross Bracing -", "Concrete for Deck Slab &",
        "Reinforcement Steel &", "Shear Stud Connectors &", "Crash Barrier &",
    ))]
    assert len(rows) == len(prefixes)
    for row in rows:
        assert "& 0 & N/A & N/A & N/A" in row
        assert "nan" not in row and "None" not in row and "-1" not in row


def test_upstream_formula_fragments_preserve_math_and_plain_explanations_are_escaped():
    formula = r"$0.06000\text{ m}^2 \times 25.00\text{ m} = 1.50000\text{ m}^3$"
    quantities = {"steel_girders_vol_formula": formula, "concrete_deck_vol_formula": "Width & length_1"}
    before = deepcopy(quantities)
    source = ch7_quantities(quantities)
    assert formula in source
    assert r"Width \& length\_\allowbreak{}1" in source
    assert quantities == before


def test_missing_formula_placeholders_do_not_reappear_as_available_quantities():
    source = ch7_quantities({"steel_girders_vol_formula": r"\placeholder{Area $\times$ Length}"})
    assert r"\placeholder" not in source


@pytest.mark.parametrize("value,expected", [(2.75, 2.75), (0, 0), (None, None), (float("nan"), None), (-1, None)])
def test_generator_preserves_supplied_diaphragm_mass_and_exports_charts_before_cleanup(tmp_path, monkeypatch, value, expected):
    data = demonstration_data()
    data["inputs"]["end_diaphragm_wt_total"] = value
    before = json.dumps(data, sort_keys=True)
    request = reports.ReportRequest(
        reports.ReportMetadata(**data["metadata"]),
        reports.ReportOptions([], True, False, False), str(tmp_path), "materials",
    )
    payload = reports.build_report_payload(request, data["inputs"], data["outputs"])
    recorded = {}
    original_charts = charts.generate_summary_charts

    def record_chart_inputs(inputs, outputs, asset_dir):
        recorded["series"] = charts.material_series(inputs)
        recorded["temporary_assets"] = Path(asset_dir)
        return original_charts(inputs, outputs, asset_dir)

    monkeypatch.setattr(charts, "generate_summary_charts", record_chart_inputs)
    result = reports.generate_report(payload, request)
    assert result.error is None, result.error
    assert result.pdf_path is None
    source = Path(result.tex_path).read_text(encoding="utf-8")
    assert recorded["series"]["Structural steel (MT)"]["End diaphragms"] == expected
    assert diaphragm_cell(source) == (str(value) if expected is not None else "N/A")
    assert not recorded["temporary_assets"].exists()
    for name in ("steel_quantities", "deck_quantities", "utilization"):
        assert (tmp_path / "materials_assets" / (name + ".png")).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert json.dumps(data, sort_keys=True) == before


def test_chart_assets_are_retained_for_rebuilding_after_failed_compilation_but_staging_is_cleaned(tmp_path, monkeypatch):
    data = demonstration_data()
    data["inputs"]["end_diaphragm_wt_total"] = 1.25
    request = reports.ReportRequest(
        reports.ReportMetadata(**data["metadata"]),
        reports.ReportOptions([], True, False, True), str(tmp_path), "failed_materials",
    )
    payload = reports.build_report_payload(request, data["inputs"], data["outputs"])
    recorded = {}

    def fail_compilation(source, executable=None):
        recorded["temporary_source"] = source
        assert (source.parent / "failed_materials_assets/steel_quantities.png").is_file()
        raise ReportCompilationError("Controlled compiler failure for asset-lifetime regression")

    monkeypatch.setattr(reports, "compile_latex", fail_compilation)
    result = reports.generate_report(payload, request)
    assert "Controlled compiler failure" in result.error
    assert result.pdf_path is None
    assert not recorded["temporary_source"].parent.exists()
    assert Path(result.tex_path).is_file()
    assert (tmp_path / "failed_materials_assets/steel_quantities.png").is_file()
