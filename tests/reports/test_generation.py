"""Public report API regression tests using a minimal bridge snapshot."""

import base64
from copy import deepcopy
from pathlib import Path
import re

import pytest

from osdagbridge.core.reports import report_generator as reports
from osdagbridge.core.reports.compilation import ReportCompilationError
from osdagbridge.core.utils.common import KEY_SPAN, KEY_TS_NO_OF_GIRDERS


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
)


@pytest.fixture
def snapshot(tmp_path):
    metadata = reports.ReportMetadata(
        project_name="Bridge & Road #1",
        project_location="Mumbai",
        designer="Student",
        client="Test Client",
        company="Example",
        report_date="2026-11-17",
    )
    options = reports.ReportOptions(sections=["loads"], include_figures=False, include_toc=True, include_pdf=False)
    request = reports.ReportRequest(metadata, options, str(tmp_path / "output"), "bridge_report")
    inputs = {KEY_SPAN: 30, KEY_TS_NO_OF_GIRDERS: 0, "nested": {"values": [1, 2]}}
    output = {"analysis_summary": {"values": [3, 4]}, "design_log": ["Example design log"]}
    payload = reports.build_report_payload(request, inputs, output)
    return request, payload, inputs, output


def test_payload_builder_enriches_a_snapshot_without_mutating_caller_data(snapshot):
    request, _, inputs, output = snapshot
    request.metadata.project_location = ""
    original_inputs, original_output = deepcopy(inputs), deepcopy(output)
    inputs["project.location"] = {
        "data": {"latitude": 19.0, "longitude": 72.0},
        "weather_data": {"wind_speed": 39, "zone": "III"},
    }
    original_inputs = deepcopy(inputs)
    payload = reports.build_report_payload(request, inputs, output)

    assert inputs == original_inputs
    assert output == original_output
    assert payload.inputs["wind_speed"] == 39
    assert payload.inputs["latitude"] == 19.0
    payload.inputs["nested"]["values"].append(5)
    assert inputs["nested"]["values"] == [1, 2]


def test_source_only_generation_never_calls_compiler_and_preserves_payload(snapshot, monkeypatch):
    request, payload, inputs, output = snapshot
    payload.figure_data["plan"] = PNG
    before = deepcopy(payload)
    original_inputs, original_output = deepcopy(inputs), deepcopy(output)

    def compiler(*args, **kwargs):
        pytest.fail("Source-only rendering must not invoke a compiler")

    monkeypatch.setattr(reports, "compile_latex", compiler)
    result = reports.generate_report(payload, request)

    assert result.error is None
    assert result.pdf_path is None
    source = Path(result.tex_path)
    assert source.is_file()
    text = source.read_text(encoding="utf-8")
    assert text.startswith("\n\\documentclass") or r"\documentclass" in text
    assert text.rstrip().endswith(r"\end{document}")
    assert r"Bridge \& Road \#1" in text
    assert "Vehicular Live Loads (LL)" in text
    assert payload == before
    assert inputs == original_inputs and output == original_output


def test_source_bundle_copies_assets_and_uses_rebuildable_relative_paths(snapshot, tmp_path):
    request, payload, _, _ = snapshot
    logo = tmp_path / "custom logo.png"
    logo.write_bytes(PNG)
    payload.metadata.logo_path = str(logo)
    payload.figure_data["girder_top"] = PNG
    before = deepcopy(payload)

    result = reports.generate_report(payload, request)

    assert result.error is None
    source = Path(result.tex_path)
    assert (source.parent / "bridge_report_assets" / "girder_top.png").read_bytes() == PNG
    assert (source.parent / "bridge_report_assets" / "org_logo.png").read_bytes() == PNG
    text = source.read_text(encoding="utf-8")
    image_paths = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text)
    assert image_paths
    for image in image_paths:
        assert not Path(image).is_absolute()
        assert (source.parent / image).is_file(), image
    assert str(tmp_path) not in text
    assert payload == before


def test_failed_compilation_returns_error_and_retains_source_instead_of_stale_pdf(snapshot, monkeypatch):
    request, payload, _, _ = snapshot
    request.options.include_pdf = True
    destination = Path(request.output_dir)
    destination.mkdir()
    old_pdf = destination / "bridge_report.pdf"
    old_pdf.write_bytes(b"%PDF-1.7\nstale")

    def fail(source, executable=None):
        source.with_suffix(".compile.log").write_text("Missing LaTeX package example.sty", encoding="utf-8")
        raise ReportCompilationError("Missing LaTeX package example.sty")

    monkeypatch.setattr(reports, "compile_latex", fail)
    result = reports.generate_report(payload, request)

    assert result.pdf_path is None
    assert "example.sty" in result.error
    assert Path(result.tex_path).is_file()
    assert (destination / "bridge_report.compile.log").read_text(encoding="utf-8") == "Missing LaTeX package example.sty"


def test_successful_compilation_copies_new_pdf_to_requested_directory(snapshot, monkeypatch):
    request, payload, _, _ = snapshot
    request.options.include_pdf = True

    def compile_pdf(source, executable=None):
        assert executable == "chosen-compiler"
        source.with_suffix(".pdf").write_bytes(b"%PDF-1.7\nnew output")
        return source.with_suffix(".pdf")

    monkeypatch.setattr(reports, "compile_latex", compile_pdf)
    result = reports.generate_report(payload, request, compiler="chosen-compiler")

    assert result.error is None
    assert Path(result.pdf_path).read_bytes() == b"%PDF-1.7\nnew output"
    assert Path(result.pdf_path).parent == Path(request.output_dir)
    assert Path(result.tex_path).is_file()


@pytest.mark.parametrize("file_stem", ["../outside", "..", "/absolute", r"..\outside", "bad/name", "name with spaces", "", "a..b"])
def test_report_rejects_filename_traversal_before_writing(snapshot, file_stem):
    request, payload, _, _ = snapshot
    request.file_stem = file_stem
    result = reports.generate_report(payload, request)

    assert result.pdf_path is None and result.tex_path is None
    assert "filename" in result.error.lower()
    assert not Path(request.output_dir).exists()
