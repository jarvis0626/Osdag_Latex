"""Render the same synthetic fixture with upstream and enhanced report code.

The baseline intentionally retains upstream TeX errors, using Tectonic's
continue-on-errors mode to match the original nonstop compilation behavior.
It is evidence of rendering changes, not an executed bridge analysis.
"""

import argparse
import ast
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "d74f56dd7f22925fb8148cabf5740ed8d1e39ff3"


def baseline_worker(checkout, data_path, destination, compiler):
    sys.path.insert(0, str(Path(checkout) / "src"))
    # Extract only the upstream's pure alias mapper. Importing its containing
    # module otherwise starts a solver dependency unrelated to rendering.
    helper_path = Path(checkout) / "src/osdagbridge/core/bridge_types/plate_girder/results_data.py"
    tree = ast.parse(helper_path.read_text(encoding="utf-8"))
    helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_extract_osdag_summary")
    module_name = "osdagbridge.core.bridge_types.plate_girder.results_data"
    module = types.ModuleType(module_name)
    exec(compile(ast.Module(body=[helper], type_ignores=[]), str(helper_path), "exec"), module.__dict__)
    sys.modules[module_name] = module
    from osdagbridge.core.reports import report_generator as generator
    data = json.loads(Path(data_path).read_text(encoding="utf-8"))
    metadata = generator.ReportMetadata(**data["metadata"])
    options = generator.ReportOptions(["loads", "analysis", "design_checks", "drawings"], True, True, True)
    request = generator.ReportRequest(metadata, options, str(destination), "Report_Before")
    payload = generator.build_report_payload(request, data["inputs"], data["outputs"])
    original_run = subprocess.run
    diagnostics = []

    def compile_original(command, **kwargs):
        directory = Path(kwargs["cwd"])
        result = original_run(
            [compiler, "--untrusted", "--keep-logs", "--keep-intermediates", "-Z", "continue-on-errors", command[-1]],
            cwd=directory, capture_output=True, timeout=300, check=False,
        )
        diagnostics.append((result.stdout + result.stderr).decode("utf-8", errors="replace"))
        for name in ("assets", "images"):
            if (directory / name).is_dir():
                shutil.copytree(directory / name, destination / name, dirs_exist_ok=True)
        return result

    generator.subprocess.run = compile_original
    result = generator.generate_report(payload, request)
    (destination / "Report_Before.compile.log").write_text("\n".join(diagnostics), encoding="utf-8")
    if not result.pdf_path or not Path(result.pdf_path).read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("The unmodified renderer did not produce a baseline PDF; inspect Report_Before.compile.log.")
    print("Baseline PDF rendered from unmodified upstream templates; its compiler errors are retained in the log.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "demo")
    parser.add_argument("--compiler", required=True, help="Tectonic executable for this comparison harness.")
    parser.add_argument("--baseline-root", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--data", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    compiler = shutil.which(args.compiler)
    if not compiler:
        parser.error("Tectonic executable was not found.")
    compiler = str(Path(compiler).resolve())
    destination = args.output.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if args.baseline_root:
        baseline_worker(args.baseline_root, args.data, destination, compiler)
        return
    sys.path.insert(0, str(ROOT / "src"))
    from osdagbridge.core.reports.demo import demonstration_data
    data_path = destination / "demo_input.json"
    data_path.write_text(json.dumps(demonstration_data(), indent=2), encoding="utf-8")
    archive = subprocess.run(["git", "archive", "--format=tar", BASELINE], cwd=ROOT, capture_output=True, check=True).stdout
    with tempfile.TemporaryDirectory(prefix="osdagbridge-baseline-") as staging:
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            bundle.extractall(staging, filter="data")
        subprocess.run([sys.executable, str(Path(__file__).resolve()), "--baseline-root", staging,
                        "--data", str(data_path), "--output", str(destination), "--compiler", compiler], check=True)
    subprocess.run([sys.executable, str(ROOT / "run_report.py"), "--input", str(data_path),
                    "--output", str(destination), "--name", "Report_After", "--compiler", compiler], check=True)
    print("Comparison artifacts:", destination)


if __name__ == "__main__":
    main()
