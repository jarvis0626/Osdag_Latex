# Screening task scope and evidence

This project addresses the OsdagBridge report task associated with the FOSSEE
2026 internship. This file separates published requirements from implementation
and validation evidence; it does not claim selection or mentor approval.

## Source and programme identity

- The [official Winter 2026 page](https://fossee.in/winter-internship/2026)
  lists the LaTeX report task and a registration/submission deadline of
  **23 November 2026**. These details were available in indexed official content.
- The detailed [report task document](https://docs.google.com/document/d/1CkrRTk1bH3JnEhLIM8RMJodouv-yUlIx/edit)
  was obtained through the
  [official Autumn 2026 page](https://fossee.in/semester-internship/autumn/2026)
  and its [Osdag programme document](https://docs.google.com/document/d/158MxhFBwD7iGAcIjvDPUx-urcD23FEoz0ozpvrVdL5s/edit).
- **Unverified:** the Winter programme's nested document links could not be
  retrieved, so equivalence between its detailed instructions and the linked
  Autumn task has not been established. Confirm the Winter task PDF before
  treating this as a compliant final submission.

The detailed document identifies
[Nidhikhare12/OsdagBridge](https://github.com/Nidhikhare12/OsdagBridge), branch
`dev`, as the implementation target. The starting revision is
`d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`. This is the bridge plugin, rather
than an unrelated standalone report generator or the desktop Osdag repository.

## Published work and implementation mapping

| Published requirement, paraphrased | Implementation | Verification still required |
| --- | --- | --- |
| Repeat table headings when a table continues onto another page. | `styles.py` converts legacy tables to `longtable`, adds continuation headings, and preserves data rows. | Inspect repeated headings in a PDF generated from a full bridge design. |
| Keep tables and text clear of headers and footers. | Shared page geometry reserves header/footer space; table widths include padding and rules; table starts reserve vertical space. | Inspect long tables, multirow cells, and the original page-30 problem on the same design. |
| Present vehicle and footway loads separately, with units and vehicles matching UI selection. | Chapter 3 uses separate tables and reads selected standard/custom vehicle fields. Unavailable centrifugal data is labeled. | Confirm GUI selections and report content using saved real design inputs. |
| Add utilization graphics for girders, slab, cross bracing, and end diaphragms in Section 5.5, with a red dashed unity line. | Four independently sourced chart panels; invalid or missing demand/capacity stays N/A. | Compare chart values with real backend checks, including failed and incomplete designs. |
| Visualize steel, concrete, and reinforcement quantities in Chapter 7. | Steel mass chart plus separate concrete-volume and rebar-mass axes. End diaphragm mass remains N/A when the upstream quantity calculation provides none. | End diaphragm quantity production remains an upstream data gap; verify the available quantities against a real BOQ. |
| Centralize document and chapter presentation settings. | `styles.py` supplies the shared theme and chapter formatting boundary. Chart formatting uses the same configuration. | Verify any future chapter template follows the supported table structure. |

These are the six technical areas in the retrieved detailed document. Tests,
headless execution, source exports, and compiler diagnostics are supporting
engineering improvements, not an invented evaluation rubric.

## Deliverables and remaining submission work

The detailed task asks for a repository, access for GitHub user
`Nidhikhare12`, original and enhanced PDFs named `Report_Before.pdf` and
`Report_After.pdf`, and an explanation of the changes. It also invites relevant
presentation improvements. The original workflow calls for a full GUI design
followed by report generation and a before/after comparison.

The requested private repository is an independent repository retaining the
upstream history: GitHub does not support making a fork of a public repository
private. A collaborator invitation has **not** been sent; sharing this private
repository requires an explicit user instruction to grant access.

The current automated checks and synthetic report example are useful evidence
of report behavior. They do not replace a real GUI analysis or establish that
the two required reports were generated from the same genuine design. Follow
the current Winter programme instructions for application materials and upload
format; the Autumn programme's general submission list is not assumed to apply.

No AI-use restriction or numerical evaluation rubric was identified in the
retrieved detailed document. The inaccessible Winter-linked instructions remain
unverified; absence of a restriction in the retrieved document is not proof of
the Winter programme's policy.
