# Validation evidence and limits

The follow-up audit ran on 17 November 2026 with Windows and Python 3.12 in the isolated reporting environment.

## Executed checks

The final local suite records **321 passing tests, zero failures and zero skips**, with both real Tectonic pagination and the exported-package check enabled. The source revision, aggregate results and artifact hashes are recorded in `artifacts/audit/validation.json`.

The varied report matrix compiles **33 distinct synthetic report scenarios** into actual PDFs. It covers missing geometry, one/twelve girders, optional chapters, vehicle selections, custom text, Unicode and Greek/Celsius symbols, long metadata, partial and nonfinite results, unity/exceeded ratios, separate transverse components, material scales, 150 load cases and supplied image bytes. The summary is in `artifacts/audit/report_matrix.json`. These are reporting fixtures, not independent bridge analyses.

Four existing nonpersonal local PDFs, covering **17 pages**, passed read-only structural inspection. One textless diagram page produced a warning rather than a false invalid-document failure. File hashes before and after inspection confirmed all originals were unchanged. Only anonymized outcomes are stored in `artifacts/audit/local_pdf_checks.json`; original content, filenames and paths are excluded.

The real pagination fixture preserves **100 unique rows over four pages**, repeats headings and member labels, and checks footer clearance using PyMuPDF coordinates. The measured minimum baseline gap is **43.56pt**, above the 18pt project regression threshold. This is a test policy, not an internship evaluation rubric.

The final Docker image was built and generated a 36-page PDF in a Linux container. The exported ZIP was extracted into an unrelated directory with spaces and without the checkout on PYTHONPATH. Running `start.py` installed a fresh local virtual environment and checksum-verified compiler, then generated a 36-page PDF successfully. All 45 bundled file hashes were verified. This uses the same computer and may reuse pip/TeX user caches; it is not a clean-machine or offline installation test. The ZIP is allowlisted and normalizes text newlines for reproducible builds. The deployment instructions distinguish a source distribution from a bundled Python installation.

The updated synthetic before/after comparison was generated from the same fixture. The enhanced document is compiled with a successful exit, parsed, and visually reviewed at the title, member-check, chart and material-summary pages. Small text-box/fontconfig warnings remain; arbitrary genuine GUI content still requires visual review. The original baseline intentionally retains upstream LaTeX errors and uses continue-on-errors mode, as disclosed in `artifacts/demo/README.md`.

## Source and engineering scope

There are no changes to the upstream designer, analyser, IRC helper implementations or BOQ calculator. Tests check report consistency and one dimensionally explicit BOQ example. They do not certify structural adequacy or every upstream numerical method. See [engineering data audit](engineering_data_audit.md).

The initial GitHub Windows/Linux checks passed before this follow-up. The revised workflow additionally runs the varied PDF matrix and distribution smoke checks; its current remote status must be read from GitHub, not inferred from local results.

## Submission limits

The complete GUI/CAD Design-to-Report workflow has not been executed with a genuine bridge model. The before/after examples remain synthetic. End-diaphragm BOQ mass and some forces are missing; reinforcement mass remains an estimate. Standard editions and template assumptions require project-specific verification. Exact Winter task linkage/policies and reviewer access are unresolved. See [requirement-by-requirement audit](submission_audit.md).
