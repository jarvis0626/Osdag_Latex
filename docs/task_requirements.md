# Screening task scope and evidence

## Current authoritative implementation scope

On **18 November 2026**, the user supplied the six requirements of the official
FOSSEE Winter Internship task, **OsdagBridge LaTeX Report Generator Refactoring
& Enhancements**, in the attached text request. Those six requirements are the
authoritative implementation specification for this follow-up.

The attachment is a text request, not the actual screening PDF. No PDF bytes
were attached or found for this review. Therefore, this project can implement
and audit the six supplied requirements, but cannot claim to have independently
read the PDF's exact wording, PDF-only instructions, additional policies or
submission rules. The user-provided scope does not establish mentor acceptance.

The [six-requirement audit](official_requirements_audit.md) maps each area to
actual functions, tests, remaining limitations and verification steps. The
[GUI verification record](gui_verification.md) separately records the attempted
application startup and the manual design-to-report checklist.

## Six requirements and implementation mapping

| Authoritative requirement, paraphrased | Current implementation | Verification and remaining limits |
| --- | --- | --- |
| Repeat table headers across page breaks using LongTable or equivalent mechanisms. | `styles.py` converts legacy tables to LaTeX `longtable`, installs first/continuation headings and preserves data rows and member labels. | `test_styles.py`, `test_pdf_integration.py` and actual compiled-report evidence; genuine GUI content still needs inspection. |
| Fix footer overlap, geometry, vertical spacing and table pagination. | Shared geometry reserves page furniture; fitted column widths account for padding/rules; table-start spacing and repeated body labels improve page breaks. | The PDF pagination regression checks row preservation and measured footer clearance. Visually inspect the real design's page transitions and long content. |
| Separate vehicle live-load and footway tables, using vehicles selected in the application UI and including parameters/units. | `chap3.ch3_loads()` renders separate tables and reads standard selection flags plus custom vehicles' `included` flags. | `test_loads.py` covers selections, false-valued saved flags, units and nonmutation. Missing braking/centrifugal or vehicle-specific outputs remain explicit N/A; compare a genuine saved UI design. |
| Add dynamic UR charts for girders, slab, cross bracing and end diaphragms in Section 5.5, including a red dashed UR = 1.0 threshold. | `charts.py` reads each component's supplied results; `chap5.py` embeds the four-category chart in its fifth section. Missing/invalid data does not become zero, and above-threshold values are distinguished. | Chart/source-separation tests and `test_official_requirements.py` check the Section 5.5 placement and real report pipeline. Supplied engineering records still require comparison with a real design. |
| Add dynamic Chapter 7 quantity charts for steel tonnage, concrete volume and reinforcement mass using temporary assets and PyLaTeX Figure. | `charts.py` and `chap7.py` share validated quantity data; girders, cross bracing and end diaphragms have steel categories, while concrete m³ and reinforcement MT use separate labeled axes. `report_generator.py` manages temporary staging and retained export assets. | `test_material_quantities.py` and contract tests cover table/chart agreement and cleanup after success/failure. End-diaphragm mass is used when supplied; the upstream BOQ does not produce it automatically. Missing values stay N/A. Reinforcement remains the disclosed upstream estimate. |
| Centralize margins, typography, colors, table spacing, headers and footers consistently across chapters. | `styles.py` supplies the shared configuration and chapter-formatting boundary; chapter modules use it and charts read its theme. | Style and source-contract tests inspect shared settings and chapter output. Review future templates against the supported table structure. |

These six areas are implemented in the existing reporting package. Implementation
and automated verification do not establish complete acceptance of genuine GUI
outputs. Read the current [validation record](validation.md) and
[`artifacts/audit/validation.json`](../artifacts/audit/validation.json) for the
checks actually executed and their source revisions; test definitions alone
are not reported as passing executions.

## Repository identity and historical source provenance

The implementation target is
[Nidhikhare12/OsdagBridge](https://github.com/Nidhikhare12/OsdagBridge), branch
`dev`, starting at `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`. The reporting code
remains in `src/osdagbridge/core/reports`, with the existing GUI/backend entry
points. This is not a replacement engineering solver.

For historical context, the earlier audit independently retrieved the
[detailed report task document](https://docs.google.com/document/d/1CkrRTk1bH3JnEhLIM8RMJodouv-yUlIx/edit)
through the [official Autumn programme](https://fossee.in/semester-internship/autumn/2026)
and its [Osdag programme document](https://docs.google.com/document/d/158MxhFBwD7iGAcIjvDPUx-urcD23FEoz0ozpvrVdL5s/edit).
The [official Winter page](https://fossee.in/winter-internship/2026) listed the
task, but its nested document link could not be fetched. That earlier link
provenance remains historical evidence; the current six-requirement scope is
now supplied directly by the user. Exact PDF contents beyond that supplied
scope have not been independently inspected.

## Deliverables and approval boundaries

The existing detailed task document asks for a repository, reviewer access,
`Report_Before.pdf`, `Report_After.pdf` and a technical explanation. The current
request also requires preserving the baseline, updating the enhanced report,
recording changes and checking genuine GUI integration wherever possible.

The requested private repository is an independent copy retaining upstream
history, not a private fork of the public repository. The tracked before/after
examples are explicitly synthetic; they do not establish that the same genuine
bridge was designed and exported through both GUI revisions.

The GUI launch attempted on 18 November failed before opening a window because
`PySide6` is missing. OCC/OpenSeesPy are also absent from the reporting runtime.
See the [exact environment checks and manual steps](gui_verification.md).

The user's current instruction explicitly prohibits collaborator invitations
and programme submission without approval. No invitation or submission has been
performed. Reviewer access, any required repository/fork arrangement and final
application materials remain pending. Do not infer approval from this task.

No PDF-only policy, AI-use rule, submission format or evaluation rubric is
invented here. Such details must be read from the actual screening document
when available; they do not invalidate the six functional requirements already
provided as the implementation scope.
