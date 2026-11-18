"""Regression checks for genuine source separation and honest missing values."""
from copy import deepcopy

import pytest

from osdagbridge.core.reports.charts import (
    _bars, chart_figure, demand_capacity_ratio, generate_summary_charts,
    material_series, nonnegative_number, transverse_checks, utilization_series,
)
from osdagbridge.core.reports.chap5 import _end_diaphragm_tables
from osdagbridge.core.utils import common as keys


def transverse_output(prefix, force, capacity, section):
    return {
        prefix + "_forces_dict": {"pairs": {"G1-G2": {
            "diag_compression_kN": force, "diag_compression_gov_lc": "ULS_1",
        }}},
        prefix + "_design_results": {"G1-G2": {"diagonal": {"compression": {
            "Design.Strength": capacity, "Optimum.Designation": section,
            "Member.Slenderness": 120,
        }}}},
    }


def test_real_result_schemas_keep_girders_deck_bracing_and_diaphragms_distinct():
    outputs = {
        "design_results": {"per_girder": {
            "G1": {"checks": [{"demand": 80, "capacity": 100, "dcr": 0.8}]},
            "G2": {"per_lc": {"SLS": {"checks": [{"demand": 120, "capacity": 100, "dcr": 1.2}]}}},
            "EB1": {"checks": [{"demand": 990, "capacity": 100}]},
        }},
        "deck_report_values": {keys.KEY_DD_M_ULS_SAG: 30, keys.KEY_DD_MU_BOT: 60},
        **transverse_output("crossbracing", 20, 100, "CB section"),
        **transverse_output("end_diaphragm", 70, 100, "ED section"),
    }
    original = deepcopy(outputs)
    series = utilization_series({}, outputs)
    assert series["Steel plate girders"] == {"G1": 0.8, "G2": 1.2}
    assert series["Concrete deck slab"]["Sagging"] == 0.5
    assert series["Cross bracing"]["G1-G2\ndiagonal"] == 0.2
    assert series["End diaphragms"]["G1-G2\ndiagonal"] == 0.7
    assert outputs == original
    ed_tables = "\n".join(_end_diaphragm_tables(outputs))
    assert "ED section" in ed_tables
    assert "CB section" not in ed_tables
    assert "70.000" in ed_tables


@pytest.mark.parametrize("demand,capacity", [
    (None, 100), (10, None), (10, 0), (10, -3), (-10, 100),
    (float("nan"), 100), (10, float("inf")), (True, 2), (10, "N.A."),
])
def test_invalid_demands_or_capacities_are_unavailable(demand, capacity):
    assert demand_capacity_ratio(demand, capacity) is None


def test_actual_zero_demand_is_distinguished_from_missing():
    assert demand_capacity_ratio(0, 10) == 0
    assert nonnegative_number("0.00") == 0
    assert nonnegative_number("nan") is None
    missing = utilization_series({}, {})
    assert all(value is None for values in missing.values() for value in values.values())
    invalid = utilization_series({}, {"design_results": {"per_girder": {
        "G1": {"checks": [{"demand": 10, "capacity": 0, "dcr": 999}]},
    }}})
    assert invalid["Steel plate girders"]["G1"] is None


def test_missing_transverse_capacity_does_not_trust_reported_efficiency():
    outputs = transverse_output("end_diaphragm", 50, None, "ED")
    outputs["end_diaphragm_design_results"]["G1-G2"]["diagonal"]["compression"]["Optimum.UR"] = 0
    assert transverse_checks(outputs, diaphragm=True)[0].ratio is None
    assert "PASS" not in _end_diaphragm_tables(outputs)[2]
    assert "N/A" in _end_diaphragm_tables({})[2]


def test_material_units_and_incomplete_bracing_are_explicit():
    quantities = {
        "steel_girders_wt_total": "10.50", "bracing_top_wt_total": 1,
        "bracing_bot_wt_total": 2, "bracing_diag_wt_total": 3,
        "concrete_deck_vol_total": 30, "rebar_deck_wt_total": 3.6,
    }
    result = material_series(quantities)
    assert result["Structural steel (MT)"] == {"Girders": 10.5, "Cross bracing": 6, "End diaphragms": None}
    assert result["Concrete volume (m³)"] == {"Deck slab": 30}
    assert result["Reinforcement steel (MT)"] == {"Deck reinforcement": 3.6}
    del quantities["bracing_bot_wt_total"]
    assert material_series(quantities)["Structural steel (MT)"]["Cross bracing"] is None


def test_plot_has_red_dashed_threshold_and_missing_marker_without_zero_bar():
    from matplotlib.figure import Figure
    from osdagbridge.core.reports.styles import STYLE
    fig = Figure()
    ax = fig.subplots()
    _bars(ax, {"Valid": 0.8, "Missing": None, "Failing": 1.2}, "UR", "Utilization Ratio", utilization=True)
    assert len(ax.patches) == 2
    assert any(text.get_text() == "N/A" for text in ax.texts)
    threshold = ax.lines[0]
    assert list(threshold.get_ydata()) == [1.0, 1.0]
    assert threshold.get_linestyle() == "--"
    assert threshold.get_color() == STYLE.failure_color


def test_unity_and_above_unity_are_red_without_reclassifying_backend_statuses():
    from matplotlib.colors import to_rgba
    from matplotlib.figure import Figure
    from osdagbridge.core.reports.styles import STYLE

    ax = Figure().subplots()
    _bars(ax, {"Below": 0.99, "Unity": 1.0, "Above": 1.01}, "UR", "Utilization Ratio", utilization=True)
    assert [bar.get_facecolor() for bar in ax.patches] == [
        to_rgba(STYLE.green), to_rgba(STYLE.failure_color), to_rgba(STYLE.failure_color),
    ]


def test_three_png_assets_are_rendered_without_changing_backend(tmp_path):
    import matplotlib
    backend = matplotlib.get_backend()
    paths = generate_summary_charts({}, {}, tmp_path)
    assert set(paths) == {"utilization", "steel_quantities", "deck_quantities"}
    assert matplotlib.get_backend() == backend
    contents = []
    for path in paths.values():
        from pathlib import Path
        data = Path(path).read_bytes()
        assert data.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(data) > 1000
        contents.append(data)
    assert len(set(contents)) == 3
    tex = chart_figure(paths, "utilization", "Demand & capacity")
    assert r"\begin{figure}" in tex and r"\includegraphics" in tex
    assert r"Demand \& capacity" in tex
    assert chart_figure(None, "utilization", "No chart") == ""
