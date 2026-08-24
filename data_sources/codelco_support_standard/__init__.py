"""Codelco pipe support standard.

Registered as an available reference only (V0.2.2). Describes multiple
support families (consoles, pedestals, U-bolts, clamps, guides, anchors,
shoes, HDPE supports, hangers, trunnions, axial restraints) — none of
which are digitized or modeled yet; see core/library/support_family.py
for the (currently empty) placeholder those will eventually populate.
"""

from __future__ import annotations

from data_sources.registry import DataSourceMetadata, DataSourceStatus

SOURCE = DataSourceMetadata(
    key="codelco_support_standard",
    name="Soportes Cañerías Codelco 1.pdf",
    organization="Codelco",
    document_type="SUPPORT_STANDARD",
    status=DataSourceStatus.REGISTERED_NOT_DIGITIZED,
    notes="Multiples familias de soportes de tuberia; no digitalizado todavia.",
)
