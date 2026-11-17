"""Inspect an actual compiled PDF; optionally verify multipage table evidence.

Requires ``pypdf``; coordinate checks also require ``PyMuPDF``. This validates text and the
baselines of explicitly identified table rows; it is not a replacement for
visually reviewing drawings, equations, or arbitrary PDF content.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import unicodedata


def inspect_pdf(path, *, required_text=(), row_pattern=None, repeated_heading=None,
                expected_rows=None, footer_clearance=18.0):
    """Return reproducible page/text evidence and any failed requirements."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF inspection requires pypdf: python -m pip install pypdf") from exc

    reader = PdfReader(str(path), strict=True)
    row_expression = re.compile(row_pattern) if row_pattern else None
    positioned_document = None
    if row_expression:
        try:
            import pymupdf
        except ImportError as exc:
            raise RuntimeError("Table coordinate inspection requires PyMuPDF: "
                               "python -m pip install PyMuPDF") from exc
        positioned_document = pymupdf.open(str(path))
    all_text = []
    all_rows = []
    pages = []
    errors = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        all_text.append(text)
        if not text.strip():
            errors.append(f"Page {number} has no extractable text.")
        evidence = {"page": number, "characters": len(text)}
        if row_expression:
            # PyMuPDF resolves the complete text graphics state. pypdf's text
            # visitor can return repeated/approximate matrices for XeTeX output,
            # so those matrices are unsuitable for footer clearance evidence.
            positioned_page = positioned_document[number - 1]
            positions = [
                ("".join(span["text"] for span in line["spans"]),
                 positioned_page.rect.height - max(span["origin"][1] for span in line["spans"]))
                for block in positioned_page.get_text("dict")["blocks"]
                for line in block.get("lines", [])
                if line["spans"]
            ]
            rows = row_expression.findall(text)
            all_rows.extend(rows)
            evidence["rows"] = len(rows)
            if rows:
                normalized = " ".join(text.split())
                if repeated_heading and " ".join(repeated_heading.split()) not in normalized:
                    errors.append(f"Page {number} has table rows but lacks the repeated heading.")
                row_positions = [y for fragment, y in positions if row_expression.search(fragment)]
                footer_positions = [y for fragment, y in positions if re.search(r"\bPage\s+\d", fragment)]
                if not row_positions:
                    errors.append(f"Page {number}: table row coordinates were unavailable.")
                elif not footer_positions:
                    errors.append(f"Page {number}: the numbered footer could not be located.")
                else:
                    lowest_row = min(row_positions)
                    footer = max(footer_positions)
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

    normalized_all = " ".join(unicodedata.normalize("NFKC", "\n".join(all_text)).split())
    for phrase in required_text:
        if " ".join(unicodedata.normalize("NFKC", phrase).split()) not in normalized_all:
            errors.append(f"Required text was not found: {phrase}")
    if not pages:
        errors.append("The PDF contains no pages.")
    if row_expression:
        counts = Counter(all_rows)
        duplicated = sorted(str(row) for row, count in counts.items() if count != 1)
        if duplicated:
            errors.append("Rows must occur exactly once: " + ", ".join(duplicated))
        if expected_rows is not None and len(all_rows) != expected_rows:
            errors.append(f"Expected {expected_rows} rows, found {len(all_rows)}.")
        positioned_document.close()
    return {
        "pdf": str(Path(path).resolve()),
        "page_count": len(pages),
        "pages": pages,
        "row_count": len(all_rows) if row_expression else None,
        "errors": errors,
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
    args = parser.parse_args(argv)
    if (args.heading or args.expected_rows is not None) and not args.row_pattern:
        parser.error("--heading and --expected-rows require --row-pattern")
    try:
        evidence = inspect_pdf(args.pdf, required_text=args.require_text,
                               row_pattern=args.row_pattern, repeated_heading=args.heading,
                               expected_rows=args.expected_rows, footer_clearance=args.footer_clearance)
    except Exception as exc:
        parser.exit(2, f"PDF inspection failed: {exc}\n")
    rendered = json.dumps(evidence, indent=2)
    if args.json_output:
        args.json_output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
