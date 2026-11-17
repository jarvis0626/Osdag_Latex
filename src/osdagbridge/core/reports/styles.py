"""Report presentation rules shared by every chapter.

The existing chapter renderers deliberately remain pure string renderers.  The
``styled_chapter`` boundary applies one table policy to those legacy templates:
tables can break across pages, repeat their column headings, and fit the body
width after accounting for cell padding and vertical rules.  Engineering values
and equations are never interpreted or changed here.
"""

from dataclasses import dataclass
from functools import wraps
import re


@dataclass(frozen=True)
class ReportStyle:
    page_width_cm: float = 21.0
    side_margin_cm: float = 2.0
    top_margin_cm: float = 2.0
    bottom_margin_cm: float = 2.0
    head_height_pt: float = 30.0
    foot_skip_pt: float = 32.0
    table_padding_pt: float = 3.0
    rule_width_pt: float = 0.4
    row_height: float = 1.18
    row_gap_pt: float = 3.0
    green: str = "#91B014"
    failure_color: str = "#B33724"
    warning_color: str = "#1D5B8F"
    text_color: str = "#263238"
    chart_font_family: str = "DejaVu Sans"
    chart_missing_color: str = "#8A959B"
    chart_grid_color: str = "#DCE2E4"
    chart_dpi: int = 150
    chart_font_size: int = 9
    chart_width_inches: float = 10.4
    chart_panel_height_inches: float = 4.2
    chart_width_fraction: float = 0.98

    @property
    def text_width_cm(self):
        return self.page_width_cm - 2 * self.side_margin_cm


STYLE = ReportStyle()


def style_preamble():
    """Return the shared LaTeX style after packages and metadata macros.

    The orchestrator supplies ``reportProject``, ``reportJob``, ``reportDate`` and
    ``reportVersion`` as already-escaped text, and loads the packages used here.
    ``includeheadfoot`` reserves real space for both boxes; no negative footer
    offsets or artificial changes to page contents are needed.
    """
    return r"""
% All presentation settings originate in reports/styles.py.
\geometry{a4paper,left=SIDEcm,right=SIDEcm,top=TOPcm,bottom=BOTTOMcm,
  includeheadfoot,headheight=HEADpt,headsep=10pt,footskip=FOOTpt}
\definecolor{osdagGreen}{HTML}{GREEN}
\definecolor{reportFail}{HTML}{FAIL}
\definecolor{reportWarning}{HTML}{WARNING}
\definecolor{reportText}{HTML}{TEXT}
\color{reportText}
\setstretch{1.12}
\setlength{\parindent}{0pt}
\setlength{\emergencystretch}{2em}
\captionsetup{labelfont=bf,justification=raggedright,singlelinecheck=false,
  format=plain,font=small,skip=5pt}
\newcommand{\ReportCaptionSetup}{%
  \setlength{\abovecaptionskip}{5pt}\setlength{\belowcaptionskip}{5pt}}
\newcommand{\ReportTableSetup}{%
  \setlength{\tabcolsep}{PADpt}%
  \renewcommand{\arraystretch}{STRETCH}%
  \setlength{\arrayrulewidth}{RULEpt}\setlength{\extrarowheight}{0.5pt}%
  \setlength{\LTleft}{\fill}\setlength{\LTright}{\fill}%
  \setlength{\LTpre}{4pt}\setlength{\LTpost}{8pt}}
\newcommand{\ReportTableFont}{\small}
\newcommand{\ReportSmallText}{\footnotesize}
\newcommand{\ReportExecutiveTitle}{\centering\Large\bfseries}
\newcommand{\ReportRowGap}{ROWGAPpt}
\newcommand{\ReportTableGap}{\vspace{0.5em}}
\newcommand{\ReportSectionGap}{\vspace{0.8em}}
\newcommand{\ReportCellGap}{\vspace{3pt}}
\newcommand{\ReportChapterFormat}{%
  \titleformat{\chapter}[block]{\normalfont\Large\bfseries\centering}%
    {\thechapter}{1em}{}%
  \titlespacing*{\chapter}{0pt}{0pt}{10pt}}
\ReportChapterFormat
\BeforeBeginEnvironment{longtable}{\Needspace{6\baselineskip}}
\newcommand{\ReportPageFurniture}{%
  \fancyhf{}%
  \fancyhead[L]{\parbox[b]{0.48\headwidth}{\scriptsize\raggedright\reportProject\ $|$ \reportJob}}%
  \fancyhead[R]{\parbox[b]{0.48\headwidth}{\scriptsize\raggedleft\reportDate\ $|$ \reportVersion}}%
  \fancyfoot[L]{\scriptsize Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}%
  \fancyfoot[R]{\scriptsize Page \thepage\ of \pageref{LastPage}}%
  \renewcommand{\headrulewidth}{0.6pt}%
  \renewcommand{\footrulewidth}{0.6pt}%
  \renewcommand{\headrule}{\hbox to\headwidth{\color{osdagGreen}\leaders\hrule height 0.6pt\hfill}}%
  \renewcommand{\footrule}{\hbox to\headwidth{\color{osdagGreen}\leaders\hrule height 0.6pt\hfill}}}
\fancypagestyle{main}{\ReportPageFurniture}
\fancypagestyle{plain}{\ReportPageFurniture}
\fancypagestyle{firstpage}{\ReportPageFurniture\fancyhead{}\renewcommand{\headrulewidth}{0pt}}
\pagestyle{main}
\setcounter{tocdepth}{2}
\titlecontents{chapter}[1.5em]{\normalfont\vspace{2pt}}{\contentslabel{1.5em}}{\hspace*{-1.5em}}{\hfill\contentspage}
\titlecontents{section}[3.8em]{\normalfont}{\contentslabel{2.3em}}{\hspace*{-2.3em}}{\hfill\contentspage}
\titlecontents{subsection}[7em]{\normalfont}{\contentslabel{3.2em}}{\hspace*{-3.2em}}{\hfill\contentspage}
\renewcommand{\contentsname}{\centering\Large\bfseries Table of Contents}
""".replace("SIDE", str(STYLE.side_margin_cm)).replace("TOP", str(STYLE.top_margin_cm)).replace(
        "BOTTOM", str(STYLE.bottom_margin_cm)
    ).replace("HEAD", str(STYLE.head_height_pt)).replace("FOOT", str(STYLE.foot_skip_pt)).replace(
        "GREEN", STYLE.green.lstrip("#")
    ).replace("FAIL", STYLE.failure_color.lstrip("#")).replace(
        "WARNING", STYLE.warning_color.lstrip("#")
    ).replace("TEXT", STYLE.text_color.lstrip("#")).replace("PAD", str(STYLE.table_padding_pt)).replace(
        "STRETCH", str(STYLE.row_height)
    ).replace("RULE", str(STYLE.rule_width_pt)).replace("ROWGAP", str(STYLE.row_gap_pt))


