"""Regression coverage for the report's UI live-load definitions."""

from copy import deepcopy

import pytest

from osdagbridge.core.reports.chap3 import ch3_loads
from osdagbridge.core.utils.common import (
    KEY_FOOTPATH,
    KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_SPAN,
    KEY_WC_LD_LANE_TABLE_COUNT,
)


VEHICLES = (
    (KEY_LL_IRC_CLASS_A, "Class A"),
    (KEY_LL_IRC_70R_WHEELED, "Class 70R (Wheeled)"),
    (KEY_LL_IRC_70R_TRACKED, "Class 70R (Tracked)"),
    (KEY_LL_IRC_AA_WHEELED, "Class AA (Wheeled)"),
    (KEY_LL_IRC_AA_TRACKED, "Class AA (Tracked)"),
    (KEY_LL_IRC_CLASS_SV, "Class SV"),
    (KEY_LL_IRC_70R_BOGIE, "Class 70R (Bogie)"),
    (KEY_LL_IRC_CLASS_FATIGUE, "Class Fatigue"),
)


def _table(report, caption):
    return report.split(caption, 1)[1].split(r"\end{longtable}", 1)[0]


@pytest.mark.parametrize("false_value", [False, "False", "false", "No", "0", 0, None, ""])
def test_unselected_saved_vehicle_values_are_not_treated_as_true(false_value):
    inputs = {key: false_value for key, _ in VEHICLES}
    inputs[KEY_SPAN] = 30
    table = _table(ch3_loads(inputs), "Vehicular Live Loads (LL)")

    assert "Vehicles Considered & None" in table
    assert "Class A" not in table
    assert "Class 70R" not in table
    assert "Class AA" not in table


@pytest.mark.parametrize("key,label", VEHICLES)
@pytest.mark.parametrize("true_value", [True, "True", " yes ", "checked", "1", 1])
def test_report_includes_each_selected_ui_vehicle(key, label, true_value):
    table = _table(ch3_loads({key: true_value}), "Vehicular Live Loads (LL)")
    assert "Vehicles Considered & " + label + " & --" in table


def test_custom_vehicle_names_are_escaped_and_inputs_are_not_mutated():
    inputs = {
        KEY_LL_IRC_CLASS_A: True,
        KEY_LL_CUSTOM_VEHICLES: [{"name": "Heavy & Co #1", "impact_factor": 0.25}, "50% load"],
        KEY_FOOTPATH: "Both Sides",
        KEY_LL_FOOTPATH_PRESSURE_MODE: "User-defined",
        KEY_LL_FOOTPATH_PRESSURE_VALUE: 7.25,
    }
    original = deepcopy(inputs)
    output = ch3_loads(inputs)

    assert r"Heavy \& Co \#1" in output
    assert r"50\% load" in output
    assert inputs == original


def test_vehicular_and_footway_loads_have_separate_parameter_value_unit_tables():
    output = ch3_loads({
        KEY_FOOTPATH: "Single Side",
        KEY_LL_FOOTPATH_PRESSURE_MODE: "User-defined",
        KEY_LL_FOOTPATH_PRESSURE_VALUE: 7.25,
        KEY_LL_ECCENTRICITY: 1.2,
    })
    vehicle = _table(output, "Vehicular Live Loads (LL)")
    footway = _table(output, "Footway Live Load")

    for table in (vehicle, footway):
        assert r"\textbf{Parameter} & \textbf{Value} & \textbf{Unit}" in table
    assert "Footway Pressure" not in vehicle
    assert "Vehicles Considered" not in footway
    assert "1.2 & m" in vehicle
    assert r"7.25 & kN/m\textsuperscript{2}" in footway
    assert "Single Side" in footway


def test_automatic_footway_pressure_uses_existing_irc_helper():
    output = ch3_loads({
        KEY_FOOTPATH: "Both Sides",
        KEY_LL_FOOTPATH_PRESSURE_MODE: "Automatic",
        # A stale custom value must not override automatic mode.
        KEY_LL_FOOTPATH_PRESSURE_VALUE: 99,
    })
    footway = _table(output, "Footway Live Load")
    assert r"4.905 & kN/m\textsuperscript{2}" in footway
    assert "99" not in footway


def test_user_defined_zero_pressure_is_retained():
    output = ch3_loads({
        KEY_LL_FOOTPATH_PRESSURE_MODE: "User-defined",
        KEY_LL_FOOTPATH_PRESSURE_VALUE: 0,
    })
    assert r"0 & kN/m\textsuperscript{2}" in _table(output, "Footway Live Load")


def test_absent_footway_does_not_report_a_stale_pressure():
    output = ch3_loads({
        KEY_FOOTPATH: "None",
        KEY_LL_FOOTPATH_PRESSURE_MODE: "User-defined",
        KEY_LL_FOOTPATH_PRESSURE_VALUE: 99,
    })
    footway = _table(output, "Footway Live Load")
    assert "Not applicable" in footway
    assert "99" not in footway


def test_impact_multiplier_keeps_existing_backend_result():
    output = ch3_loads({KEY_LL_IRC_CLASS_A: True, KEY_SPAN: 30})
    assert r"Class A:\allowbreak{} 1.207" in _table(output, "Vehicular Live Loads (LL)")


def test_unavailable_force_results_are_not_fabricated_as_zero():
    output = ch3_loads({KEY_WC_LD_LANE_TABLE_COUNT: 2})
    vehicle = _table(output, "Vehicular Live Loads (LL)")
    assert "Braking Load (IRC 6) & N/A & kN" in vehicle
    assert "Centrifugal Load & Not available from backend & kN" in vehicle
    assert "unavailable braking or" in output
