"""Regressions for supplied geometry, analysis values and automatic pagination."""

from copy import deepcopy
import re
from types import SimpleNamespace

import pytest

from osdagbridge.core.reports.chap2 import _bracing_tables, ch2_input_parameters
from osdagbridge.core.reports.chap4 import ch4_analysis
from osdagbridge.core.reports.styles import format_chapter
from osdagbridge.core.utils.common import (
    KEY_MP_CB_BRACING_SECTION_DESIGNATION,
    KEY_MP_CB_MEMBER_ID,
    KEY_MP_CB_SELECT_GIRDERS,
    KEY_MP_CB_SPACING,
    KEY_MP_CB_TYPE,
    KEY_MP_ED_BRACING_SECTION_DESIGNATION,
    KEY_MP_ED_MEMBER_ID,
    KEY_MP_ED_SELECT_GIRDERS,
    KEY_MP_ED_TYPE,
    KEY_SD_DEFL_LIVE,
    KEY_SD_DEFL_TOTAL,
    KEY_SPAN,
    KEY_TS_NO_OF_GIRDERS,
)


def _table(report, caption):
    return next(block for block in report.split(r"\end{longtable}") if caption in block)


def _column_count(table):
    spec = table.rsplit(r"\begin{longtable}", 1)[1].split("\n", 1)[0]
    return len(re.findall(r"[LCRp]\{[\d.]+cm\}", spec))


def _analysis(inputs=None, outputs=None, summary=None):
    bridge = SimpleNamespace(input_dict=inputs or {}, output_dict=outputs or {})
    return ch4_analysis(summary or {}, {}, bridge, 0)


def _row(report, label):
    return next(line for line in report.splitlines() if label in line and "&" in line)


def test_bracing_tables_use_only_the_columns_with_real_headers_and_values():
    inputs = {
        f"{KEY_MP_CB_SELECT_GIRDERS}.G1G2.B1M1": "G1-G2",
        f"{KEY_MP_CB_MEMBER_ID}.G1G2.B1M1": "B1M1",
        f"{KEY_MP_CB_TYPE}.G1G2.B1M1": "Cross",
        f"{KEY_MP_CB_BRACING_SECTION_DESIGNATION}.G1G2.B1M1": "ISA 75x75x8",
        f"{KEY_MP_CB_SPACING}.G1G2.B1M1": 4.5,
        f"{KEY_MP_ED_SELECT_GIRDERS}.G1G2.E1M1": "G1-G2",
        f"{KEY_MP_ED_MEMBER_ID}.G1G2.E1M1": "E1M1",
        f"{KEY_MP_ED_TYPE}.G1G2.E1M1": "Single diagonal",
        f"{KEY_MP_ED_BRACING_SECTION_DESIGNATION}.G1G2.E1M1": "ISMC 100",
    }
    original = deepcopy(inputs)
    report = format_chapter(_bracing_tables(inputs, 2))
    cb = _table(report, "Cross Bracing Details")
    ed = _table(report, "End Diaphragm Details")
    assert _column_count(cb) == 5
    assert _column_count(ed) == 4
    assert "G1-G2 & B1M1 & Cross & ISA 75x75x8 & 4.5 m" in cb
    assert "G1-G2 & E1M1 & Single diagonal & ISMC 100" in ed
    assert inputs == original


@pytest.mark.parametrize("count", [0, 1])
def test_no_bracing_pair_is_invented_when_geometry_has_fewer_than_two_girders(count):
    # Stale pair properties must not create a member absent from current geometry.
    report = format_chapter(_bracing_tables({f"{KEY_MP_CB_MEMBER_ID}.G1G2.B1M1": "STALE-PAIR"}, count))
    assert report.count("No adjacent girder pair is available") == 2
    assert "STALE-PAIR" not in report
    assert r"\multicolumn{5}" in report and r"\multicolumn{4}" in report


def test_input_sections_rely_on_automatic_pagination():
    report = ch2_input_parameters(SimpleNamespace(project_location="Example"), {})
    assert r"\newpage" not in report
    assert r"\clearpage" not in report


@pytest.mark.parametrize("value", [None, "", "not a number", float("nan"), float("inf"), -float("inf"), True, -0.5])
def test_invalid_deflection_magnitudes_are_unavailable_not_failures(value):
    report = _analysis({KEY_SPAN: 24, KEY_TS_NO_OF_GIRDERS: 1}, {
        f"{KEY_SD_DEFL_LIVE}.G1": value,
        f"{KEY_SD_DEFL_TOTAL}.G1": value,
    })
    assert "& N/A" in _row(report, "Deflection due to Live Load")
    assert "& N/A" in _row(report, "Deflection due to Total Load")
    assert "& N/A" in _row(report, "Live Load Deflection Check Status")
    assert "& N/A" in _row(report, "Total Load Deflection Check Status")


