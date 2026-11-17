"""Missing deck results must not turn into passing zero/zero comparisons."""

import re

import pytest

from osdagbridge.core.reports.chap5 import ch5_design_checks
from osdagbridge.core.reports.report_generator import (
    ReportDataBridge, ReportFigures, ReportMetadata, ReportOptions, ReportPayload,
)
from osdagbridge.core.utils import common as keys


def _render_deck(deck, *, inputs=None):
    metadata = ReportMetadata("Test", "Test location", "Designer", "Client", "Company")
    options = ReportOptions(["design_checks"], False, False, False)
    if inputs is None:
        inputs = {
            keys.KEY_TS_NO_OF_GIRDERS: 1,
            f"{keys.KEY_MP_GD_SELECT_GIRDER}.G1": "G1",
            f"{keys.KEY_MP_GD_MEMBER_ID}.G1.M1": "G1M1",
        }
    outputs = {"deck_report_values": deck}
    payload = ReportPayload(metadata, options, inputs, {}, [], ReportFigures(), output_dict=outputs)
    return ch5_design_checks([], ReportDataBridge(outputs, inputs, payload))


def _table(report, caption):
    return report.split(caption, 1)[1].split(r"\end{longtable}", 1)[0]


def _statuses(table):
    return re.findall(r"& (PASS|FAIL|N/A) \\", table)


@pytest.mark.parametrize("demand,capacity,expected", [
    (None, None, "N/A"),
    (0, None, "N/A"),
    (None, 100, "N/A"),
    (0, 0, "N/A"),
    (10, 0, "N/A"),
    (10, -2, "N/A"),
    (float("nan"), 100, "N/A"),
    (0, 100, "PASS"),
    (100, 100, "PASS"),
    (120, 100, "FAIL"),
])
def test_flexure_status_requires_real_finite_demand_and_positive_capacity(demand, capacity, expected):
    report = _render_deck({keys.KEY_DD_M_ULS_SAG: demand, keys.KEY_DD_MU_BOT: capacity})
    table = _table(report, "Deck Slab --- Flexure Check: Interior Panel")
    # First status is sagging; the absent hogging result stays unavailable.
    assert _statuses(table) == [expected, "N/A"]


def test_partial_deck_results_do_not_pass_unrelated_detailing_checks():
    report = _render_deck({keys.KEY_DD_M_ULS_SAG: 50, keys.KEY_DD_MU_BOT: 100})
    detailing = _table(report, "Reinforcement Detailing Summary (Deck Slab)")
    assert "PASS" not in detailing
    assert "FAIL" not in detailing
    assert len(_statuses(detailing)) == 6
    assert set(_statuses(detailing)) == {"N/A"}
    assert "All reinforcement provisions satisfy" not in report


@pytest.mark.parametrize("flag,expected", [
    (None, "N/A"),
    (False, "FAIL"),
    (True, "PASS"),
    ("False", "FAIL"),
    ("True", "PASS"),
    (0, "FAIL"),
    (1, "PASS"),
    ("unavailable", "N/A"),
])
def test_explicit_backend_flags_distinguish_missing_from_failed_results(flag, expected):
    report = _render_deck({
        keys.KEY_DD_PUNCH_OK: flag,
        keys.KEY_DD_SHEAR_OK: flag,
        keys.KEY_DD_COVER_OK: flag,
    })
    punching = _table(report, "Deck Slab --- Punching Shear Check")
    shear = _table(report, "One-Way (Beam) Shear Check (Deck Slab)")
    detailing = _table(report, "Reinforcement Detailing Summary (Deck Slab)")
    assert _statuses(punching) == [expected]
    assert _statuses(shear) == [expected]
    assert _statuses(detailing)[-1] == expected


def test_missing_shear_demand_does_not_display_a_fabricated_zero_ratio():
    report = _render_deck({keys.KEY_DD_SHEAR_VRDC: 100, keys.KEY_DD_VRD_C_MPA: 1.5})
    punching = _table(report, "Deck Slab --- Punching Shear Check")
    shear = _table(report, "One-Way (Beam) Shear Check (Deck Slab)")
    assert "0.00 & N/A" not in punching
    assert "0.00 & N/A" not in shear
    assert "N/A & N/A" in punching
    assert "N/A & N/A" in shear


@pytest.mark.parametrize("provided,required,expected", [(0, 0, "N/A"), (100, 0, "PASS"), (50, 100, "FAIL")])
def test_reinforcement_area_checks_do_not_use_missing_or_zero_provided_area_as_capacity(provided, required, expected):
    report = _render_deck({keys.KEY_DD_AS_BOT: provided, keys.KEY_DD_AS_REQ_BOT: required})
    detailing = _table(report, "Reinforcement Detailing Summary (Deck Slab)")
    assert _statuses(detailing)[0] == expected


@pytest.mark.parametrize("inputs", [{}, {keys.KEY_TS_NO_OF_GIRDERS: 0}])
def test_missing_or_zero_girder_snapshot_renders_unavailable_rows_without_assuming_a_girder(inputs):
    report = _render_deck({}, inputs=inputs)
    assert "PASS" not in report
    assert r"\makecell{G1}" not in report
    for caption in ("Girder Section Properties", "Moment Capacity Check", "Stiffener Design Summary", "Girder Design Summary"):
        assert "N/A --- no girder result entries supplied" in _table(report, caption)
    stiffener = _table(report, "Stiffener Design Summary")
    assert r"\textbf{Girder} & \textbf{Parameter} & \textbf{Value}" in stiffener
    assert r"\endhead" in stiffener
