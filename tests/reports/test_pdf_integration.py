"""Opt-in evidence from a real compiler and a real multipage PDF.

Set OSDAG_TEST_LATEX to a pdflatex or Tectonic executable. The regular unit
suite remains usable without TeX; this test never substitutes a fake compiler.
"""

import importlib.util
import os
from pathlib import Path

import pytest

from osdagbridge.core.reports.compilation import compile_latex
from osdagbridge.core.reports.report_generator import preamble
from osdagbridge.core.reports.styles import format_chapter


COMPILER = os.environ.get("OSDAG_TEST_LATEX")


@pytest.mark.skipif(not COMPILER, reason="Set OSDAG_TEST_LATEX to run the real PDF pagination test")
def test_real_longtable_repeats_headings_preserves_rows_and_clears_footer(tmp_path):
    pytest.importorskip("pypdf")
    pytest.importorskip("pymupdf")
    verifier_path = Path(__file__).resolve().parents[2] / "scripts" / "verify_report_pdf.py"
    module_spec = importlib.util.spec_from_file_location("report_pdf_verifier", verifier_path)
    verifier = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(verifier)

    rows = []
    for number in range(1, 101):
        label = (r"\multirow{20}{*}{G" + str((number - 1) // 20 + 1) + "}"
                 if (number - 1) % 20 == 0 else "")
        rows.append(label + f" & ROW-{number:03d}" + r" & 123.456 \\[6pt]\cline{2-3}")
    table = (r"\begin{longtable}{|L{2cm}|L{6cm}|p{6cm}|}"
             r"\caption{Pagination regression fixture}\hline"
             r"\textbf{Member} & \textbf{Pagination Heading} & \textbf{Value}\\\hline"
             + "\n".join(rows) + r"\end{longtable}")
    source = tmp_path / "pagination.tex"
    source.write_text(preamble("Pagination fixture", "PAGINATION", "2026-11-17")
                      + format_chapter(table) + r"\end{document}", encoding="utf-8")
    pdf = compile_latex(source, executable=COMPILER)
    evidence = verifier.inspect_pdf(pdf, row_pattern=r"ROW-\d{3}",
                                    repeated_heading="Pagination Heading", expected_rows=100,
                                    footer_clearance=18.0)
    assert evidence["passed"], evidence["errors"]
    data_pages = [page for page in evidence["pages"] if page.get("rows")]
    assert len(data_pages) >= 2, "The fixture must actually cross a page boundary"
    assert evidence["row_count"] == 100
    from pypdf import PdfReader
    import re
    text = "\n".join(page.extract_text() for page in PdfReader(pdf).pages)
    for member in range(1, 6):
        assert len(re.findall(rf"\bG{member}\b", text)) == 20
