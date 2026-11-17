# OsdagBridge LaTeX report improvements

Report generation improvements based on
[Nidhikhare12/OsdagBridge, `dev`](https://github.com/Nidhikhare12/OsdagBridge/tree/dev),
starting at `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`. Upstream history and the
[original license](LICENSE) are retained. This private development copy is not
an official Osdag release or a certified bridge design tool.

The reporting changes add repeating table headings, safer page layout, separate
vehicle/footway tables, utilization charts in Section 5.5, material charts in
Chapter 7, and shared styling. They also correct copied end-diaphragm results
and misleading passing statuses for missing data. Structural calculations are
unchanged. See the [technical explanation](docs/technical_changes.md) and
[task requirements and remaining submission work](docs/task_requirements.md).

## Run the report demo

Use **Python 3.11 or 3.12** and an internet connection for setup. From this
directory:

```powershell
python scripts/setup_reports.py --with-compiler --dev
.\.venv\Scripts\python.exe run_report.py --demo
```

On Linux/macOS, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.
Setup creates a local environment with reporting dependencies only. The optional
compiler download installs Tectonic 0.17.0 into `.tools/` after checking its
pinned SHA-256 checksum. Its first compilation downloads LaTeX resources and
may take several minutes. No GUI or CAD installation is needed for this demo.

The command writes `output/Report_After.pdf`, `.tex`, and a matching assets
directory. **The example is synthetic rendering data, includes deliberate
failed checks, and does not run bridge analysis.** Missing data stays N/A.

If you already have MiKTeX or TeX Live, omit `--with-compiler`. To choose a
compiler explicitly:

```powershell
.\.venv\Scripts\python.exe run_report.py --demo --compiler "C:\path\to\pdflatex.exe"
```

Use `--no-pdf` to export source and charts without a compiler. Compiler failures
return a nonzero status, retain source/assets and diagnostics, and never report
an older PDF as a successful new result.

## Use saved design results

```powershell
.\.venv\Scripts\python.exe run_report.py --input my_results.json --output output --name Bridge_Report
```

The JSON must contain three objects: `metadata`, `inputs`, and `outputs`. Inputs
and outputs use OsdagBridge's existing backend keys. See the labeled
[example input](artifacts/demo/demo_input.json). At minimum, metadata contains
`project_name`, `project_location`, `designer`, `client`, and `company`.
This interface consumes existing results; it does not analyze a bridge or
invent missing calculations. Treat input files as trusted project data.

The existing GUI continues using `build_report_payload()` and `generate_report()`;
the reporting refactor preserves their existing positional interfaces and adds
an optional error field to `ReportResult`.

## Verify the changes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
$env:OSDAG_TEST_LATEX = "$PWD\.tools\tectonic.exe"
.\.venv\Scripts\python.exe -m pytest tests/reports/test_pdf_integration.py -q
```

The first command runs unit/regression tests; the real compiler test is skipped
unless `OSDAG_TEST_LATEX` is set. On Linux/macOS, use
`OSDAG_TEST_LATEX="$PWD/.tools/tectonic" .venv/bin/python -m pytest tests/reports/test_pdf_integration.py -q`.
The real test checks 100 rows across page breaks, repeated headings, and footer
clearance. [Validation evidence and limitations](docs/validation.md) distinguish
what was actually run from the full GUI checks still required. CI is configured
in [.github/workflows/reports.yml](.github/workflows/reports.yml).

## Compare before and after

The [demo artifacts](artifacts/demo/README.md) include the original and enhanced
PDFs for the same synthetic fixture. Rebuild both with Tectonic:

```powershell
.\.venv\Scripts\python.exe scripts/build_comparison.py --compiler .tools/tectonic.exe
```

The baseline uses the original upstream report functions and retains their
compiler errors in a diagnostic log. These rendering examples do not replace
the task's required before/after comparison from the same full GUI design.

## Full desktop application

For actual bridge design, use the upstream Conda/CAD environment:

```powershell
conda env create -f environment.yml
conda activate osdagbridge-env
python -m osdagbridge.desktop
```

Run **Design**, then **Generate Report**, using the same saved bridge inputs
before and after the refactor. That full GUI/CAD workflow has not been validated
in this reporting-only environment. The [preserved upstream README](docs/upstream_readme.md)
and [developer guide](docs/developer_guide.md) provide the broader application
context; this README's reporting commands are the exercised quick start.
