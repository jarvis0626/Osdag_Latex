from .styles import styled_chapter

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

from osdagbridge.core.reports.report_utils import _fig_or_placeholder, _render_value, _tex, get_girder_entries
from osdagbridge.core.utils.common import (
    KEY_CARRIAGEWAY_WIDTH,
    KEY_SD_SECTION_DESIGNATION,
    KEY_SPAN,
    KEY_STRUCTURE_TYPE,
    KEY_TS_DECK_THICKNESS,
    KEY_TS_GIRDER_SPACING,
    KEY_TS_NO_OF_GIRDERS
)


def _max_float(values):
    """Return the largest value coercible to float, or None if there are none."""
    out = None
    for v in values:
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if out is None or f > out:
            out = f
    return out


def _max_member_efficiency(pair_designs):
    """Maximum Osdag 'efficiency' (utilization ratio) over a cross-bracing or
    end-diaphragm result dump (nested pair -> member -> force_type -> raw).
    Reads already-computed results only; nothing is recalculated here."""
    from .report_utils import extract_result_summary as _extract_osdag_summary
    if not isinstance(pair_designs, dict):
        return None
    best = None
    for members in pair_designs.values():
        if not isinstance(members, dict):
            continue
        for force_types in members.values():
            if not isinstance(force_types, dict):
                continue
            for raw in force_types.values():
                try:
                    val = _extract_osdag_summary(raw or {}).get("efficiency")
                    if val is None:
                        continue
                    f = float(val)
                except (TypeError, ValueError, AttributeError):
                    continue
                if best is None or f > best:
                    best = f
    return best


