"""Registry of engineering standards this library knows *about*.

Registering a standard here is a bookkeeping act — it says "this
organization/code exists and this is what we know about our data
coverage for it" — never an act of transcribing that standard's tables.
A standard can (and mostly does, right now) sit at DATA_NOT_LOADED: known
to exist, zero data loaded, not usable for anything yet. Only
DIN 16963-1 has actual data behind it, sourced from the manufacturer
catalog cross-checked in docs/DATA_NOTES.md — and even that is tracked as
SOURCE_DATA, not VERIFIED_DATA, since it hasn't been checked against the
standard's own text (see docs/GEOMETRY_VALIDATION_REFERENCE.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

from core.library.component_family import ComponentCategory


class StandardOrganization(str, Enum):
    DIN = "DIN"
    ISO = "ISO"
    ASME = "ASME"
    EN = "EN"
    MSS = "MSS"
    PROJECT_STANDARD = "PROJECT_STANDARD"
    CUSTOM = "CUSTOM"


class StandardDataStatus(str, Enum):
    VERIFIED_DATA = "VERIFIED_DATA"
    SOURCE_DATA = "SOURCE_DATA"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    DATA_NOT_LOADED = "DATA_NOT_LOADED"
    PROJECT_STANDARD = "PROJECT_STANDARD"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class StandardDefinition:
    key: str
    organization: StandardOrganization
    code: str
    part: Optional[str] = None
    edition: Optional[str] = None
    title: Optional[str] = None
    component_categories: Tuple[ComponentCategory, ...] = ()
    source_reference: Optional[str] = None
    data_status: StandardDataStatus = StandardDataStatus.DATA_NOT_LOADED


STANDARDS_REGISTRY: Dict[str, StandardDefinition] = {
    "DIN_16963_1": StandardDefinition(
        key="DIN_16963_1",
        organization=StandardOrganization.DIN,
        code="16963",
        part="1",
        title="Segmented (mitred) HDPE elbows for thermofusion welding",
        component_categories=(ComponentCategory.FITTING,),
        source_reference="Catalogo HDPE 2(1).pdf, seccion 6.1",
        data_status=StandardDataStatus.SOURCE_DATA,
    ),
    "ASME_B16_9": StandardDefinition(
        key="ASME_B16_9",
        organization=StandardOrganization.ASME,
        code="B16.9",
        title="Factory-Made Wrought Buttwelding Fittings",
        component_categories=(ComponentCategory.FITTING,),
        data_status=StandardDataStatus.DATA_NOT_LOADED,
    ),
    "ISO_4427": StandardDefinition(
        key="ISO_4427",
        organization=StandardOrganization.ISO,
        code="4427",
        title="Polyethylene pipes for water supply",
        component_categories=(ComponentCategory.FITTING,),
        data_status=StandardDataStatus.REFERENCE_ONLY,
        source_reference="Citada en BUSCADOR del Excel origen como norma de tuberia PE100 (no de fitting).",
    ),
    "MSS_SP_58": StandardDefinition(
        key="MSS_SP_58",
        organization=StandardOrganization.MSS,
        code="SP-58",
        title="Pipe Hangers and Supports",
        component_categories=(ComponentCategory.SUPPORT,),
        data_status=StandardDataStatus.DATA_NOT_LOADED,
    ),
    "PROJECT_STANDARD": StandardDefinition(
        key="PROJECT_STANDARD",
        organization=StandardOrganization.PROJECT_STANDARD,
        code="PROJECT_STANDARD",
        title="Norma o especificacion de proyecto (a definir por documento especifico)",
        data_status=StandardDataStatus.PROJECT_STANDARD,
    ),
    "CUSTOM": StandardDefinition(
        key="CUSTOM",
        organization=StandardOrganization.CUSTOM,
        code="CUSTOM",
        title="Sin norma declarada (Modo Personalizado)",
        data_status=StandardDataStatus.CUSTOM,
    ),
}


def get_standard(key: str) -> StandardDefinition:
    try:
        return STANDARDS_REGISTRY[key]
    except KeyError as exc:
        raise KeyError(f"Standard '{key}' no esta registrado en STANDARDS_REGISTRY.") from exc
