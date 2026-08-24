"""General component taxonomy: Category -> Type -> Family.

This is a registry/definition layer only. It never touches geometry: the
existing HDPE segmented elbow engine (core/geometry/, components/elbows/)
is unchanged — this module just gives that component a place in a wider
catalog of families that will eventually include tees, reducers, flanges,
valves, supports and equipment.

    COMPONENT
      |- FITTING
      |    |- ELBOW
      |    |- TEE
      |    |- REDUCER
      |    `- FLANGE
      |- VALVE
      |- SUPPORT
      `- EQUIPMENT
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class ComponentCategory(str, Enum):
    FITTING = "FITTING"
    VALVE = "VALVE"
    SUPPORT = "SUPPORT"
    EQUIPMENT = "EQUIPMENT"


class ComponentType(str, Enum):
    ELBOW = "ELBOW"
    TEE = "TEE"
    REDUCER = "REDUCER"
    FLANGE = "FLANGE"
    GENERIC_VALVE = "GENERIC_VALVE"
    GENERIC_SUPPORT = "GENERIC_SUPPORT"
    GENERIC_EQUIPMENT = "GENERIC_EQUIPMENT"


@dataclass(frozen=True)
class ComponentFamilyDefinition:
    key: str
    category: ComponentCategory
    type: ComponentType
    display_name: str
    default_material_key: Optional[str] = None
    default_standard_key: Optional[str] = None
    implemented: bool = False
    notes: Optional[str] = None


COMPONENT_FAMILIES: Dict[str, ComponentFamilyDefinition] = {
    "HDPE_SEGMENTED_ELBOW": ComponentFamilyDefinition(
        key="HDPE_SEGMENTED_ELBOW",
        category=ComponentCategory.FITTING,
        type=ComponentType.ELBOW,
        display_name="Codo HDPE segmentado",
        default_material_key="PE100",
        default_standard_key="DIN_16963_1",
        implemented=True,
        notes="Unica familia con motor geometrico real; ver core/geometry/segmented_elbow.py.",
    ),
    # Placeholders: registered as names in the taxonomy, no geometry engine
    # behind them yet. Registering here is not a promise they work.
    "GENERIC_TEE": ComponentFamilyDefinition(
        key="GENERIC_TEE", category=ComponentCategory.FITTING, type=ComponentType.TEE,
        display_name="Tee (no implementado)", implemented=False,
    ),
    "GENERIC_REDUCER": ComponentFamilyDefinition(
        key="GENERIC_REDUCER", category=ComponentCategory.FITTING, type=ComponentType.REDUCER,
        display_name="Reductor (no implementado)", implemented=False,
    ),
    "GENERIC_FLANGE": ComponentFamilyDefinition(
        key="GENERIC_FLANGE", category=ComponentCategory.FITTING, type=ComponentType.FLANGE,
        display_name="Flange (no implementado)", implemented=False,
    ),
    "GENERIC_VALVE": ComponentFamilyDefinition(
        key="GENERIC_VALVE", category=ComponentCategory.VALVE, type=ComponentType.GENERIC_VALVE,
        display_name="Valvula (no implementado)", implemented=False,
    ),
    "GENERIC_SUPPORT": ComponentFamilyDefinition(
        key="GENERIC_SUPPORT", category=ComponentCategory.SUPPORT, type=ComponentType.GENERIC_SUPPORT,
        display_name="Soporte (no implementado, ver core/library/support_family.py)", implemented=False,
    ),
    "GENERIC_EQUIPMENT": ComponentFamilyDefinition(
        key="GENERIC_EQUIPMENT", category=ComponentCategory.EQUIPMENT, type=ComponentType.GENERIC_EQUIPMENT,
        display_name="Equipo (no implementado)", implemented=False,
    ),
}


def get_component_family(key: str) -> ComponentFamilyDefinition:
    try:
        return COMPONENT_FAMILIES[key]
    except KeyError as exc:
        raise KeyError(f"Familia de componente '{key}' no esta registrada en COMPONENT_FAMILIES.") from exc
