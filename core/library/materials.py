"""Independent material registry.

Registering a material here never invents mechanical properties: every
numeric field defaults to None and stays None unless a real, sourced
value is loaded. A material with every property None is still useful to
register — it lets other layers (compatibility, JSON export) refer to it
by a stable key while being honest that no property data backs it yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple


class MaterialFamily(str, Enum):
    HDPE = "HDPE"
    CARBON_STEEL = "CARBON_STEEL"
    STAINLESS_STEEL = "STAINLESS_STEEL"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class MaterialDefinition:
    key: str
    family: MaterialFamily
    specification: Optional[str] = None
    grade: Optional[str] = None
    density_kg_m3: Optional[float] = None
    yield_strength_mpa: Optional[float] = None
    temperature_limits_c: Optional[Tuple[float, float]] = None
    notes: Optional[str] = None


MATERIALS_REGISTRY: Dict[str, MaterialDefinition] = {
    "PE80": MaterialDefinition(key="PE80", family=MaterialFamily.HDPE, grade="PE80"),
    "PE100": MaterialDefinition(
        key="PE100", family=MaterialFamily.HDPE, grade="PE100",
        notes="Material del Golden Case actual; sin propiedades mecanicas cargadas todavia.",
    ),
    "CARBON_STEEL": MaterialDefinition(key="CARBON_STEEL", family=MaterialFamily.CARBON_STEEL),
    "STAINLESS_STEEL": MaterialDefinition(key="STAINLESS_STEEL", family=MaterialFamily.STAINLESS_STEEL),
    "ASTM_A36": MaterialDefinition(
        key="ASTM_A36", family=MaterialFamily.CARBON_STEEL, specification="ASTM A36",
        notes="Registrado como nombre; sin propiedades cargadas.",
    ),
    "ASTM_A106_GR_B": MaterialDefinition(
        key="ASTM_A106_GR_B", family=MaterialFamily.CARBON_STEEL, specification="ASTM A106", grade="Gr.B",
        notes="Registrado como nombre; sin propiedades cargadas.",
    ),
    "ASTM_A312_TP304L": MaterialDefinition(
        key="ASTM_A312_TP304L", family=MaterialFamily.STAINLESS_STEEL, specification="ASTM A312", grade="TP304L",
        notes="Registrado como nombre; sin propiedades cargadas.",
    ),
    "ASTM_A312_TP316L": MaterialDefinition(
        key="ASTM_A312_TP316L", family=MaterialFamily.STAINLESS_STEEL, specification="ASTM A312", grade="TP316L",
        notes="Registrado como nombre; sin propiedades cargadas.",
    ),
    "CUSTOM": MaterialDefinition(key="CUSTOM", family=MaterialFamily.CUSTOM, notes="Modo Personalizado, sin material normado declarado."),
}


def get_material(key: str) -> MaterialDefinition:
    try:
        return MATERIALS_REGISTRY[key]
    except KeyError as exc:
        raise KeyError(f"Material '{key}' no esta registrado en MATERIALS_REGISTRY.") from exc
