"""Inspect an actual compiled PDF; optionally verify multipage table evidence.

Requires ``pypdf``; coordinate checks also require ``PyMuPDF``. This validates text and the
baselines of explicitly identified table rows; it is not a replacement for
visually reviewing drawings, equations, or arbitrary PDF content.
"""

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import re
import unicodedata


class PDFInspectionError(ValueError):
    """An input document cannot be opened or authenticated for inspection."""


def _normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).split())


def inspect_pdf(path, *, required_text=(), row_pattern=None, repeated_heading=None,
                expected_rows=None, footer_clearance=18.0, password=None):
    """Inspect structure and optional report requirements without changing a PDF.

    A valid scanned, drawn, or blank page is a warning rather than a failed PDF.
    Text and table requirements, when explicitly requested, remain mandatory.
    Passwords are used only to read encrypted documents and never enter results.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF inspection requires pypdf: python -m pip install pypdf") from exc

    if isinstance(required_text, str):
        required_text = (required_text,)
    else:
        try:
            required_text = tuple(required_text)
        except TypeError as exc:
            raise ValueError("Required text must be a string or an iterable of strings.") from exc
    if any(not isinstance(phrase, str) for phrase in required_text):
        raise ValueError("Required text must contain strings.")
    if isinstance(expected_rows, bool) or (expected_rows is not None and
            (not isinstance(expected_rows, int) or expected_rows < 0)):
        raise ValueError("Expected rows must be a nonnegative integer.")
    if isinstance(footer_clearance, bool) or not isinstance(footer_clearance, (float, int)) or not math.isfinite(footer_clearance) or footer_clearance < 0:
        raise ValueError("Footer clearance must be a finite nonnegative number.")
    if (repeated_heading or expected_rows is not None) and not row_pattern:
        raise ValueError("A row pattern is required for heading or row-count checks.")
    try:
        row_expression = re.compile(row_pattern) if row_pattern else None
    except re.error as exc:
        raise ValueError("The row pattern is not a valid regular expression.") from exc
    if row_expression and row_expression.search(""):
        raise ValueError("The row pattern must identify nonempty row labels.")

    path = Path(path)
    try:
        reader = PdfReader(str(path), strict=False)
    except OSError as exc:
        raise PDFInspectionError("The PDF could not be read; check the file path and permissions.") from exc
    except Exception as exc:
        raise PDFInspectionError("The file is not a readable PDF or is damaged.") from exc
    encrypted = reader.is_encrypted
    if encrypted:
        try:
            authenticated = reader.decrypt(password if password is not None else "")
        except Exception as exc:
            reader.close()
            raise PDFInspectionError("The encrypted PDF could not be opened with this password.") from exc
        if not authenticated:
            reader.close()
            raise PDFInspectionError("The encrypted PDF requires the correct password.")
    positioned_document = None
    if row_expression:
        try:
            import pymupdf
        except ImportError as exc:
            reader.close()
            raise RuntimeError("Table coordinate inspection requires PyMuPDF: "
                               "python -m pip install PyMuPDF") from exc
        try:
            positioned_document = pymupdf.open(str(path))
            if positioned_document.needs_pass and not positioned_document.authenticate(password or ""):
                positioned_document.close()
                raise PDFInspectionError("The encrypted PDF requires the correct password.")
        except Exception:
            reader.close()
            raise
    all_text = []
    all_rows = []
    pages = []
    errors = []
    warnings = []
    textless_pages = []
    try:
        for number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
                warnings.append(f"Page {number}: text extraction was unavailable.")
            all_text.append(text)
            if not text.strip():
                textless_pages.append(number)
                warnings.append(f"Page {number} has no extractable text; it may be scanned, drawn, or blank.")
            evidence = {"page": number, "characters": len(text), "rotation": int(page.rotation)}
            if row_expression:
                # PyMuPDF resolves the complete text graphics state. pypdf's text
                # visitor can return repeated/approximate matrices for XeTeX output,
                # so those matrices are unsuitable for footer clearance evidence.
                positioned_page = positioned_document[number - 1]
                positions = [
                    ("".join(span["text"] for span in line["spans"]),
                     positioned_page.cropbox.height - max(span["origin"][1] for span in line["spans"]))
                    for block in positioned_page.get_text("dict")["blocks"]
                    for line in block.get("lines", [])
                    if line["spans"]
                ]
                rows = [match.group(0) for match in row_expression.finditer(text)]
                all_rows.extend(rows)
                evidence["rows"] = len(rows)
                if rows:
                    normalized = _normalized(text)
                    if repeated_heading and _normalized(repeated_heading) not in normalized:
                        errors.append(f"Page {number} has table rows but lacks the repeated heading.")
                    row_positions = [y for fragment, y in positions if row_expression.search(fragment)]
                    footer_positions = [y for fragment, y in positions if re.search(r"\bPage\s+\d", fragment)]
                    if not row_positions:
                        errors.append(f"Page {number}: table row coordinates were unavailable.")
                    elif not footer_positions:
                        errors.append(f"Page {number}: the numbered footer could not be located.")
                    else:
                        lowest_row = min(row_positions)
                        footer = min(footer_positions)
                        clearance = lowest_row - footer
                        evidence.update({
                            "lowest_row_baseline_pt": round(lowest_row, 2),
                            "footer_baseline_pt": round(footer, 2),
                            "clearance_pt": round(clearance, 2),
                        })
                        if clearance < footer_clearance:
                            errors.append(f"Page {number}: table row/footer clearance is {clearance:.2f}pt, "
                                          f"below the required {footer_clearance:.2f}pt.")
            pages.append(evidence)
    finally:
        if positioned_document is not None:
            positioned_document.close()
        reader.close()

    normalized_all = _normalized("\n".join(all_text))
    for phrase in required_text:
        if _normalized(phrase) not in normalized_all:
            errors.append(f"Required text was not found: {phrase}")
    if not pages:
        errors.append("The PDF contains no pages.")
    if row_expression:
        counts = Counter(all_rows)
        if not all_rows and expected_rows != 0:
            errors.append("No table rows matched the requested pattern.")
        duplicated = sorted(str(row) for row, count in counts.items() if count != 1)
        if duplicated:
            errors.append("Rows must occur exactly once: " + ", ".join(duplicated))
        if expected_rows is not None and len(all_rows) != expected_rows:
            errors.append(f"Expected {expected_rows} rows, found {len(all_rows)}.")
    return {
        "pdf": str(Path(path).resolve()),
        "page_count": len(pages),
        "pages": pages,
        "row_count": len(all_rows) if row_expression else None,
        "errors": errors,
        "warnings": warnings,
        "textless_pages": textless_pages,
        "encrypted": encrypted,
        "passed": not errors,
        "scope": "Extractable text and identified table-row baselines (PyMuPDF); drawings require visual review.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--require-text", action="append", default=[])
    parser.add_argument("--row-pattern", help="Regular expression identifying unique table rows.")
    parser.add_argument("--heading", help="Column heading required on every page containing matched rows.")
    parser.add_argument("--expected-rows", type=int)
    parser.add_argument("--footer-clearance", type=float, default=18.0,
                        help="Minimum row/footer baseline distance in PDF points (default: 18).")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--password-env", metavar="NAME",
                        help="Read an encrypted PDF password from this environment variable.")
    args = parser.parse_args(argv)
    if (args.heading or args.expected_rows is not None) and not args.row_pattern:
        parser.error("--heading and --expected-rows require --row-pattern")
    try:
        password = None
        if args.password_env:
            password = os.environ.get(args.password_env)
            if password is None:
                raise ValueError("The selected password environment variable is not set.")
        evidence = inspect_pdf(args.pdf, required_text=args.require_text,
                               row_pattern=args.row_pattern, repeated_heading=args.heading,
                               expected_rows=args.expected_rows, footer_clearance=args.footer_clearance,
                               password=password)
        rendered = json.dumps(evidence, indent=2)
        if args.json_output:
            args.json_output.write_text(rendered + "\n", encoding="utf-8")
    except Exception as exc:
        parser.exit(2, f"PDF inspection failed: {exc}\n")
    print(rendered)
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
