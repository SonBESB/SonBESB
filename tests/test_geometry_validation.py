from dataclasses import replace

import pytest

from core.geometry.geometry_validation import GeometryValidationError, validate_segmented_elbow_geometry
from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from core.models.elbow import SegmentConfiguration
from data.repository import ElbowRepository


@pytest.fixture(scope="module")
def repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


@pytest.mark.parametrize("angle", [30, 45, 60, 90])
def test_golden_dn315_passes_validation_at_every_angle(repository, angle):
    """Regression guard: this must pass for EVERY angle, not just 90 — a
    validator bug once passed only at 90 because sin(45)==cos(45) masked a
    wrong reference angle (see geometry_validation.py check 1's comment)."""
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=angle)
    geometry = build_segmented_elbow_geometry(result.elbow)
    validate_segmented_elbow_geometry(result.elbow, geometry)  # must not raise


def test_mismatched_segment_sum_raises_geometry_validation_error(repository):
    """Never silently adjust: a segment config that doesn't sum to
    angle_deg must raise, carrying the found-vs-expected difference."""
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    broken_config = SegmentConfiguration(
        total_angle_deg=90.0, is_itemized=True, segment_angles_deg=[15.0, 30.0, 30.0, 10.0]
    )
    broken_params = replace(result.elbow, segment_configuration=broken_config)
    geometry = build_segmented_elbow_geometry(broken_params)

    with pytest.raises(GeometryValidationError) as exc_info:
        validate_segmented_elbow_geometry(broken_params, geometry)

    codes = {f.code for f in exc_info.value.failures}
    assert "SEGMENT_ANGLE_SUM_MISMATCH" in codes
    failure = next(f for f in exc_info.value.failures if f.code == "SEGMENT_ANGLE_SUM_MISMATCH")
    assert failure.expected == 90.0
    assert failure.found == 85.0
    assert failure.difference == 5.0


def test_mismatched_angle_deg_raises(repository):
    """A params.angle_deg that disagrees with the geometry's own built
    direction (simulated by mutating angle_deg after building) is caught."""
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    geometry = build_segmented_elbow_geometry(result.elbow)
    tampered_params = replace(result.elbow, angle_deg=91.0)

    with pytest.raises(GeometryValidationError) as exc_info:
        validate_segmented_elbow_geometry(tampered_params, geometry)

    codes = {f.code for f in exc_info.value.failures}
    assert "ANGLE_MISMATCH" in codes
