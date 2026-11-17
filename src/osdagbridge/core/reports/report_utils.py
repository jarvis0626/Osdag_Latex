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
    text = '' if value is None else str(value)
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
    if val in ("", None):
        return ""
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
    n = int(input_dict.get(KEY_TS_NO_OF_GIRDERS, 0))

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
    return (r'\begin{figure}[H]' + '\n'
            r'\centering' + '\n'
            r'\fbox{\parbox{0.97\textwidth}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
            r'}}' + '\n'
            r'\caption*{' + caption + '}\n'
            r'\end{figure}')

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
    # fbox placeholder — matches template exactly
    return (r'\noindent\fbox{\parbox{0.97\textwidth}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
            r'}}')


