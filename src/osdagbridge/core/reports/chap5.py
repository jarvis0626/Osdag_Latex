# =============================================================================
# Chapter 5: Design Checks
# Extracted from report_generator.py — DO NOT add business logic here.
# =============================================================================
from __future__ import annotations
from typing import TYPE_CHECKING

from osdagbridge.core.utils.common import (
    KEY_DD_AS_BOT,
    KEY_DD_AS_LONG,
    KEY_DD_AS_MIN,
    KEY_DD_AS_REQ_BOT,
    KEY_DD_AS_REQ_TOP,
    KEY_DD_AS_TOP,
    KEY_DD_COVER_OK,
    KEY_DD_DIA_BOT,
    KEY_DD_D_BOT,
    KEY_DD_FY,
    KEY_DD_GAMMA_DL,
    KEY_DD_GAMMA_LL,
    KEY_DD_HAS_OVERHANG,
    KEY_DD_IMPACT_FACTOR,
    KEY_DD_MIN_COVER,
    KEY_DD_MU_BOT,
    KEY_DD_MU_OH,
    KEY_DD_MU_TOP,
    KEY_DD_M_BARRIER,
    KEY_DD_M_DL,
    KEY_DD_M_DL_OH,
    KEY_DD_M_LL,
    KEY_DD_M_LL_OH,
    KEY_DD_M_ULS_HOG,
    KEY_DD_M_ULS_OH,
    KEY_DD_M_ULS_SAG,
    KEY_DD_PUNCH_C1,
    KEY_DD_PUNCH_C2,
    KEY_DD_PUNCH_OK,
    KEY_DD_PUNCH_U1,
    KEY_DD_PUNCH_VED,
    KEY_DD_PUNCH_VED_KN,
    KEY_DD_SHEAR_OK,
    KEY_DD_SHEAR_VED,
    KEY_DD_SHEAR_VRDC,
    KEY_DD_SPACING_MAX,
    KEY_DD_SPAN,
    KEY_DD_SPC_BOT,
    KEY_DD_TYRE_LENGTH,
    KEY_DD_TYRE_WIDTH,
    KEY_DD_VEHICLE,
    KEY_DD_VRD_C_MPA,
    KEY_DD_WDL,
    KEY_DD_WHEEL_LOAD,
    KEY_DD_WK_BOT,
    KEY_DD_WK_LIMIT,
    KEY_DD_WK_OH,
    KEY_DD_WK_TOP,
    KEY_DECK_CONCRETE_GRADE_BASIC,
    KEY_DS_BOTTOM_CLEAR_COVER,
    KEY_DS_REINF_MATERIAL,
    KEY_DS_TOP_CLEAR_COVER,
    KEY_MATERIAL_DECK_FCK,
    KEY_MATERIAL_DECK_FCTM,
    KEY_TS_DECK_OVERHANG,
    KEY_TS_DECK_THICKNESS,
)

from osdagbridge.core.reports.report_utils import _tex, _render_value
from .charts import chart_figure, demand_capacity_ratio, nonnegative_number, transverse_checks, reported_check_ratio
from .styles import styled_chapter
from .data import backend_girder_table

if TYPE_CHECKING:
    pass


def _end_diaphragm_tables(outputs):
    """Render actual support diaphragm results, independently of cross bracing."""
    checks = transverse_checks(outputs, diaphragm=True)
    if not checks:
        return (
            r"\multicolumn{6}{|c|}{N/A --- no end diaphragm design results supplied} \\ \hline",
            r"\multicolumn{6}{|c|}{N/A --- no end diaphragm design results supplied} \\ \hline",
            r"\multicolumn{8}{|c|}{N/A --- no end diaphragm design results supplied} \\ \hline",
        )
    properties, slenderness, capacities = [], [], []
    seen = set()
    for check in checks:
        label = _tex(check.member + " (" + check.force_type + ")")
        pair_id = check.pair.replace("-", "")
        prop_name = "end_diaphragm" if check.member == "diagonal" else "bottom_chord"
        prefix = f"transverse_member_design.ed.section_properties.{prop_name}.{pair_id}"
        if check.member == "chord" and outputs.get(prefix + ".A") is None:
            prefix = f"transverse_member_design.ed.section_properties.top_chord.{pair_id}"
        area = nonnegative_number(outputs.get(prefix + ".A"))
        radius = nonnegative_number(outputs.get(prefix + ".rv"))
        if (check.pair, check.member) not in seen:
            properties.append(" & ".join((
                _tex(check.pair), _tex(check.member), _tex(check.connection), _tex(check.section),
                f"{area * 100:.1f}" if area is not None else "N/A",
                f"{radius * 10:.1f}" if radius is not None else "N/A",
            )) + r" \\[6pt] \hline")
            seen.add((check.pair, check.member))
        limit = 250 if check.force_type == "compression" else 400
        slender_status = ("PASS" if check.slenderness <= limit else "FAIL") if check.slenderness is not None else "N/A"
        slenderness.append(" & ".join((
            _tex(check.pair), _tex(check.member), _tex(check.force_type), "N/A",
            f"{check.slenderness:.1f}" if check.slenderness is not None else "N/A",
            f"{limit} / {slender_status}",
        )) + r" \\[6pt] \hline")
        status = ("PASS" if check.ratio <= 1 else r"\textcolor{red}{FAIL}") if check.ratio is not None else "N/A"
        capacities.append(" & ".join((
            _tex(check.pair), label, _tex(check.section), _tex(check.governing_lc),
            f"{check.demand:.3f}" if check.demand is not None else "N/A",
            f"{check.capacity:.3f}" if check.capacity is not None else "N/A",
            f"{check.ratio:.3f}" if check.ratio is not None else "N/A", status,
        )) + r" \\[6pt] \hline")
    return "\n".join(properties), "\n".join(slenderness), "\n".join(capacities)


