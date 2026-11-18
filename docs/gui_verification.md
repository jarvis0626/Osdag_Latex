# Real application integration and manual verification

This records the environment checks actually executed on **18 November 2026**.
It separates source integration from an end-to-end GUI test. No bridge design
was performed and no GUI-generated before/after comparison is claimed.

## Integration found in the existing application

The reporting changes are inside the original `osdagbridge/core/reports`
package. The desktop application still uses that package:

1. `desktop/ui/docks/output_dock.py`,
   `OutputDock._on_report_clicked()`, requires a completed design and captures
   available CAD/plot image bytes on the Qt main thread.
2. It passes those bytes to `desktop/ui/template_page.py`,
   `open_report_dialog()`. The report options dialog constructs the existing
   `ReportRequest` and a worker invokes the backend.
3. `core/bridge_types/plate_girder/plategirderbridge.py`,
   `PlateGirderBridge.generate_design_report()`, supplies its own input/output
   dictionaries, available analysis summaries and captured figures.
4. That method calls the same `build_report_payload()` and `generate_report()`
   functions used by the standalone reporting command. It does not call the
   synthetic demonstration-data provider.

These source connections establish that the implementation remains integrated
with the application. They do not establish that its native GUI/CAD dependencies
or a complete bridge design have run successfully in this environment.

## Executed environment checks

Both the global Python and the isolated reporting Python are version 3.12.3.
Module-availability probes found:

| Module | Global Python | Reporting `.venv` |
| --- | --- | --- |
| PySide6 | Missing | Missing |
| pythonOCC import `OCC` | Missing | Missing |
| OpenSeesPy | Missing | Missing |
| Fiona | Missing | Missing |
| xarray | Missing | Missing |
| SciPy | Available | Missing |
| PyLaTeX and Matplotlib | Available | Available |

Conda was not found on `PATH`. The usual user and ProgramData
Miniconda/Anaconda `Scripts/conda.exe` locations were also checked and absent.
This does not prove that no unrelated Conda installation exists elsewhere.

A native-stack import probe failed with `ModuleNotFoundError: No module named
'PySide6'`. The actual desktop entry point was then attempted from the checkout:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
.\.venv\Scripts\python.exe -m osdagbridge.desktop
```

It returned **exit code 1**, before creating a window, at
`desktop/__main__.py:75`:

```text
from PySide6.QtWidgets import QApplication
ModuleNotFoundError: No module named 'PySide6'
```

No native dependencies were installed for this probe. No GUI design, CAD
capture or GUI report export was executed. Successful headless report tests
cannot replace this outstanding check.

## Prepare the full application environment

The following are reproduction instructions, not commands that passed here.
Install a suitable Conda distribution first, then run these commands from the
full repository checkout in a Conda-enabled PowerShell:

```powershell
conda env create -f environment.yml
conda activate osdagbridge-env
python -m pip install -r requirements-report.txt
python scripts/setup_reports.py --with-compiler
$env:OSDAGBRIDGE_LATEX_COMPILER = (Resolve-Path '.tools\tectonic.exe').Path
$env:PYTHONPATH = (Resolve-Path src).Path
python -m osdagbridge.desktop
```

`environment.yml` is the upstream environment specification: it installs
`osdag::osdag`, bridge libraries, OpenSeesPy and the editable project. The
additional reporting requirements ensure the active application environment
also contains the reporting Python dependencies. `setup_reports.py` prepares
the separate reporting environment and downloads the verified compiler; it
does not install the GUI/CAD stack.

Before launching, the native stack can be checked without opening a window:

```powershell
python -c "from PySide6.QtWidgets import QApplication; from OCC.Core.BRep import BRep_Builder; import openseespy.opensees"
```

Resolving a Conda package or native-DLL failure is part of environment setup;
do not report a passing GUI test until the application actually runs.

## Genuine design-to-report checklist

1. Open the application and use **File > Load Input** (`Ctrl+L`) to load a
   genuine saved `.osi` bridge input. The existing `loadOSI_inputs()` reads
   YAML and validates it. The standalone reporter's JSON result snapshot is a
   different interface and does not replace this bridge input.
2. Review geometry, materials, load parameters and the actual checked vehicle
   classes. In custom vehicles, review each **included** checkbox as well.
   Save the chosen input using **File > Save Input** (`Ctrl+S`).
3. Run **Design** and wait for analysis/design processing to finish. Record
   software errors separately from a legitimate engineering FAIL/WARN result.
   Verify that the output panels contain actual results.
4. Open/render the relevant CAD and analysis plot views. Click **Generate
   Report** in the output dock. That button exercises the main-thread image
   capture path. The File menu's **Create Design Report** action opens the
   dialog directly and does not itself supply captured CAD bytes.
5. Complete the metadata, click **Next**, leave the relevant chapters and
   drawings selected, then use **Save PDF**. Save genuine comparison artifacts
   in a separate directory so the tracked synthetic baseline is preserved.
6. Check vehicle selections and units, every reported controlling member and
   load case, demands/capacities/statuses, four Section 5.5 chart categories,
   Chapter 7 quantities and their units, and available drawings against the
   application's actual results. Missing backend values must remain N/A.
7. Visually inspect all page transitions, repeated table headers, table
   widths, footer separation, symbols and chart labels. Verify applicable
   standard editions and project assumptions separately.
8. Repeat with a different saved vehicle selection and rerun **Design** before
   exporting. A changed selection must be reflected in the new report.
9. For a genuine before/after comparison, perform these steps with the same
   saved bridge inputs against upstream revision
   `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3` and the enhanced revision. Record
   both source revisions, compiler versions, output hashes and any failures.

The unchanged upstream GUI report generator requires a working bundled
`OsdagLatexEnv` pdfLaTeX or `pdflatex` on `PATH`. It does **not** implement the
enhanced `OSDAGBRIDGE_LATEX_COMPILER` override or Tectonic support. Thus a
Tectonic-only setup is sufficient for the enhanced report, but not for an
unmodified baseline GUI export. Preserve and report baseline compilation
errors instead of describing them as a successful genuine comparison.

The existing `scripts/build_comparison.py` command produces the explicitly
synthetic rendering comparison using a separately disclosed compiler route.
It is useful regression evidence but does not complete this GUI checklist.

## Separate diagnostic improvement candidate

The current desktop failure dialog displays generic compiler causes when no
PDF is returned. The reporting API now also supplies `ReportResult.error`.
A small future UI diagnostic improvement could display that actual error,
for example `Compiler not found: ...`, alongside the retained source path.
This document does not implement or claim to test that UI change.

No collaborator invitation or programme submission is part of these steps.
