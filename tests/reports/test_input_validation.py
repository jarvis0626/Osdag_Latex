"""Saved-result input errors must be actionable and never look like a new report."""

from copy import deepcopy
import json
from pathlib import Path
import re

import pytest

from osdagbridge.core.reports import __main__ as cli
from osdagbridge.core.reports import report_generator as reports
from osdagbridge.core.reports.demo import demonstration_data
from osdagbridge.core.reports.report_utils import _tex, get_girder_entries
from osdagbridge.core.reports.chap2 import ch2_input_parameters
from osdagbridge.core.utils.common import KEY_SPAN, KEY_TS_NO_OF_GIRDERS


def write_data(tmp_path, data, *, encoding="utf-8"):
    path = tmp_path / "results.json"
    path.write_text(json.dumps(data), encoding=encoding)
    return path


@pytest.mark.parametrize("path,value,field", [
    (("metadata",), [], "metadata"),
    (("inputs",), [], "inputs"),
    (("outputs",), "results", "outputs"),
    (("metadata", "designer"), 37, "metadata.designer"),
    (("metadata", "company"), None, "metadata.company"),
    (("outputs", "analysis_summary"), [], "outputs.analysis_summary"),
    (("outputs", "analysis_summary", "load_cases"), [], "load_cases"),
    (("outputs", "analysis_summary", "load_cases", "case"), 3, "load_cases.case"),
    (("outputs", "design_results"), [], "outputs.design_results"),
    (("outputs", "design_results", "per_girder"), [], "per_girder"),
    (("outputs", "design_results", "per_girder", "G1"), [], "per_girder.G1"),
    (("outputs", "design_results", "per_girder", "G1", "checks"), {}, "G1.checks"),
    (("outputs", "design_results", "per_girder", "G1", "checks"), [3], "checks[0]"),
    (("outputs", "design_results", "per_girder", "G1", "per_lc"), [], "G1.per_lc"),
    (("outputs", "deck_report_values"), [], "deck_report_values"),
    (("outputs", "end_diaphragm_design_results"), [], "end_diaphragm_design_results"),
    (("outputs", "crossbracing_forces_dict"), [], "crossbracing_forces_dict"),
    (("outputs", "design_checks"), "checks", "design_checks"),
    (("outputs", "design_log"), "line", "design_log"),
    (("outputs", "design_log"), [37], "design_log"),
    (("inputs", KEY_SPAN), "unknown", KEY_SPAN),
    (("inputs", KEY_SPAN), True, KEY_SPAN),
    (("inputs", KEY_SPAN), -3, KEY_SPAN),
    (("inputs", KEY_TS_NO_OF_GIRDERS), 1.5, KEY_TS_NO_OF_GIRDERS),
])
def test_nested_input_errors_name_the_invalid_field(tmp_path, path, value, field):
    data = demonstration_data()
    current = data
    for key in path[:-1]:
        current = current.setdefault(key, {})
    current[path[-1]] = value
    with pytest.raises(ValueError, match=re.escape(field)):
        cli.load_report_data(write_data(tmp_path, data))


def test_utf8_bom_json_can_generate_a_source_report(tmp_path, capsys):
    data = demonstration_data()
    source = write_data(tmp_path, data, encoding="utf-8-sig")
    assert cli.load_report_data(source) == data
    output = tmp_path / "report output"
    assert cli.main(["--input", str(source), "--output", str(output), "--no-pdf"]) == 0
    assert (output / "Report_After.tex").is_file()
    assert "LaTeX:" in capsys.readouterr().out


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_nonstandard_json_constants_have_a_clear_error(tmp_path, constant):
    source = tmp_path / "bad.json"
    source.write_text('{"value":' + constant + '}', encoding="utf-8")
    with pytest.raises(ValueError, match="use null"):
        cli.load_report_data(source)


def test_invalid_json_reports_line_and_column_without_traceback(tmp_path, capsys):
    source = tmp_path / "bad.json"
    source.write_text('{\n "metadata": [}', encoding="utf-8")
    with pytest.raises(SystemExit) as failure:
        cli.main(["--input", str(source)])
    assert failure.value.code == 2
    error = capsys.readouterr().err
    assert "line 2, column" in error
    assert "Traceback" not in error