def _group_end(text, start):
    """Return the position after a balanced TeX group, respecting escaped braces."""
    if start >= len(text) or text[start] != "{":
        raise ValueError("Expected a LaTeX group")
    depth = 0
    position = start
    while position < len(text):
        char = text[position]
        if char == "\\":
            position += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return position + 1
        position += 1
    raise ValueError("Unclosed LaTeX group")


def _fit_columns(spec):
    """Scale fixed widths proportionally, reserving padding and rule space.

    Unlike a resizebox this preserves normal text size and permits page breaks.
    Legacy l/c/r columns become paragraph columns so their content wraps too.
    """
    columns = []
    position = 0
    while position < len(spec):
        char = spec[position]
        if char in "><@!" and position + 1 < len(spec) and spec[position + 1] == "{":
            position = _group_end(spec, position + 1)
            continue
        if char in "LCRpmb" and position + 1 < len(spec) and spec[position + 1] == "{":
            end = _group_end(spec, position + 1)
            dimension = spec[position + 2:end - 1]
            match = re.fullmatch(r"\s*([\d.]+)\s*(cm|mm|pt|in)\s*", dimension)
            if match:
                value, unit = match.groups()
                cm = float(value) * {"cm": 1, "mm": .1, "pt": 2.54 / 72.27, "in": 2.54}[unit]
                columns.append((position, end, char, cm))
            position = end
            continue
        if char in "lcr":
            columns.append((position, position + 1, char.upper(), 2.0))
        position += 1
    if not columns:
        return spec, 0
    # TeX points use 72.27pt/in; each column has padding on both sides.
    reserved = (2 * len(columns) * STYLE.table_padding_pt + spec.count("|") * STYLE.rule_width_pt) * 2.54 / 72.27
    available = STYLE.text_width_cm - reserved - .05
    if available <= 0:
        raise ValueError("Table has too many columns for the configured page width")
    total = sum(column[3] for column in columns)
    scale = min(1.0, available / total)
    for start, end, kind, cm in reversed(columns):
        spec = spec[:start] + kind + "{" + f"{cm * scale:.4f}" + "cm}" + spec[end:]
    return spec, len(columns)


