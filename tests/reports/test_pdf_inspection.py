"""Inspect real PDF structures, without a compiler or personal document fixtures."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pymupdf
from pypdf import PdfReader, PdfWriter
import pytest


@pytest.fixture(scope="module")
def verifier():
    path = Path(__file__).resolve().parents[2] / "scripts" / "verify_report_pdf.py"
    spec = importlib.util.spec_from_file_location("pdf_inspection_verifier", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_pdf(tmp_path, pages=(("Report heading", "Example body"),), *, name="example.pdf",
             row_y=150, footer=True, rotation=0):
    path = tmp_path / name
    with pymupdf.open() as document:
        for number, lines in enumerate(pages, start=1):
            page = document.new_page(width=612, height=792)
            for index, text in enumerate(lines):
                page.insert_text((40, 65 if index == 0 else row_y + (index - 1) * 18), text)
            if footer:
                page.insert_text((40, 755), f"Page {number} of {len(pages)}")
            page.set_rotation(rotation)
        document.save(path)
    return path


def encrypt_pdf(source, destination, password="example-secret"):
    writer = PdfWriter()
    reader = PdfReader(source)
    writer.append_pages_from_reader(reader)
    writer.encrypt(password)
    writer.write(destination)
    writer.close()
    reader.close()
    return destination


def test_regular_pdf_has_text_and_structure_evidence(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path), required_text=["Report heading", "Example body"])
    assert result["passed"]
    assert result["page_count"] == 1
    assert result["pages"][0]["characters"] > 0
    assert result["warnings"] == []


def test_single_required_phrase_is_treated_as_one_phrase(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path), required_text="Example body")
    assert result["passed"]


def test_required_text_accepts_generator_without_consuming_it(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path), required_text=(value for value in ["Missing phrase"]))
    assert not result["passed"]


def test_missing_required_text_fails_with_clear_evidence(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path), required_text=["Missing phrase"])
    assert not result["passed"]
    assert result["errors"] == ["Required text was not found: Missing phrase"]


def test_pdf_font_ligatures_are_normalized_for_text_checks(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path, (("office",),)), required_text=["of\ufb01ce"])
    assert result["passed"]


def test_latin_accented_text_survives_inspection(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path, (("Caf\u00e9 project",),)), required_text=["Caf\u00e9"])
    assert result["passed"]


def test_required_text_can_span_extracted_line_breaks(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path, (("Report", "heading"),)), required_text=["Report heading"])
    assert result["passed"]


def test_image_only_pdf_is_valid_with_text_warning(verifier, tmp_path):
    path = tmp_path / "image-only.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        image = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 8, 8), False)
        image.clear_with(0x99)
        page.insert_image(pymupdf.Rect(30, 30, 300, 300), stream=image.tobytes("png"))
        document.save(path)
    result = verifier.inspect_pdf(path)
    assert result["passed"]
    assert result["textless_pages"] == [1]
    assert "no extractable text" in result["warnings"][0]


def test_vector_diagram_without_text_is_valid_with_warning(verifier, tmp_path):
    path = tmp_path / "drawing.pdf"
    with pymupdf.open() as document:
        document.new_page().draw_rect(pymupdf.Rect(40, 40, 200, 200))
        document.save(path)
    result = verifier.inspect_pdf(path)
    assert result["passed"] and result["warnings"]


def test_blank_page_is_structurally_valid_but_disclosed(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path, ((),), footer=False))
    assert result["passed"]
    assert result["textless_pages"] == [1]


def test_textless_page_does_not_satisfy_required_text(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path, ((),), footer=False), required_text=["Design summary"])
    assert not result["passed"]


def test_mixed_document_retains_every_page(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path, (("Text page",), (), ("Final page",)), footer=False))
    assert result["passed"] and result["page_count"] == 3
    assert result["textless_pages"] == [2]


def test_rotated_pdf_is_readable(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path, rotation=90), required_text=["Example body"])
    assert result["passed"] and result["pages"][0]["rotation"] == 90


def test_inspection_never_changes_source_bytes(verifier, tmp_path):
    path = make_pdf(tmp_path)
    before = hashlib.sha256(path.read_bytes()).digest()
    verifier.inspect_pdf(path)
    assert hashlib.sha256(path.read_bytes()).digest() == before


def test_encrypted_pdf_accepts_correct_password_without_disclosing_it(verifier, tmp_path):
    path = encrypt_pdf(make_pdf(tmp_path), tmp_path / "encrypted.pdf")
    result = verifier.inspect_pdf(path, password="example-secret", required_text=["Example body"])
    assert result["passed"] and result["encrypted"]
    assert "example-secret" not in json.dumps(result)


@pytest.mark.parametrize("password", [None, "incorrect-password"])
def test_encrypted_pdf_rejects_missing_or_wrong_password(verifier, tmp_path, password):
    path = encrypt_pdf(make_pdf(tmp_path), tmp_path / "encrypted.pdf")
    with pytest.raises(verifier.PDFInspectionError, match="correct password"):
        verifier.inspect_pdf(path, password=password)


def test_encrypted_pdf_allows_geometry_checks_with_password(verifier, tmp_path):
    path = encrypt_pdf(make_pdf(tmp_path, (("Column heading", "ROW-001"),)), tmp_path / "encrypted.pdf")
    result = verifier.inspect_pdf(path, password="example-secret", row_pattern=r"ROW-\d{3}", expected_rows=1)
    assert result["passed"]
    assert result["pages"][0]["clearance_pt"] > 18


def test_corrupt_pdf_is_rejected_cleanly(verifier, tmp_path):
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.7\nnot a PDF document")
    with pytest.raises(verifier.PDFInspectionError, match="damaged"):
        verifier.inspect_pdf(path)


def test_non_pdf_file_is_rejected(verifier, tmp_path):
    path = tmp_path / "file.pdf"
    path.write_text("This is ordinary text.", encoding="utf-8")
    with pytest.raises(verifier.PDFInspectionError):
        verifier.inspect_pdf(path)


def test_empty_file_is_rejected(verifier, tmp_path):
    path = tmp_path / "empty.pdf"
    path.touch()
    with pytest.raises(verifier.PDFInspectionError):
        verifier.inspect_pdf(path)


def test_zero_page_pdf_is_reported_as_invalid(verifier, tmp_path):
    path = tmp_path / "no-pages.pdf"
    writer = PdfWriter()
    writer.write(path)
    writer.close()
    result = verifier.inspect_pdf(path)
    assert not result["passed"] and result["page_count"] == 0


def test_missing_file_is_rejected_cleanly(verifier, tmp_path):
    with pytest.raises(verifier.PDFInspectionError, match="file path"):
        verifier.inspect_pdf(tmp_path / "absent.pdf")


def test_directory_instead_of_pdf_is_rejected(verifier, tmp_path):
    with pytest.raises(verifier.PDFInspectionError, match="file path"):
        verifier.inspect_pdf(tmp_path)


def test_repeated_headings_and_unique_rows_on_multiple_pages(verifier, tmp_path):
    path = make_pdf(tmp_path, (("Column heading", "ROW-001"), ("Column heading", "ROW-002")))
    result = verifier.inspect_pdf(path, row_pattern=r"ROW-\d{3}", repeated_heading="Column heading", expected_rows=2)
    assert result["passed"] and result["row_count"] == 2


def test_missing_continuation_heading_is_detected(verifier, tmp_path):
    path = make_pdf(tmp_path, (("Column heading", "ROW-001"), ("Another heading", "ROW-002")))
    result = verifier.inspect_pdf(path, row_pattern=r"ROW-\d{3}", repeated_heading="Column heading", expected_rows=2)
    assert not result["passed"]
    assert any("Page 2" in error and "repeated heading" in error for error in result["errors"])


def test_duplicate_row_labels_are_detected_across_pages(verifier, tmp_path):
    path = make_pdf(tmp_path, (("Heading", "ROW-001"), ("Heading", "ROW-001")))
    result = verifier.inspect_pdf(path, row_pattern=r"ROW-\d{3}", expected_rows=2)
    assert not result["passed"]
    assert any("exactly once" in error for error in result["errors"])


def test_expected_row_count_mismatch_is_detected(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path), row_pattern=r"ROW-\d{3}", expected_rows=1)
    assert not result["passed"]
    assert "Expected 1 rows, found 0." in result["errors"]


def test_row_inspection_does_not_silently_succeed_without_matches(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path), row_pattern=r"ROW-\d{3}")
    assert not result["passed"]
    assert "No table rows matched" in result["errors"][0]


def test_explicitly_expected_zero_rows_can_pass(verifier, tmp_path):
    result = verifier.inspect_pdf(make_pdf(tmp_path), row_pattern=r"ROW-\d{3}", expected_rows=0)
    assert result["passed"]


def test_capture_groups_do_not_hide_distinct_row_labels(verifier, tmp_path):
    path = make_pdf(tmp_path, (("Heading", "ROW-001", "ITEM-001"),))
    result = verifier.inspect_pdf(path, row_pattern=r"(?:ROW|ITEM)-(\d{3})", expected_rows=2)
    assert result["passed"]


def test_footer_clearance_violation_is_detected(verifier, tmp_path):
    path = make_pdf(tmp_path, (("Heading", "ROW-001"),), row_y=745)
    result = verifier.inspect_pdf(path, row_pattern=r"ROW-\d{3}", expected_rows=1)
    assert not result["passed"]
    assert result["pages"][0]["clearance_pt"] == pytest.approx(10)


def test_missing_footer_is_detected_only_when_requested(verifier, tmp_path):
    path = make_pdf(tmp_path, (("Heading", "ROW-001"),), footer=False)
    assert verifier.inspect_pdf(path)["passed"]
    result = verifier.inspect_pdf(path, row_pattern=r"ROW-\d{3}")
    assert not result["passed"]
    assert any("footer could not be located" in error for error in result["errors"])


def test_page_number_in_heading_is_not_mistaken_for_bottom_footer(verifier, tmp_path):
    path = make_pdf(tmp_path, (("Page 99 sample heading", "ROW-001"),))
    result = verifier.inspect_pdf(path, row_pattern=r"ROW-\d{3}")
    assert result["passed"]


def test_geometry_uses_logical_page_coordinates_for_rotated_document(verifier, tmp_path):
    path = make_pdf(tmp_path, (("Heading", "ROW-001"),), rotation=90)
    result = verifier.inspect_pdf(path, row_pattern=r"ROW-\d{3}", expected_rows=1)
    assert result["passed"]
    assert result["pages"][0]["clearance_pt"] == pytest.approx(605)


@pytest.mark.parametrize("arguments", [
    {"row_pattern": "["},
    {"row_pattern": ".*"},
    {"expected_rows": -1},
    {"expected_rows": 1.5},
    {"expected_rows": True},
    {"expected_rows": 1},
    {"repeated_heading": "Heading"},
    {"footer_clearance": -1},
    {"footer_clearance": float("nan")},
    {"footer_clearance": float("inf")},
    {"footer_clearance": True},
    {"required_text": [123]},
    {"required_text": None},
])
def test_invalid_inspection_options_are_rejected(verifier, tmp_path, arguments):
    with pytest.raises(ValueError):
        verifier.inspect_pdf(make_pdf(tmp_path), **arguments)


def test_cli_json_evidence_is_written_and_return_code_matches_success(verifier, tmp_path, capsys):
    path = make_pdf(tmp_path)
    output = tmp_path / "evidence.json"
    assert verifier.main([str(path), "--json-output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["passed"]
    assert json.loads(capsys.readouterr().out)["passed"]


def test_cli_returns_failure_for_unmet_text_requirement(verifier, tmp_path, capsys):
    assert verifier.main([str(make_pdf(tmp_path)), "--require-text", "Missing phrase"]) == 1
    assert not json.loads(capsys.readouterr().out)["passed"]


def test_cli_can_read_password_from_environment(verifier, tmp_path, monkeypatch, capsys):
    path = encrypt_pdf(make_pdf(tmp_path), tmp_path / "encrypted.pdf")
    monkeypatch.setenv("TEST_PDF_PASSWORD", "example-secret")
    assert verifier.main([str(path), "--password-env", "TEST_PDF_PASSWORD"]) == 0
    assert "example-secret" not in capsys.readouterr().out


def test_cli_missing_password_environment_is_clear_without_traceback(verifier, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TEST_PDF_PASSWORD", raising=False)
    with pytest.raises(SystemExit) as error:
        verifier.main([str(make_pdf(tmp_path)), "--password-env", "TEST_PDF_PASSWORD"])
    assert error.value.code == 2
    assert "environment variable is not set" in capsys.readouterr().err


def test_cli_evidence_write_error_is_reported_cleanly(verifier, tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        verifier.main([str(make_pdf(tmp_path)), "--json-output", str(tmp_path / "missing" / "evidence.json")])
    assert error.value.code == 2
    assert "PDF inspection failed" in capsys.readouterr().err


def test_cli_option_dependencies_are_enforced(verifier, tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        verifier.main([str(make_pdf(tmp_path)), "--expected-rows", "1"])
    assert error.value.code == 2
    assert "require --row-pattern" in capsys.readouterr().err
