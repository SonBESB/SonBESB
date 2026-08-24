"""Wraps an already-built ElbowParameters in the general component-library
metadata (family, material, standard, compliance, provenance) — WITHOUT
touching the geometry engine at all.

This module only *reads* core/models/elbow.py's ElbowParameters and
core/geometry/segmented_elbow.py's SegmentedElbowGeometry; it does not
modify either. See docs/COMPONENT_LIBRARY.md for the full picture.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.geometry.elbow_geometry import GEOMETRIC_RELATION_VERIFIED_AGAINST_SOURCE_DATA
from core.geometry.segmented_elbow import SegmentedElbowGeometry
from core.library.component_family import ComponentFamilyDefinition, get_component_family
from core.library.materials import MATERIALS_REGISTRY, MaterialDefinition, get_material
from core.library.provenance import DataProvenance, SourceType
from core.library.standards import StandardDefinition, get_standard
from core.models.common import ComponentMode
from core.models.elbow import ElbowParameters

HDPE_SEGMENTED_ELBOW_FAMILY_KEY = "HDPE_SEGMENTED_ELBOW"
DIN_16963_1_KEY = "DIN_16963_1"

# Always true once a (DN, PN, angle) combination exists in the catalog at
# all — R/Le/Z are known regardless of whether the segment breakdown is
# itemized. Kept as an explicit label (not just an implicit "not None")
# because the 30-degree case is exactly "geometry known, decomposition
# not" and that distinction deserves its own name (see item 4 of the
# V0.2.2 request and docs/GEOMETRY_VALIDATION_REFERENCE.md).
SOURCE_GEOMETRY_AVAILABLE = "SOURCE_GEOMETRY_AVAILABLE"


class SegmentDecompositionStatus(str, Enum):
    DEFINED = "SEGMENT_DECOMPOSITION_DEFINED"
    NOT_DEFINED = "SEGMENT_DECOMPOSITION_NOT_DEFINED"


class ComplianceStatus(str, Enum):
    SOURCE_DATA = "SOURCE_DATA"
    OUT_OF_STANDARD_SCOPE = "OUT_OF_STANDARD_SCOPE"
    NOT_CERTIFIED = "NOT_CERTIFIED"


# Provenance for the normalized-mode HDPE elbow data (BD_Codos/BD_PN,
# ultimately sourced from the manufacturer catalog). See docs/DATA_NOTES.md
# for how the Excel itself was interpreted.
HDPE_CATALOG_ELBOW_PROVENANCE = DataProvenance(
    document="Catalogo HDPE 2(1).pdf",
    section="6.1",
    table="6.1.1",
    standard_reference="DIN 16963 Part 1",
    source_type=SourceType.MANUFACTURER_CATALOG,
    notes=(
        "Codos segmentados para soldadura por termofusion. Tabla tambien "
        "cruzada contra BD_Codos/BD_PN del Excel derivado del catalogo "
        "(ver docs/DATA_NOTES.md)."
    ),
)


@dataclass(frozen=True)
class ComponentRegistration:
    family: ComponentFamilyDefinition
    material: MaterialDefinition
    standard: StandardDefinition
    compliance_status: ComplianceStatus
    segment_decomposition_status: SegmentDecompositionStatus
    provenance: Optional[DataProvenance] = None
    source_geometry_status: str = SOURCE_GEOMETRY_AVAILABLE
    geometric_relation_status: str = GEOMETRIC_RELATION_VERIFIED_AGAINST_SOURCE_DATA


def register_hdpe_segmented_elbow(
    params: ElbowParameters,
    geometry: Optional[SegmentedElbowGeometry] = None,
) -> ComponentRegistration:
    """Builds the library-layer registration for an already-built elbow.

    Never re-derives or second-guesses params/geometry — only reads them.
    """
    family = get_component_family(HDPE_SEGMENTED_ELBOW_FAMILY_KEY)
    material = MATERIALS_REGISTRY.get(params.material, get_material("CUSTOM"))

    if params.mode is ComponentMode.CUSTOM:
        standard = get_standard("CUSTOM")
        compliance_status = ComplianceStatus.NOT_CERTIFIED
        provenance = None
    else:
        standard = get_standard(DIN_16963_1_KEY)
        compliance_status = (
            ComplianceStatus.SOURCE_DATA if params.din16963_compliant else ComplianceStatus.OUT_OF_STANDARD_SCOPE
        )
        provenance = HDPE_CATALOG_ELBOW_PROVENANCE

    if geometry is not None and geometry.segments_available:
        segment_status = SegmentDecompositionStatus.DEFINED
    else:
        segment_status = SegmentDecompositionStatus.NOT_DEFINED

    return ComponentRegistration(
        family=family,
        material=material,
        standard=standard,
        compliance_status=compliance_status,
        segment_decomposition_status=segment_status,
        provenance=provenance,
    )
