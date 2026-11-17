"""Prepare the local runtime once, then generate or inspect a report."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def runtime_python(root=ROOT):
    return root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def runtime_ready(python, *, inspect=False):
    if not python.is_file():
        return False
    modules = ["matplotlib", "pylatex"] + (["pypdf", "pymupdf"] if inspect else [])
    code = "import sys; assert (3,11) <= sys.version_info[:2] < (3,13); " + "; ".join("import " + name for name in modules)
    return subprocess.run([str(python), "-c", code], capture_output=True, check=False).returncode == 0


def available_compiler(root=ROOT):
    explicit = os.environ.get("OSDAGBRIDGE_LATEX_COMPILER")
    if explicit:
        return shutil.which(explicit)
    local = root / ".tools" / ("tectonic.exe" if os.name == "nt" else "tectonic")
    return str(local) if local.is_file() else (shutil.which("pdflatex") or shutil.which("tectonic"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--demo", action="store_true", help="Generate the demonstration report (default).")
    source.add_argument("--input", type=Path, help="Saved bridge-results JSON.")
    source.add_argument("--inspect", type=Path, help="Inspect an existing PDF locally.")
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--name", default="Report_After")
    parser.add_argument("--no-pdf", action="store_true", help="Export source without requiring a compiler.")
    parser.add_argument("--compiler", help="Existing pdflatex or Tectonic executable.")
    parser.add_argument("--open", action="store_true", help="Open the generated PDF or inspected document after success.")
    args = parser.parse_args(argv)
    for source_path in (args.input, args.inspect):
        if source_path is not None and not source_path.expanduser().is_file():
            parser.exit(2, f"Input file does not exist: {source_path}\n")
    if not (3, 11) <= sys.version_info[:2] < (3, 13):
        parser.exit(2, "Use Python 3.11 or 3.12 to run OsdagBridge reports.\n")
    python = runtime_python()
    needs_runtime = not runtime_ready(python, inspect=bool(args.inspect))
    needs_compiler = not (args.inspect or args.no_pdf or args.compiler or available_compiler())
    if needs_runtime or needs_compiler:
        print("Preparing the reporting environment. First setup needs internet access.", flush=True)
        setup = [sys.executable, str(ROOT / "scripts/setup_reports.py")]
        if args.inspect:
            setup.append("--inspect-tools")
        if needs_compiler:
            setup.append("--with-compiler")
        result = subprocess.run(setup, cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    if args.inspect:
        document = args.inspect.expanduser().resolve()
        command = [str(python), str(ROOT / "scripts/verify_report_pdf.py"), str(document)]
    else:
        output = args.output.expanduser().resolve()
        document = output / (args.name + ".pdf")
        command = [str(python), str(ROOT / "run_report.py"), "--output", str(output), "--name", args.name]
        command += ["--input", str(args.input.expanduser().resolve())] if args.input else ["--demo"]
        if args.no_pdf:
            command.append("--no-pdf")
        if args.compiler:
            command += ["--compiler", args.compiler]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode == 0 and args.open and document.is_file() and not args.no_pdf:
        if os.name == "nt":
            os.startfile(document)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(document)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", str(document)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.SubprocessError) as exc:
        print("Could not start reporting:", exc, file=sys.stderr)
        raise SystemExit(1)
