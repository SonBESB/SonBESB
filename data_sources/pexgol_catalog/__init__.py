"""Partially transcribed manufacturer source; all extracted data remain draft."""
from data_sources.registry import DataSourceMetadata, DataSourceStatus
SOURCE = DataSourceMetadata(
    key='pexgol_catalog', name='Engineering Guide Spanish 16-05-2023.pdf',
    document_type='MANUFACTURER_CATALOG', status=DataSourceStatus.PARTIALLY_DIGITIZED,
    organization='PEXGOL', revision='2023-05-16',
    notes='170 referencias pp. 10-13; tabla 9.1 y rugosidad p. 23. DRAFT_UNVERIFIED; no aprobadas para diseno.',
)
