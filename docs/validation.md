# Validation evidence and limits

Verified on **17 November 2026**, Windows, Python 3.12, in a fresh `.venv`
created by `scripts/setup_reports.py --dev`. The report environment contains
Matplotlib and PyLaTeX, without the GUI, CAD tools, or OpenSeesPy. The optional
Tectonic 0.17.0 installer was executed and its archive checksum verified.

## Executed checks

```powershell
$env:OSDAG_TEST_LATEX = "$PWD\.tools\tectonic.exe"
.\.venv\Scripts\python.exe -m pytest -q
```

Result: **160 passed**, including the real compiler integration test. The
suite covers load selections, escaping, missing and invalid engineering
results, cross-bracing/diaphragm separation, source assets, payload immutability,
compiler failures/timeouts, stale PDFs, and real table pagination. Inherited
placeholder tests are included in this total; they do not validate the GUI or
structural solver.

The real PDF fixture has **100 distinct rows over four pages**, with repeated
column headings and each of five member labels repeated on its 20 rows. All
rows occur exactly once. PyMuPDF measures a minimum **43.56pt** gap between the
lowest table-row baseline and footer baseline, above the required 18pt margin
used by this regression test. This measured threshold is a project test policy,
not an invented internship rubric.

Both full synthetic reports were compiled using
`scripts/build_comparison.py`. The enhanced PDF was regenerated from the final
implementation and inspected for its expected chapters, utilization status,
and material summary. Its source contains a continuation header for every
longtable. Samples of the header, footer, long tables and charts were visually
inspected during development. The compiler exits successfully; small overfull
and underfull text-box warnings and a nonfatal local fontconfig message remain.
No undefined references or duplicate page anchors were found in its final log.

The baseline deliberately retains upstream LaTeX errors. Its comparison-only
compiler runs in continue-on-errors mode, matching the original renderer's
nonstop behavior. Its existence is not evidence of a clean upstream compile.

[The artifact manifest](../artifacts/demo/validation.json) records exact PDF
hashes, page/table counts, tool versions, and the synthetic-data limitation.
The [demo artifacts](../artifacts/demo/README.md) explain how to reproduce them.
`git diff --check` also passed. GitHub CI is configured separately; local
results should not be confused with a completed remote CI run.

## Not yet established

- The complete desktop **Design → Generate Report** flow has not been run with
  the upstream Conda/CAD environment or a genuine bridge project. Synthetic
  before/after reports do not fulfill that final comparison requirement.
- The Winter programme's nested task document could not be retrieved. The
  exact detailed task used here was linked from the official Autumn programme;
  the Winter linkage and any additional rules remain unverified.
- The backend does not currently supply end-diaphragm BOQ mass or a canonical
  centrifugal force result. Those values remain unavailable. The inherited
  braking helper errors and is reported as N/A. No engineering routine was
  changed to manufacture a result.
- Reinforcement mass is the existing 120 kg/m³ estimate, not a detailed bar
  schedule. Chart reference limits do not replace individual code-check rules.
- Linux and Python 3.11 checks are configured in CI; they were not run locally.
- The private repository has not been shared with the task's requested reviewer.
  Its collaborator access and final programme submission remain separate work.
