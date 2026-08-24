"""Parametric model for a segmented HDPE elbow (DIN 16963).

This module holds pure data structures. Nothing here reads Excel files,
touches a UI widget, or draws geometry — see data/repository.py,
ui/app_streamlit.py and core/geometry/elbow_geometry.py respectively.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from core.models.common import ComponentMode, EndType, Port

COMPONENT_TYPE_HDPE_SEGMENTED_ELBOW = "HDPE_SEGMENTED_ELBOW"


@dataclass
class SegmentConfiguration:
    """Miter-cut layout of a segmented elbow for one angle.

    The source catalog gives this as a human-readable string per angle
    (e.g. "15° - 30° - 30° - 15°" for 90°). When that string is itemized we
    also parse it into ``segment_angles_deg`` (each entry summing to
    ``total_angle_deg``); when the source only has generic prose (this is
    the case for 30° in the supplied workbook) ``segment_angles_deg`` stays
    None rather than guessing a breakdown.
    """

    total_angle_deg: float
    is_itemized: bool
    segment_angles_deg: Optional[List[float]] = None
    source_text: Optional[str] = None

    @property
    def segment_count(self) -> Optional[int]:
        return len(self.segment_angles_deg) if self.segment_angles_deg else None


@dataclass
class ElbowParameters:
    """Complete parametric definition of one HDPE segmented elbow instance.

    This is the single object that geometry generation, validation, JSON
    export and (later) Plant 3D export all consume. UI code only ever
    builds one of these via components/elbows/hdpe_segmented_elbow.py — it
    never assembles geometry directly from widget values.
    """

    mode: ComponentMode
    component_type: str = COMPONENT_TYPE_HDPE_SEGMENTED_ELBOW
    material: str = "PE100"

    # Catalog identity (normalized mode only; None in custom mode).
    dn_mm: Optional[float] = None
    dn_equivalent_in: Optional[str] = None
    pn: Optional[str] = None
    sdr: Optional[float] = None

    # Geometry-defining dimensions (always present, any mode).
    od_mm: float = 0.0
    thickness_mm: float = 0.0
    angle_deg: float = 0.0
    radius_mm: float = 0.0
    le_mm: float = 0.0
    z_mm: Optional[float] = None

    segment_configuration: Optional[SegmentConfiguration] = None
    end_type: EndType = EndType.BUTT_FUSION

    ports: List[Port] = field(default_factory=list)

    din16963_compliant: Optional[bool] = None
    notes: List[str] = field(default_factory=list)

    @property
    def inside_diameter_mm(self) -> float:
        """Derived, never looked up: ID = OD - 2 * thickness."""
        return self.od_mm - 2 * self.thickness_mm

    @property
    def is_normalized(self) -> bool:
        return self.mode is ComponentMode.NORMALIZED