def _caption_rows(body):
    """Terminate longtable captions as rows; caption text can contain nested groups."""
    cursor = 0
    while True:
        match = re.search(r"\\caption(?:\[[^\]]*\])?\{", body[cursor:])
        if not match:
            return body
        start = cursor + match.end() - 1
        end = _group_end(body, start)
        # A label belongs to the caption row, before its terminating line break.
        tail = end
        while True:
            following = re.match(r"\s*\\label\{", body[tail:])
            if not following:
                break
            tail = _group_end(body, tail + following.end() - 1)
        next_token = tail + len(body[tail:]) - len(body[tail:].lstrip())
        if not body.startswith(r"\\", next_token):
            body = body[:tail] + r"\\" + body[tail:]
            tail += 2
        cursor = tail


def _repeat_header(body, columns):
    body = _caption_rows(body)
    first = body.find(r"\hline")
    if first < 0:
        raise ValueError("Report table is missing its top rule")
    second = body.find(r"\hline", first + len(r"\hline"))
    if second < 0:
        raise ValueError("Report table is missing its heading rule")
    header_end = second + len(r"\hline")
    prefix, header = body[:first], body[first:header_end]
    rest = body[header_end:]
    if r"\endfirsthead" in body:
        before, after = body.split(r"\endfirsthead", 1)
        if r"\endhead" in after:
            repeated, tail = after.split(r"\endhead", 1)
            if repeated.strip():
                return body  # A pre-existing multi-row heading is authoritative.
            # The old girder-restraint table declared an empty continuation head.
            return before + "\n\\endfirsthead\n" + header + "\n\\endhead\n" + tail
    # Key/value tables have no column headings in the original templates. Add
    # headings rather than incorrectly repeating the first project's data row.
    # Ampersands inside a command group or escaped as text are not cell breaks.
    heading_cells = []
    cell_start = depth = position = 0
    while position < len(header):
        char = header[position]
        if char == "\\":
            position += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif char == "&" and depth == 0:
            heading_cells.append(header[cell_start:position])
            cell_start = position + 1
        position += 1
    heading_cells.append(header[cell_start:])
    if columns == 2 and (len(heading_cells) < 2 or r"\textbf" not in heading_cells[1]):
        header = r"\hline" + "\n" + r"\textbf{Parameter} & \textbf{Value} \\" + "\n" + r"\hline"
        rest = body[first + len(r"\hline"):]
    return (prefix + header + "\n\\endfirsthead\n" + header + "\n\\endhead\n"
            + "\\hline\n\\endfoot\n\\hline\n\\endlastfoot\n" + rest)


def _unfloat_tables(text):
    """Move float captions inside their table before making it multipage."""
    pattern = re.compile(r"\\begin\{table\}(?:\[[^\]]*\])?(.*?)\\end\{table\}", re.S)

    def convert(match):
        block = match.group(1)
        table = re.search(r"\\begin\{tabular\}\{", block)
        if not table:
            return match.group(0)
        end_spec = _group_end(block, table.end() - 1)
        prefix = block[:table.start()]
        return block[table.start():end_spec] + "\n" + prefix + block[end_spec:]

    return pattern.sub(convert, text)


