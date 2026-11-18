"""Compile and inspect varied synthetic OsdagBridge report scenarios.

This exercises rendering of supplied result dictionaries, not bridge analysis.
All PDFs stay under output/ by default. A real compiler is required: failures
are recorded, never replaced by a mocked success or a PDF from an earlier run.
"""

import argparse
import copy
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from osdagbridge.core.reports.demo import demonstration_data
from osdagbridge.core.reports.report_generator import (
    ReportMetadata, ReportOptions, ReportRequest, build_report_payload, generate_report,
)
from osdagbridge.core.utils import common as keys


ALL_SECTIONS = ("loads", "analysis", "design_checks", "drawings")
VEHICLE_KEYS = (
    keys.KEY_LL_IRC_CLASS_A, keys.KEY_LL_IRC_70R_WHEELED,
    keys.KEY_LL_IRC_70R_TRACKED, keys.KEY_LL_IRC_AA_WHEELED,
    keys.KEY_LL_IRC_AA_TRACKED, keys.KEY_LL_IRC_CLASS_SV,
    keys.KEY_LL_IRC_70R_BOGIE, keys.KEY_LL_IRC_CLASS_FATIGUE,
)


@dataclass
class Scenario:
    name: str
    purpose: str
    data: dict
    sections: tuple = ALL_SECTIONS
    figures: bool = True
    toc: bool = True
    required_text: tuple = ()
    forbidden_text: tuple = ()
    required_source: tuple = ()
    forbidden_source: tuple = ()
    minimum_pages: int = 1
    figure_bytes: dict = field(default_factory=dict)


def _fresh(name, purpose, **options):
    return Scenario(name, purpose, copy.deepcopy(demonstration_data()), **options)


def _girder_count(data, count):
    inputs = data["inputs"]
    for key in list(inputs):
        if key.startswith(keys.KEY_MP_GD_SELECT_GIRDER + ".") or key.startswith(keys.KEY_MP_GD_MEMBER_ID + "."):
            del inputs[key]
    inputs[keys.KEY_TS_NO_OF_GIRDERS] = count
    results = {}
    for index in range(1, count + 1):
        inputs[f"{keys.KEY_MP_GD_SELECT_GIRDER}.G{index}"] = f"G{index}"
        inputs[f"{keys.KEY_MP_GD_MEMBER_ID}.G{index}.M1"] = f"G{index}M1"
        ratio = .5 + index / max(count, 1) * .3
        results[f"G{index}"] = {"checks": [{
            "name": "Synthetic girder flexure", "check_id": 1,
            "demand": ratio * 100, "capacity": 100, "dcr": ratio,
            "demand_unit": "kNm", "capacity_unit": "kNm", "status": "PASS",
        }]}
    data["outputs"]["design_results"] = {"per_girder": results}


def _all_component_ratios(data, ratio):
    for girder in data["outputs"]["design_results"]["per_girder"].values():
        for check in girder["checks"]:
            check.update(demand=ratio * 100, capacity=100, dcr=ratio,
                         status="FAIL" if ratio >= 1 else "WARN" if ratio >= 0.9 else "PASS")
    for prefix in ("crossbracing", "end_diaphragm"):
        data["outputs"][prefix + "_forces_dict"]["pairs"]["G1-G2"]["diag_compression_kN"] = ratio * 100
        data["outputs"][prefix + "_design_results"]["G1-G2"]["diagonal"]["compression"]["Optimum.UR"] = ratio


