"""Behavioral tests for table pagination and shared layout rules."""

import re

import pytest

from osdagbridge.core.reports.styles import STYLE, _fit_columns, format_chapter, style_preamble


def test_continuation_repeats_column_labels_but_never_data_or_caption():
    source = (r"\begin{longtable}{|L{6cm}|p{12cm}|}"
              r"\caption{A {nested} title}\hline"
              r"\textbf{Demand} & \textbf{Capacity} \\\hline"
              r"12.34 & 45.67 \\\hline\end{longtable}")
    result = format_chapter(source)
    assert result.count(r"\textbf{Demand}") == 2
    assert result.count(r"\textbf{Capacity}") == 2
    assert result.count("12.34 & 45.67") == 1
    assert result.count(r"\caption{A {nested} title}") == 1
    assert r"\caption{A {nested} title}\\" in result
    assert result.count(r"\endfirsthead") == result.count(r"\endhead") == 1


def test_key_value_table_gets_real_labels_instead_of_repeated_project_data():
    result = format_chapter(r"\begin{tabular}{|L{5cm}|L{9cm}|}\hline"
                            r"\textbf{Project} & Bridge One \\\hline"
                            r"\textbf{Designer} & Ada \\\hline\end{tabular}")
    assert result.count(r"\textbf{Parameter}") == 2
    assert result.count(r"\textbf{Value}") == 2
    assert result.count("Bridge One") == result.count("Ada") == 1
    assert r"\begin{tabular}" not in result


def test_float_caption_and_label_move_inside_breakable_table():
    result = format_chapter(r"\begin{table}[H]\caption{Location}\label{tab:location}"
                            r"\begin{tabular}{|L{5cm}|L{9cm}|}\hline"
                            r"\textbf{Parameter} & \textbf{Value}\\\hline"
                            r"City & Mumbai\\\hline\end{tabular}\end{table}")
    assert r"\begin{table}" not in result
    assert result.index(r"\begin{longtable}") < result.index(r"\caption{Location}")
    assert r"\caption{Location}\label{tab:location}\\" in result
    assert result.count("Mumbai") == 1


def test_existing_multiline_header_is_preserved_without_a_second_header_set():
    header = r"\hline\textbf{Load} & \textbf{Moment}\\\hline"
    source = (r"\begin{longtable}{|L{4cm}|p{9cm}|}" + header
              + r"\endfirsthead" + header + r"\endhead"
              + r"Case 1 & 10.00\\\hline\end{longtable}")
    result = format_chapter(source)
    assert result.count(r"\textbf{Moment}") == 2
    assert result.count(r"\endhead") == 1
    assert result.count("Case 1") == 1


def test_empty_legacy_continuation_head_is_repaired():
    result = format_chapter(r"\begin{longtable}{|L{4cm}|p{9cm}|}\hline"
                            r"\textbf{Girder} & \textbf{Restraint}\\\hline"
                            r"\endfirsthead\endhead G4 & Fixed\\\hline\end{longtable}")
    continuation = result.split(r"\endfirsthead")[1].split(r"\endhead")[0]
    assert r"\textbf{Girder}" in continuation
    assert r"\textbf{Restraint}" in continuation
    assert "G4" not in continuation


def test_escaped_ampersand_in_a_heading_is_not_a_column_separator():
    result = format_chapter(r"\begin{longtable}{|L{4cm}|p{9cm}|}\hline"
                            r"\textbf{Demand \& Capacity} & \textbf{Ratio}\\\hline"
                            r"100 / 200 & 0.5\\\hline\end{longtable}")
    assert result.count(r"\textbf{Demand \& Capacity}") == 2
    assert result.count("100 / 200") == 1


def test_body_multirow_labels_repeat_per_row_so_page_breaks_cannot_strand_them():
    result = format_chapter(r"\begin{longtable}{|L{3cm}|p{9cm}|}\hline"
                            r"\textbf{Girder} & \textbf{Check}\\\hline"
                            r"\multirow{3}{*}{\makecell{G4}} & Depth\\[6pt]\cline{2-2}"
                            r" & Width\\[6pt]\cline{2-2}"
                            r" & Thickness\\[6pt]\hline\end{longtable}")
    body = result.split(r"\endhead", 1)[1]
    assert r"\multirow" not in body
    assert body.count(r"\makecell{G4}") == 3
    assert result.count("Depth") == result.count("Width") == result.count("Thickness") == 1
    assert r"\cline{2-2}" not in body


def test_body_label_expansion_preserves_nested_linebreaks_and_heading_multirows():
    header = (r"\hline\multirow{2}{*}{\makecell{Load\\Case}} & \textbf{Value}\\"
              r" & \textbf{Units}\\\hline")
    result = format_chapter(r"\begin{longtable}{|L{3cm}|p{9cm}|}" + header
                            + r"\endfirsthead" + header + r"\endhead"
                            + r"\multirow{2}{*}{\makecell{At Midspan\\(Sagging)}} & 123.45\\\cline{2-2}"
                            + r" & 678.90\\\hline\end{longtable}")
    heading, body = result.split(r"\endhead", 1)
    assert heading.count(r"\multirow{2}{*}{\makecell{Load\\Case}}") == 2
    assert body.count(r"\makecell{At Midspan\\(Sagging)}") == 2
    assert body.count("123.45") == body.count("678.90") == 1


@pytest.mark.parametrize("spec", ["|L{8cm}|p{14cm}|", "|c|c|p{13cm}|",
                                     "|>{\\centering\\arraybackslash}p{4cm}|C{9cm}|L{5cm}|"])
def test_width_includes_padding_and_rules_and_stays_inside_margins(spec):
    fitted, columns = _fit_columns(spec)
    widths = [float(value) for value in re.findall(r"\{([\d.]+)cm\}", fitted)]
    reserved = (2 * columns * STYLE.table_padding_pt + spec.count("|") * STYLE.rule_width_pt) * 2.54 / 72.27
    assert sum(widths) + reserved <= STYLE.text_width_cm


def test_style_reserves_header_and_footer_space_without_negative_offsets():
    source = style_preamble()
    assert "includeheadfoot" in source
    assert f"headheight={STYLE.head_height_pt}pt" in source
    assert f"footskip={STYLE.foot_skip_pt}pt" in source
    assert r"\vspace{-" not in source
    assert STYLE.green.lstrip("#") in source


def test_style_changes_only_formatting_of_equations_and_values():
    body = r"$V_{Ed} \leq V_{Rd,c}$ & 123.456 \\[6pt]\hline"
    result = format_chapter(r"\begin{longtable}{|L{4cm}|L{8cm}|}\hline"
                            r"\textbf{Check} & \textbf{Value}\\\hline" + body + r"\end{longtable}")
    assert r"$V_{Ed} \leq V_{Rd,c}$ & 123.456" in result
    assert r"\\[\ReportRowGap]" in result


def test_malformed_table_fails_with_a_useful_error():
    with pytest.raises(ValueError, match="Unclosed report table"):
        format_chapter(r"\begin{longtable}{|L{4cm}|L{8cm}|}\hline")
