from .charts import chart_figure, nonnegative_number
from .report_utils import _tex
from .styles import styled_chapter


def _quantity_cell(input_dict, key):
    """Use the chart's quantity validity rules without changing BOQ values.

    The existing BOQ helper supplies delimited LaTeX formula fragments. Keep
    those trusted fragments intact; escape any ordinary explanatory text.
    Numeric cells preserve supplied precision, but unavailable, negative and
    nonfinite quantities cannot become values in either the table or chart.
    """
    value = input_dict.get(key)
    if key.endswith("_vol_formula"):
        if not isinstance(value, str) or not value.strip():
            return "N/A"
        value = value.strip()
        if value.lower() in {"n.a.", "n/a", "nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"} or "\\placeholder" in value:
            return "N/A"
        return value if value.startswith("$") and value.endswith("$") else _tex(value)
    return _tex(value) if nonnegative_number(value) is not None else "N/A"


@styled_chapter
def ch7_quantities(input_dict, chart_paths=None):
    return r"""
\chapter{Material Take-off \& Quantity Summary}
\label{ch:material-takeoff}

\noindent\textbf{Table 7.1  Bill of Materials (Steel, Concrete, and Reinforcement Quantities)}

\begingroup
\setlength{\tabcolsep}{3.5pt}
\begin{longtable}{|C{1.0cm}|L{3.8cm}|C{2.6cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|}
\hline
\textbf{S.N.} & \textbf{Item Description} & \textbf{Volume} & \textbf{Quantity} & \textbf{Total Volume} & \textbf{Weight (MT)} & \textbf{Total Weight (MT)} \\
\hline
1 & Structural Steel for Girders & """ + _quantity_cell(input_dict, "steel_girders_vol_formula") + r""" & """ + _quantity_cell(input_dict, "steel_girders_qty") + r""" & """ + _quantity_cell(input_dict, "steel_girders_vol_total") + r""" & """ + _quantity_cell(input_dict, "steel_girders_wt_single") + r""" & """ + _quantity_cell(input_dict, "steel_girders_wt_total") + r""" \\
\hline
2(a) & Cross Bracing - Top Chord & """ + _quantity_cell(input_dict, "bracing_top_vol_formula") + r""" & """ + _quantity_cell(input_dict, "bracing_top_qty") + r""" & """ + _quantity_cell(input_dict, "bracing_top_vol_total") + r""" & """ + _quantity_cell(input_dict, "bracing_top_wt_single") + r""" & """ + _quantity_cell(input_dict, "bracing_top_wt_total") + r""" \\
\hline
2(b) & Cross Bracing - Bottom Chord & """ + _quantity_cell(input_dict, "bracing_bot_vol_formula") + r""" & """ + _quantity_cell(input_dict, "bracing_bot_qty") + r""" & """ + _quantity_cell(input_dict, "bracing_bot_vol_total") + r""" & """ + _quantity_cell(input_dict, "bracing_bot_wt_single") + r""" & """ + _quantity_cell(input_dict, "bracing_bot_wt_total") + r""" \\
\hline
2(c) & Cross Bracing - Diagonal Chord & """ + _quantity_cell(input_dict, "bracing_diag_vol_formula") + r""" & """ + _quantity_cell(input_dict, "bracing_diag_qty") + r""" & """ + _quantity_cell(input_dict, "bracing_diag_vol_total") + r""" & """ + _quantity_cell(input_dict, "bracing_diag_wt_single") + r""" & """ + _quantity_cell(input_dict, "bracing_diag_wt_total") + r""" \\
\hline
2(d) & End Diaphragms & N/A & N/A & N/A & N/A & """ + _quantity_cell(input_dict, "end_diaphragm_wt_total") + r""" \\
\hline
3 & Concrete for Deck Slab & """ + _quantity_cell(input_dict, "concrete_deck_vol_formula") + r""" & """ + _quantity_cell(input_dict, "concrete_deck_qty") + r""" & """ + _quantity_cell(input_dict, "concrete_deck_vol_total") + r""" & """ + _quantity_cell(input_dict, "concrete_deck_wt_single") + r""" & """ + _quantity_cell(input_dict, "concrete_deck_wt_total") + r""" \\
\hline
4 & Reinforcement Steel & """ + _quantity_cell(input_dict, "rebar_deck_vol_formula") + r""" & """ + _quantity_cell(input_dict, "rebar_deck_qty") + r""" & """ + _quantity_cell(input_dict, "rebar_deck_vol_total") + r""" & """ + _quantity_cell(input_dict, "rebar_deck_wt_single") + r""" & """ + _quantity_cell(input_dict, "rebar_deck_wt_total") + r""" \\
\hline
5 & Shear Stud Connectors & """ + _quantity_cell(input_dict, "shear_studs_vol_formula") + r""" & """ + _quantity_cell(input_dict, "shear_studs_qty") + r""" & """ + _quantity_cell(input_dict, "shear_studs_vol_total") + r""" & """ + _quantity_cell(input_dict, "shear_studs_wt_single") + r""" & """ + _quantity_cell(input_dict, "shear_studs_wt_total") + r""" \\
\hline
6 & Crash Barrier & """ + _quantity_cell(input_dict, "crash_barrier_vol_formula") + r""" & """ + _quantity_cell(input_dict, "crash_barrier_qty") + r""" & """ + _quantity_cell(input_dict, "crash_barrier_vol_total") + r""" & """ + _quantity_cell(input_dict, "crash_barrier_wt_single") + r""" & """ + _quantity_cell(input_dict, "crash_barrier_wt_total") + r""" \\
\hline
\end{longtable}
\endgroup
\noindent\textit{Quantities reproduce the existing bill of quantities. End diaphragm mass is N/A unless explicitly supplied; it is not inferred from cross bracing. Reinforcement tonnage in the upstream bill of quantities is an estimate of 120 kg per cubic metre of deck concrete, not a reinforcement schedule.}
""" + chart_figure(chart_paths, "steel_quantities", "Structural steel quantities in metric tonnes. N/A denotes unavailable quantities.") + chart_figure(chart_paths, "deck_quantities", "Deck concrete volume and estimated reinforcement mass, displayed on separate axes because their units differ.")


