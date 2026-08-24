"""Registry of documentary sources available to the project.

Registering a source here means "this document exists and we know its
metadata" — NOT "this document's tables are loaded". Only the HDPE
catalog has any data actually flowing into the app today (via
data/raw/*.xlsx, itself derived from this catalog's section 6.1 — see
docs/DATA_NOTES.md); the other two are registered purely as available
references, per the V0.2.2 instruction not to digitize them yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class DataSourceStatus(str, Enum):
    PARTIALLY_DIGITIZED = "PARTIALLY_DIGITIZED"
    REGISTERED_NOT_DIGITIZED = "REGISTERED_NOT_DIGITIZED"


@dataclass(frozen=True)
class DataSourceMetadata:
    key: str
    name: str
    document_type: str
    status: DataSourceStatus
    organization: Optional[str] = None
    document_number: Optional[str] = None
    revision: Optional[str] = None
    notes: Optional[str] = None


def _load_registered_sources() -> List[DataSourceMetadata]:
    from data_sources.codelco_support_standard import SOURCE as codelco_source
    from data_sources.hdpe_catalog import SOURCE as hdpe_source
    from data_sources.hipogeno_support_standard import SOURCE as hipogeno_source

    return [hdpe_source, codelco_source, hipogeno_source]


REGISTERED_SOURCES: List[DataSourceMetadata] = _load_registered_sources()
REGISTERED_SOURCES_BY_KEY: Dict[str, DataSourceMetadata] = {s.key: s for s in REGISTERED_SOURCES}


def get_data_source(key: str) -> DataSourceMetadata:
    try:
        return REGISTERED_SOURCES_BY_KEY[key]
    except KeyError as exc:
        raise KeyError(f"Fuente de datos '{key}' no esta registrada.") from exc