@styled_chapter
def executive_summary(input_dict, output_dict, fig_paths) -> str:
    plan_fig = _fig_or_placeholder(fig_paths.get('girder_top'), 'Figure 1 -- Overall Bridge Plan')
    cs_fig = _fig_or_placeholder(fig_paths.get('cross_section'),
                                  'Figure 2 -- Typical Cross-Section (with girder, deck, barriers, footpath)')
    geom_fig = _fig_or_placeholder(fig_paths.get('final_geometry'),
                                    'Figure 3 -- 3D View of Bridge Superstructure')

    # All girders share the same section, governing check, and UR.
    # The section designation is produced by the designer pipeline, so it lives
    # in output_dict (not input_dict).
    sec = _render_value(output_dict, KEY_SD_SECTION_DESIGNATION)

    # ── Pull the stored result dicts once, then work off these locals ─────────
    # (no value is recomputed here — the pipeline already filled these in).
    design_results = output_dict.get("design_results", {}) or {}
    per_girder     = design_results.get("per_girder", {}) or {}
    deck_results   = output_dict.get("deck_design_results", {}) or {}
    cb_results     = output_dict.get("crossbracing_design_results", {}) or {}
    ed_results     = output_dict.get("end_diaphragm_design_results", {}) or {}

    # Reuse the same finite, capacity-validated ratios shown in Section 5.5.
    # Missing results must not become a fabricated passing design outcome.
    from .charts import utilization_series, conflicting_check_ratio
    from .data import supplied_girder_checks
    backend_records = list(supplied_girder_checks(output_dict))
    backend_failures = [record for record in backend_records if str(record[2].get("status", "")).upper() == "FAIL"]
    backend_warnings = [record for record in backend_records if str(record[2].get("status", "")).upper() == "WARN"]
    conflicts = [record for record in backend_records if conflicting_check_ratio(record[2])]
    component_series = utilization_series(input_dict, output_dict)
    component_urs = []
    outcomes = []
    incomplete = False
    for label, values in component_series.items():
        valid = [value for value in values.values() if value is not None]
        incomplete = incomplete or not valid or any(value is None for value in values.values())
        if valid:
            maximum = max(valid)
            component_urs.append((maximum, label))
            status = 'Exceeds UR limit' if maximum > 1 else 'Within UR limit (reported checks)'
            outcomes.append(_tex(f'{label}: {status}; maximum UR {maximum:.2f}'))
        else:
            outcomes.append(_tex(f'{label}: No valid demand/capacity results'))
    if conflicts:
        overall_design_status = 'Inconsistent supplied ratios - review backend results'
    elif any(value > 1 for value, _ in component_urs):
        overall_design_status = 'Exceeds UR limit'
    elif backend_failures:
        overall_design_status = 'Backend reports FAIL - review the supplied checks'
    elif incomplete:
        overall_design_status = 'Incomplete results - review unavailable checks'
    else:
        overall_design_status = 'Within UR limit (reported checks only)'
    if backend_warnings:
        outcomes.append(_tex('Backend WARN statuses are present; review the detailed checks.'))
    if backend_failures:
        outcomes.append(_tex('Backend FAIL statuses are present; a numeric chart limit does not override them.'))
    if component_urs:
        max_ur, max_label = max(component_urs, key=lambda item: item[0])
        overall_utilization_ratio = f'{max_ur:.2f} ({max_label})'
        gov_name = max_label
    else:
        overall_utilization_ratio = 'N/A'
        gov_name = 'N/A'
    outcomes_tex = (r'\\' + '\n').join(outcomes)

    gov = _tex(gov_name) if gov_name not in (None, '', 'None') else ''
    ur = _tex(overall_utilization_ratio) if overall_utilization_ratio else ''

    # A row per member remains readable for wide bridges and never copies a
    # global controlling-girder utilization into every member column.
    from .data import check_ratio
    labels = [(str(label), str(member_id)) for label, member_id in get_girder_entries(input_dict) if label]
    known = {label for label, _ in labels}
    labels.extend((str(label), 'N/A') for label in per_girder if str(label) not in known and not str(label).startswith('EB'))
    rows = []
    girder_series = component_series.get('Steel plate girders', {})
    for label, member_id in labels:
        records = [record[2] for record in backend_records if record[0] == label]
        valid = [record for record in records if check_ratio(record) is not None]
        controlling = max(valid, key=check_ratio) if valid else {}
        flags = {str(record.get('status') or '').upper() for record in records}
        status = next((flag for flag in ('FAIL', 'WARN', 'PASS', 'INFO') if flag in flags), 'N/A')
        ratio = girder_series.get(label)
        if ratio is None and status in {'PASS', 'WARN'}:
            status = 'N/A'
        rows.append(' & '.join((_tex(label), _tex(member_id or 'N/A'),
                               _tex(controlling.get('name') or 'N/A'),
                               f'{ratio:.2f}' if ratio is not None else 'N/A', _tex(status))) + r' \\ \hline')
    if not rows:
        rows = [r'\multicolumn{5}{|c|}{N/A --- no named girder checks supplied} \\ \hline']
    table1 = (r'\begin{longtable}{|L{1.5cm}|L{2.8cm}|L{6cm}|C{1.6cm}|C{2cm}|}' + '\n'
              + r'\caption{Reported Girder Summary}\hline' + '\n'
              + r'\textbf{Member} & \textbf{Member ID} & \textbf{Governing reported check} & \textbf{UR} & \textbf{Backend status} \\ \hline'
              + '\n' + '\n'.join(rows) + '\n' + r'\end{longtable}')
    table1 += '\n' + r'\textit{Controlling-girder section designation (legacy reference): ' + (sec or 'N/A') + r'.}'

    return r"""
\newpage
{\ReportExecutiveTitle Executive Summary\par}
\addcontentsline{toc}{chapter}{Executive Summary}
\ReportTableGap

This section provides a concise summary of the bridge design, key inputs, governing loads, and final design outcomes.

\section*{Project Overview}
\addcontentsline{toc}{section}{Project Overview}
\label{sec:project-overview}


\begin{tabular}{|L{5.5cm}|L{8.5cm}|}
\hline
\textbf{Bridge Type} & """ + (_render_value(input_dict, KEY_STRUCTURE_TYPE)) + r""" \\
\hline
\textbf{Design Standard} & IRC 5, IRC 6, IRC 22, IRC 24, IS 800 \\
\hline
\textbf{Span} & """ + (_render_value(input_dict, KEY_SPAN, ' m')) + r""" \\
\hline
\textbf{Carriageway Width} & """ + (_render_value(input_dict, KEY_CARRIAGEWAY_WIDTH, ' m')) + r""" \\
\hline
\textbf{No. of Girders} & """ + (_render_value(input_dict, KEY_TS_NO_OF_GIRDERS)) + r""" \\
\hline
\textbf{Girder Spacing} & """ + (_render_value(input_dict, KEY_TS_GIRDER_SPACING)) + r""" \\
\hline
\textbf{Deck Thickness} & """ + (_render_value(input_dict, KEY_TS_DECK_THICKNESS)) + r""" \\
\hline
\textbf{Overall Design Status} & """ + (_tex(overall_design_status)) + r""" \\
\hline
\textbf{Governing Check} & """ + gov + r""" \\
\hline
\textbf{Overall Utilization Ratio (max)} & """ + ur + r""" \\
\hline
\end{tabular}


""" + plan_fig + r"""

\ReportTableGap

""" + cs_fig + '\n\n' + geom_fig + '\n\n' + table1 + r"""

\ReportTableGap
\noindent\textit{Note: Utilization ratio (UR) = demand / capacity. The chart reference limit is $1.0$. Missing results remain unavailable; review each engine check and status.}

\ReportTableGap

\section*{Key Design Outcomes Summary}
\addcontentsline{toc}{section}{Key Design Outcomes Summary}
\label{sec:key-outcomes}

\noindent """ + outcomes_tex + r"""

\section*{Design Assumptions and Limitations}
\addcontentsline{toc}{section}{Design Assumptions and Limitations}
\label{sec:assumptions}

\begin{itemize}
\item Additional inputs not provided by the user were assumed by software per IRC/IS code defaults or practical consideration.
\item This document renders supplied results. Generating a report does not run or validate a structural analysis.
\item Substructure and foundation design are not included in this report.
\item Splice connections and bearings are not designed in this version.
\end{itemize}

% Restore numbered chapter format
\ReportChapterFormat
"""
