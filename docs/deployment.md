# Run and distribute the reporting tool

## Windows: double-click

Install Python 3.11 or 3.12, then double-click **Start_Report.cmd**. The first
launch creates `.venv`, installs the small reporting dependencies, downloads a
checksum-verified compiler when needed, and generates the demo. A successful PDF
opens in your normal PDF viewer. Later launches reuse the environment.

The demonstration contains synthetic results and deliberate failed checks.
Generating it does not run bridge analysis. Your existing PDF documents can be
inspected locally; they do not become structural calculation inputs.

## One command on any supported platform

```powershell
python start.py
```

Use `python3` on Linux/macOS when appropriate. Other commands:

```powershell
python start.py --input my_results.json --output output --name My_Bridge
python start.py --inspect "C:\path\to\existing.pdf"
python start.py --demo --no-pdf
```

PDF inspection keeps documents local and prints structural/text evidence.
Image-only pages are valid documents, with a warning when text extraction is
unavailable. For encrypted PDFs and advanced row checks, use
`scripts/verify_report_pdf.py --help` after installing inspection tools.

Setup and the first compiler run need internet access. After dependencies and
LaTeX resources are cached, the same reports can be generated offline. New
LaTeX packages may require an initial download. The full OsdagBridge GUI still
uses the separate upstream Conda/CAD installation described in the README.

## Distributable ZIP

From a clean, committed checkout:

```powershell
python scripts/package_reports.py
```

This writes `dist/OsdagBridge-Reports.zip`, a SHA-256 checksum file, and an
internal manifest with source revision and individual file hashes. The bundle
contains the reporting source, launchers, setup script and license. It excludes
the GUI, local PDFs, virtual environments, credentials and generated scratch
output. Extract it on another machine and run `Start_Report.cmd` or
`python start.py`. Python 3.11/3.12 and first-run internet access are required.

## Container deployment

With Docker running:

```powershell
docker build -t osdagbridge-reports .
docker run --rm --mount "type=bind,source=$PWD\output,target=/output" osdagbridge-reports
```

Create the `output` directory first. On Linux/macOS use
`source="$PWD/output"` in the mount. To consume saved inputs, mount their
directory at `/inputs`, then append
`--input /inputs/my_results.json --output /output --name My_Bridge`.

The image runs the report command directly and requires no web server, ports or
cloud account. No local documents enter its build context. It needs access to
the Tectonic bundle on first compilation, which can be cached in a persistent
Docker volume mounted at `/root/.cache`. Do not replace a real GUI analysis
with the synthetic container demo when preparing the internship submission.
