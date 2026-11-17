import math
import unicodedata

from osdagbridge.core.utils.common import (
    KEY_MP_GD_MEMBER_ID,
    KEY_MP_GD_SELECT_GIRDER,
    KEY_MP_GIRDER_DEPTH,
    KEY_TS_NO_OF_GIRDERS
)


def _tex(value):
    """Escape plain text once, without escaping commands inserted by this function.

    Common engineering glyphs are normalized for pdfLaTeX; trusted report
    formulas must be passed separately, never through this plain-text function.
    """
    text = unicodedata.normalize("NFC", '' if value is None else str(value))
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%",
        "$": r"\$", "#": r"\#", "{": r"\{", "}": r"\}",
        "_": r"\_\allowbreak{}", "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}", ":": r":\allowbreak{}",
        "\u2220": "L", "\u2179": "x", "\u00d7": r"\ensuremath{\times}",
        "\u00b2": r"\textsuperscript{2}", "\u00b3": r"\textsuperscript{3}",
        "\u2013": "--", "\u2014": "---", "\u2212": "-", "\u2019": "'", "\u2018": "'",
        "\u201c": "``", "\u201d": "''", "\u2264": r"\ensuremath{\leq}",
        "\u2265": r"\ensuremath{\geq}", "\u00b0": r"\ensuremath{^\circ}",
    }
    greek = {
        0x03b1: "alpha", 0x03b2: "beta", 0x03b3: "gamma", 0x03b4: "delta",
        0x03b5: "epsilon", 0x03b6: "zeta", 0x03b7: "eta", 0x03b8: "theta",
        0x03b9: "iota", 0x03ba: "kappa", 0x03bb: "lambda", 0x03bc: "mu",
        0x03bd: "nu", 0x03be: "xi", 0x03c0: "pi", 0x03c1: "rho",
        0x03c2: "varsigma", 0x03c3: "sigma", 0x03c4: "tau", 0x03c5: "upsilon",
        0x03c6: "phi", 0x03c7: "chi", 0x03c8: "psi", 0x03c9: "omega",
        0x0393: "Gamma", 0x0394: "Delta", 0x0398: "Theta", 0x039b: "Lambda",
        0x039e: "Xi", 0x03a0: "Pi", 0x03a3: "Sigma", 0x03a5: "Upsilon",
        0x03a6: "Phi", 0x03a8: "Psi", 0x03a9: "Omega", 0x03d5: "varphi",
    }
    replacements.update({chr(code): "\\ensuremath{\\" + name + "}" for code, name in greek.items()})
    replacements["\u00b5"] = r"\ensuremath{\mu}"
    replacements["\u2103"] = r"\ensuremath{^\circ}C"
    return ''.join(replacements.get(character, character) for character in text)


def extract_result_summary(result):
    """Read upstream Osdag result aliases without importing its analysis solver.

    This mirrors results_data._extract_osdag_summary's field mapping; it does
    not calculate capacities or change any numerical result.
    """
    if not isinstance(result, dict) or not result:
        return {}

    def first(*names):
        return next((result[name] for name in names if result.get(name) is not None), None)

    return {
        "section": first("section_size.designation", "Optimum.Designation"),
        "capacity_kN": first("Member.tension_capacity", "Design.Strength"),
        "efficiency": first("Member.efficiency", "Optimum.UR"),
        "slenderness": result.get("Member.Slenderness"),
        "connection": "Welded" if "Weld.Type" in result else "Bolted",
    }


def _render_value(source_dict, key, unit=""):
    val = source_dict.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        return "N/A"
    if isinstance(val, str) and val.strip().lower() in {"nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity", "n.a."}:
        return "N/A"
    if isinstance(val, (float, int)) and not isinstance(val, bool) and not math.isfinite(val):
        return "N/A"
    return _tex(val) + unit


def get_girder_entries(input_dict):
    """
    Retrieve all girder labels and member IDs from backend keys.

    Usage Example:
    --------------------------
    girder_entries = get_girder_entries(bridge.input_dict)
    
    # 1. Fallback handling (if backend hasn't populated keys yet)
    if not girder_entries:
        n = int(bridge.input_dict.get(KEY_TS_NO_OF_GIRDERS, 1))
        girder_entries = [(f"Girder {i}", f"M1") for i in range(1, n + 1)]
        
    # 2. Get total number of girders safely
    n_girders = len(girder_entries)
    
    # 3. Iterate over the girders to build table rows
    for lbl, mid in girder_entries:
        # lbl will be e.g., "G1", mid will be e.g., "G1M1"
        # Access girder specific keys dynamically:
        # val = input_dict.get(f"{KEY_MP_GIRDER_DEPTH}.{lbl}.{mid}")
        pass

    Returns:
        List[Tuple[str, str]]
    """
    try:
        number = float(input_dict.get(KEY_TS_NO_OF_GIRDERS) or 0)
        if not math.isfinite(number) or number < 0 or not number.is_integer():
            return []
        n = int(number)
    except (TypeError, ValueError, OverflowError):
        return []

    entries = []

    for i in range(1, n + 1):
        entries.append(
            (
                input_dict.get(f"{KEY_MP_GD_SELECT_GIRDER}.G{i}", ""),
                input_dict.get(f"{KEY_MP_GD_MEMBER_ID}.G{i}.M1", ""),
            )
        )

    return entries


def _fig_or_placeholder(path, caption, width=r'0.9\textwidth'):
    """Embed figure if path is provided (file already copied to assets), else show placeholder box.
    path is the relative path as pdflatex will see it (e.g. 'assets/plan.png').
    """
    if path:
        p = path.replace('\\', '/')
        return (r'\begin{figure}[H]' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[width=' + width + ']{' + p + '}\n'
                r'\caption*{' + caption + '}\n'
                r'\end{figure}')
    return (r'\noindent\textit{Unavailable: ' + _tex(caption)
            + r'. No drawing was supplied.}\par' + '\n')


def _fig_embed(path, caption, width=r'\textwidth', height=None):
    """Embed a real figure when path is provided (already copied); otherwise use an fbox placeholder."""
    if path:
        p = path.replace('\\', '/')
        opts = 'width=' + width
        if height:
            opts += ',height=' + height + ',keepaspectratio'
        return (r'\begin{figure}[H]' + '\n'
                r'\vspace{-0.5em}' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[' + opts + ']{' + p + '}\n'
                r'\vspace{0.5em}' + '\n'
                r'\caption*{\small ' + caption + '}\n'
                r'\vspace{-0.5em}' + '\n'
                r'\end{figure}')
    return (r'\noindent\textit{Unavailable: ' + _tex(caption)
            + r'. No drawing was supplied.}\par' + '\n')