def build_scenarios():
    """Return independent, named scenarios covering different report behavior."""
    cases = []

    case = _fresh("01_full_report", "Full nine-chapter demo with deliberately failed component checks.",
                  required_text=("Exceeds UR limit", "Overall Design Check Summary"))
    cases.append(case)

    case = _fresh("02_minimal_data", "Only mandatory metadata; missing analysis remains explicitly unavailable.",
                  required_text=("Incomplete results",), forbidden_source=("Girder 1",))
    case.data["inputs"] = {}
    case.data["outputs"] = {"design_log": ["Synthetic minimum-data report."]}
    cases.append(case)

    case = _fresh("03_one_girder", "Single-column girder summaries and individual member tables.",
                  required_source=("G1M1",), forbidden_source=("G2M1",))
    _girder_count(case.data, 1)
    cases.append(case)

    case = _fresh("04_twelve_girders", "Wide executive summary plus long repeated member tables.",
                  required_source=("G12M1",), minimum_pages=2)
    _girder_count(case.data, 12)
    cases.append(case)

    case = _fresh("05_zero_girders", "Explicit zero girders produces unavailable rows without inventing members.",
                  required_text=("No valid demand/capacity results",), forbidden_source=("Girder 1",))
    _girder_count(case.data, 0)
    cases.append(case)

    cases.append(_fresh("06_without_figures", "Text/tables render when figures are disabled.", figures=False,
                        forbidden_source=("utilization.png", "steel_quantities.png", "deck_quantities.png")))
    cases.append(_fresh("07_without_toc", "Report numbering works when the table of contents is disabled.", toc=False,
                        forbidden_source=(r"\tableofcontents",)))
    cases.append(_fresh("08_loads_only", "Optional loads chapter without analysis or design chapters.", sections=("loads",),
                        required_text=("Vehicular Live Loads", "Footway Live Load"),
                        forbidden_source=(r"\chapter{Analysis Results}", r"\chapter{Design Checks}")))
    cases.append(_fresh("09_analysis_only", "Analysis chapter can be selected independently.", sections=("analysis",),
                        required_source=(r"\chapter{Analysis Results}",), forbidden_source=(r"\chapter{Loads and Load Combinations}",)))
    cases.append(_fresh("10_design_only", "Design tables/chart can be selected without optional loads and analysis.",
                        sections=("design_checks",), required_text=("Overall Design Check Summary",)))
    cases.append(_fresh("11_core_sections_only", "Required intro/input/material/reference chapters without optional chapters.",
                        sections=(), forbidden_source=(r"\chapter{Design Checks}", r"\chapter{Analysis Results}")))

    case = _fresh("12_all_vehicle_classes", "All eight standard UI vehicle selections render, including fatigue.",
                  required_text=("Class Fatigue", "Class SV", "Class AA (Tracked)"))
    case.data["inputs"].update({key: True for key in VEHICLE_KEYS})
    cases.append(case)

    case = _fresh("13_saved_false_flags", "Saved checkbox strings False/0 never select vehicles.",
                  required_source=("Vehicles Considered & None",))
    case.data["inputs"].update({key: "False" if index % 2 else "0" for index, key in enumerate(VEHICLE_KEYS)})
    cases.append(case)

    case = _fresh("14_custom_vehicle_escaping", "Custom vehicle names include ampersand, percent, underscore and braces.",
                  required_source=(r"Inspection\_\allowbreak{}Truck \& Trailer 20\% \{custom\}",))
    case.data["inputs"][keys.KEY_LL_CUSTOM_VEHICLES] = [{"name": "Inspection_Truck & Trailer 20% {custom}"}, "Maintenance vehicle"]
    cases.append(case)

    case = _fresh("15_metadata_metacharacters", "Plain metadata escapes every LaTeX metacharacter safely.",
                  required_source=(r"\textbackslash{}", r"\textasciitilde{}", r"\textasciicircum{}"))
    case.data["metadata"].update(company=r"A&B_Design#1 100% ${draft} \ ~ ^", reviewer="Reviewer & Team")
    cases.append(case)

    case = _fresh("16_unicode_engineering_text", "Accented Latin text and common engineering glyphs compile.",
                  required_text=("Café",), required_source=(r"\textsuperscript{2}", r"\ensuremath{\geq}"))
    case.data["metadata"].update(company="Café civil — design ≥ 2 m²", client="München × consulting")
    cases.append(case)

    case = _fresh("17_long_wrapped_metadata", "Long metadata wraps inside separate header columns.",
                  required_text=("SYNTHETIC LONG PROJECT",))
    case.data["metadata"]["project_name"] = "SYNTHETIC LONG PROJECT " + "bridge geometry and durability review " * 3
    case.data["metadata"]["subtitle"] = "Long revision note " + "construction stage " * 3
    case.data["metadata"]["additional_comments"] = "Synthetic commentary for wrapping. " * 20
    cases.append(case)

    case = _fresh("18_automatic_footway", "Automatic footway mode reports the existing IRC helper value.",
                  required_text=("4.905", "Footway Live Load"))
    case.data["inputs"][keys.KEY_LL_FOOTPATH_PRESSURE_MODE] = "Automatic"
    case.data["inputs"].pop(keys.KEY_LL_FOOTPATH_PRESSURE_VALUE)
    cases.append(case)

    case = _fresh("19_zero_custom_footway", "A valid custom zero is retained, rather than treated as missing.",
                  required_source=("Footway Pressure (IRC 6 Cl. 206.1 or user-defined) & 0",))
    case.data["inputs"][keys.KEY_LL_FOOTPATH_PRESSURE_VALUE] = 0
    cases.append(case)

    case = _fresh("20_no_footway", "Explicitly absent footway is distinct from missing pressure.",
                  required_text=("Not applicable",))
    case.data["inputs"][keys.KEY_FOOTPATH] = "None"
    cases.append(case)

    case = _fresh("21_no_design_results", "Analysis-only backend output must not claim a passing design.",
                  required_text=("Incomplete results", "No valid demand/capacity results"),
                  forbidden_text=("design pass",))
    case.data["outputs"] = {"analysis_summary": case.data["outputs"]["analysis_summary"], "design_log": ["No synthetic design results."]}
    cases.append(case)

    case = _fresh("22_unity_threshold", "Ratios equal to one stay on the reference threshold.",
                  required_text=("Within UR limit (reported checks)", "Backend reports FAIL"),
                  required_source=("1.0000 & FAIL",), forbidden_text=("Exceeds UR limit",))
    _all_component_ratios(case.data, 1.0)
    cases.append(case)

    case = _fresh("23_exceeded_threshold", "Ratios above one are visibly reported as exceeding the limit.",
                  required_text=("Exceeds UR limit", "1.50"))
    _all_component_ratios(case.data, 1.5)
    cases.append(case)

    case = _fresh("24_zero_capacity", "A zero capacity never becomes a passing zero ratio.",
                  required_text=("No valid demand/capacity results",))
    for member in case.data["outputs"]["design_results"]["per_girder"].values():
        member["checks"][0].update(capacity=0, dcr=999, status="FAIL")
    cases.append(case)

    case = _fresh("25_nonfinite_result_fields", "Nonfinite demand/capacity inputs remain unavailable in summaries.",
                  required_text=("No valid demand/capacity results",))
    for member in case.data["outputs"]["design_results"]["per_girder"].values():
        member["checks"][0].update(demand=float("nan"), capacity=float("inf"), dcr=float("nan"))
    case.data["outputs"]["deck_report_values"][keys.KEY_DD_MU_BOT] = float("nan")
    cases.append(case)

    case = _fresh("26_partial_deck_results", "Missing deck flags remain N/A; an explicit failed flag stays failed.",
                  required_source=("N/A", "FAIL"))
    case.data["outputs"]["deck_report_values"] = {
        keys.KEY_DD_M_ULS_SAG: 90, keys.KEY_DD_MU_BOT: 120,
        keys.KEY_DD_PUNCH_OK: False,
    }
    cases.append(case)

    case = _fresh("27_diaphragm_only", "Diaphragm data is independent when cross-bracing data is absent.",
                  required_text=("Cross bracing: No valid demand/capacity results", "End diaphragms: Exceeds UR limit"))
    case.data["outputs"].pop("crossbracing_forces_dict")
    case.data["outputs"].pop("crossbracing_design_results")
    cases.append(case)

    case = _fresh("28_cross_bracing_only", "Missing diaphragm results cannot be copied from cross bracing.",
                  required_text=("End diaphragms: No valid demand/capacity results", "Cross bracing: Within UR limit"))
    case.data["outputs"].pop("end_diaphragm_forces_dict")
    case.data["outputs"].pop("end_diaphragm_design_results")
    cases.append(case)

    case = _fresh("29_missing_material_geometry", "Absent dimensions produce unavailable quantities, not invented tonnage.",
                  required_text=("N/A",))
    case.data["inputs"].pop(keys.KEY_TS_OVERALL_WIDTH)
    case.data["inputs"].pop(keys.KEY_TS_DECK_THICKNESS)
    case.data["inputs"].pop("member_properties.girder_details.section_properties.area")
    case.data["inputs"].pop("member_properties.girder_details.section_properties.mass")
    cases.append(case)

    case = _fresh("30_large_material_scale", "Quantity chart scales large masses and keeps concrete/rebar units separate.",
                  required_source=("deck_quantities.png", "steel_quantities.png"))
    case.data["inputs"].update({keys.KEY_SPAN: 100, keys.KEY_TS_OVERALL_WIDTH: 30,
                                keys.KEY_TS_DECK_THICKNESS: 500, "end_diaphragm_wt_total": 25})
    cases.append(case)

    case = _fresh("31_multipage_analysis", "150 uniquely named loadcases survive repeated-header page breaks.",
                  required_text=("MATRIX-LC-001", "MATRIX-LC-150"), minimum_pages=30)
    case.data["outputs"]["analysis_summary"]["load_cases"] = {
        f"MATRIX-LC-{index:03d}": {"max_bm": index * 10, "max_sf": index,
                                  "bm_girder": "G1", "sf_girder": "G2",
                                  "bm_location": 12.5, "sf_location": 0}
        for index in range(1, 151)
    }
    cases.append(case)

    case = _fresh("32_embedded_raster_figure", "Real in-memory PNG bytes survive the temporary assets lifecycle.",
                  required_source=("girder_top.png",))
    # A tiny valid RGB PNG produced without an image library or external file.
    import struct
    import zlib

    def chunk(kind, contents):
        return struct.pack("!I", len(contents)) + kind + contents + struct.pack("!I", zlib.crc32(kind + contents))

    case.figure_bytes["girder_top"] = (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\x91\xb0\x14" * 2) * 2)) + chunk(b"IEND", b""))
    cases.append(case)
    case = _fresh("33_greek_temperature_symbols", "Greek engineering labels and Celsius symbols render with explicit TeX commands.",
                  required_source=(r"\ensuremath{\alpha}", r"\ensuremath{\sigma}", r"\ensuremath{^\circ}C"))
    case.data["metadata"]["company"] = "Engineering \u03b1, \u03c3, \u0394 at 25\u2103"
    cases.append(case)

    case = _fresh("34_custom_vehicle_inclusion", "The actual custom-vehicle UI inclusion flag controls report selection.",
                  required_source=("Included inspection truck",), forbidden_source=("Excluded control truck",))
    case.data["inputs"][keys.KEY_LL_CUSTOM_VEHICLES] = [
        {"name": "Included inspection truck", "included": True},
        {"name": "Excluded control truck", "included": False},
    ]
    cases.append(case)

    case = _fresh("35_supplied_diaphragm_quantity", "Explicitly supplied end-diaphragm tonnage is retained in the table and material chart.",
                  required_source=("End Diaphragms", "steel_quantities.png"), required_text=("2.75",))
    case.data["inputs"]["end_diaphragm_wt_total"] = 2.75
    cases.append(case)
    return cases


def _normal(text):
    return "".join(unicodedata.normalize("NFKC", text).split())


def run_scenario(case, output, compiler=None):
    """Render one actual PDF and inspect its source, pages and expected content."""
    from pypdf import PdfReader

    started = time.monotonic()
    directory = Path(output) / case.name
    data = copy.deepcopy(case.data)
    snapshot = json.dumps(data, sort_keys=True, ensure_ascii=True)
    record = {"name": case.name, "purpose": case.purpose, "passed": False, "errors": []}
    try:
        options = ReportOptions(list(case.sections), case.figures, case.toc, True)
        request = ReportRequest(ReportMetadata(**data["metadata"]), options, str(directory), "report")
        payload = build_report_payload(request, data["inputs"], data["outputs"])
        payload.figure_data.update(case.figure_bytes)
        result = generate_report(payload, request, compiler=compiler)
        if result.error or not result.pdf_path or not result.tex_path:
            raise RuntimeError(result.error or "The renderer returned no PDF or source.")
        pdf = Path(result.pdf_path)
        source = Path(result.tex_path).read_text(encoding="utf-8")
        reader = PdfReader(pdf, strict=True)
        text = _normal("\n".join(page.extract_text() or "" for page in reader.pages))
        for phrase in case.required_text:
            if _normal(phrase) not in text:
                record["errors"].append("Missing expected PDF text: " + phrase)
        for phrase in case.forbidden_text:
            if _normal(phrase) in text:
                record["errors"].append("Unexpected PDF text: " + phrase)
        for phrase in case.required_source:
            if phrase not in source:
                record["errors"].append("Missing expected source content: " + phrase)
        for phrase in case.forbidden_source:
            if phrase in source:
                record["errors"].append("Unexpected source content: " + phrase)
        tables = source.count(r"\begin{longtable}")
        headers = source.count(r"\endhead")
        if tables != headers:
            record["errors"].append(f"Table/continuation-header count differs: {tables}/{headers}")
        if len(reader.pages) < case.minimum_pages:
            record["errors"].append(f"Expected at least {case.minimum_pages} pages, found {len(reader.pages)}")
        if "design pass" in text.lower():
            record["errors"].append("The PDF contains an unconditional design-pass claim.")
        if json.dumps(data, sort_keys=True, ensure_ascii=True) != snapshot:
            record["errors"].append("Rendering mutated the supplied scenario data.")
        if not text:
            record["errors"].append("The PDF contains no extractable report text.")
        record.update(pdf=case.name + "/report.pdf", pages=len(reader.pages), tables=tables,
                      continuation_headers=headers, sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
                      passed=not record["errors"])
    except Exception as exc:
        # Keep machine-specific paths and input content out of shared evidence.
        message = str(exc).replace(str(ROOT), "<checkout>").replace(str(Path(output).resolve()), "<matrix-output>")
        message = re.sub(r"[A-Za-z]:[\\/][^\s\n]+", "<local-path>", message)
        record["errors"].append(message)
    record["seconds"] = round(time.monotonic() - started, 3)
    return record


def run_matrix(output, compiler=None, limit=None, names=None):
    cases = build_scenarios()
    if names:
        cases = [case for case in cases if case.name in names]
    if limit:
        cases = cases[:limit]
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=True)
    results = []
    for case in cases:
        result = run_scenario(case, directory, compiler)
        results.append(result)
        print(("PASS " if result["passed"] else "FAIL ") + case.name +
              ("" if result["passed"] else ": " + "; ".join(result["errors"])), flush=True)
    summary = {"scope": "Synthetic report rendering with a real compiler; no bridge analysis executed.",
               "total": len(results), "passed": sum(result["passed"] for result in results),
               "failed": sum(not result["passed"] for result in results), "scenarios": results}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "report-matrix")
    parser.add_argument("--compiler", default=os.environ.get("OSDAG_TEST_LATEX"))
    parser.add_argument("--limit", type=int, help="Run only the first N scenarios during development.")
    parser.add_argument("--case", action="append", help="Run a named case; may be repeated.")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    known = {case.name for case in build_scenarios()}
    if args.case and not set(args.case) <= known:
        parser.error("Unknown scenario: " + ", ".join(sorted(set(args.case) - known)))
    summary = run_matrix(args.output, args.compiler, args.limit, args.case)
    print(f"{summary['passed']}/{summary['total']} real PDF scenarios passed. Evidence: {args.output / 'summary.json'}")
    return 0 if summary["total"] and summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
