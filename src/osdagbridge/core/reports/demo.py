"""Deterministic synthetic inputs for exercising rendering, never bridge design."""

from osdagbridge.core.utils import common as keys


def demonstration_data():
    """Use real backend field names and make the synthetic origin explicit."""
    inputs = {
        keys.KEY_SPAN: 25,
        keys.KEY_TS_NO_OF_GIRDERS: 4,
        keys.KEY_TS_GIRDER_SPACING: 2.5,
        keys.KEY_TS_OVERALL_WIDTH: 10.5,
        keys.KEY_TS_DECK_THICKNESS: 250,
        keys.KEY_LL_IRC_CLASS_A: True,
        keys.KEY_LL_IRC_70R_TRACKED: True,
        keys.KEY_LL_IRC_70R_WHEELED: False,
        keys.KEY_LL_FOOTPATH_PRESSURE_MODE: "Custom",
        keys.KEY_LL_FOOTPATH_PRESSURE_VALUE: 5,
        keys.KEY_WC_LD_LANE_TABLE_COUNT: 2,
        "member_properties.girder_details.section_properties.area": 0.06,
        "member_properties.girder_details.section_properties.mass": 471,
    }
    for number in range(1, 5):
        inputs[f"{keys.KEY_MP_GD_SELECT_GIRDER}.G{number}"] = f"G{number}"
        inputs[f"{keys.KEY_MP_GD_MEMBER_ID}.G{number}.M1"] = f"G{number}M1"
    outputs = {
        "design_results": {
            "per_girder": {
                f"G{i}": {"checks": [
                    {"name": "Flexure (synthetic)", "check_id": 1,
                     "demand": ratio * 100, "capacity": 100, "dcr": ratio,
                     "demand_unit": "kNm", "capacity_unit": "kNm",
                     "status": "PASS" if ratio <= 1 else "FAIL"},
                ]}
                for i, ratio in enumerate((0.72, 0.88, 1.08, 0.93), start=1)
            },
        },
        keys.KEY_SD_TOTAL_DEPTH: 1500,
        keys.KEY_SD_MU_APPLIED: 2640,
        keys.KEY_SD_MD_CAPACITY: 3000,
        keys.KEY_UTIL_FLEXURE: 88,
        keys.KEY_UTIL_SHEAR: 61,
        keys.KEY_UTIL_INTERACTION: 90,
        keys.KEY_UTIL_LTB: 76,
        "deck_report_values": {
            keys.KEY_DD_M_ULS_SAG: 92,
            keys.KEY_DD_MU_BOT: 120,
            keys.KEY_DD_SHEAR_VED: 120,
            keys.KEY_DD_SHEAR_VRDC: 180,
        },
        "analysis_summary": {
            "load_cases": {
                f"Synthetic LC {i:02d}": {"max_bm": 1800 + i * 20, "bm_girder": "G2",
                                           "bm_location": 12.5, "max_sf": 250 + i,
                                           "sf_girder": "G1", "sf_location": 0}
                for i in range(1, 45)
            },
        },
        "design_log": ["DEMONSTRATION ONLY. These are synthetic results; no structural analysis was executed."],
    }
    for prefix, demand in (("crossbracing", 50), ("end_diaphragm", 115)):
        outputs[prefix + "_forces_dict"] = {
            "pairs": {"G1-G2": {"diag_compression_kN": demand,
                                 "diag_compression_gov_lc": "Synthetic ULS"}},
        }
        outputs[prefix + "_design_results"] = {
            "G1-G2": {"diagonal": {"compression": {
                "Design.Strength": 100, "Optimum.UR": demand / 100,
                "Optimum.Designation": "ISA 75x75x8", "Member.Slenderness": 120,
            }}},
        }
    return {
        "metadata": {
            "project_name": "DEMONSTRATION ONLY - synthetic bridge results",
            "project_location": "Sample location",
            "designer": "Report rendering demonstration",
            "client": "Not for construction",
            "company": "OsdagBridge screening exercise",
            "job_number": "DEMO-001",
            "subtitle": "Synthetic data - no structural analysis",
            "report_date": "2026-11-17",
        },
        "inputs": inputs,
        "outputs": outputs,
    }
