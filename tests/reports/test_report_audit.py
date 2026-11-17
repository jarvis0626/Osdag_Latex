"""Integrity regressions found while auditing the real report templates."""

from copy import deepcopy
import re

import pytest

from osdagbridge.core.reports.chap5 import ch5_design_checks
from osdagbridge.core.reports.chap6 import ch6_drawings
from osdagbridge.core.reports.data import backend_girder_table, check_ratio
from osdagbridge.core.reports.demo import demonstration_data
from osdagbridge.core.reports.executive_summary import executive_summary
from osdagbridge.core.reports.report_generator import ReportDataBridge, ReportFigures, ReportMetadata, ReportOptions, ReportPayload
from osdagbridge.core.reports.report_utils import _render_value, _tex, _fig_or_placeholder
from osdagbridge.core.reports.styles import format_chapter


@pytest.mark.parametrize("value", [None, "", " ", float("nan"), float("inf"), "NaN", "-Infinity", "N.A."])
def test_unavailable_values_are_explicit_and_do_not_claim_units(value):
    assert _render_value({"result": value}, "result", " kN") == "N/A"


@pytest.mark.parametrize("glyph,command", [
    ("\u03b1", "alpha"), ("\u03b2", "beta"), ("\u03b3", "gamma"),
    ("\u03bb", "lambda"), ("\u03bc", "mu"), ("\u03c3", "sigma"),
    ("\u03c4", "tau"), ("\u0394", "Delta"), ("\u03a9", "Omega"),
])
def test_engineering_greek_uses_supported_tex_commands(glyph, command):
    assert _tex(glyph) == "\\ensuremath{\\" + command + "}"


def test_temperature_degree_and_celsius_symbol_are_safe():
    assert _tex("25\u2103") == r"25\ensuremath{^\circ}C"
    assert _tex("-10\u00b0C") == r"-10\ensuremath{^\circ}C"


def test_empty_body_cells_are_marked_without_destroying_header_or_row_shape():
    table = (r"\begin{longtable}{|L{3cm}|L{3cm}|L{3cm}|}\hline"
             r" & Label & Value\\\hline A & & \\\hline\end{longtable}")
    source = format_chapter(table)
    assert "A & N/A & N/A" in source
    heading, body = source.split(r"\endhead", 1)
    assert "N/A" not in heading
    assert body.count("&") == 2


def test_missing_drawings_do_not_create_large_placeholder_figures():
    source = ch6_drawings({})
    assert "Unavailable:" in source
    assert "PLACEHOLDER" not in source
    assert r"\begin{figure}" not in source
    assert r"\includegraphics" not in source


def test_real_supplied_drawing_path_is_retained():
    source = _fig_or_placeholder("assets/real_cad.png", "Supplied CAD")
    assert r"\includegraphics" in source and "assets/real_cad.png" in source
    assert "Unavailable" not in source


def test_individual_engine_checks_replace_controlling_girder_scalars():
    data = demonstration_data()
    original = deepcopy(data)
    metadata = ReportMetadata(**data["metadata"])
    payload = ReportPayload(metadata, ReportOptions([], False, False, False), data["inputs"], {}, [], ReportFigures(), output_dict=data["outputs"])
    bridge = ReportDataBridge(data["outputs"], data["inputs"], payload)
    source = ch5_design_checks([], bridge)
    girder_section = source.split(r"\section{Plate Girder Design}", 1)[1].split(r"\section{Deck Slab Design}", 1)[0]
    assert "Supplied Girder Design Checks" in girder_section
    assert "0.7200 & PASS" in girder_section
    assert "1.0800 & FAIL" in girder_section
    assert "2640" not in girder_section
    assert data == original


def test_backend_warning_is_preserved_below_visual_unity_limit():
    data = demonstration_data()
    check = data["outputs"]["design_results"]["per_girder"]["G1"]["checks"][0]
    check.update(status="WARN", dcr=0.95, demand=95, capacity=100)
    assert "0.9500 & WARN" in backend_girder_table(data["outputs"])
    assert "Backend WARN statuses are present" in executive_summary(data["inputs"], data["outputs"], {})


