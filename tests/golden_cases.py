"""Named golden-case lookup parameters, shared across test files.

GOLDEN_CASE_DN110_PN10_90 is the project's PRIMARY golden case as of
V0.2.2 (see docs/COMPONENT_LIBRARY.md): it comes from the same source
documented in section 6.1 of the HDPE manufacturer catalog and matches
every published dimension exactly.

GOLDEN_CASE_DN315_PN10_90 was primary through V0.2.1 and is kept as the
scalability/regression case — a different DN, same angle, exercising the
same code paths at a different scale. It is NOT removed.
"""

GOLDEN_CASE_DN110_PN10_90 = dict(dn_mm=110, pn_label="PN10", angle_deg=90)
GOLDEN_CASE_DN315_PN10_90 = dict(dn_mm=315, pn_label="PN10", angle_deg=90)