def _repeat_body_labels(body):
    """Replace body-only multirows with a label on every physical table row.

    A multirow box is unbreakable and is positioned across an assumed number of
    rows. Longtable may break those rows across pages, leaving the box in the
    footer or detaching its member name from the continued data. Repeating the
    existing label permits ordinary row pagination and preserves identification.
    Heading multirows are deliberately kept in the repeated heading block.
    """
    if r"\endhead" not in body:
        return body
    heading, data = body.split(r"\endhead", 1)
    rows = []
    start = position = depth = 0
    while position < len(data):
        char = data[position]
        if char == "\\":
            if data.startswith(r"\\", position) and depth == 0:
                end = position + 2
                if end < len(data) and data[end] == "*":
                    end += 1
                if end < len(data) and data[end] == "[":
                    closing = data.find("]", end)
                    if closing >= 0:
                        end = closing + 1
                rows.append(data[start:end])
                start = position = end
                continue
            position += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        position += 1
    rows.append(data[start:])

    remaining = 0
    label = ""
    expanded = False
    for index, row in enumerate(rows):
        # First cell only: all legacy body multirows identify the member or
        # location in that column. Nested makecell line breaks stay untouched.
        cell_end = None
        depth = position = 0
        while position < len(row):
            char = row[position]
            if char == "\\":
                position += 2
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            elif char == "&" and depth == 0:
                cell_end = position
                break
            position += 1
        if cell_end is None:
            continue
        first_cell = row[:cell_end]
        match = re.search(r"\\multirow\{(\d+)\}\{[^{}]*\}\{", first_cell)
        if match:
            end = _group_end(first_cell, match.end() - 1)
            label = first_cell[match.end():end - 1]
            remaining = max(0, int(match.group(1)) - 1)
            rows[index] = first_cell[:match.start()] + label + first_cell[end:] + row[cell_end:]
            expanded = True
        elif remaining:
            commands = r"(?:\\hline|\\cline\{[^{}]*\}|\\endfoot|\\endlastfoot)"
            empty = re.fullmatch(r"\s*(?:" + commands + r"\s*)*", first_cell)
            if empty:
                rows[index] = first_cell + label + " " + row[cell_end:]
            else:
                remaining = 0
                continue
            remaining -= 1
    normalized = "".join(rows)
    if expanded:
        normalized = re.sub(r"\\cline\{2-\d+\}", lambda _: r"\hline", normalized)
    return heading + r"\endhead" + normalized


def format_chapter(text):
    """Apply centralized presentation to a rendered legacy chapter."""
    text = _unfloat_tables(text)
    pattern = re.compile(r"\\begin\{(longtable|tabular)\}\{")
    cursor = 0
    result = []
    while True:
        match = pattern.search(text, cursor)
        if not match:
            result.append(text[cursor:])
            break
        end_spec = _group_end(text, match.end() - 1)
        ending = r"\end{" + match.group(1) + "}"
        table_end = text.find(ending, end_spec)
        if table_end < 0:
            raise ValueError("Unclosed report table")
        spec, columns = _fit_columns(text[match.end():end_spec - 1])
        body = _repeat_body_labels(_repeat_header(text[end_spec:table_end], columns))
        # In a table body, empty cells represent unavailable data. Header cells
        # can intentionally be blank, so keep the repeated heading untouched.
        if r"\endhead" in body:
            header, data = body.split(r"\endhead", 1)
            data = re.sub(r"(?<!\\)&\s*(?=&|\\\\)", "& N/A ", data)
            data = re.sub(r"(\\hline\s*)(?=&)", lambda match: match.group(1) + "N/A ", data)
            data = re.sub(r"(?<!\\)&\s*---\s*(?=&|\\\\)", "& N/A ", data)
            body = header + r"\endhead" + data
        result.append(text[cursor:match.start()])
        result.append("\\begingroup\n\\ReportTableSetup\n\\ReportTableFont\n\\begin{longtable}{" + spec + "}" + body + "\\end{longtable}\n\\endgroup")
        cursor = table_end + len(ending)
    text = "".join(result)
    # Consume existing chapter-local choices using the shared policy. The rules
    # only match formatting commands, never numeric values or equations.
    text = re.sub(r"\\setlength\{\\(?:tabcolsep|LTleft|LTright|abovecaptionskip|belowcaptionskip)\}\{[^{}]*\}", "", text)
    text = re.sub(r"\\setlength\\(?:LTleft|LTright)\{[^{}]*\}", "", text)
    text = re.sub(r"\\renewcommand\{\\arraystretch\}\{[^{}]*\}", "", text)
    text = re.sub(r"\\vspace\{[^{}]*\}", lambda _: r"\ReportTableGap", text)
    text = re.sub(r"\\\\\[[\d.]+pt\]", lambda _: r"\\[\ReportRowGap]", text)
    text = text.replace(r"\textcolor{red}", r"\textcolor{reportFail}")
    text = text.replace(r"\textcolor{blue}", r"\textcolor{reportWarning}")
    text = text.replace(r"\footnotesize", r"\ReportSmallText")
    return text


def styled_chapter(render):
    """Keep chapter APIs intact while applying the same layout to every caller."""
    @wraps(render)
    def render_styled(*args, **kwargs):
        return format_chapter(render(*args, **kwargs))
    return render_styled
