# Internship readiness audit

The official [Winter 2026 page](https://fossee.in/winter-internship/2026) lists
the LaTeX task. Its nested task link could not be fetched, including a repeat
attempt during this audit. The detailed
[OsdagBridge task document](https://docs.google.com/document/d/1CkrRTk1bH3JnEhLIM8RMJodouv-yUlIx/edit)
used here was linked from the official Autumn programme. Winter equivalence,
additional submission rules and any AI-use policy are **not verifiable** from
the retrieved material. See [source details](task_requirements.md).

The following statuses concern the retrieved detailed task, not mentor approval.

| Requirement | Status | Evidence and remaining work |
| --- | --- | --- |
| Repeating table headers | Completed | `styles.py`; `test_styles.py`; actual multipage PDF regression preserves 100 rows and member labels. |
| Footer overlap and spacing | Partially completed | Reserved page furniture, fitted columns and repeated body labels are tested. Full GUI reports and unusually long real content still need visual review. |
| Separate vehicle and footway loads, units, selected vehicles | Partially completed | `chap3.py`, `test_loads.py`, vehicle matrix cases. UI flags are read correctly; missing centrifugal/braking/per-vehicle outputs remain explicit gaps. |
| Four utilization chart groups in Section 5.5 | Completed | `charts.py`, `data.py`, `chap5.py`, source-separation and consistency tests; actual PDF compilation. Full-backend numerical validation remains separate. |
| Material charts in Chapter 7 | Partially completed | Steel and deck/rebar charts work with unit separation. End-diaphragm quantity production is missing upstream, and is displayed as N/A. |
| Single style configuration consumed by chapters | Completed | `styles.py` controls geometry, colors, type, padding and table processing; plotting uses the same theme. |
| Correct specified upstream source | Completed | Original `Nidhikhare12/OsdagBridge` history is retained from `dev` revision `d74f56d`. |
| Public fork workflow from the detailed instructions | Partially completed | The user requested a private repository, so this is an independent private copy retaining history. It is not represented as a private fork of a public repository. |
| GitHub reviewer collaborator | Missing | Access has not been granted to `Nidhikhare12`. The repository remains private. |
| Report_Before.pdf and Report_After.pdf | Partially completed | Both demonstration PDFs exist and are reproducible. They use synthetic inputs, not the required same genuine GUI design. The original renderer's baseline LaTeX errors are disclosed. |
| Technical changes explanation | Completed | `technical_changes.md`, `project_walkthrough.md`, `engineering_data_audit.md` and test evidence. |
| Complete GUI Design → Generate Report comparison | Not verifiable | No full Conda/CAD/GUI run with a real bridge project has been performed here. |
| Exact Winter rules and final submission format | Not verifiable | Obtain the Winter-linked detailed document/PDF and confirm its requirements. Do not assume the Autumn programme's whole submission format applies. |

## What would weaken a submission if left unexplained

An attractive synthetic PDF is not proof of real application compatibility.
Ordinary local PDF inspection checks parsing and document structure, not bridge
design. A passed test suite does not validate every IRC/IS calculation. A
quantity estimate is not a detailed take-off, and N/A is not a passing check.
The implementation and accompanying explanation must state those distinctions.

## Submission gates

1. Confirm the exact Winter task and its policies.
2. Run a genuine saved bridge through the upstream GUI before and after the
   report changes, with the same inputs and actual drawings.
3. Check PDF values against backend records and review page transitions and
   standard/reference editions. Resolve or explain missing quantity/force data.
4. Complete reviewer access and the programme's actual submission materials.

The report product is working and testable. The official screening submission
should remain marked incomplete until those gates are satisfied.
