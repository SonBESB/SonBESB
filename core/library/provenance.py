"""Traceability model: where did a given set of data actually come from.

Independent of any specific component. Every registered dataset (a
catalog table, a standard's tabulated values, a project drawing extract)
should be able to point at one of these, so a JSON export or a UI panel
can answer "where did this number come from" without digging through
source code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SourceType(str, Enum):
    MANUFACTURER_CATALOG = "MANUFACTURER_CATALOG"
    STANDARD_DOCUMENT = "STANDARD_DOCUMENT"
    PROJECT_DRAWING = "PROJECT_DRAWING"
    INTERNAL_CALCULATION = "INTERNAL_CALCULATION"
    USER_PROVIDED = "USER_PROVIDED"


@dataclass(frozen=True)
class DataProvenance:
    document: str
    document_revision: Optional[str] = None
    page: Optional[str] = None
    section: Optional[str] = None
    table: Optional[str] = None
    standard_reference: Optional[str] = None
    source_type: SourceType = SourceType.MANUFACTURER_CATALOG
    notes: Optional[str] = None
