"""Report visualizations from existing design outputs; no design calculations.

The plotting code uses an Agg canvas directly so generating reports in a worker
does not change the desktop application's Matplotlib backend. Missing or invalid
data is retained as ``None`` and drawn as N/A, never as a passing zero bar.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from pathlib import Path

from osdagbridge.core.utils import common as keys
from .styles import STYLE


def nonnegative_number(value) -> float | None:
    """Accept finite nonnegative numbers, excluding booleans and placeholders."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def demand_capacity_ratio(demand, capacity) -> float | None:
    """Return a presentation ratio only for a valid demand and positive capacity."""
    demand = nonnegative_number(demand)
    capacity = nonnegative_number(capacity)
    if demand is None or capacity is None or capacity <= 0:
        return None
    return nonnegative_number(demand / capacity)


def _mapping(value) -> Mapping:
    return value if isinstance(value, Mapping) else {}


@dataclass(frozen=True)
class TransverseCheck:
    pair: str
    member: str
    force_type: str
    demand: float | None
    capacity: float | None
    ratio: float | None
    section: str
    governing_lc: str
    connection: str
    slenderness: float | None


def transverse_checks(outputs: Mapping, *, diaphragm: bool = False) -> list[TransverseCheck]:
    """Read the real Osdag CB or ED result schema without importing the solver.

    The two capacity/section keys are the same aliases used by upstream
    ``results_data._extract_osdag_summary``. Demand and governing load case come
    from the matching force envelope, not from another component's results.
    """
    prefix = "end_diaphragm" if diaphragm else "crossbracing"
    forces = _mapping(_mapping(outputs.get(prefix + "_forces_dict")).get("pairs"))
    designs = _mapping(outputs.get(prefix + "_design_results"))
    checks = []
    for pair in sorted(set(forces) | set(designs)):
        pair_forces = _mapping(forces.get(pair))
        pair_designs = _mapping(designs.get(pair))
        for member, force_prefix in (("diagonal", "diag"), ("chord", "chord")):
            member_design = _mapping(pair_designs.get(member))
            for nature in ("compression", "tension"):
                raw = _mapping(member_design.get(nature))
                force_key = f"{force_prefix}_{nature}_kN"
                # Do not add nonexistent tension/compression cases as zero.
                if force_key not in pair_forces and nature not in member_design:
                    continue
                capacity = raw.get("Member.tension_capacity")
                if capacity is None:
                    capacity = raw.get("Design.Strength")
                demand = pair_forces.get(force_key)
                section = raw.get("section_size.designation")
                if section is None:
                    section = raw.get("Optimum.Designation")
                checks.append(TransverseCheck(
                    pair=str(pair), member=member, force_type=nature,
                    demand=nonnegative_number(demand),
                    capacity=nonnegative_number(capacity),
                    ratio=demand_capacity_ratio(demand, capacity),
                    section=str(section) if section is not None else "N/A",
                    governing_lc=str(pair_forces.get(f"{force_prefix}_{nature}_gov_lc") or "N/A"),
                    connection=("Welded" if "Weld.Type" in raw else "Bolted") if raw else "N/A",
                    slenderness=nonnegative_number(raw.get("Member.Slenderness")),
                ))
    return checks


def _worst(values) -> float | None:
    valid = [value for value in values if value is not None]
    return max(valid) if valid else None


def utilization_series(inputs: Mapping, outputs: Mapping) -> dict[str, dict[str, float | None]]:
    """Return independently sourced component series for the Section 5.5 plot."""
    girder_values = {}
    per_girder = _mapping(_mapping(outputs.get("design_results")).get("per_girder"))
    for girder, data in per_girder.items():
        if str(girder).startswith("EB"):
            continue
        data = _mapping(data)
        checks = list(data.get("checks") or [])
        # Include actual per-LC checks (e.g. deflection) omitted by the envelope.
        for lc in _mapping(data.get("per_lc")).values():
            checks.extend(_mapping(lc).get("checks") or [])
        ratios = []
        for check in checks:
            check = _mapping(check)
            ratio = demand_capacity_ratio(check.get("demand"), check.get("capacity"))
            # Preserve the engine's unrounded ratio when available, but only
            # after checking demand/capacity (zero capacity uses sentinel 999).
            if ratio is not None:
                reported = nonnegative_number(check.get("dcr"))
                ratio = reported if reported is not None else ratio
            ratios.append(ratio)
        girder_values[str(girder)] = _worst(ratios)
    if not girder_values:
        girder_values["No girder results"] = None

    deck = _mapping(outputs.get("deck_report_values"))
    deck_values = {}
    deck_keys = (
        ("Sagging", keys.KEY_DD_M_ULS_SAG, keys.KEY_DD_MU_BOT),
        ("Hogging", keys.KEY_DD_M_ULS_HOG, keys.KEY_DD_MU_TOP),
        ("Punching", keys.KEY_DD_PUNCH_VED, keys.KEY_DD_VRD_C_MPA),
        ("One-way shear", keys.KEY_DD_SHEAR_VED, keys.KEY_DD_SHEAR_VRDC),
    )
    for label, demand_key, capacity_key in deck_keys:
        deck_values[label] = demand_capacity_ratio(deck.get(demand_key), deck.get(capacity_key))
    if deck.get(keys.KEY_DD_HAS_OVERHANG):
        deck_values["Overhang"] = demand_capacity_ratio(deck.get(keys.KEY_DD_M_ULS_OH), deck.get(keys.KEY_DD_MU_OH))
    crack_values = [nonnegative_number(deck.get(key)) for key in
                    (keys.KEY_DD_WK_BOT, keys.KEY_DD_WK_TOP)]
    if deck.get(keys.KEY_DD_HAS_OVERHANG):
        crack_values.append(nonnegative_number(deck.get(keys.KEY_DD_WK_OH)))
    deck_values["Crack width"] = demand_capacity_ratio(_worst(crack_values), deck.get(keys.KEY_DD_WK_LIMIT))

    series = {"Steel plate girders": girder_values, "Concrete deck slab": deck_values}
    for label, diaphragm in (("Cross bracing", False), ("End diaphragms", True)):
        values = {}
        for check in transverse_checks(outputs, diaphragm=diaphragm):
            member_label = f"{check.pair}\n{check.member}"
            values.setdefault(member_label, []).append(check.ratio)
        series[label] = {name: _worst(ratios) for name, ratios in values.items()} or {"No design results": None}
    return series


