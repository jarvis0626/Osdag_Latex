# Technical changes

The original report pipeline already separated chapters into Python functions,
but each chapter carried its own table widths and spacing. Large tables could
exceed the page body, continuation pages could lose headings, and end diaphragm
tables reused intermediate cross-bracing values. The changes keep the existing
chapter interfaces and engineering backend while improving report presentation,
source extraction, and reproducibility.

The source baseline is
[`Nidhikhare12/OsdagBridge`, `dev`](https://github.com/Nidhikhare12/OsdagBridge/tree/dev),
revision `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`.
See [task_requirements.md](task_requirements.md) for the detailed task source,
the unresolved Winter/Autumn linkage, and remaining submission requirements.

## Rendering architecture

The pipeline is:

```text
GUI design outputs or saved result JSON
    -> report payload snapshot
    -> existing quantity extraction + temporary chart assets
    -> chapter renderers + shared style policy
    -> .tex and matching asset directory
    -> optional LaTeX compilation -> PDF or actionable failure
```

The new report command can also render a clearly labeled synthetic example.
That example exercises report formatting with actual backend field names;
it does not run an analysis or certify structural safety. Existing desktop
request and result objects remain the integration boundary.

## One presentation configuration

`src/osdagbridge/core/reports/styles.py` defines `ReportStyle` and `STYLE` for
page geometry, table padding, rules, row spacing, colors, and chart appearance.
The preamble consumes these settings, including real space for page furniture.
Negative footer offsets are removed.

Every chapter renderer uses `@styled_chapter`. This compatibility boundary
normalizes legacy formatting commands, turns supported fixed tables into
breakable tables, and inserts first-page and continuation headings. Column
widths are fitted after reserving space for padding and vertical rules. The
policy changes presentation, not numerical cells or equations. It avoids a
large rewrite of upstream chapter templates and preserves their callable
interfaces. Its balanced-group table handling is intentionally scoped to the
project's generated LaTeX; new table constructs need matching regression tests.

## Data and visual changes

Chapter 3 separates vehicle loading from footway loading and provides unit
columns. Vehicle labels come from the selected standard-vehicle flags and
custom names. Unsupported values, including centrifugal force not exposed by
the backend, are identified rather than invented. Existing code helpers remain
responsible for the load factors already used by the report.

`charts.py` builds the Section 5.5 visualization from independent sources:

| Component | Source |
| --- | --- |
| Steel girders | `design_results.per_girder` checks and per-load-case checks |
| Concrete slab | Canonical `KEY_DD_*` demand/capacity values in `deck_report_values` |
| Cross bracing | `crossbracing_forces_dict` and `crossbracing_design_results` |
| End diaphragms | `end_diaphragm_forces_dict` and `end_diaphragm_design_results` |

Demand/capacity requires finite nonnegative demand and positive finite capacity.
Missing values, invalid numbers, and zero capacity produce N/A. Where valid,
girder checks retain the backend's reported ratio to preserve its rounding.
Bars aggregate the highest available check ratio per girder or bracing member;
slab bars show individual checks. A red dashed line marks UR = 1.0. Individual
backend warning and failure bands still govern the detailed checks; this chart
does not redefine engineering acceptance criteria.

Chapter 5's diaphragm property, slenderness, and capacity tables now read actual
support diaphragm results. Its summary labels axial compression and tension
correctly instead of labeling copied bracing results as diaphragm moment and
shear. No available result is substituted from another component.

Chapter 7 adds a structural-steel mass chart. Concrete volume and reinforcement
mass appear on separate axes with their respective units. The existing BOQ does
not produce end diaphragm mass, so that item is explicitly unavailable unless
a total is supplied. The upstream reinforcement estimate of **120 kg per cubic
metre of deck concrete** is preserved and disclosed; it is not a detailed
reinforcement schedule. Engineering and quantity calculation code is unchanged.

Charts use Matplotlib's object-oriented Agg canvas, without changing the GUI's
global plotting backend. PNGs live in a caller-owned temporary asset directory
until compilation finishes. Chapter renderers include them using PyLaTeX
`Figure`; captions are escaped. Chapter 7 also closes its previously unmatched
LaTeX group.

## Execution and failure handling

The report orchestrator copies the mutable report inputs before enriching them,
so report generation does not update the caller's analysis inputs. It exports
the source with a matching asset directory before attempting compilation.
Those files remain available for inspection or rebuilding if compilation fails.

`compilation.py` discovers an explicitly selected compiler, the Osdag LaTeX
bundle, or supported PATH/local compilers. It invokes the compiler without a
shell, disables shell escape for pdfLaTeX, uses Tectonic's untrusted mode, and
preserves diagnostics. Nonzero exits, timeouts, missing executables, and absent
or invalid PDF output return a failure rather than apparent success. The
command-line entry point returns a nonzero exit status on failures.

Plain-text escaping in `report_utils.py` handles LaTeX metacharacters and common
engineering glyphs. Trusted report formulas remain separate from plain text.

## Changed report files and verification

| Files under `src/osdagbridge/core/reports/` | Purpose |
| --- | --- |
| `styles.py` | Shared layout and table continuation rules |
| `chap1.py` through `chap9.py`, `executive_summary.py` | Adopt shared formatting; Chapters 3, 5, and 7 contain the specific changes above |
| `charts.py` | Source mapping, missing-value handling, rendering, and figure inclusion |
| `report_generator.py` | Payload snapshot, chart lifecycle, source bundles, compiler integration |
| `compilation.py` | Compiler discovery, execution, artifact verification, diagnostics |
| `report_utils.py` | Plain-text escaping and shared report helpers |
| `__main__.py`, `demo.py` | Headless saved-result workflow and labeled synthetic fixture |

At the implementation checkpoint, `python -m pytest tests/reports -q` ran
successfully with **124 tests passing** using `src` on `PYTHONPATH`. The suite
covers continuation headings and column widths, escaping, selected loads,
component-source separation, invalid/missing ratios, PNG output, compiler
failure handling, and report integration. Consult the final validation record
for subsequent runs and actual PDF evidence.

A full GUI design, before/after reports from the same real analysis, and visual
verification of every original layout defect remain separate integration work.
Unit tests and the synthetic fixture alone do not establish that those steps
have succeeded.
