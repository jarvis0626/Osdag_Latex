"""Headless entry point for saved result dictionaries or a labeled demo."""

import argparse
import json
from pathlib import Path

from .report_generator import (
    ReportMetadata, ReportOptions, ReportRequest, build_report_payload, generate_report,
)


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
        if args.demo:
            from .demo import demonstration_data
            data = demonstration_data()
        else:
            data = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Input must be a JSON object.")
        for key in ("metadata", "inputs", "outputs"):
            if not isinstance(data.get(key), dict):
                raise ValueError(f"Input must contain a '{key}' object.")
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
