"""Builds the intermediate dataset a future CatalogBuilderExcelExporter
would transform into the Excel format Plant 3D's Catalog Builder expects.

This dataset is safe to build: it is just our own already-validated
numbers (DN, PN, OD, THK, R, LE, Z, ANGLE), read from ElbowParameters/
SegmentedElbowGeometry, not a guess at Autodesk's file format. Producing
`catalog_builder_payload.json` does NOT claim it is importable into
Catalog Builder — see catalog_builder_excel_exporter.py for why.
"""

from __future__ import annotations

from typing import Any, Dict

from core.geometry.segmented_elbow import SegmentedElbowGeometry
from core.models.elbow import ElbowParameters


def build_catalog_builder_payload(params: ElbowParameters, geometry: SegmentedElbowGeometry) -> Dict[str, Any]:
    """Plain DN/PN/OD/THK/R/LE/Z/ANGLE dataset — no Excel formatting
    decisions are made here (see docs/PLANT3D_CATALOG_WORKFLOW.md)."""
    return {
        "status": "REFERENCE_TEMPLATE_REQUIRED",
        "component_family": "HDPE_SEGMENTED_ELBOW",
        "dn_mm": params.dn_mm,
        "pn": params.pn,
        "od_mm": params.od_mm,
        "thickness_mm": params.thickness_mm,
        "inside_diameter_mm": round(params.inside_diameter_mm, 6),
        "sdr": params.sdr,
        "radius_mm": params.radius_mm,
        "le_mm": params.le_mm,
        "z_mm": geometry.z_mm,
        "angle_deg": params.angle_deg,
        "segment_configuration": (
            params.segment_configuration.segment_angles_deg if params.segment_configuration else None
        ),
    }