def material_series(inputs: Mapping) -> dict[str, dict[str, float | None]]:
    """Read Chapter 7 quantities, keeping mass and volume on separate axes."""
    bracing = [nonnegative_number(inputs.get(f"bracing_{part}_wt_total")) for part in ("top", "bot", "diag")]
    return {
        "Structural steel (MT)": {
            "Girders": nonnegative_number(inputs.get("steel_girders_wt_total")),
            "Cross bracing": sum(bracing) if all(value is not None for value in bracing) else None,
            "End diaphragms": nonnegative_number(inputs.get("end_diaphragm_wt_total")),
        },
        "Concrete volume (m³)": {"Deck slab": nonnegative_number(inputs.get("concrete_deck_vol_total"))},
        "Reinforcement steel (MT)": {"Deck reinforcement": nonnegative_number(inputs.get("rebar_deck_wt_total"))},
    }


def _bars(ax, values, title, ylabel, *, utilization=False):
    labels = list(values)
    for index, value in enumerate(values.values()):
        if value is None:
            ax.text(index, 0.04, "N/A", ha="center", color=STYLE.chart_missing_color,
                    transform=ax.get_xaxis_transform(), fontsize=STYLE.chart_font_size)
        else:
            color = STYLE.failure_color if utilization and value > 1 else STYLE.green
            ax.bar(index, value, color=color, width=0.58)
            ax.annotate(f"{value:.2f}", (index, value), xytext=(0, 4),
                        textcoords="offset points", ha="center", fontsize=STYLE.chart_font_size)
    ax.set_xticks(range(len(labels)), labels, fontsize=STYLE.chart_font_size)
    ax.tick_params(axis="x", labelrotation=25)
    ax.set_ylabel(ylabel, fontfamily=STYLE.chart_font_family)
    ax.set_title(title, fontfamily=STYLE.chart_font_family, color=STYLE.text_color)
    ax.set_xlim(-0.6, max(len(labels) - 0.4, 0.6))
    maximum = max((value for value in values.values() if value is not None), default=0)
    ax.set_ylim(0, max(1.25 if utilization else 1, maximum * 1.24))
    ax.grid(axis="y", color=STYLE.chart_grid_color, alpha=0.8)
    ax.set_axisbelow(True)
    if utilization:
        ax.axhline(1.0, color=STYLE.failure_color, linestyle="--", linewidth=1.5, label="UR = 1.0")
        ax.legend(loc="upper right", fontsize=STYLE.chart_font_size)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(STYLE.chart_font_family)


def generate_summary_charts(inputs: Mapping, outputs: Mapping, asset_dir) -> dict[str, str]:
    """Save PNGs in the caller-owned temporary asset directory.

    The directory must live until LaTeX compilation completes. This function
    creates no GUI windows and does not modify global pyplot state.
    """
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    directory = Path(asset_dir)
    directory.mkdir(parents=True, exist_ok=True)
    result = {}
    utilization = Figure(figsize=(STYLE.chart_width_inches, STYLE.chart_panel_height_inches * 2), layout="constrained")
    FigureCanvasAgg(utilization)
    for ax, (title, values) in zip(utilization.subplots(2, 2).flat, utilization_series(inputs, outputs).items()):
        _bars(ax, values, title, "Utilization Ratio", utilization=True)
    material = material_series(inputs)
    steel = Figure(figsize=(STYLE.chart_width_inches, STYLE.chart_panel_height_inches), layout="constrained")
    FigureCanvasAgg(steel)
    _bars(steel.subplots(), material["Structural steel (MT)"], "Structural steel quantities", "Mass (MT)")
    deck = Figure(figsize=(STYLE.chart_width_inches, STYLE.chart_panel_height_inches), layout="constrained")
    FigureCanvasAgg(deck)
    for ax, (title, ylabel) in zip(deck.subplots(1, 2), (("Concrete volume (m³)", "Volume (m³)"), ("Reinforcement steel (MT)", "Mass (MT)"))):
        _bars(ax, material[title], title, ylabel)
    for key, figure in (("utilization", utilization), ("steel_quantities", steel), ("deck_quantities", deck)):
        path = directory / (key + ".png")
        figure.savefig(path, dpi=STYLE.chart_dpi)
        figure.clear()
        result[key] = str(path)
    return result


def chart_figure(chart_paths, key: str, caption: str) -> str:
    """Create an escaped PyLaTeX figure from a generated chart asset."""
    if not chart_paths or not chart_paths.get(key):
        return ""
    from pylatex import Figure, NoEscape

    with_figure = Figure(position="htbp")
    with_figure.add_image(str(chart_paths[key]).replace("\\", "/"),
                          width=NoEscape(f"{STYLE.chart_width_fraction}\\linewidth"))
    with_figure.add_caption(caption)
    return with_figure.dumps()
