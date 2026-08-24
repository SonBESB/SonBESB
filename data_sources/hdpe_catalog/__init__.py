"""HDPE fittings manufacturer catalog.

Section 6.1 (segmented elbows) is already in use by the app, via the
Excel workbook derived from this catalog (data/raw/*.xlsx — see
docs/DATA_NOTES.md for how that Excel itself is interpreted). The rest of
the catalog (other fitting types, other sections) is not digitized.
"""

from __future__ import annotations

from data_sources.registry import DataSourceMetadata, DataSourceStatus

SOURCE = DataSourceMetadata(
    key="hdpe_catalog",
    name="Catalogo HDPE 2(1).pdf",
    document_type="MANUFACTURER_CATALOG",
    status=DataSourceStatus.PARTIALLY_DIGITIZED,
    notes=(
        "Seccion 6.1 (codos segmentados para soldadura por termofusion, "
        "base de DIN 16963 Parte 1) ya en uso via el Excel derivado. "
        "El resto del documento no esta digitalizado."
    ),
)
