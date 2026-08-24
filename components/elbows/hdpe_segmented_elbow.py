"""Domain-level entry point for the HDPE segmented elbow component.

This is the only module the UI layer should call to build an
ElbowParameters instance. It ties together the data repository (MODE A),
the geometric validation rules (MODE B) and the shared model — the UI never
constructs ElbowParameters, calls the repository, or runs validation
directly.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from core.geometry.elbow_geometry import calculate_z_mm
from core.models.common import ComponentMode, EndType
from core.models.elbow import ElbowParameters, SegmentConfiguration
from core.validation.elbow_validation import ValidationIssue, validate_custom_elbow
from data.repository import ElbowRepository, LookupResult

CUSTOM_MODE_NOTICE = "COMPONENTE PERSONALIZADO: no se declara cumplimiento con DIN 16963."


def build_normalized(repository: ElbowRepository, dn_mm: float, pn_label: str, angle_deg: int) -> LookupResult:
    """MODE A: looks up a catalog-defined elbow. Never fabricates values."""
    return repository.lookup(dn_mm=dn_mm, pn_label=pn_label, angle_deg=angle_deg)


def build_custom(
    od_mm: float,
    thickness_mm: float,
    angle_deg: float,
    radius_mm: float,
    le_mm: float,
    z_mm: Optional[float] = None,
    segment_angles_deg: Optional[List[float]] = None,
    end_type: EndType = EndType.BUTT_FUSION,
) -> Tuple[ElbowParameters, List[ValidationIssue]]:
    """MODE B: builds an elbow from user-supplied dimensions.

    z_mm is calculated (Z = Le + R*tan(angle/2)) only when the user leaves
    it blank; an explicitly supplied z_mm is kept as-is, per the spec
    ("Z = valor ingresado o calculado cuando corresponda").
    """
    notes = [CUSTOM_MODE_NOTICE]

    resolved_z_mm = z_mm
    if resolved_z_mm is None:
        try:
            resolved_z_mm = calculate_z_mm(le_mm, radius_mm, angle_deg)
        except (ValueError, ZeroDivisionError, OverflowError):
            resolved_z_mm = None
            notes.append("No fue posible calcular Z automaticamente con los valores ingresados.")

    segment_configuration = None
    if segment_angles_deg:
        segment_configuration = SegmentConfiguration(
            total_angle_deg=angle_deg,
            is_itemized=True,
            segment_angles_deg=list(segment_angles_deg),
            source_text=None,
        )

    params = ElbowParameters(
        mode=ComponentMode.CUSTOM,
        dn_mm=None,
        dn_equivalent_in=None,
        pn=None,
        sdr=None,
        od_mm=od_mm,
        thickness_mm=thickness_mm,
        angle_deg=angle_deg,
        radius_mm=radius_mm,
        le_mm=le_mm,
        z_mm=resolved_z_mm,
        segment_configuration=segment_configuration,
        end_type=end_type,
        din16963_compliant=False,
        notes=notes,
    )

    issues = validate_custom_elbow(params)
    return params, issues
