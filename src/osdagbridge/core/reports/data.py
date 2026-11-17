"""Read supplied check records consistently; never run a design calculation."""

from .charts import conflicting_check_ratio, nonnegative_number, reported_check_ratio
from .report_utils import _tex
from osdagbridge.core.utils import common as keys


def check_ratio(check):
    """Keep the engine's unrounded ratio after validating its displayed operands."""
    return reported_check_ratio(check)


def supplied_girder_checks(outputs):
    """Yield (member, load-case/source, check) from the actual backend schema.

    Envelope checks retain their backend values. Load-case checks are included
    separately, with their actual source label, rather than borrowing a global
    controlling-girder result for every member.
    """
    per_girder = (outputs.get("design_results") or {}).get("per_girder") or {}
    for member, values in per_girder.items():
        if str(member).startswith("EB"):
            continue
        for check in values.get("checks") or []:
            yield str(member), "Envelope", check
        for load_case, result in (values.get("per_lc") or {}).items():
            for check in result.get("checks") or []:
                yield str(member), str(load_case), check


def backend_girder_table(outputs):
    """Render supplied member/check values and statuses without reclassification."""
    rows = []
    conflicts = []

    def value(number, unit):
        parsed = nonnegative_number(number)
        return _tex(f"{parsed:.2f}" + (" " + str(unit) if unit else "")) if parsed is not None else "N/A"

    for member, origin, check in supplied_girder_checks(outputs):
        if conflicting_check_ratio(check):
            conflicts.append(_tex(member + " / " + str(check.get("name") or "Unnamed check")))
        ratio = check_ratio(check)
        status = str(check.get("status") or "N/A").upper()
        if status not in {"PASS", "WARN", "FAIL", "INFO"}:
            status = "N/A"
        # Invalid operands cannot substantiate a passing numerical check.
        if ratio is None and status in {"PASS", "WARN"}:
            status = "N/A"
        check_id = check.get("check_id", check.get("id"))
        label = check.get("name") or (f"Check {check_id}" if check_id is not None else "Unnamed check")
        rows.append(" & ".join((
            _tex(member), _tex(label),
            value(check.get("demand"), check.get("demand_unit")),
            value(check.get("capacity"), check.get("capacity_unit")),
            f"{ratio:.4f}" if ratio is not None else "N/A", _tex(status),
            _tex(origin), _tex(check.get("clause") or "N/A"),
        )) + r" \\ \hline")
    has_records = bool(rows)
    if not rows:
        rows.append(r"\multicolumn{8}{|c|}{N/A --- no structured girder checks supplied} \\ \hline")
    notes = (r"\par\textbf{Inconsistent supplied ratios: }" + "; ".join(conflicts)
             + r". The supplied DCR conflicts with its demand/capacity beyond rounding tolerance. Review the backend export; the report has not repaired the engineering values." if conflicts else "")
    return _structured_table_with_notes(rows, notes) + ("" if has_records else legacy_reference_table(outputs))


def _structured_table_with_notes(rows, notes):
    # Keep one formatter for both complete and incomplete structured snapshots.
    return (r"\section{Plate Girder Design}\label{sec:plate-girder}" + "\n"
            r"These are supplied backend checks, with each member and load case kept separate. "
            r"Backend acceptance bands and statuses remain authoritative."
            + "\n" + r"\begin{longtable}{|L{1.6cm}|L{3.5cm}|L{1.8cm}|L{1.8cm}|C{1.4cm}|C{2.0cm}|L{2.8cm}|L{2.2cm}|}"
            + "\n" + r"\caption{Supplied Girder Design Checks}\hline"
            + "\n" + r"\textbf{Member} & \textbf{Check} & \textbf{Demand} & \textbf{Capacity} & \textbf{UR} & \textbf{Backend status} & \textbf{Source / load case} & \textbf{Reference} \\ \hline"
            + "\n" + "\n".join(rows) + "\n" + r"\end{longtable}"
            + "\n" + r"\textit{N/A marks unavailable data. A supplied FAIL is retained even when capacity is invalid.}" + notes + "\n")


def legacy_reference_table(outputs):
    fields = (("Applied moment", keys.KEY_SD_MU_APPLIED, "kNm"),
              ("Moment capacity", keys.KEY_SD_MD_CAPACITY, "kNm"),
              ("Applied shear", keys.KEY_SD_SHEAR_VU, "kN"),
              ("Shear resistance", keys.KEY_SD_SHEAR_VCR, "kN"),
              ("Flexure utilization", keys.KEY_UTIL_FLEXURE, "percent"),
              ("Shear utilization", keys.KEY_UTIL_SHEAR, "percent"),
              ("Interaction utilization", keys.KEY_UTIL_INTERACTION, "percent"),
              ("LTB utilization", keys.KEY_UTIL_LTB, "percent"))
    available = [(label, outputs.get(key), unit) for label, key, unit in fields if outputs.get(key) is not None]
    if not available:
        return ""
    rows = [" & ".join((_tex(label), _tex(value), _tex(unit))) + r" \\ \hline"
            for label, value, unit in available]
    return (r"\par\textbf{Unattributed legacy reference values.} "
            r"These flat fields are supplied by the older controlling-girder interface. "
            r"No per-member check or passing status can be established from them alone."
            + r"\begin{longtable}{|L{6cm}|L{5cm}|L{3cm}|}\caption{Legacy Reference Values}\hline"
            + r"\textbf{Parameter} & \textbf{Supplied value} & \textbf{Unit} \\ \hline"
            + "\n" + "\n".join(rows) + r"\end{longtable}")
