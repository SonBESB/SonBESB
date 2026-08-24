"""GOLDEN_CASE_DN110_PN10_90 — the project's primary golden case (V0.2.2+).

Source: Catalogo HDPE 2(1).pdf, seccion 6.1 (codos segmentados para
soldadura por termofusion, base DIN 16963 Parte 1). Every value below is
the one explicitly given in that source, cross-checked against the
Excel-derived database (see docs/DATA_NOTES.md).

DN315/PN10/90 remains covered separately in tests/test_repository.py,
tests/test_segmented_elbow.py etc. as the scalability/regression case —
untouched by this file.
"""

import math

import pytest

from core.geometry.engineering_report import build_overall_dimensions
from core.geometry.geometry_validation import validate_segmented_elbow_geometry
from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from core.library.elbow_registration import (
    ComplianceStatus,
    SegmentDecompositionStatus,
    register_hdpe_segmented_elbow,
)
from core.serialization.json_export import elbow_to_dict
from core.validation.reference_comparison import DEFAULT_TOLERANCE_MM
from data.repository import ElbowRepository
from tests.golden_cases import GOLDEN_CASE_DN110_PN10_90
from ui.results_view import build_result_rows


@pytest.fixture(scope="module")
def repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


@pytest.fixture(scope="module")
def golden(repository):
    result = repository.lookup(**GOLDEN_CASE_DN110_PN10_90)
    geometry = build_segmented_elbow_geometry(result.elbow)
    return result.elbow, geometry


def test_published_dimensions_match_exactly(golden):
    params, _geometry = golden
    assert params.od_mm == 110
    assert params.thickness_mm == 6.6
    assert math.isclose(params.inside_diameter_mm, 96.8, abs_tol=1e-9)
    assert params.radius_mm == 165
    assert params.le_mm == 150
    assert params.z_mm == 315
    assert params.sdr == 17
    assert params.dn_equivalent_in == '4"'


def test_id_equation(golden):
    """ID = OD - 2e = 110 - 2(6.6) = 96.8, always computed, never looked up."""
    params, _geometry = golden
    assert math.isclose(params.od_mm - 2 * params.thickness_mm, 96.8, abs_tol=1e-9)
    assert math.isclose(params.inside_diameter_mm, 96.8, abs_tol=1e-9)


def test_z_relation_verified_against_source_data(golden):
    """Z = Le + R*tan(angle/2) = 150 + 165*tan(45) = 315.

    Tracked as GEOMETRIC_RELATION_VERIFIED_AGAINST_SOURCE_DATA, not as a
    formula quoted directly from DIN — see core/geometry/elbow_geometry.py.
    """
    from core.geometry.elbow_geometry import (
        GEOMETRIC_RELATION_VERIFIED_AGAINST_SOURCE_DATA,
        calculate_z_mm,
    )

    params, _geometry = golden
    computed = calculate_z_mm(le_mm=params.le_mm, radius_mm=params.radius_mm, angle_deg=params.angle_deg)
    assert math.isclose(computed, 315.0, abs_tol=1e-9)
    assert GEOMETRIC_RELATION_VERIFIED_AGAINST_SOURCE_DATA == "GEOMETRIC_RELATION_VERIFIED_AGAINST_SOURCE_DATA"


def test_segment_configuration_15_30_30_15(golden):
    params, geometry = golden
    config = params.segment_configuration
    assert config.is_itemized is True
    assert config.segment_angles_deg == [15.0, 30.0, 30.0, 15.0]
    assert geometry.segments_available is True
    assert len(geometry.segments) == 4


def test_sdr_has_no_unit_in_the_ui_table(golden):
    """Regression guard: SDR is dimensionless. 'SDR = 17 mm' must never
    appear — SDR must render as a bare number."""
    params, _geometry = golden
    rows = build_result_rows(params, missing_fields=[])
    sdr_row = next(label_value for label_value in rows if label_value[0] == "SDR")
    assert sdr_row[1] == "17"
    assert "mm" not in sdr_row[1]


def test_geometry_validation_passes(golden):
    params, geometry = golden
    validate_segmented_elbow_geometry(params, geometry)  # must not raise


def test_overall_dimensions_are_physically_sane(golden):
    params, geometry = golden
    overall = build_overall_dimensions(params, geometry)
    assert math.isclose(overall.height_mm, params.od_mm, rel_tol=1e-9)
    assert math.isclose(overall.z_resultant_mm, 315.0, abs_tol=1e-9)
    assert math.isclose(overall.radius_used_mm, 165.0, abs_tol=1e-9)


def test_component_registration_marks_source_data_and_defined_segments(golden):
    params, geometry = golden
    registration = register_hdpe_segmented_elbow(params, geometry)
    assert registration.compliance_status is ComplianceStatus.SOURCE_DATA
    assert registration.segment_decomposition_status is SegmentDecompositionStatus.DEFINED
    assert registration.standard.key == "DIN_16963_1"
    assert registration.material.key == "PE100"
    assert registration.provenance is not None
    assert registration.provenance.document == "Catalogo HDPE 2(1).pdf"


def test_json_export_matches_published_values(golden):
    params, geometry = golden
    registration = register_hdpe_segmented_elbow(params, geometry)
    payload = elbow_to_dict(params, geometry=geometry, registration=registration)
    component = payload["component"]

    assert component["dn_mm"] == 110
    assert component["thickness_mm"] == 6.6
    assert component["id_mm"] == 96.8
    assert component["radius_mm"] == 165
    assert component["le_mm"] == 150
    assert component["z_mm"] == 315
    assert component["sdr"] == 17
    assert component["component_family"] == "HDPE_SEGMENTED_ELBOW"
    assert component["standard"]["organization"] == "DIN"
    assert component["standard"]["code"] == "16963"
    assert component["standard"]["part"] == "1"
    assert component["material"]["grade"] == "PE100"
    assert component["compliance_status"] == "SOURCE_DATA"
    assert component["provenance"]["standard_reference"] == "DIN 16963 Part 1"


def test_tolerance_default_used_by_reference_comparison_is_reasonable():
    """Sanity guard on the editable-tolerance default (+-1/2/5mm presets)."""
    assert DEFAULT_TOLERANCE_MM == 1.0
