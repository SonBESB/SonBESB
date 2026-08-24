"""Maps this project's Port model onto what a Plant 3D CustomScript needs
for its connection points — P1/P2 with position, direction, diameters
and end type.

This is the CRITICAL piece the V0.3 request called out: Plant 3D must
recognize the generated component as connectable, not a bare solid. The
mapping itself is a straight read of core/models/common.py's Port
objects (already populated by core/geometry/segmented_elbow.py) — no new
geometry is computed here.

EndType: per docs/PLANT3D_ENVIRONMENT.md's source investigation, no
verified Plant 3D end-type code for HDPE thermofusion/butt-fusion was
found (Plant 3D manages end codes via its own PLANTENDCODES command, and
this project has no installed instance to read that registry from). Per
the explicit fallback in the V0.3 spec, `plant_end_type` therefore
defaults to the literal marker "REQUIRES_PLANT_CONFIGURATION" unless the
caller supplies a confirmed value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from core.geometry.segmented_elbow import SegmentedElbowGeometry

Vector3 = Tuple[float, float, float]

PLANT_END_TYPE_REQUIRES_CONFIGURATION = "REQUIRES_PLANT_CONFIGURATION"


@dataclass(frozen=True)
class PlantPortMapping:
    plant_port_index: int  # 1-based: Plant 3D's "Ports=N" convention
    source_port_id: str  # "P1" / "P2" in our own model
    position_mm: Vector3
    direction: Vector3
    nominal_diameter_mm: Optional[float]
    outside_diameter_mm: Optional[float]
    source_end_type: str
    plant_end_type: str
    plant_end_type_confirmed: bool


def map_ports(
    geometry: SegmentedElbowGeometry,
    plant_end_type_override: Optional[str] = None,
) -> List[PlantPortMapping]:
    """Reads geometry.ports (already built by segmented_elbow.py) and
    reshapes each into the fields a Plant 3D script would need to expose.
    Does not compute, adjust, or re-derive any coordinate."""
    mappings = []
    for index, port in enumerate(geometry.ports, start=1):
        mappings.append(
            PlantPortMapping(
                plant_port_index=index,
                source_port_id=port.id,
                position_mm=port.position_mm,
                direction=port.direction,
                nominal_diameter_mm=port.nominal_diameter_mm,
                outside_diameter_mm=port.outside_diameter_mm,
                source_end_type=port.end_type.value,
                plant_end_type=plant_end_type_override or PLANT_END_TYPE_REQUIRES_CONFIGURATION,
                plant_end_type_confirmed=plant_end_type_override is not None,
            )
        )
    return mappings
