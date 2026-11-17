# Engineering data and calculation audit

This audit checks reporting provenance and consistency. It does not establish
structural adequacy or independently validate all IRC/IS implementations.
No changes were made to `core/bridge_types`, `core/utils/codes`, or `core/boq`
relative to the starting upstream revision. The report layer and its tests
were changed.

| Category | Actual source | What reporting does |
| --- | --- | --- |
| Engineering analysis/design | `analyser.py`, `designer.py`, `deckdesign.py` and the component routines in the original plate-girder backend | Consumes their exported dictionaries. The headless report command does not run them. |
| Supplied girder checks | `design_results.per_girder.<member>.checks` and `.per_lc.<case>.checks` | Shows each member's own values, units, clause, source and status. |
| Supplied slab results | `deck_report_values` using canonical `KEY_DD_*` fields | Renders provided values and flags; computes presentation ratios/limited comparisons only when operands are valid. |
| Supplied transverse results | Separate `crossbracing_*` and `end_diaphragm_*` force/design dictionaries | Reads the matching component; never substitutes cross-bracing data for a diaphragm. |
| Presentation arithmetic | `charts.py` and `data.py` | Validates finite nonnegative operands, divides demand by positive capacity, aggregates available ratios and accounts for rounded exports. This is not a capacity calculation. |
| Existing quantity estimates | `boq_generator.calculate_material_quantities()` | Invokes the original helper, normalizes unavailable labels and plots its results. Its formulas and densities were not changed. |
| Existing load helpers | `chap3.ch3_loads()` calls original IRC helper routines | Separates helper evaluations from an actual supplied governing multiplier. Braking-helper failures remain N/A. |
| Existing temperature enrichment | `build_report_payload()` calls the original effective-temperature helper when required input data exists | Preserves the inherited enrichment in a report snapshot; it is not a new structural model. |
| Hardcoded presentation/reference content | Chapter titles, units, explanatory text, code labels and assumptions | These are template content. Inherited standard editions and project applicability require verification. |
| Synthetic data | `demo.demonstration_data()` and the named matrix cases | Explicit fixture values for testing. They are not solved bridge designs. |
| Missing data | Unavailable checks, drawings and force/quantity fields | N/A or an unavailable note, without a passing zero or invented drawing. |

## Specific defects identified and corrected

1. The old girder detail tables copied the same flat controlling-girder values
   under every member label. The structured table now reads actual member
   records. Flat legacy values cannot establish a member-specific passing check.
2. Some deck comparisons used missing values as zero. Missing operands now
   produce N/A; a real zero demand remains valid when capacity is positive.
3. Executive and detail statuses could disagree. Summaries preserve backend
   FAIL/WARN evidence and use the same valid ratios as the chart. The synthetic
   statuses also follow the upstream thresholds instead of inventing new bands.
4. A supplied DCR could contradict its demand/capacity. Such conflicts are
   flagged instead of being silently presented as valid. The interval check
   accounts for `DCREngine._add_check()` rounding operands to two decimals and
   DCR to four decimals. Engineering values are not repaired or recalculated.
5. The inherited heavy-vehicle impact helper reads module-level `KEY_VEHICLE`
   defaults rather than receiving the selected vehicle. Reporting no longer
   labels that default as an actual vehicle-specific result. It shows a supplied
   backend governing multiplier when available, otherwise N/A. The Class A
   helper evaluation is identified separately as a reporting helper evaluation.
6. `cl_211_2_braking_force()` can access an unassigned local variable. Its
   reporting result stays N/A. The numerical routine was not patched to make
   a table look complete.
7. Fixed “M40” and “Fe 500” material labels were not justified by arbitrary
   snapshots. The quantity table now uses neutral material descriptions.

## Quantities: what has and has not been checked

A dimensional fixture checks the unchanged helper with an explicitly supplied
steel area of 0.06 m², four 25 m girders and mass 471 kg/m:

- Steel volume: `0.06 × 25 × 4 = 6.00 m³`.
- Steel mass: `471 × 25 × 4 / 1000 = 47.10 MT`.
- Deck volume: `25 × 10.5 × 0.25 = 65.625 m³`, then formatted by the helper.

This is a test of that example and its stated units, not independent validation
of every possible upstream unit conversion. Reinforcement uses the inherited
120 kg per m³ of deck estimate. It is not a reinforcement schedule. The backend
does not provide end-diaphragm BOQ mass; the report does not infer it from another
component. Different physical units are plotted on separate axes.

## Remaining engineering verification

Run a genuine model through the original GUI and compare selected UI vehicles,
actual result dictionaries, drawings, member-specific checks, quantities and the
PDF. Verify applicable standard editions and the numerical backend separately.
The existing report fixtures, four ordinary local PDFs and a successful compiler
run cannot substitute for those checks.
