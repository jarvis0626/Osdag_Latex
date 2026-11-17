"""Text escaping checks that prevent user text from becoming LaTeX commands."""

import pytest

from osdagbridge.core.reports.report_utils import _render_value, _tex


@pytest.mark.parametrize("value,expected", [
    (None, ""),
    (0, "0"),
    ("A & B 50%", r"A \& B 50\%"),
    ("#1 ${x}", r"\#1 \$\{x\}"),
    (r"a\b", r"a\textbackslash{}b"),
    (r"\input{secrets}", r"\textbackslash{}input\{secrets\}"),
    ("a_b", r"a\_\allowbreak{}b"),
    ("~^", r"\textasciitilde{}\textasciicircum{}"),
    ("∠ 100 × 100 ⅹ 10", r"L 100 \ensuremath{\times} 100 x 10"),
])
def test_tex_escapes_original_characters_once(value, expected):
    assert _tex(value) == expected


def test_render_value_keeps_trusted_units_outside_plain_text_escaping():
    assert _render_value({"load": "5 & 6"}, "load", r" kN/m\textsuperscript{2}") == r"5 \& 6 kN/m\textsuperscript{2}"
    assert _render_value({"load": 0}, "load", " kN") == "0 kN"
    assert _render_value({}, "load", " kN") == "N/A"
