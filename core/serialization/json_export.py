"""Converts an ElbowParameters into the project's intermediate JSON schema.

Schema version "piping-component-generator/0.2": V0.1's flat parameter
fields plus (when a SegmentedElbowGeometry is supplied) the 3D gajo/stub
breakdown. Fields the source data does not provide are omitted rather than
filled with invented values (see data/repository.py LookupResult).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.geometry.segmented_elbow import ElbowSegment, SegmentedElbowGeometry
from core.models.elbow import ElbowParameters

SCHEMA_VERSION = "piping-component-generator/0.2"


def _round_vector(vector, ndigits: int = 6):
    """Rounds a 3-tuple, clearing the float noise trig functions leave behind."""
    return [round(v, ndigits) + 0.0 for v in vector]


def _port_to_dict(port) -> Dict[str, Any]:
    return {
        "id": port.id,
        "position_mm": _round_vector(port.position_mm),
        "direction": _round_vector(port.direction),
        "nominal_diameter_mm": port.nominal_diameter_mm,
        "outside_diameter_mm": port.outside_diameter_mm,
        "end_type": port.end_type.value,
        "orientation_deg": port.orientation_deg,
    }


def _segment_to_dict(segment: ElbowSegment) -> Dict[str, Any]:
    return {
        "index": segment.index,
        "label": segment.label,
        "angle_deg": segment.angle_deg,
        "cumulative_angle_deg": segment.cumulative_angle_deg,
        "start_point_mm": _round_vector(segment.axis_start),
        "end_point_mm": _round_vector(segment.axis_end),
        "direction": _round_vector(segment.direction),
    }


def elbow_to_dict(params: ElbowParameters, geometry: Optional[SegmentedElbowGeometry] = None) -> Dict[str, Any]:
    """Builds the JSON-ready dict for one elbow component.

    `geometry` is optional (a SegmentedElbowGeometry from
    core/geometry/segmented_elbow.py) and only adds the 3D "segments"
    (gajo) breakdown and the two straight-leg stubs; every V0.1 field is
    still produced without it.
    """
    config = params.segment_configuration
    component: Dict[str, Any] = {
        "type": params.component_type,
        "material": params.material,
        "mode": params.mode.value,
        "dn_mm": params.dn_mm,
        "dn_equivalent_in": params.dn_equivalent_in,
        "pn": params.pn,
        "sdr": params.sdr,
        "od_mm": params.od_mm,
        "thickness_mm": params.thickness_mm,
        "id_mm": round(params.inside_diameter_mm, 3),
        "angle_deg": params.angle_deg,
        "radius_mm": params.radius_mm,
        "le_mm": params.le_mm,
        "z_mm": params.z_mm,
        "end_type": params.end_type.value,
        "segment_configuration": (
            {
                "total_angle_deg": config.total_angle_deg,
                "is_itemized": config.is_itemized,
                "segment_angles_deg": config.segment_angles_deg,
                "source_text": config.source_text,
            }
            if config
            else None
        ),
        "din16963_compliant": params.din16963_compliant,
        "notes": params.notes,
        "ports": [_port_to_dict(p) for p in params.ports],
    }

    if geometry is not None:
        component["segments_available"] = geometry.segments_available
        component["segments_unavailable_reason"] = geometry.unavailable_reason
        component["segments"] = [_segment_to_dict(s) for s in geometry.segments] if geometry.segments else []
        component["leg1_stub"] = _segment_to_dict(geometry.leg1_stub)
        component["leg2_stub"] = _segment_to_dict(geometry.leg2_stub)

    return {"schema": SCHEMA_VERSION, "component": component}
