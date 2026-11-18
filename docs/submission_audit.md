# Internship readiness audit

The user supplied the official task's six functional requirements on
**18 November 2026**. They are accepted as the authoritative implementation
scope. The supplied attachment contains text instructions; the actual PDF bytes
were not attached or found, so no claim is made that PDF-only wording or rules
have been independently read. See [authority and historical provenance](task_requirements.md).

The [six-requirement audit](official_requirements_audit.md) contains detailed
source/function mappings and verification steps. The table below separates code
implementation from genuine GUI acceptance and final submission readiness.

| Requirement or deliverable | Status | Evidence and remaining work |
| --- | --- | --- |
| Repeating table headers | Implemented; automated verification available | `styles.py`, `test_styles.py`, and the real multipage PDF regression check row/header preservation. Inspect real GUI output as well. |
| Footer overlap, spacing and pagination | Implemented; genuine-design visual acceptance pending | Reserved page furniture, fitted columns and repeated member labels are covered by style/pagination checks. Review all page transitions with actual GUI content. |
| Separate vehicle/footway tables and selected vehicles | Implemented; genuine UI comparison pending | `chap3.py` reads standard flags and custom `included` selections; `test_loads.py` covers both. Missing force/per-vehicle outputs remain N/A rather than invented results. |
| Four UR component categories in Section 5.5 | Implemented; backend-result comparison pending | `charts.py`, `data.py`, `chap5.py`, source-separation tests and `test_official_requirements.py` cover categories, threshold behavior and section placement. This does not independently certify supplied engineering values. |
| Dynamic Chapter 7 material charts and safe asset lifecycle | Implemented; source-data limitation remains | Steel categories include girders, cross bracing and end diaphragms; concrete/rebar use separate labeled units. Material/contract tests cover table/chart consistency and temporary cleanup. Upstream end-diaphragm mass production is absent; a supplied valid mass is displayed, otherwise N/A. |
| Central style module used by chapters | Implemented; automated verification available | `styles.py` controls geometry, colors, typography, table spacing and page furniture; chapter decorators and chart theme share it. |
| Correct existing source/report package | Verified in source/history | Original `Nidhikhare12/OsdagBridge` history from `dev` revision `d74f56d` remains; changes are inside its report package. The engineering calculators are not replaced. |
| Complete GUI Design → Generate Report comparison | Blocked by current environment; not verified | The actual desktop entry command returned exit code 1 because `PySide6` is missing; OCC/OpenSeesPy are also unavailable. No window or real bridge design ran. Follow [GUI reproduction and manual checklist](gui_verification.md). |
| Required repository/fork arrangement | Pending clarification/acceptance | The user requested a private repository. The current repository is an independent private copy preserving history, not a private fork of the public upstream. |
| Reviewer collaborator access | Pending explicit user approval | Access has not been granted. The user explicitly prohibits adding collaborators without approval. |
| `Report_Before.pdf` and `Report_After.pdf` | Rendering deliverables available; genuine comparison pending | Preserve the tracked synthetic baseline and disclose its original compiler errors. Updated synthetic enhanced output verifies report behavior, not the required same genuine GUI design. |
| Technical changes explanation | Prepared | `technical_changes.md`, `project_walkthrough.md`, `engineering_data_audit.md` and the two requirement audits explain source changes, style architecture, rationale and limits. |
| Six supplied functional requirements | Authoritative scope available | They are no longer treated as unknown merely because earlier independent Winter/Autumn link equivalence was unverified. |
| Additional PDF-only policies and final submission format | Not independently verifiable | No actual screening PDF bytes were available in this review. Do not infer additional rules or assume a complete PDF read from the text attachment. |
| Programme submission | Pending explicit user approval and acceptance checks | No application or submission has been sent. Code/report preparation does not authorize submission. |

"Implemented" means the required code path exists with the stated behavior and
test coverage. It does not mean all six requirements have received genuine GUI
or mentor acceptance. The [current validation record](validation.md) and
[`artifacts/audit/validation.json`](../artifacts/audit/validation.json) identify
executed results and source revisions. New test definitions are not, by
themselves, evidence of passing execution.

## Evidence that must remain distinct

An enhanced synthetic PDF verifies report rendering, not a real application
design. Ordinary local PDF inspection checks parsing/document structure, not
bridge calculations. Successful compilation and report tests do not validate
every IRC/IS routine. Reinforcement mass is the disclosed upstream estimate,
not a detailed reinforcement schedule. Missing braking/centrifugal results or
end-diaphragm mass are unavailable data, not zero values or passing checks.

The earlier [Winter programme page](https://fossee.in/winter-internship/2026)
and [Autumn-linked detailed task](https://docs.google.com/document/d/1CkrRTk1bH3JnEhLIM8RMJodouv-yUlIx/edit)
remain historical source links. The current supplied six-requirement authority
and the still-unread PDF-only details are documented separately.

## Remaining submission gates

1. Read any additional instructions/policies from the actual screening PDF
   when available; retain the six user-provided functional requirements as the
   current implementation scope.
2. Prepare the upstream native environment and run the same genuine saved
   bridge through the baseline and enhanced GUI workflows, with actual drawing
   capture. Record software failures separately from engineering FAIL/WARN.
3. Compare PDF values with backend records, selected UI vehicles and quantities;
   inspect all page transitions and verify applicable standard editions and
   project assumptions. Resolve or explicitly explain unavailable data.
4. Confirm the programme's repository/access and submission format, then obtain
   the user's explicit approval before inviting collaborators or submitting.

The reporting product is implemented and testable. The complete screening
submission remains pending until genuine application acceptance and these
submission gates are satisfied.
