"""Shared model primitives used across all piping component types.

These types are intentionally generic (not elbow-specific) so that future
component families (tees, reducers, flanges, valves, ...) can reuse them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


class ComponentMode(str, Enum):
    """Which of the three input philosophies produced a component."""

    NORMALIZED = "NORMALIZED"
    CUSTOM = "CUSTOM"
    ENGINEERING = "ENGINEERING"


class DataAvailability(str, Enum):
    """Result of a normalized-mode lookup against the catalog database."""

    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    INCOMPLETE = "INCOMPLETE"


class EndType(str, Enum):
    """Connection type at a component port.

    Values are descriptive labels for this application's own model; they are
    not AutoCAD Plant 3D API identifiers (Plant 3D integration is a later
    stage, see plant3d/).
    """

    BUTT_FUSION = "BUTT_FUSION"
    FLANGE = "FLANGE"
    SOCKET = "SOCKET"
    THREADED = "THREADED"
    UNDEFINED = "UNDEFINED"


Vector3 = Tuple[float, float, float]


@dataclass
class Port:
    """One connection point of a component (e.g. P1 / P2 of an elbow).

    Position/direction default to the origin because most of this
    application's V0.1 usage only needs 2D preview geometry; the fields
    exist now so Plant 3D export (which needs full 3D placement) does not
    require a model redesign later.
    """

    id: str
    position_mm: Vector3 = (0.0, 0.0, 0.0)
    direction: Vector3 = (0.0, 0.0, 0.0)
    nominal_diameter_mm: Optional[float] = None
    outside_diameter_mm: Optional[float] = None
    end_type: EndType = EndType.UNDEFINED
    orientation_deg: Optional[float] = None