def test_failed_zero_capacity_record_cannot_disappear_into_a_pass():
    outputs = {"design_results": {"per_girder": {"G1": {"checks": [
        {"name": "No capacity", "demand": 20, "capacity": 0, "dcr": 999, "status": "FAIL"},
    ]}}}}
    source = backend_girder_table(outputs)
    assert "N/A & FAIL" in source
    assert check_ratio(outputs["design_results"]["per_girder"]["G1"]["checks"][0]) is None
    assert "Backend reports FAIL" in executive_summary({}, outputs, {})


def test_load_case_values_keep_their_actual_member_and_source():
    outputs = {"design_results": {"per_girder": {"G2": {"per_lc": {"SLS & Wind": {"checks": [
        {"id": 13, "name": "Deflection", "demand": 10, "capacity": 20, "dcr": 0.5, "status": "PASS"},
    ]}}}}}}
    source = backend_girder_table(outputs)
    assert "G2 & Deflection" in source
    assert "SLS \\& Wind" in source
    assert "0.5000 & PASS" in source


def test_conflicting_ratio_cannot_be_presented_as_a_valid_passing_check():
    outputs = {"design_results": {"per_girder": {"G1": {"checks": [
        {"name": "Conflicting export", "demand": 110, "capacity": 100, "dcr": 0.5, "status": "PASS"},
    ]}}}}
    assert check_ratio(outputs["design_results"]["per_girder"]["G1"]["checks"][0]) is None
    assert "Inconsistent supplied ratios" in backend_girder_table(outputs)
    assert "Inconsistent supplied ratios" in executive_summary({}, outputs, {})


def test_backend_rounding_does_not_create_a_false_conflict():
    assert check_ratio({"demand": 10.0, "capacity": 3.0, "dcr": 3.3333}) == 3.3333


def test_heavy_vehicle_defaults_are_not_presented_as_selected_vehicle_results():
    from osdagbridge.core.reports.chap3 import ch3_loads
    from osdagbridge.core.utils import common as keys
    source = ch3_loads({keys.KEY_SPAN: 25, keys.KEY_LL_IRC_70R_WHEELED: True})
    assert "Class AA/70R:" in source
    assert "vehicle-specific result not supplied" in source
    assert "Governing Impact Multiplier (backend) & N/A" in source


def test_report_uses_the_actual_supplied_governing_impact_multiplier():
    from osdagbridge.core.reports.chap3 import ch3_loads
    from osdagbridge.core.utils import common as keys
    source = ch3_loads({}, {"deck_report_values": {keys.KEY_DD_IMPACT_FACTOR: 1.25, keys.KEY_DD_VEHICLE: "Class 70R (Wheeled)"}})
    assert r"Class 70R (Wheeled):\allowbreak{} 1.250" in source


def test_demo_statuses_follow_the_real_backend_thresholds():
    from osdagbridge.core.reports.demo import demonstration_status
    assert [demonstration_status(ratio) for ratio in (0.89, 0.9, 0.99, 1.0)] == ["PASS", "WARN", "WARN", "FAIL"]


def test_upstream_quantity_example_has_consistent_volume_and_mass_units():
    from osdagbridge.core.boq.boq_generator import calculate_material_quantities
    data = demonstration_data()
    quantities = calculate_material_quantities(data["inputs"], data["outputs"])
    assert float(quantities["steel_girders_vol_total"]) == pytest.approx(0.06 * 25 * 4)
    assert float(quantities["steel_girders_wt_total"]) == pytest.approx(471 * 25 * 4 / 1000)
    assert float(quantities["concrete_deck_vol_total"]) == pytest.approx(25 * 10.5 * 0.25, abs=0.01)


def test_material_table_does_not_invent_concrete_or_rebar_grades():
    from osdagbridge.core.reports.chap7 import ch7_quantities
    source = ch7_quantities({})
    assert "Concrete (M40)" not in source
    assert "Reinforcement Steel (Fe 500)" not in source
