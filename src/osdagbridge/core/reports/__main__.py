"""Headless entry point for saved result dictionaries or a labeled demo."""

import argparse
import json
from dataclasses import fields, MISSING
from pathlib import Path

from .report_generator import (
    ReportMetadata, ReportOptions, ReportRequest, build_report_payload, generate_report,
    validate_report_data, validate_report_stem,
)


def load_report_data(path):
    """Read a saved snapshot, including Windows UTF-8 BOM files, with clear errors."""
    def reject_constant(value):
        raise ValueError(f"JSON contains {value}; use null for unavailable values, not NaN or Infinity.")

    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_constant=reject_constant)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object.")
    for key in ("metadata", "inputs", "outputs"):
        if not isinstance(data.get(key), dict):
            raise ValueError(f"Input must contain a '{key}' object.")
    metadata = data["metadata"]
    known = {item.name: item for item in fields(ReportMetadata)}
    extra = set(metadata) - set(known)
    if extra:
        raise ValueError("Unknown metadata field(s): " + ", ".join(sorted(extra)))
    for name, item in known.items():
        if name not in metadata:
            if item.default is MISSING and item.default_factory is MISSING:
                raise ValueError(f"metadata.{name} is required.")
            continue
        value = metadata[name]
        if name == "project_location" and isinstance(value, dict):
            continue
        if name == "logo_path" and value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(f"metadata.{name} must be text.")
    validate_report_data(data["inputs"], data["outputs"])
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate an OsdagBridge report from saved results.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", action="store_true", help="Use synthetic demonstration data; no structural analysis is run.")
    source.add_argument("--input", type=Path, help="JSON with metadata, inputs, and outputs objects.")
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--name", default="Report_After")
    parser.add_argument("--no-pdf", action="store_true", help="Export rebuildable LaTeX and assets without a compiler.")
    parser.add_argument("--compiler", help="Path to pdflatex or Tectonic.")
    args = parser.parse_args(argv)
    try:
        validate_report_stem(args.name)
        if args.demo:
            from .demo import demonstration_data
            data = demonstration_data()
        else:
            data = load_report_data(args.input)
        metadata = ReportMetadata(**data["metadata"])
        options = ReportOptions(
            sections=["loads", "analysis", "design_checks", "drawings"],
            include_figures=True, include_toc=True, include_pdf=not args.no_pdf,
        )
        request = ReportRequest(metadata, options, str(args.output), args.name)
        payload = build_report_payload(request, data["inputs"], data["outputs"])
        result = generate_report(payload, request, compiler=args.compiler)
        if result.error:
            print(result.error)
            if result.tex_path:
                print("LaTeX source retained:", result.tex_path)
            return 1
        if args.demo:
            print("DEMONSTRATION DATA: no bridge analysis was run; not for construction.")
        print("LaTeX:", result.tex_path)
        if result.pdf_path:
            print("PDF:", result.pdf_path)
        return 0
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Report input error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
