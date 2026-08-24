"""Project-specific pipe support drawing/standard (document 2111-1CD-6-057).

Registered as an available reference only (V0.2.2) — not digitized. Folder
name kept exactly as specified when this source was registered.
"""

from __future__ import annotations

from data_sources.registry import DataSourceMetadata, DataSourceStatus

SOURCE = DataSourceMetadata(
    key="hipogeno_support_standard",
    name="2111-1CD-6-057_R1 3.pdf",
    document_number="2111-1CD-6-057",
    revision="R1",
    document_type="SUPPORT_STANDARD",
    status=DataSourceStatus.REGISTERED_NOT_DIGITIZED,
    notes="Documento/plano de proyecto para soportes; no digitalizado todavia.",
)
