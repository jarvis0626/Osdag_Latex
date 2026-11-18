from .styles import styled_chapter

import math
from typing import TYPE_CHECKING
from osdagbridge.core.utils.common import (
    KEY_SPAN,
    KEY_TS_NO_OF_GIRDERS,
    KEY_SD_DEFL_LIVE,
    KEY_SD_DEFL_TOTAL,
)
from osdagbridge.core.reports.report_utils import _tex, _fig_embed

if TYPE_CHECKING:
    from .report_generator import ReportDataBridge

@styled_chapter
def ch4_analysis(asum, fig_paths, bridge: "ReportDataBridge", span_m: float):
    lc_summary  = (asum or {}).get('load_cases') or {}
    rxn_summary = (asum or {}).get('reactions') or {}

    def _is_moving(lc_name: str) -> bool:
        n = lc_name.lower()
        return "moving" in n or " pos_" in n

    lc_summary  = {k: v for k, v in lc_summary.items()  if not _is_moving(k)}
    rxn_summary = {k: v for k, v in rxn_summary.items() if not _is_moving(k)}

    def _finite(val):
        if isinstance(val, bool):
            return None
        try:
            number = float(val)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if math.isfinite(number) else None

    def _fmt(val, nd=3):
        number = _finite(val)
        return f"{number:.{nd}f}" if number is not None else "N/A"

    def _merged_row(lc, bm_d, rxn_d):
        bm_d  = bm_d  or {}
        rxn_d = rxn_d or {}
        return (
            _tex(lc)                              + r" & "
            + _fmt(bm_d.get('max_bm'))           + r" & "
            + _tex(bm_d.get('bm_girder', '---')) + r" & "
            + _fmt(bm_d.get('bm_location'))      + r" & "
            + _fmt(bm_d.get('max_sf'))           + r" & "
            + _tex(bm_d.get('sf_girder', '---')) + r" & "
            + _fmt(bm_d.get('sf_location'))      + r" & "
            + _fmt(rxn_d.get('left_kN'))         + r" & "
            + _fmt(rxn_d.get('right_kN'))        + r" \\[6pt]"
        )

    all_lcs = list(lc_summary.keys()) + [k for k in rxn_summary if k not in lc_summary]

    merged_body = ("\n\\hline\n").join(
        _merged_row(lc, lc_summary.get(lc), rxn_summary.get(lc))
        for lc in all_lcs
    ) if all_lcs else r"--- & --- & --- & --- & --- & --- & --- & --- & --- \\[6pt]"

    reaction_body = "\n\\hline\n".join(
        _tex(lc) + " & " + _fmt((values or {}).get('left_kN')) + " & "
        + _fmt((values or {}).get('right_kN')) + r" \\[6pt]"
        for lc, values in rxn_summary.items()
    ) if rxn_summary else r"N/A & N/A & N/A \\[6pt]"

    _span_m = _finite(bridge.input_dict.get(KEY_SPAN))
    _valid_span = _span_m is not None and _span_m > 0
    _allow_live_mm = _finite(_span_m * 1000.0 / 800.0) if _valid_span else None
    _allow_total_mm = _finite(_span_m * 1000.0 / 600.0) if _valid_span else None

    # Find governing girder — worst (max) deflection across all girders
    count = _finite(bridge.input_dict.get(KEY_TS_NO_OF_GIRDERS))
    n = int(count) if count is not None and count.is_integer() and count >= 0 else 0

    _live_mm  = None
    _total_mm = None
    _live_complete = _total_complete = n > 0
    for _gi in range(1, n + 1):
        _l = _finite(bridge.output_dict.get(f"{KEY_SD_DEFL_LIVE}.G{_gi}"))
        _t = _finite(bridge.output_dict.get(f"{KEY_SD_DEFL_TOTAL}.G{_gi}"))
        # The backend exports maximum absolute deflection magnitudes in mm.
        # Missing or invalid member coverage cannot establish an overall pass.
        if _l is not None and _l >= 0:
            _live_mm = max(_live_mm, _l) if _live_mm is not None else _l
        else:
            _live_complete = False
        if _t is not None and _t >= 0:
            _total_mm = max(_total_mm, _t) if _total_mm is not None else _t
        else:
            _total_complete = False

    def _status(value, limit, complete):
        if value is not None and limit is not None:
            if value > limit:
                return r"\textcolor{reportFail}{FAIL}"
            if complete:
                return "PASS"
        return "N/A"

    _live_str = f"{_live_mm:.3f} mm" if _live_mm is not None else "N/A"
    _total_str = f"{_total_mm:.3f} mm" if _total_mm is not None else "N/A"
    _allow_live_str = f"L/800 = {_allow_live_mm:.1f} mm" if _allow_live_mm is not None else "N/A"
    _allow_total_str = f"L/600 = {_allow_total_mm:.1f} mm" if _allow_total_mm is not None else "N/A"
    _live_status = _status(_live_mm, _allow_live_mm, _live_complete)
    _total_status = _status(_total_mm, _allow_total_mm, _total_complete)
    return r"""
\chapter{Analysis Results}

The OsdagBridge analysis backend uses a grillage model: longitudinal members represent the composite steel girders with effective slab, and transverse members represent the slab or cross frames. This section presents the supplied analysis results; generating this document does not run a new analysis.

\ReportTableGap
\begingroup


\begin{longtable}{|
>{\centering\arraybackslash}p{3.1cm}|
>{\centering\arraybackslash}p{1.7cm}|
>{\centering\arraybackslash}p{1.35cm}|
>{\centering\arraybackslash}p{1.3cm}|
>{\centering\arraybackslash}p{1.7cm}|
>{\centering\arraybackslash}p{1.35cm}|
>{\centering\arraybackslash}p{1.3cm}|
>{\centering\arraybackslash}p{1.6cm}|
>{\centering\arraybackslash}p{1.6cm}|}

\caption{\textbf{Summary of Maximum Demands}}\\
\hline
\multirow{2}{*}{\makecell{\textbf{Load Case /}\\\textbf{Combination}}}
& \multicolumn{3}{c|}{\textbf{Bending Moment}}
& \multicolumn{3}{c|}{\textbf{Shear Force}}
& \multicolumn{2}{c|}{\makecell{\textbf{Reaction at}\\\textbf{Supports}}}\\
\cline{2-9}

& \makecell{\textbf{Max}\\\textbf{(kNm)}}
& \textbf{Girder}
& \makecell{\textbf{Loc.}\\\textbf{(m)}}
& \makecell{\textbf{Max}\\\textbf{(kN)}}
& \textbf{Girder}
& \makecell{\textbf{Loc.}\\\textbf{(m)}}
& \makecell{\textbf{Left}}
& \makecell{\textbf{Right }}\\
\hline
\endfirsthead

\hline
\multirow{2}{*}{\makecell{\textbf{Load Case /}\\\textbf{Combination}}}
& \multicolumn{3}{c|}{\textbf{Bending Moment}}
& \multicolumn{3}{c|}{\textbf{Shear Force}}
& \multicolumn{2}{c|}{\makecell{\textbf{Reaction at}\\\textbf{Supports}}}\\
\cline{2-9}

& \makecell{\textbf{Max}\\\textbf{(kNm)}}
& \textbf{Girder}
& \makecell{\textbf{Loc.}\\\textbf{(m)}}
& \makecell{\textbf{Max}\\\textbf{(kN)}}
& \textbf{Girder}
& \makecell{\textbf{Loc.}\\\textbf{(m)}}
& \makecell{\textbf{Left}}
& \makecell{\textbf{Right}}\\
\hline
\endhead

""" + merged_body + r"""

\hline
\end{longtable}
\endgroup

\ReportTableGap
\begin{longtable}{|>{\centering\arraybackslash}p{5.2cm}|>{\centering\arraybackslash}p{5.2cm}|>{\centering\arraybackslash}p{5.2cm}|}
\caption{\textbf{Reactions at Supports}}
\hline
\textbf{Load Case} & \textbf{Left Support (kN)} & \textbf{Right Support (kN)} \\[6pt]
\hline
""" + reaction_body + r"""
\hline
\end{longtable}

\ReportTableGap
\begin{longtable}{|L{7cm}|p{8.5cm}|}
\caption{\textbf{Deflection Summary (Live Load \& Total Load)}}
\hline
\textbf{parameter} & \textbf{value} \\
\hline
\textnormal{Deflection due to Live Load, $\delta_{LL}$} & """ + _live_str + r""" \\[6pt]
\hline
\textnormal{Allowable Live Load Deflection ($\Delta_{allow}$)} & """ + _allow_live_str + r""" \\[6pt]
\hline
\textnormal{Live Load Deflection Check Status} & """ + _live_status + r""" \\[6pt]
\hline
\textnormal{Deflection due to Total Load, $\delta_{total}$} & """ + _total_str + r""" \\[6pt]
\hline
\textnormal{Allowable Total Deflection ($\Delta_{allow}$)} & """ + _allow_total_str + r""" \\[6pt]
\hline
\textnormal{Total Load Deflection Check Status} & """ + _total_status + r""" \\[6pt]
\hline
\end{longtable}

\ReportTableGap
\noindent\textit{Deflections are maximum available supplied magnitudes. N/A check status denotes an unavailable span, invalid results, or incomplete girder coverage. Supplied failures remain visible.}
\par
\noindent
""" + _fig_embed(fig_paths.get('bm_envelope'), 'Bending Moment Envelope (Envelope ULS): Max/min BM along span. X-axis: distance from left support (m). Y-axis: Bending Moment (kN-m).', width=r'0.75\textwidth') + r"""
""" + _fig_embed(fig_paths.get('sf_envelope'), 'Shear Force Envelope (Envelope ULS): Max/min SF along span. X-axis: distance from left support (m). Y-axis: Shear Force (kN).', width=r'0.75\textwidth') + r"""
""" + _fig_embed(fig_paths.get('defl_ll'), 'Vertical Deflection D$_y$ (1.0 LL): Maximum deflection along span. Load Case: 1.0 LL, Combination: $D_y$. Nodes shown. Isometric view.', width=r'0.75\textwidth') + r"""
"""

