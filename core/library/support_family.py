"""Placeholder definition for future pipe support families.

The reference documents now registered in data_sources/ (Codelco and
project-specific support standards) describe many support families —
consoles, pedestals, U-bolts, clamps, guides, anchors, shoes, HDPE
supports, hangers, trunnions, axial restraints. None of that geometry is
implemented in V0.2.2. This dataclass only reserves the shape a future
SupportFamilyDefinition will need, so the eventual geometry work has a
place to plug into without a data-model redesign.

Every field below is intentionally Optional/empty — populating them is
future work, not something this stage invents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.library.provenance import DataProvenance


@dataclass(frozen=True)
class SupportFamilyDefinition:
    key: str
    display_name: str
    drawing_reference: Optional[str] = None
    pipe_size_range_mm: Optional[Tuple[float, float]] = None
    material_key: Optional[str] = None

    user_inputs: List[str] = field(default_factory=list)
    database_values: Dict[str, Any] = field(default_factory=dict)
    rule_derived_parameters: Dict[str, Any] = field(default_factory=dict)
    geometry_derived_parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    variants: List[str] = field(default_factory=list)
    anchor_variants: List[str] = field(default_factory=list)
    load_limits: Dict[str, Any] = field(default_factory=dict)

    provenance: Optional[DataProvenance] = None
    notes: Optional[str] = None


# No support families are registered yet — only the shape above is ready.
SUPPORT_FAMILIES: Dict[str, SupportFamilyDefinition] = {}
