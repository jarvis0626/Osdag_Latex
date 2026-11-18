# Validation evidence and limits

The latest six-requirement follow-up ran on **18 November 2026**, on Windows
with Python 3.12 in the isolated reporting environment. Source, hashes and
executed counts are recorded in
[`artifacts/official_verification/validation.json`](../artifacts/official_verification/validation.json).

## Latest executed checks

The final suite passed **393 tests with zero failures and zero skips**. Both
real compiler tests and the exported-package check were enabled. The real
contract PDF confirms Section 5.5 placement and all three generated chart
assets; other checks verify four independent result sources, plot properties,
temporary cleanup, UI selection, material consistency and incomplete analysis.

The final matrix compiles **35 distinct synthetic report scenarios** into real
PDFs, adding actual custom-vehicle inclusion flags and supplied diaphragm mass
to the previous cases. The checked summary is
`artifacts/official_verification/report_matrix.json`.

`Report_Before.pdf` remains byte-for-byte unchanged, with SHA-256
`693e1dda930aa91e6f78948ec4773134111764ecef0afe62744451530fe76e82`.
Only `Report_After.pdf` was regenerated from the existing saved fixture. It has
**33 pages**, no empty-text pages, no overfull-box or missing-glyph warnings,
and passed PDF parsing/required-text checks. Underfull-text and a local
Fontconfig configuration warning remain; these do not imply compiler failure.
Input, analysis, structured-check, utilization and material pages were visually
reviewed. The minimum extracted body-text/footer baseline gap over all 33 pages
was **40.67pt**, above the 18pt regression policy. This does not prove arbitrary
image/page layouts safe; drawing geometry still needs visual review.

The real 100-row pagination regression also passed again. The original
engineering backend/IRC/BOQ source remains unchanged. The actual GUI entry
command failed before opening a window because PySide6 is unavailable; this is
a recorded environment limitation, not a passed GUI test. See
[gui_verification.md](gui_verification.md) and the
[six-requirement audit](official_requirements_audit.md).

## Previous 17 November checkpoint

That checkpoint recorded **321 passing tests, zero failures and zero skips**, with both real Tectonic pagination and the exported-package check enabled. Its source revision, aggregate results and artifact hashes are retained in `artifacts/audit/validation.json` as historical evidence.

The varied report matrix compiles **33 distinct synthetic report scenarios** into actual PDFs. It covers missing geometry, one/twelve girders, optional chapters, vehicle selections, custom text, Unicode and Greek/Celsius symbols, long metadata, partial and nonfinite results, unity/exceeded ratios, separate transverse components, material scales, 150 load cases and supplied image bytes. The summary is in `artifacts/audit/report_matrix.json`. These are reporting fixtures, not independent bridge analyses.

Four existing nonpersonal local PDFs, covering **17 pages**, passed read-only structural inspection. One textless diagram page produced a warning rather than a false invalid-document failure. File hashes before and after inspection confirmed all originals were unchanged. Only anonymized outcomes are stored in `artifacts/audit/local_pdf_checks.json`; original content, filenames and paths are excluded.

The real pagination fixture preserves **100 unique rows over four pages**, repeats headings and member labels, and checks footer clearance using PyMuPDF coordinates. The measured minimum baseline gap is **43.56pt**, above the 18pt project regression threshold. This is a test policy, not an internship evaluation rubric.

The final Docker image was built and generated a 36-page PDF in a Linux container. The exported ZIP was extracted into an unrelated directory with spaces and without the checkout on PYTHONPATH. Running `start.py` installed a fresh local virtual environment and checksum-verified compiler, then generated a 36-page PDF successfully. All 45 bundled file hashes were verified. This uses the same computer and may reuse pip/TeX user caches; it is not a clean-machine or offline installation test. The ZIP is allowlisted and normalizes text newlines for reproducible builds. The deployment instructions distinguish a source distribution from a bundled Python installation.

The updated synthetic before/after comparison was generated from the same fixture. The enhanced document is compiled with a successful exit, parsed, and visually reviewed at the title, member-check, chart and material-summary pages. Small text-box/fontconfig warnings remain; arbitrary genuine GUI content still requires visual review. The original baseline intentionally retains upstream LaTeX errors and uses continue-on-errors mode, as disclosed in `artifacts/demo/README.md`.

## Source and engineering scope

There are no changes to the upstream designer, analyser, IRC helper implementations or BOQ calculator. Tests check report consistency and one dimensionally explicit BOQ example. They do not certify structural adequacy or every upstream numerical method. See [engineering data audit](engineering_data_audit.md).

The initial GitHub Windows/Linux checks passed before this follow-up. The revised workflow additionally runs the varied PDF matrix and distribution smoke checks; its current remote status must be read from GitHub, not inferred from local results.

## Submission limits

The complete GUI/CAD Design-to-Report workflow has not been executed with a genuine bridge model. The before/after examples remain synthetic. End-diaphragm BOQ mass and some forces are missing; reinforcement mass remains an estimate. Standard editions and template assumptions require project-specific verification. The six user-supplied requirements now define implementation scope; the actual screening PDF, additional PDF-only rules and reviewer access remain outstanding. See [requirement-by-requirement audit](submission_audit.md).