@pytest.mark.parametrize("span", [None, "", "missing", 0, -24, float("nan"), float("inf"), True])
def test_missing_or_invalid_span_does_not_invent_zero_allowances_or_a_pass(span):
    report = _analysis({KEY_SPAN: span, KEY_TS_NO_OF_GIRDERS: 1}, {
        f"{KEY_SD_DEFL_LIVE}.G1": 0,
        f"{KEY_SD_DEFL_TOTAL}.G1": 10,
    })
    assert "0.000 mm" in _row(report, "Deflection due to Live Load")
    assert "& N/A" in _row(report, "Allowable Live Load Deflection")
    assert "& N/A" in _row(report, "Allowable Total Deflection")
    assert "& N/A" in _row(report, "Live Load Deflection Check Status")
    assert "L/800 = 0.0" not in report and "L/600 = 0.0" not in report


def test_valid_maximum_deflections_and_inherited_limits_keep_their_results():
    inputs = {KEY_SPAN: 24, KEY_TS_NO_OF_GIRDERS: 2}
    outputs = {
        f"{KEY_SD_DEFL_LIVE}.G1": "10.5", f"{KEY_SD_DEFL_LIVE}.G2": 30,
        f"{KEY_SD_DEFL_TOTAL}.G1": 25, f"{KEY_SD_DEFL_TOTAL}.G2": 45.5,
    }
    before = deepcopy((inputs, outputs))
    report = _analysis(inputs, outputs)
    assert "30.000 mm" in _row(report, "Deflection due to Live Load")
    assert "45.500 mm" in _row(report, "Deflection due to Total Load")
    assert "L/800 = 30.0 mm" in report and "L/600 = 40.0 mm" in report
    assert "& PASS" in _row(report, "Live Load Deflection Check Status")
    assert r"\textcolor{reportFail}{FAIL}" in _row(report, "Total Load Deflection Check Status")
    assert (inputs, outputs) == before


@pytest.mark.parametrize("value,expected", [(10, "N/A"), (35, r"\textcolor{reportFail}{FAIL}")])
def test_incomplete_member_coverage_cannot_establish_a_pass_but_preserves_failure(value, expected):
    report = _analysis({KEY_SPAN: 24, KEY_TS_NO_OF_GIRDERS: 2}, {f"{KEY_SD_DEFL_LIVE}.G1": value})
    assert f"{value:.3f} mm" in _row(report, "Deflection due to Live Load")
    assert expected in _row(report, "Live Load Deflection Check Status")


def test_missing_girder_count_does_not_assign_or_approve_a_stray_girder_result():
    report = _analysis({KEY_SPAN: 24}, {f"{KEY_SD_DEFL_LIVE}.G1": 0})
    assert "& N/A" in _row(report, "Deflection due to Live Load")
    assert "& N/A" in _row(report, "Live Load Deflection Check Status")


def test_support_reaction_table_uses_supplied_values_and_excludes_moving_cases():
    summary = {"reactions": {
        "ULS & load": {"left_kN": -12.25, "right_kN": 25.5},
        "SLS": {"left_kN": 0, "right_kN": float("nan")},
        "Moving pos_001": {"left_kN": 999, "right_kN": 999},
    }}
    report = _analysis(summary=summary)
    table = _table(report, "Reactions at Supports")
    assert r"ULS \& load & -12.250 & 25.500" in table
    assert "SLS & 0.000 & N/A" in table
    assert "999" not in table


def test_missing_reactions_have_one_explicit_unavailable_row():
    table = _table(_analysis(), "Reactions at Supports")
    assert table.count("N/A & N/A & N/A") == 1


def test_optional_null_analysis_containers_are_treated_as_unavailable():
    report = _analysis(summary={"load_cases": None, "reactions": None})
    table = _table(report, "Reactions at Supports")
    assert table.count("N/A & N/A & N/A") == 1


def test_nonfinite_or_invalid_analysis_values_are_unavailable_while_signed_values_survive():
    summary = {"load_cases": {"ULS": {"max_bm": float("nan"), "max_sf": "invalid", "bm_location": -2.25}}}
    report = _analysis(summary=summary)
    row = _row(report, "ULS &")
    assert "N/A" in row and "-2.250" in row
    assert "nan" not in row and "invalid" not in row
