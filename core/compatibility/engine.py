"""Answers "does this library support family + standard + material" —
and, just as importantly, distinguishes NOT lending support from being
engineering-invalid.

NOT_AVAILABLE_IN_LIBRARY means exactly that: this codebase has no data or
geometry for that combination yet. It says nothing about whether the
combination makes physical/engineering sense — an HDPE elbow built to
ASME B16.9 might be perfectly reasonable in the real world; this library
just doesn't have B16.9 loaded (see core/library/standards.py). Actually
invalid engineering combinations are a distinct, currently-unpopulated
concept (`engineering_invalid`) — never conflate the two.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Tuple

from core.library.component_family import COMPONENT_FAMILIES
from core.library.materials import MATERIALS_REGISTRY
from core.library.standards import STANDARDS_REGISTRY


class CompatibilityStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NOT_AVAILABLE_IN_LIBRARY = "NOT_AVAILABLE_IN_LIBRARY"
    UNKNOWN_KEY = "UNKNOWN_KEY"


@dataclass(frozen=True)
class CompatibilityResult:
    status: CompatibilityStatus
    message: str
    engineering_invalid: bool = False


# The only combination this library actually has a working geometry engine
# and sourced data for today. Adding to this set is how a *real*, tested
# capability gets declared supported — never a placeholder for "probably
# fine".
SUPPORTED_COMBINATIONS: FrozenSet[Tuple[str, str, str]] = frozenset(
    {
        ("HDPE_SEGMENTED_ELBOW", "DIN_16963_1", "PE100"),
    }
)


def check_compatibility(family_key: str, standard_key: str, material_key: str) -> CompatibilityResult:
    unknown = [
        name
        for name, key, registry in (
            ("familia", family_key, COMPONENT_FAMILIES),
            ("norma", standard_key, STANDARDS_REGISTRY),
            ("material", material_key, MATERIALS_REGISTRY),
        )
        if key not in registry
    ]
    if unknown:
        return CompatibilityResult(
            status=CompatibilityStatus.UNKNOWN_KEY,
            message=f"Clave(s) no registrada(s): {', '.join(unknown)}.",
        )

    if (family_key, standard_key, material_key) in SUPPORTED_COMBINATIONS:
        return CompatibilityResult(
            status=CompatibilityStatus.SUPPORTED,
            message=f"{family_key} + {standard_key} + {material_key} tiene motor geometrico y datos en esta libreria.",
        )

    return CompatibilityResult(
        status=CompatibilityStatus.NOT_AVAILABLE_IN_LIBRARY,
        message=(
            f"{family_key} + {standard_key} + {material_key} no esta disponible en esta libreria todavia. "
            "Esto NO significa que la combinacion sea invalida en ingenieria — solo que aun no tenemos "
            "datos/geometria cargados para ella."
        ),
    )
