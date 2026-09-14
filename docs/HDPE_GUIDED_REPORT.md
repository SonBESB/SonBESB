# Public pumping workflow and PDF report

The app remains public and uses only per-session inputs. PDF and JSON downloads are generated in memory; no shared case history or account storage was introduced.

## Guided entry

Four selectable stages expand the relevant section, with Continue buttons for liquid, piping and pump data. Existing input widgets remain mounted so switching stages preserves their values. Initial values remain explicitly marked as examples.

## HDPE catalog scope

173 populated diameter/SDR pairs transcribed from the user's `Catalogo HDPE 2.pdf`, Duratec, table 5.1.1, printed/PDF page 10. PE100 ISO 4427 only. DIN 8074 and PE80 are not mixed into this selector. Empty cells are unavailable; the three manufacturer note-4 exceptions retain their note. Commercial availability colors were not interpreted as current availability.

The internal diameter is calculated from the published minimum thickness: DI = DE - 2e. It is not calculated from unrounded DE/SDR and does not account for dimensional tolerances. Rows remain pending review. PDF hash and source page are included in JSON. Pressure comparison is allowed only for automatic water properties at exactly 20 C, the reference condition of the dimensional table. Other temperatures/fluids return no allowable pressure; no derating is invented. Roughness 0.007 mm remains an editable assumption. Surge for catalog HDPE requires the user to supply E; it does not inherit PEXGOL's example modulus.

## PDF

ReportLab builds a PDF in memory with case name, UTC timestamp, actual plotted Q-H samples as vector graphics, liquid properties, segments, accessory quantities and K values, catalog references, entered pump curve, efficiencies, scenario configuration, formulas, polynomial coefficients, nominal loss details and performed checks. Non-evaluated checks remain explicit. The report preserves existing hydraulic model limitations, including interpolated system samples and illustrative elevations.

Embedded serif fonts derive from STIX under its included OFL license, subset and renamed BESBReport/BESBReportBold. This avoids PDF viewer substitution; it is not a bundled Microsoft Times New Roman font. The browser graph retains the user's Times New Roman/Times/serif preference. No logo is added.

Validation: catalog reference cells and missing combinations, conservative pressure scope, mixed PEXGOL/manual regression tests, guided navigation, HDPE surge input, VDF controls and PDF generation. A representative three-page PDF was rendered and inspected.
