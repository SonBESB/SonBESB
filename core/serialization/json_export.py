"""Converts an ElbowParameters into the project's intermediate JSON schema.

Schema version "piping-component-generator/0.1" as defined in the project
spec. Fields the source data does not provide are omitted rather than
filled with invented values (see data/repository.py LookupResult).
"""

from __future__ import annotations

from typing import Any, Dict

from core.models.elbow import ElbowParameters

SCHEMA_VERSION = "piping-component-generator/0.1"


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


def elbow_to_dict(params: ElbowParameters) -> Dict[str, Any]:
    """Builds the JSON-ready dict for one elbow component."""
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
    return {"schema": SCHEMA_VERSION, "component": component}