def test_missing_metadata_key_has_a_field_specific_message(tmp_path):
    data = demonstration_data()
    del data["metadata"]["company"]
    with pytest.raises(ValueError, match="metadata.company is required"):
        cli.load_report_data(write_data(tmp_path, data))


def test_unknown_metadata_key_does_not_escape_as_a_constructor_error(tmp_path):
    data = demonstration_data()
    data["metadata"]["unexpected"] = "text"
    with pytest.raises(ValueError, match="Unknown metadata field.*unexpected"):
        cli.load_report_data(write_data(tmp_path, data))


@pytest.mark.parametrize("name", ["CON", "con.pdf", "NUL", "AUX", "PRN", "COM1", "LPT9", "report.", "../report", "a/b", "", "a" * 121])
def test_unsafe_portable_names_are_rejected_before_creating_output(tmp_path, name):
    with pytest.raises(SystemExit) as failure:
        cli.main(["--demo", "--name", name, "--output", str(tmp_path / "new"), "--no-pdf"])
    assert failure.value.code == 2
    assert not (tmp_path / "new").exists()


def test_failed_payload_is_not_silently_replaced_with_an_empty_report(tmp_path):
    data = demonstration_data()
    metadata = reports.ReportMetadata(**data["metadata"])
    options = reports.ReportOptions([], False, False, False)
    request = reports.ReportRequest(metadata, options, str(tmp_path), "report")
    prior_source = tmp_path / "report.tex"
    prior_source.write_text("an older report", encoding="utf-8")
    payload = reports.build_report_payload(request, [], {})
    assert "inputs must be an object" in payload.error
    result = reports.generate_report(payload, request)
    assert result.error and result.pdf_path is None and result.tex_path is None
    assert prior_source.read_text(encoding="utf-8") == "an older report"


def test_atomic_file_publication_keeps_previous_file_when_copy_fails(tmp_path, monkeypatch):
    source, destination = tmp_path / "new.pdf", tmp_path / "published.pdf"
    source.write_bytes(b"new complete file")
    destination.write_bytes(b"old complete file")

    def fail_copy(source, target):
        Path(target).write_bytes(b"partial")
        raise OSError("Disk full")

    monkeypatch.setattr(reports.shutil, "copy2", fail_copy)
    with pytest.raises(OSError, match="Disk full"):
        reports._atomic_copy(source, destination)
    assert destination.read_bytes() == b"old complete file"
    assert not list(tmp_path.glob(".published.pdf.*"))


def test_omitted_optional_chapters_keep_canonical_material_chapter_number(tmp_path):
    data = demonstration_data()
    request = reports.ReportRequest(reports.ReportMetadata(**data["metadata"]),
                                    reports.ReportOptions([], False, False, False), str(tmp_path), "report")
    result = reports.generate_report(reports.build_report_payload(request, data["inputs"], data["outputs"]), request)
    assert result.error is None
    source = Path(result.tex_path).read_text(encoding="utf-8")
    assert r"\setcounter{chapter}{6}" in source
    assert r"\chapter{Loads" not in source
    assert r"\chapter{Material Take-off" in source


@pytest.mark.parametrize("value", [None, "", "0", "4.0", "four", -1, float("nan")])
def test_incomplete_girder_counts_cannot_crash_plain_chapter_helpers(value):
    entries = get_girder_entries({KEY_TS_NO_OF_GIRDERS: value})
    assert len(entries) == (4 if value == "4.0" else 0)


def test_decomposed_unicode_accent_is_normalized_before_tex_escaping():
    assert _tex("Cafe\u0301 & bridge") == _tex("Caf\u00e9 & bridge")


@pytest.mark.parametrize("inputs", [{}, {KEY_TS_NO_OF_GIRDERS: 0}])
def test_input_tables_do_not_invent_a_girder_for_missing_geometry(inputs):
    metadata = reports.ReportMetadata(**demonstration_data()["metadata"])
    source = ch2_input_parameters(metadata, inputs, {})
    assert "Girder 1" not in source
    assert "N/A & N/A & N/A & N/A & N/A" in source
