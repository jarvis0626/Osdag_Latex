"""Verify the supplied six-requirement contract without claiming a GUI design.

The optional PDF check uses explicitly synthetic supplied results. It exercises
the real report pipeline and compiler, not the structural analysis backend.
"""

from copy import deepcopy
import os
from pathlib import Path
import re

import pytest

from osdagbridge.core.reports import report_generator as reports
from osdagbridge.core.reports.compilation import ReportCompilationError
from osdagbridge.core.reports.demo import demonstration_data
from osdagbridge.core.utils.common import KEY_LL_CUSTOM_VEHICLES


def request_and_payload(destination, *, pdf=True):
    data = demonstration_data()
    data["metadata"]["company"] = "Contract fixture: \u03b1, \u03c3 and 25\u2103"
    data["inputs"]["end_diaphragm_wt_total"] = 2.75
    data["inputs"][KEY_LL_CUSTOM_VEHICLES] = [
        {"name": "Included contract truck", "included": True},
        {"name": "Excluded control truck", "included": False},
    ]
    request = reports.ReportRequest(
        reports.ReportMetadata(**data["metadata"]),
        reports.ReportOptions(["loads", "analysis", "design_checks", "drawings"], True, True, pdf),
        str(destination), "contract_report",
    )
    return request, reports.build_report_payload(request, data["inputs"], data["outputs"])


def verify_source_bundle(source):
    text = source.read_text(encoding="utf-8")
    assert text.count(r"\begin{longtable}") == text.count(r"\endhead")
    assert r"includeheadfoot" in text
    assert "Included contract truck" in text and "Excluded control truck" not in text
    assert "Vehicular Live Loads (LL)" in text and "Footway Live Load" in text
    assert r"\ensuremath{\alpha}" in text and r"\ensuremath{\sigma}" in text
    assert r"\ensuremath{^\circ}C" in text

    design = text.split(r"\chapter{Design Checks}", 1)[1].split(r"\setcounter{chapter}{5}", 1)[0]
    summary = design.index(r"\section{Overall Design Check Summary}")
    assert design[:summary].count(r"\section{") == 4
    assert design.index("utilization.png") > summary
    quantities = text.split(r"\chapter{Material Take-off \& Quantity Summary}", 1)[1]
    assert quantities.index("steel_quantities.png") < quantities.index(r"\chapter{")
    assert quantities.index("deck_quantities.png") < quantities.index(r"\chapter{")
    assert "End Diaphragms" in quantities and "2.75" in quantities
    assert text.count(r"\begin{figure}") >= 3
    for name in ("utilization", "steel_quantities", "deck_quantities"):
        image = source.parent / "contract_report_assets" / (name + ".png")
        assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    return text


@pytest.mark.parametrize("mode", ["source", "success", "compiler_failure"])
def test_chart_staging_is_cleaned_and_exported_bundle_survives(tmp_path, monkeypatch, mode):
    request, payload = request_and_payload(tmp_path / "exported", pdf=mode != "source")
    before = deepcopy(payload)
    temporary_directories = []
    real_temporary_directory = reports.tempfile.TemporaryDirectory

    def staging(*args, **kwargs):
        directory = real_temporary_directory(*args, **kwargs)
        temporary_directories.append(Path(directory.name))
        return directory

    def compiler(source, **kwargs):
        assert source.parent.is_dir()
        assert len(list((source.parent / "contract_report_assets").glob("*.png"))) >= 3
        if mode == "compiler_failure":
            raise ReportCompilationError("Contract fixture compiler failure")
        assert mode == "success", "Source-only mode must not call the compiler"
        source.with_suffix(".pdf").write_bytes(b"%PDF-1.7\ncontract test double")
        return source.with_suffix(".pdf")

    monkeypatch.setattr(reports.tempfile, "TemporaryDirectory", staging)
    monkeypatch.setattr(reports, "compile_latex", compiler)
    result = reports.generate_report(payload, request)
    assert payload == before
    assert temporary_directories and all(not path.exists() for path in temporary_directories)
    assert result.tex_path is not None
    verify_source_bundle(Path(result.tex_path))
    assert (result.error is not None) == (mode == "compiler_failure")
    assert (result.pdf_path is not None) == (mode == "success")


@pytest.mark.skipif(not os.environ.get("OSDAG_TEST_LATEX"), reason="Set OSDAG_TEST_LATEX for actual contract PDF compilation")
def test_real_pdf_contains_required_sections_and_preserves_supplied_data(tmp_path):
    from pypdf import PdfReader

    request, payload = request_and_payload(tmp_path)
    before = deepcopy(payload)
    result = reports.generate_report(payload, request, compiler=os.environ["OSDAG_TEST_LATEX"])
    assert result.error is None, result.error
    assert result.pdf_path and payload == before
    verify_source_bundle(Path(result.tex_path))
    reader = PdfReader(result.pdf_path, strict=True)
    compact = re.sub(r"\s+", "", "\n".join(page.extract_text() or "" for page in reader.pages))
    for phrase in ("5.5OverallDesignCheckSummary", "VehicularLiveLoads", "FootwayLiveLoad",
                   "Structuralsteelquantitiesinmetrictonnes", "Deckconcretevolume"):
        assert phrase in compact, phrase
    assert len(reader.pages) > 1