@styled_chapter
def ch5_design_checks(checks_data, bridge, chart_paths=None) -> str:
    """Chapter 5 — Design Checks.

    Parameters
    ----------
    checks_data : dict
        Raw checks payload (currently unused; data is sourced from bridge).
    bridge : ReportDataBridge
        Provides input_dict, output_dict, and helper methods.
    """
    # Deck slab design report values (Tables 5.17(a)-(g)), keyed to
    # common.KEY_DD_*. Populated by deckdesign.design_deck_slab(); empty
    # dict when deck design has not been run. Look up with deck_rpt.get(KEY_...).
    deck_rpt = bridge.output_dict.get("deck_report_values", {}) or {}
    ed_forces_content, ed_slenderness_content, ed_capacity_content = _end_diaphragm_tables(bridge.output_dict)

    def _dfmt(value, nd=2):
        number = nonnegative_number(value)
        return f"{number:.{nd}f}" if number is not None else ""

    # Generate Table 5.20(a) rows
    cb_forces_rows = []
    pairs = bridge.get_cb_pairs()

    if not pairs:
        # fallback: one placeholder row
        cb_forces_rows.append(
            r"""Between Girders & Diagonal &  &  &  &  \\[6pt]
\hline"""
        )
    else:
        for pair in pairs:
            pair_id = pair.replace("-", "")
            for member, label in [("diagonal", "Diagonal"),
                                ("chord", "Top / Bottom chord")]:
                force_str, ftype = bridge.get_cb_governing_force(pair, member)
                conn_type = bridge.get_cb_connection(pair, member, ftype)
                section  = bridge.get_cb_section(pair, member, ftype)

                # Fetch properties from output_dict
                if member == "diagonal":
                    pfx = f"transverse_member_design.cb.section_properties.bracing.{pair_id}"
                else:
                    pfx = f"transverse_member_design.cb.section_properties.bottom_chord.{pair_id}"
                    if bridge.output_dict.get(f"{pfx}.A") is None:
                        pfx = f"transverse_member_design.cb.section_properties.top_chord.{pair_id}"

                area_cm2 = bridge.output_dict.get(f"{pfx}.A")
                rv_cm = bridge.output_dict.get(f"{pfx}.rv")

                # Convert Area: cm² -> mm²
                area_str = f"{float(area_cm2) * 100:.1f}" if area_cm2 is not None else ""
                # Convert rv: cm -> mm
                rmin_str = f"{float(rv_cm) * 10:.1f}" if rv_cm is not None else ""
                cb_forces_rows.append(
                    r"\multirow{2}{*}{\makecell{" + _tex(pair) + r"}} & "
                    + label + r" & " + conn_type + r" & " + section
                    + r" & " + area_str + r" & " + rmin_str
                    + r" \\[6pt]\cline{2-6}"
                )
            cb_forces_rows.append(r"\hline")
    cb_forces_content = "\n".join(cb_forces_rows)

    # Generate Table 5.20(b) rows
    def get_status_str(slnd_str, limit):
        try:
            v = float(slnd_str)
            return r"\textcolor{black}{PASS}" if v <= limit else r"\textcolor{red}{FAIL}"
        except (ValueError, TypeError):
            return ""
    cb_slenderness_rows = []
    if not pairs:
        cb_slenderness_rows.append(
            r"""Between Girders & Diagonal & C &  &  &  ---  \\[6pt]
\hline"""
        )
    else:
        for pair in pairs:
            kl_diag = bridge.get_cb_effective_length("diagonal")
            slnd_diag = bridge.get_cb_slenderness(pair, "diagonal")
            status_diag = get_status_str(slnd_diag, 250)
            
            kl_tc = bridge.get_cb_effective_length("chord")
            slnd_tc = bridge.get_cb_slenderness(pair, "chord")
            status_tc = get_status_str(slnd_tc, 250)
            
            kl_bc = bridge.get_cb_effective_length("chord")
            slnd_bc = bridge.get_cb_slenderness(pair, "chord")
            status_bc = get_status_str(slnd_bc, 400)
            
            top_chord_enabled = bridge.output_dict.get("member_properties.cross_bracing_details.top_chord", True)
            bottom_chord_enabled = bridge.output_dict.get("member_properties.cross_bracing_details.bottom_chord", True)
            
            num_rows = 1 + int(top_chord_enabled) + int(bottom_chord_enabled)
            row_tex = r"\multirow{" + str(num_rows) + r"}{*}{\makecell{" + _tex(pair) + r"}}"
            row_tex += f" & Diagonal & C & {kl_diag} & {slnd_diag} & 250 --- {status_diag} \\\\[6pt]"
            
            if top_chord_enabled:
                row_tex += f"\n\\cline{{2-6}}\n & Top chord & C & {kl_tc} & {slnd_tc} & 250 --- {status_tc} \\\\[6pt]"
            if bottom_chord_enabled:
                row_tex += f"\n\\cline{{2-6}}\n & Bottom chord & T & {kl_bc} & {slnd_bc} & 400 --- {status_bc} \\\\[6pt]"
                
            row_tex += "\n\\hline"
            cb_slenderness_rows.append(row_tex)
    cb_slenderness_content = "\n".join(cb_slenderness_rows)

    # Generate Table 5.20(c) rows
    cb_capacity_rows = []
    for pair in pairs:
        rows_for_pair = []
        for member, label in [("diagonal", "Diagonal"),
                            ("chord", "Chord")]:
            force_str, ftype = bridge.get_cb_governing_force(pair, member)
            section  = bridge.get_cb_section(pair, member, ftype)
            gov_lc   = bridge.get_cb_gov_lc(pair, member, ftype)
            capacity = bridge.get_cb_capacity(pair, member, ftype)
            ur       = bridge.get_cb_efficiency(pair, member, ftype)
            status   = bridge.get_cb_status(pair, member, ftype)
            rows_for_pair.append(
                r" & " + label + r" & " + section
                + r" & " + gov_lc + r" & " + force_str + r" & " + capacity
                + r" & " + ur + r" & " + status + r" \\[6pt]\cline{2-8}"
            )
        first = r"\multirow{2}{*}{\makecell{" + _tex(pair) + r"}}" + rows_for_pair[0]
        rest  = rows_for_pair[1:]
        cb_capacity_rows.append(first)
        cb_capacity_rows.extend(rest)
        cb_capacity_rows.append(r"\hline")
    cb_capacity_content = "\n".join(cb_capacity_rows)



    # ── Deck slab design value helpers (Tables 5.17 a/b/c/e/g) ────────────────
    # Read from deck_rpt = output_dict["deck_report_values"] (common.KEY_DD_*).
    _dk_has = bool(deck_rpt)
    _dk_oh = bool(deck_rpt.get(KEY_DD_HAS_OVERHANG))
    _DKPH = "N/A"

    def _dkv(key, default=0.0):
        """Legacy numeric fallback for reference expressions, never status checks."""
        v = deck_rpt.get(key)
        if v is None or v == "":
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def _dkf(key, nd=2, scale=1.0):
        """Formatted display string; placeholder when deck design not run."""
        if not _dk_has:
            return _DKPH
        v = deck_rpt.get(key)
        if v is None or v == "":
            return _DKPH
        try:
            return f"{float(v) * scale:.{nd}f}"
        except (TypeError, ValueError):
            return _tex(v)

    def _dks(ok):
        """Keep an unavailable status distinct from an explicit failed check."""
        if not _dk_has or ok is None:
            return "N/A"
        flag = str(ok).strip().lower()
        if flag in ("true", "yes", "1", "pass"):
            return "PASS"
        if flag in ("false", "no", "0", "fail"):
            return "FAIL"
        return "N/A"

    def _dk_capacity_ok(demand_key, capacity_key):
        ratio = demand_capacity_ratio(deck_rpt.get(demand_key), deck_rpt.get(capacity_key))
        return ratio <= 1 if ratio is not None else None

    def _dk_ratio(demand_key, capacity_key):
        ratio = demand_capacity_ratio(deck_rpt.get(demand_key), deck_rpt.get(capacity_key))
        return f"{ratio:.2f}" if ratio is not None else "N/A"

    def _dk_spacing_ok():
        spacing = nonnegative_number(deck_rpt.get(KEY_DD_SPC_BOT))
        ratio = demand_capacity_ratio(spacing, deck_rpt.get(KEY_DD_SPACING_MAX))
        return spacing > 0 and ratio <= 1 if ratio is not None else None

    def _dk_distribution_ok():
        main = nonnegative_number(deck_rpt.get(KEY_DD_AS_BOT))
        minimum = nonnegative_number(deck_rpt.get(KEY_DD_AS_MIN))
        if main is None or minimum is None:
            return None
        # This is the existing displayed comparison; guard its input values.
        required = max(0.20 * main, minimum)
        ratio = demand_capacity_ratio(required, deck_rpt.get(KEY_DD_AS_LONG))
        return ratio <= 1 if ratio is not None else None

    def _dkoh(key, nd=2, scale=1.0, unit=""):
        """Overhang value; 'N/A' when there is no overhang."""
        if not _dk_has:
            return _DKPH
        if not _dk_oh:
            return "N/A"
        return _dkf(key, nd=nd, scale=scale) + unit

    # Governing crack width = max(bottom, top[, overhang]) vs the limit.
    _dk_wks = [nonnegative_number(deck_rpt.get(KEY_DD_WK_BOT)),
               nonnegative_number(deck_rpt.get(KEY_DD_WK_TOP))]
    if _dk_oh:
        _dk_wks.append(nonnegative_number(deck_rpt.get(KEY_DD_WK_OH)))
    _dk_gov_wk = max((value for value in _dk_wks if value is not None), default=None)
    _dk_gov_wk_str = (f"{_dk_gov_wk:.4f}" if _dk_gov_wk is not None else _DKPH)
    _dk_crack_ratio = demand_capacity_ratio(_dk_gov_wk, deck_rpt.get(KEY_DD_WK_LIMIT))
    _dk_crack_ok = _dk_crack_ratio <= 1 if _dk_crack_ratio is not None else None

    # ── Table 5.22: Overall Design Check Summary — fill all rows ─────────────
    # Three row families:
    #  (1) Girder DCR-engine checks: one source (design_results["per_girder"])
    #      gives Demand, Capacity, UR, and the governing LC together. Worst
    #      girder = highest DCR. Most checks fire on the envelope demand (units
    #      available in per_girder["checks"]); SLS-conditional checks (e.g.
    #      deflection) only appear per-LC, so fall back to per_lc for those.
    #  (2) Deck slab: URs from deck_design_results (Demand/Capacity not stored).
    #  (3) Cross bracing: existing get_cb_* helpers (worst pair/member by UR).
    #      End diaphragm has no report helpers yet → "---" for now.
    _pg_522 = (bridge.output_dict.get("design_results", {}) or {}).get("per_girder", {}) or {}
    _dd_522 = bridge.output_dict.get("deck_design_results", {}) or {}

    def _vu_522(v, unit):
        s = _dfmt(v, nd=2)
        if not s:
            return ""
        u = (unit or "").strip()
        return (s + " " + u) if u else s

    def _ur_522(v):
        f = nonnegative_number(v)
        if f is None:
            return "N/A"
        s = f"{f:.2f}"
        return (r"\textcolor{red}{" + s + "}") if f > 1.0 else s

    def _lc_short(lc):
        # Show the full combination expression as-is, e.g.
        # "ACCIDENTAL 1: 1.0DL + 1.0DW + 0.75LL" (the per_lc key).
        return _tex(str(lc).strip())

    def _gov_lc_in_522(g, check_ids):
        gd = _pg_522.get(g) or {}
        best = None
        for _lc, _ld in (gd.get("per_lc") or {}).items():
            if str(_lc).lower().startswith("envelope"):
                continue
            for _chk in (_ld.get("checks") or []):
                if _chk.get("id") in check_ids:
                    _d = _chk.get("dcr") or 0.0
                    if best is None or _d > best[0]:
                        best = (_d, _lc)
        return _lc_short(best[1]) if best else "---"

    def _dcr_row(check_ids, fallback_unit=""):
        # Prefer per_girder["checks"] (carries units); worst girder by DCR.
        best = None  # (dcr, demand, capacity, dunit, cunit, g)
        for g, gd in _pg_522.items():
            if str(g).startswith("EB"):
                continue
            for chk in (gd.get("checks") or []):
                if chk.get("check_id") in check_ids:
                    d = reported_check_ratio(chk)
                    if d is None:
                        continue
                    if best is None or d > best[0]:
                        best = (d, chk.get("demand"), chk.get("capacity"),
                                chk.get("demand_unit") or "", chk.get("capacity_unit") or "", g)
        if best is not None:
            d, dem, cap, du, cu, g = best
            return (_gov_lc_in_522(g, check_ids),
                    _vu_522(dem, du) or "---", _vu_522(cap, cu) or "---", _ur_522(d) or "---")
        # Fallback: per_lc (no units) for SLS-conditional checks (e.g. deflection).
        best = None  # (dcr, demand, capacity, lc)
        for g, gd in _pg_522.items():
            if str(g).startswith("EB"):
                continue
            for _lc, _ld in (gd.get("per_lc") or {}).items():
                if str(_lc).lower().startswith("envelope"):
                    continue
                for chk in (_ld.get("checks") or []):
                    if chk.get("id") in check_ids:
                        d = reported_check_ratio(chk)
                        if d is None:
                            continue
                        if best is None or d > best[0]:
                            best = (d, chk.get("demand"), chk.get("capacity"), _lc)
        if best is None:
            return ("---", "---", "---", "---")
        d, dem, cap, _lc = best
        return (_lc_short(_lc),
                _vu_522(dem, fallback_unit) or "---", _vu_522(cap, fallback_unit) or "---",
                _ur_522(d) or "---")

    # (3) Cross bracing — worst pair/member by UR for the given force type.
    _cb_pairs_522 = bridge.get_cb_pairs()

    def _cb_row(force_type):
        available = [check for check in transverse_checks(bridge.output_dict)
                     if check.force_type == force_type and check.ratio is not None]
        if not available:
            return ("N/A", "N/A", "N/A", "N/A")
        check = max(available, key=lambda result: result.ratio)
        return (_tex(check.governing_lc), f"{check.demand:.2f} kN",
                f"{check.capacity:.2f} kN", _ur_522(check.ratio))

    def _cb_slender_row():
        best = None  # (ratio, slend, limit)
        for pair in _cb_pairs_522:
            for member in ("diagonal", "chord"):
                s = bridge.get_cb_slenderness(pair, member)
                try:
                    sf = float(s)
                except (TypeError, ValueError):
                    continue
                lim = 400.0 if member == "chord" else 250.0
                ratio = sf / lim
                if best is None or ratio > best[0]:
                    best = (ratio, sf, lim)
        if best is None:
            return ("---", "---", "---", "---")
        ratio, sf, lim = best
        return ("---", f"{sf:.1f}", f"{lim:.0f}", _ur_522(ratio))

    def _row522(label, cells):
        c = [x if x else "---" for x in cells]
        return label + r" & " + r" & ".join(c) + r" \\[6pt]" + "\n\\hline"

    # Deck rows: Demand/Capacity from deck_report_values (KEY_DD_*, the same dict
    # the 5.17 tables use); UR = Demand/Capacity. The deck is designed for the
    # IRC:6 Basic ULS combination — build that combo string from the stored
    # partial factors (gamma_dl, gamma_ll).
    _deck_combo = (
        r"Basic ULS: " + _tex(f"{_dkv(KEY_DD_GAMMA_DL):g}DL + {_dkv(KEY_DD_GAMMA_LL):g}LL")
    ) if _dk_has else "---"

    def _deck_row(dem_key, cap_key, unit, is_oh=False):
        if not _dk_has:
            return ("---", "---", "---", "---")
        if is_oh and not _dk_oh:
            return (_deck_combo, "N/A", "N/A", "N/A")
        dem = nonnegative_number(deck_rpt.get(dem_key))
        cap = nonnegative_number(deck_rpt.get(cap_key))
        ur = demand_capacity_ratio(dem, cap)
        if ur is None:
            return (_deck_combo, "N/A", "N/A", "N/A")
        return (_deck_combo, f"{dem:.2f} {unit}", f"{cap:.2f} {unit}", _ur_522(ur))

    def _row522_msg(label, msg):
        # Single message spanning the 4 data columns.
        return label + r" & \multicolumn{4}{c|}{" + msg + r"} \\[6pt]" + "\n\\hline"

    def _ed_row(nature):
        available = [check for check in transverse_checks(bridge.output_dict, diaphragm=True)
                     if check.force_type == nature and check.ratio is not None]
        if not available:
            return ("N/A", "N/A", "N/A", "N/A")
        check = max(available, key=lambda result: result.ratio)
        return (_tex(check.governing_lc), f"{check.demand:.2f} kN",
                f"{check.capacity:.2f} kN", _ur_522(check.ratio))

    _ed_moment_row = _row522(r"End Diaphragm --- Compression", _ed_row("compression"))
    _ed_shear_row = _row522(r"End Diaphragm --- Tension", _ed_row("tension"))

    # Crack width (slab): governing crack width vs limit from the deck designer
    # (frequent SLS combination). _dk_gov_wk is the max of bottom/top/overhang wk.
    # The governing load combo is the SLS-frequent combination with the highest
    # DCR (its full expression comes straight from the per_lc keys).
    def _gov_sls_frequent():
        best = None  # (dcr, lc)
        for _g, _gd in _pg_522.items():
            if str(_g).startswith("EB"):
                continue
            for _lc, _ld in (_gd.get("per_lc") or {}).items():
                if "frequent" not in str(_lc).lower():
                    continue
                _d = _ld.get("max_dcr") or 0.0
                if best is None or _d > best[0]:
                    best = (_d, _lc)
        return _tex(str(best[1]).strip()) if best else "Frequent SLS"

    _wk_lim = nonnegative_number(deck_rpt.get(KEY_DD_WK_LIMIT))
    _crack_cells = (
        (_gov_sls_frequent() if _dk_has else "---"),
        (f"{_dk_gov_wk:.3f} mm" if _dk_gov_wk is not None else "N/A"),
        (f"{_wk_lim:.3f} mm" if _wk_lim is not None else "N/A"),
        _ur_522(_dk_crack_ratio),
    )

    _t522 = [
        _row522(r"Girder --- Moment",             _dcr_row({1})),
        _row522(r"Girder --- Shear",              _dcr_row({2})),
        _row522(r"Girder --- LTB (constr.)",      _dcr_row({5})),
        _row522(r"Girder --- Deflection",         _dcr_row({13, 14}, fallback_unit="mm")),
        _row522(r"Girder --- Stress",             _dcr_row({11}, fallback_unit="MPa")),
        _row522(r"Girder --- Fatigue",            _dcr_row({8, 9}, fallback_unit="MPa")),
        _row522(r"Transverse Shear (slab)",       _dcr_row({16})),
        _row522(r"Crack Width (slab)",            _crack_cells),
        _row522(r"Deck --- Flexure (sagging)",    _deck_row(KEY_DD_M_ULS_SAG, KEY_DD_MU_BOT, "kN-m/m")),
        _row522(r"Deck --- Flexure (hogging)",    _deck_row(KEY_DD_M_ULS_HOG, KEY_DD_MU_TOP, "kN-m/m")),
        _row522(r"Deck --- Cantilever Overhang",  _deck_row(KEY_DD_M_ULS_OH, KEY_DD_MU_OH, "kN-m/m", is_oh=True)),
        _row522(r"Deck --- Punching Shear",       _deck_row(KEY_DD_PUNCH_VED, KEY_DD_VRD_C_MPA, "MPa")),
        _row522(r"Deck --- One-Way Shear",        _deck_row(KEY_DD_SHEAR_VED, KEY_DD_SHEAR_VRDC, "kN/m")),
        _row522(r"Cross Bracing --- Compression", _cb_row("compression")),
        _row522(r"Cross Bracing --- Tension",     _cb_row("tension")),
        _row522(r"Cross Bracing --- Slenderness", _cb_slender_row()),
        _ed_moment_row,
        _ed_shear_row,
    ]
    t522_content = "\n".join(_t522)

    chapter = r"""
\chapter{Design Checks}

This section renders the design checks supplied for this report. Missing results are N/A. Backend values and acceptance statuses are retained; the report does not run a structural analysis. Code references come from supplied checks or inherited templates and require project-specific verification.

""" + backend_girder_table(bridge.output_dict) + r"""

\section{Deck Slab Design}
\label{sec:deck-design}
% ===========================

Deck slab values are read from supplied backend results. The following template equations and references describe the reported checks; their applicable editions must be verified for the project.

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
\caption{\textbf{Deck Slab --- Loading and Geometry}}
\hline
\textnormal{Effective Span of Deck Slab, $l_{eff}$} & """ + _dkf(KEY_DD_SPAN, nd=0, scale=1000.0) + r""" mm (girder spacing, c/c) \\[6pt]
\hline
\textnormal{Deck Thickness, $t_s$} & """ + _render_value(bridge.input_dict, KEY_TS_DECK_THICKNESS) + r""" mm \\[6pt]
\hline
\textnormal{Clear Cover (IRC 112 Cl. 15.2)} & Top """ + _render_value(bridge.input_dict, KEY_DS_TOP_CLEAR_COVER) + r""" / Bottom """ + _render_value(bridge.input_dict, KEY_DS_BOTTOM_CLEAR_COVER) + r""" mm \\[6pt]
\hline
\textnormal{Concrete Grade (IRC 112 Cl. 6.4)} & """ + _render_value(bridge.input_dict, KEY_DECK_CONCRETE_GRADE_BASIC) + r""" ($f_{ck}$ = """ + _render_value(bridge.input_dict, KEY_MATERIAL_DECK_FCK) + r""" MPa, $f_{ctm}$ = """ + _render_value(bridge.input_dict, KEY_MATERIAL_DECK_FCTM) + r""" MPa) \\[6pt]
\hline
\textnormal{Reinforcement Grade (IRC 112 Cl. 6.2)} & """ + _render_value(bridge.input_dict, KEY_DS_REINF_MATERIAL) + r""" ($f_y$ = """ + _dkf(KEY_DD_FY, nd=0) + r""" MPa) \\[6pt]
\hline
\textnormal{Dead Load per Unit Area, $w_{DL}$} & """ + _dkf(KEY_DD_WDL, nd=2) + r""" kN/m² (slab self-weight) \\[6pt]
\hline
\textnormal{IRC 6 Wheel Load (Class A / 70R)} & """ + _dkf(KEY_DD_WHEEL_LOAD, nd=1) + r""" kN \\[6pt]
\hline
\textnormal{Tyre Contact Width (IRC 6 Annex~A)} & """ + _dkf(KEY_DD_TYRE_WIDTH, nd=0, scale=1000.0) + r""" mm (transverse) \\[6pt]
\hline
\textnormal{Impact Factor (IRC 6 Cl. 208.2)} & """ + _dkf(KEY_DD_IMPACT_FACTOR, nd=3) + r""" \\[6pt]
\hline
\textnormal{Governing Live Load Case} & """ + _dkf(KEY_DD_VEHICLE) + r""" \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|C{3.0cm}|C{3.5cm}|C{3.0cm}|>{\centering\arraybackslash}p{4.2cm}|C{1.8cm}|}
\caption{\textbf{Deck Slab --- Flexure Check: Interior Panel (Pigeaud's Method)}}
\hline
\textbf{Location} & \textbf{Parameter} & \textbf{Formula / Reference} & \textbf{Value} & \textbf{Status} \\[6pt]
\hline
\multirow{5}{*}{\makecell{At Midspan\\(Sagging)}} & Transverse BM (DL), $M_{T,DL}$ & $w_{DL}\,l_{eff}^2/10$ & """ + _dkf(KEY_DD_M_DL, nd=2) + r""" kN-m/m & --- \\[6pt]
\cline{2-5}
 & Transverse BM (LL), $M_{T,LL}$ & Effective width (IRC 112 B3.1) & """ + _dkf(KEY_DD_M_LL, nd=2) + r""" kN-m/m & --- \\[6pt]
\cline{2-5}
 & Total Design BM, $M_{u,sag}$ & """ + _dkf(KEY_DD_GAMMA_DL, nd=2) + r""" DL + """ + _dkf(KEY_DD_GAMMA_LL, nd=2) + r""" LL & """ + _dkf(KEY_DD_M_ULS_SAG, nd=2) + r""" kN-m/m & --- \\[6pt]
\cline{2-5}
 & Effective depth, $d$ & $t_s - c_{nom} - \phi/2$ & """ + _dkf(KEY_DD_D_BOT, nd=1) + r""" mm & --- \\[6pt]
\cline{2-5}
 & Moment Capacity, $M_{Rd}$ & IRC 112 Cl. 12.2 & """ + _dkf(KEY_DD_MU_BOT, nd=2) + r""" kN-m/m & """ + _dks(_dk_capacity_ok(KEY_DD_M_ULS_SAG, KEY_DD_MU_BOT)) + r""" \\[6pt]
\hline
\multirow{3}{*}{\makecell{At Support\\(Hogging)}} & Total Design BM, $M_{u,hog}$ & """ + _dkf(KEY_DD_GAMMA_DL, nd=2) + r""" DL + """ + _dkf(KEY_DD_GAMMA_LL, nd=2) + r""" LL (at support) & """ + _dkf(KEY_DD_M_ULS_HOG, nd=2) + r""" kN-m/m & --- \\[6pt]
\cline{2-5}
 & Required Top Steel, $A_{st,top}$ & $M_u / (0.87\,f_y\,d)$ & """ + _dkf(KEY_DD_AS_REQ_TOP, nd=0) + r""" mm²/m & --- \\[6pt]
\cline{2-5}
 & Moment Capacity, $M_{Rd}$ & IRC 112 Cl. 12.2 & """ + _dkf(KEY_DD_MU_TOP, nd=2) + r""" kN-m/m & """ + _dks(_dk_capacity_ok(KEY_DD_M_ULS_HOG, KEY_DD_MU_TOP)) + r""" \\[6pt]
\hline
\end{longtable}
\noindent\textit{Note: IRC 112 Cl. 12.2. Distribution (longitudinal) reinforcement designed for 20\% of main steel moment (IRC 21 Cl. 305.18).}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|C{3.5cm}|>{\centering\arraybackslash}p{4.5cm}|C{2cm}|}
\caption{\textbf{Deck Slab --- Cantilever Overhang Flexure Check}}
\hline
\textbf{Parameter} & \textbf{Formula} & \textbf{Value} & \textbf{Status} \\[6pt]
\hline
Overhang Length, $l_{oh}$ & --- & """ + _render_value(bridge.input_dict, KEY_TS_DECK_OVERHANG, " m") + r""" & --- \\[6pt]
\hline
Crash Barrier Load Moment & IRC 6 Cl. 206.4 & """ + _dkoh(KEY_DD_M_BARRIER, nd=2, unit=" kN-m/m") + r""" & --- \\[6pt]
\hline
Dead Load Moment & $w_{DL}\,l_{oh}^2/2$ + railing & """ + _dkoh(KEY_DD_M_DL_OH, nd=2, unit=" kN-m/m") + r""" & --- \\[6pt]
\hline
Live Load Moment (eccentric wheel) & Wheel load $\times$ arm & """ + _dkoh(KEY_DD_M_LL_OH, nd=2, unit=" kN-m/m") + r""" & --- \\[6pt]
\hline
Total Hogging Moment, $M_{u,oh}$ & """ + _dkf(KEY_DD_GAMMA_DL, nd=2) + r""" DL + """ + _dkf(KEY_DD_GAMMA_LL, nd=2) + r""" (LL + CB) & """ + _dkoh(KEY_DD_M_ULS_OH, nd=2, unit=" kN-m/m") + r""" & --- \\[6pt]
\hline
Moment Capacity (top steel), $M_{Rd,oh}$ & IRC 112 Cl. 12.2 & """ + _dkoh(KEY_DD_MU_OH, nd=2, unit=" kN-m/m") + r""" & """ + (_dks(_dk_capacity_ok(KEY_DD_M_ULS_OH, KEY_DD_MU_OH)) if _dk_oh else ("N/A" if _dk_has else "---")) + r""" \\[6pt]
\hline
\end{longtable}
\noindent\textit{Note: IRC 6 Cl. 206.4 crash barrier loads applied at kerb face; IRC 112 Cl. 12.2 flexure.}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|C{3.5cm}|>{\centering\arraybackslash}p{4.5cm}|C{2cm}|}
\caption{\textbf{Deck Slab --- Punching Shear Check (IRC~112 Cl.~10.4.6)}}
\hline
\textbf{Parameter} & \textbf{Formula / Reference} & \textbf{Value} & \textbf{Status} \\[6pt]
\hline
Design Wheel Load (ULS), $V_{Ed}$ & $\gamma_Q\,(1+IF)\,P_w$ & """ + _dkf(KEY_DD_PUNCH_VED_KN, nd=1) + r""" kN & --- \\[6pt]
\hline
Tyre Contact Area & $a \times b$ (IRC 6 Annex~A) & """ + _dkf(KEY_DD_TYRE_WIDTH, nd=0, scale=1000.0) + r""" $\times$ """ + _dkf(KEY_DD_TYRE_LENGTH, nd=0) + r""" mm & --- \\[6pt]
\hline
Loaded Area at mid-depth, $b_0$ & $c_1 \times c_2$ (incl.\ WC dispersion) & """ + _dkf(KEY_DD_PUNCH_C1, nd=0) + r""" $\times$ """ + _dkf(KEY_DD_PUNCH_C2, nd=0) + r""" mm & --- \\[6pt]
\hline
Control Perimeter, $u_1$ & $2(c_1+c_2) + 4\pi d$ & """ + _dkf(KEY_DD_PUNCH_U1, nd=0) + r""" mm & --- \\[6pt]
\hline
Punching Shear Stress, $v_{Ed}$ & $V_{Ed} / (u_1\,d)$ & """ + _dkf(KEY_DD_PUNCH_VED, nd=3) + r""" MPa & --- \\[6pt]
\hline
Punching Resistance, $v_{Rd,c}$ & IRC 112 Eq.\ 10.1 & """ + _dkf(KEY_DD_VRD_C_MPA, nd=3) + r""" MPa & --- \\[6pt]
\hline
Punching Shear Check & $v_{Ed} \leq v_{Rd,c}$ & """ + _dk_ratio(KEY_DD_PUNCH_VED, KEY_DD_VRD_C_MPA) + r""" & """ + _dks(deck_rpt.get(KEY_DD_PUNCH_OK)) + r""" \\[6pt]
\hline
\end{longtable}
\noindent\textit{Note: Punching shear reinforcement not typically required for deck slabs with $d \geq 200$ mm and adequate longitudinal reinforcement.}

\vspace{1em}
\clearpage
\begin{longtable}{|L{7cm}|>{\arraybackslash}p{8.5cm}|}
\caption{\textbf{Crack Width Check (Deck Slab)}}
\hline
\textbf{Parameter} & \textbf{Value / Reference} \\[6pt]
\hline
\textnormal{Min. Reinforcement for Crack Control, $A_{s,min}$} & """ + _dkf(KEY_DD_AS_MIN, nd=0) + r""" mm²/m [IRC 112 Cl. 16.5.1] \\[6pt]
\hline
\textnormal{Provided Reinforcement (bottom)} & $\phi$""" + _dkf(KEY_DD_DIA_BOT, nd=0) + r""" @ """ + _dkf(KEY_DD_SPC_BOT, nd=0) + r""" mm c/c (""" + _dkf(KEY_DD_AS_BOT, nd=0) + r""" mm²/m) \\[6pt]
\hline
\textnormal{Max. Permissible Crack Width} & """ + _dkf(KEY_DD_WK_LIMIT, nd=2) + r""" mm \\[6pt]
\hline
\textnormal{Calculated Crack Width, $w_k$ (governing)} & """ + _dk_gov_wk_str + r""" mm \\[6pt]
\hline
\textnormal{Crack Width Check} & """ + _dks(_dk_crack_ok) + r""" \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|C{3.5cm}|>{\centering\arraybackslash}p{4.5cm}|C{2cm}|}
\caption{\textbf{One-Way (Beam) Shear Check (Deck Slab)}}
\hline
\textbf{Parameter} & \textbf{Formula / Reference} & \textbf{Value} & \textbf{Status} \\[6pt]
\hline
Design Shear per unit width, $V_{Ed}$ & $\gamma_{DL} V_{DL} + \gamma_{LL}(1{+}IF)V_{LL}$ & """ + _dkf(KEY_DD_SHEAR_VED, nd=2) + r""" kN/m & --- \\[6pt]
\hline
Effective depth, $d$ & $t_s - c_{nom} - \phi/2$ & """ + _dkf(KEY_DD_D_BOT, nd=1) + r""" mm & --- \\[6pt]
\hline
Size factor, $k$ & $1 + \sqrt{200/d} \leq 2.0$ & """ + (f"{min(1.0 + (200.0 / _dkv(KEY_DD_D_BOT)) ** 0.5, 2.0):.3f}" if (_dk_has and _dkv(KEY_DD_D_BOT) > 0) else _DKPH) + r""" & --- \\[6pt]
\hline
Long.\ reinforcement ratio, $\rho_l$ & $A_{sl}/(b_w\,d) \leq 0.02$ & """ + (f"{min(_dkv(KEY_DD_AS_BOT) / (1000.0 * _dkv(KEY_DD_D_BOT)), 0.02):.4f}" if (_dk_has and _dkv(KEY_DD_D_BOT) > 0) else _DKPH) + r""" & --- \\[6pt]
\hline
Shear resistance (no stirrups), $V_{Rd,c}$ & $v_{Rd,c}\,b_w\,d$ (Cl.\ 10.3.2) & """ + _dkf(KEY_DD_SHEAR_VRDC, nd=2) + r""" kN/m & --- \\[6pt]
\hline
One-Way Shear Check & $V_{Ed} \leq V_{Rd,c}$ & """ + _dk_ratio(KEY_DD_SHEAR_VED, KEY_DD_SHEAR_VRDC) + r""" & """ + _dks(deck_rpt.get(KEY_DD_SHEAR_OK)) + r""" \\[6pt]
\hline
\end{longtable}
\noindent\textit{Note: IRC 112 Cl. 10.3.2. Shear reinforcement not provided in deck slabs; capacity relies on concrete and main reinforcement.}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|>{\centering\arraybackslash}p{4.1cm}|>{\centering\arraybackslash}p{4.1cm}|C{1.8cm}|}
\caption{\textbf{Reinforcement Detailing Summary (Deck Slab)}}
\hline
\textbf{Parameter} & \textbf{Required / Limit} & \textbf{Provided} & \textbf{Status} \\[6pt]
\hline
\multicolumn{4}{|l|}{\textbf{Main Reinforcement --- Bottom (Transverse)}} \\[6pt]
\hline
Required Area, $A_{st,req}$ (mm²/m) & """ + _dkf(KEY_DD_AS_REQ_BOT, nd=0) + r""" mm²/m & """ + _dkf(KEY_DD_AS_BOT, nd=0) + r""" mm²/m & """ + _dks(_dk_capacity_ok(KEY_DD_AS_REQ_BOT, KEY_DD_AS_BOT)) + r""" \\[6pt]
\hline
Bar Diameter $\times$ Spacing & $\phi \geq 10$ mm (IRC 112) & $\phi$""" + _dkf(KEY_DD_DIA_BOT, nd=0) + r""" @ """ + _dkf(KEY_DD_SPC_BOT, nd=0) + r""" mm c/c & --- \\[6pt]
\hline
Min.\ Reinforcement $A_{s,min}$ (IRC 112 Cl. 16.3.1) & """ + _dkf(KEY_DD_AS_MIN, nd=0) + r""" mm²/m & """ + _dkf(KEY_DD_AS_BOT, nd=0) + r""" mm²/m & """ + _dks(_dk_capacity_ok(KEY_DD_AS_MIN, KEY_DD_AS_BOT)) + r""" \\[6pt]
\hline
Max.\ Bar Spacing (IRC 112 Cl. 16.3.2) & """ + _dkf(KEY_DD_SPACING_MAX, nd=0) + r""" mm & """ + _dkf(KEY_DD_SPC_BOT, nd=0) + r""" mm & """ + _dks(_dk_spacing_ok()) + r""" \\[6pt]
\hline
\multicolumn{4}{|l|}{\textbf{Distribution Reinforcement --- Longitudinal}} \\[6pt]
\hline
Required Area, $A_{st,dist}$ (mm²/m) & $\geq 20\%$ of main steel & """ + _dkf(KEY_DD_AS_LONG, nd=0) + r""" mm²/m & """ + _dks(_dk_distribution_ok()) + r""" \\[6pt]
\hline
\multicolumn{4}{|l|}{\textbf{Top Reinforcement (Support / Cantilever Overhang)}} \\[6pt]
\hline
Required Area, $A_{st,top}$ (mm²/m) & """ + _dkf(KEY_DD_AS_REQ_TOP, nd=0) + r""" mm²/m & """ + _dkf(KEY_DD_AS_TOP, nd=0) + r""" mm²/m & """ + _dks(_dk_capacity_ok(KEY_DD_AS_REQ_TOP, KEY_DD_AS_TOP)) + r""" \\[6pt]
\hline
\multicolumn{4}{|l|}{\textbf{Cover and Detailing}} \\[6pt]
\hline
Clear Cover (IRC 112 Cl. 15.2) & $\geq$ """ + _dkf(KEY_DD_MIN_COVER, nd=0) + r""" mm (Table 14.2) & Top """ + _render_value(bridge.input_dict, KEY_DS_TOP_CLEAR_COVER) + r""" / Bottom """ + _render_value(bridge.input_dict, KEY_DS_BOTTOM_CLEAR_COVER) + r""" mm & """ + _dks(deck_rpt.get(KEY_DD_COVER_OK)) + r""" \\[6pt]
\hline
\end{longtable}
\noindent\textit{Note: IRC 112 Cl. 16.3, IS 456 Cl. 26.5. Refer to the individual strength and detailing check statuses above.}

% ===========================
\section{Cross Bracing Design}
\label{sec:cross-bracing}
% ===========================

Cross bracing between adjacent plate girders provides lateral stability during construction, resists transverse loads (wind, seismic, braking) in service, and prevents lateral torsional buckling of the girders. Members are designed per IS~800:2007 Cl.~7 (compression) and Cl.~6 (tension). Forces are derived from the grillage model under the governing load combination  (DL + LL + WL).

\vspace{1em}

\vspace{0.4em}
\noindent
\setlength{\tabcolsep}{4pt}
\setlength\LTleft{0pt}
\setlength\LTright{\fill}

\begin{longtable}{|C{2.0cm}|L{2.0cm}|L{2.2cm}|C{2.5cm}|C{2.0cm}|C{2.0cm}|}
\caption{\textbf{Cross Bracing --- Connection and Section Properties}}
\hline
\textbf{Panel} & \textbf{Member} & \textbf{Connection} & \textbf{Section} & \textbf{$A_g$ (mm²)} & \textbf{$r_{min}$ (mm)} \\[6pt]
\hline
""" + cb_forces_content + r"""
\end{longtable}
\noindent\textit{Note: $A_g$ = gross cross-sectional area; $r_{min}$ = minimum radius of gyration.}

\vspace{1em}
\begin{longtable}{|C{2.2cm}|L{2.2cm}|L{2.5cm}|C{2.5cm}|C{2.5cm}|>{\centering\arraybackslash}p{3.6cm}|}
\caption{\textbf{Cross Bracing --- Slenderness Ratio Check (IS~800 Cl.~3.8 )}}
\hline
\textbf{Panel} & \textbf{Member} & \textbf{Nature} & \textbf{Eff.\ Length $KL$ (mm)} & \textbf{$KL/r$} & \textbf{Limit / Status} \\[6pt]
\hline
""" + cb_slenderness_content + r"""
\end{longtable}
\noindent\textit{Note:  3. Limit = 250 for compression members, 400 for tension members. $K = 1.0$ for members with both ends pinned.}

\vspace{1em}
\begin{longtable}{|C{2.0cm}|L{1.8cm}|C{2.2cm}|C{3.0cm}|C{1.8cm}|C{1.8cm}|C{1.2cm}|C{1.8cm}|}
\caption{\textbf{Cross Bracing Design --- Capacity Summary}}
\hline
\textbf{Panel} & \textbf{Member} & \textbf{Section} & \textbf{Governing LC} & \textbf{Demand (kN)} & \textbf{Capacity (kN)} & \textbf{UR} & \textbf{Status} \\[6pt]
\hline
""" + cb_capacity_content + r"""
\end{longtable}
\noindent\textit{Note: Designed per IS 800 Cl. 7 (compression) and Cl. 6 (tension). OsdagBridge cross-bracing module used.}

% ===========================
\section{End Diaphragm Design}
\label{sec:end-diaphragm}
% ===========================

End diaphragms at the supports transfer transverse loads to the bearings, restrain the bottom flanges against lateral displacement, and maintain the girder cross-section geometry during construction and in service. They are designed per IS~800:2007 and IRC~24:2010 Cl.~507.

\vspace{1em}

\vspace{0.4em}
\noindent
\setlength{\tabcolsep}{4pt}
\setlength{\LTleft}{0pt}
\setlength{\LTright}{\fill}

\begin{longtable}{|C{2.0cm}|L{2.0cm}|L{2.2cm}|C{2.5cm}|C{2.0cm}|C{2.0cm}|}
\caption{\textbf{End Diaphragm --- Connection and Section Properties}}
\hline
\textbf{Panel} & \textbf{Member} & \textbf{Connection} & \textbf{Section} & \textbf{$A_g$ (mm²)} & \textbf{$r_{min}$ (mm)} \\[6pt]
\hline
""" + ed_forces_content + r"""
\end{longtable}
\noindent\textit{Note: $A_g$ = gross cross-sectional area; $r_{min}$ = minimum radius of gyration.}

\vspace{1em}
\begin{longtable}{|C{2.2cm}|L{2.2cm}|L{2.5cm}|C{2.5cm}|C{2.5cm}|>{\centering\arraybackslash}p{3.6cm}|}
\caption{\textbf{End Diaphragm --- Slenderness Ratio Check (IS~800 Cl.~3.8 )}}
\hline
\textbf{Panel} & \textbf{Member} & \textbf{Nature} & \textbf{Eff.\ Length $KL$ (mm)} & \textbf{$KL/r$} & \textbf{Limit / Status} \\[6pt]
\hline
""" + ed_slenderness_content + r"""
\end{longtable}
\noindent\textit{Note:  3. Limit = 250 for compression members, 400 for tension members. $K = 1.0$ for members with both ends pinned.}

\vspace{1em}

\begin{longtable}{|C{2.0cm}|L{1.8cm}|C{2.2cm}|C{3.0cm}|C{1.8cm}|C{1.8cm}|C{1.2cm}|C{1.8cm}|}
\caption{\textbf{End Diaphragm Design --- Capacity Summary}}
\hline
\textbf{Panel} & \textbf{Member} & \textbf{Section} & \textbf{Governing LC} & \textbf{Demand (kN)} & \textbf{Capacity (kN)} & \textbf{UR} & \textbf{Status} \\[6pt]
\hline
""" + ed_capacity_content + r"""
\end{longtable}
\noindent\textit{Note: Designed per IS 800 Cl. 7 (compression) and Cl. 6 (tension). OsdagBridge cross-bracing module used.}

% ===========================
\section{Overall Design Check Summary}
\label{sec:overall-summary}
% ===========================

""" + chart_figure(chart_paths, "utilization", "Utilization ratios from existing design results. The dashed line marks UR = 1.0; N/A means no valid result was supplied. Girder and bracing bars show the highest available check ratio for each member. Refer to individual checks for code-specific warning bands.") + r"""

\vspace{1em}
\begin{longtable}{|C{3.4cm}|L{4.5cm}|C{2.3cm}|C{2.3cm}|>{\centering\arraybackslash}p{1.6cm}|}
\caption{\textbf{Overall Design Check Summary --- All Members}}
\hline
\textbf{Member / Check} & \textbf{Governing Load Combo} & \textbf{Demand} & \textbf{Capacity} & \textbf{UR} \\[6pt]
\hline
""" + t522_content + r"""
\end{longtable}
\noindent\textit{Note: UR = Demand / Capacity. The unity line is a visual reference; supplied backend statuses retain the code-specific acceptance rules. The governing check for each component is highlighted in the individual design check sections above.}

"""

    return chapter
