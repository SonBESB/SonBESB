import math

import pytest

from components.elbows.hdpe_segmented_elbow import build_custom
from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from core.models.common import ComponentMode, EndType
from core.models.elbow import ElbowParameters, SegmentConfiguration
from core.validation.elbow_validation import has_blocking_errors
from data.repository import ElbowRepository


@pytest.fixture(scope="module")
def repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


def _angle_between(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


@pytest.mark.parametrize("angle,expected_segment_count", [(45, 3), (60, 3), (90, 4)])
def test_golden_dn315_itemized_angles(repository, angle, expected_segment_count):
    """DN315/PN10 at every itemized angle: gajos close correctly."""
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=angle)
    geometry = build_segmented_elbow_geometry(result.elbow)

    assert geometry.segments_available is True
    assert len(geometry.segments) == expected_segment_count
    assert math.isclose(sum(s.angle_deg for s in geometry.segments), angle, abs_tol=1e-9)

    # Every gajo joint lies exactly on the tabulated R-radius circle.
    for segment in geometry.segments:
        assert math.isclose(math.dist(geometry.arc_center, segment.axis_start), result.elbow.radius_mm, abs_tol=1e-6)
        assert math.isclose(math.dist(geometry.arc_center, segment.axis_end), result.elbow.radius_mm, abs_tol=1e-6)

    # First/last gajo joints coincide with the tangent points.
    assert math.dist(geometry.segments[0].axis_start, geometry.tangent_point_1) < 1e-6
    assert math.dist(geometry.segments[-1].axis_end, geometry.tangent_point_2) < 1e-6

    # The true deflection angle (flow direction P1->P2) equals angle_deg —
    # NOT the angle between the outward p1_direction/p2_direction vectors,
    # which is (180 - angle_deg) instead (see geometry_validation.py).
    flow_angle = _angle_between(geometry.leg1_stub.direction, geometry.leg2_stub.direction)
    assert math.isclose(flow_angle, angle, abs_tol=1e-6)
    outward_angle = _angle_between(geometry.p1_direction, geometry.p2_direction)
    assert math.isclose(outward_angle, 180 - angle, abs_tol=1e-6)


def test_every_joint_cut_plane_bisects_symmetrically(repository):
    """The miter plane at each joint must split the local turn evenly."""
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    geometry = build_segmented_elbow_geometry(result.elbow)
    pieces = geometry.all_pieces

    for a, b in zip(pieces[:-1], pieces[1:]):
        # Both pieces must reference the identical joint plane.
        assert math.dist(a.cut_plane_end.point, b.cut_plane_start.point) < 1e-9
        assert math.dist(a.cut_plane_end.normal, b.cut_plane_start.normal) < 1e-9

        normal = a.cut_plane_end.normal
        angle_a = _angle_between(a.direction, normal)
        angle_b = _angle_between(b.direction, normal)
        assert math.isclose(angle_a, angle_b, abs_tol=1e-6)


def test_p1_p2_end_faces_are_perpendicular_not_mitred(repository):
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    geometry = build_segmented_elbow_geometry(result.elbow)

    p1_normal = geometry.leg1_stub.cut_plane_start.normal
    angle = _angle_between(geometry.leg1_stub.direction, p1_normal)
    assert math.isclose(angle, 0.0, abs_tol=1e-6) or math.isclose(angle, 180.0, abs_tol=1e-6)


def test_small_and_large_dn(repository):
    for dn_mm, pn_label in [(110, "PN10"), (1600, "PN4")]:
        result = repository.lookup(dn_mm=dn_mm, pn_label=pn_label, angle_deg=90)
        assert result.elbow is not None, f"expected DN{dn_mm}/{pn_label}/90 to be available"
        geometry = build_segmented_elbow_geometry(result.elbow)
        assert len(geometry.segments) == 4
        assert math.isclose(sum(s.angle_deg for s in geometry.segments), 90.0, abs_tol=1e-9)


def test_not_available_dn_pn_combination_has_no_elbow_to_build_from(repository):
    """N/D combination: repository refuses before geometry is ever attempted."""
    result = repository.lookup(dn_mm=560, pn_label="PN20", angle_deg=90)
    assert result.elbow is None


def test_30_degrees_has_no_gajo_geometry(repository):
    result = repository.lookup(dn_mm=110, pn_label="PN10", angle_deg=30)
    geometry = build_segmented_elbow_geometry(result.elbow)

    assert geometry.segments_available is False
    assert geometry.segments is None
    assert geometry.unavailable_reason
    # The two stubs are still well-defined (Le/T1/T2 are tabulated), just
    # not bridged by any invented gajo geometry.
    assert geometry.leg1_stub.length_mm > 0
    assert geometry.leg2_stub.length_mm > 0
    assert math.dist(geometry.tangent_point_1, geometry.tangent_point_2) > 0


def _custom_params(**overrides) -> ElbowParameters:
    defaults = dict(
        mode=ComponentMode.CUSTOM,
        od_mm=630.0,
        thickness_mm=37.4,
        angle_deg=73.0,
        radius_mm=900.0,
        le_mm=350.0,
        z_mm=None,
        end_type=EndType.BUTT_FUSION,
        din16963_compliant=False,
    )
    defaults.update(overrides)
    return ElbowParameters(**defaults)


def test_invalid_radius_collapses_gajo_joints_and_raises():
    """A zero radius, when an itemized segment config IS present, collapses
    every gajo joint onto the same point (a zero-length direction vector)."""
    config = SegmentConfiguration(total_angle_deg=73.0, is_itemized=True, segment_angles_deg=[36.5, 36.5])
    params = _custom_params(radius_mm=0.0, segment_configuration=config)
    with pytest.raises(ValueError):
        build_segmented_elbow_geometry(params)


def test_invalid_radius_is_rejected_before_reaching_geometry():
    """The normal Modo B path (build_custom) never lets a bad radius reach
    the geometry builder at all — validated at the input boundary instead."""
    params, issues = build_custom(od_mm=630.0, thickness_mm=37.4, angle_deg=73.0, radius_mm=-5.0, le_mm=350.0)
    assert has_blocking_errors(issues)


def test_invalid_thickness_is_rejected_before_reaching_geometry():
    params, issues = build_custom(od_mm=50.0, thickness_mm=30.0, angle_deg=73.0, radius_mm=900.0, le_mm=350.0)
    assert has_blocking_errors(issues)


def test_segment_angle_sum_mismatch_does_not_reach_total_angle():
    """A segment configuration whose angles don't sum to angle_deg still
    builds (the geometry builder itself doesn't police this — it only
    consumes segment_angles_deg as given); the mismatch is what
    core/geometry/geometry_validation.py's GEOMETRY_VALIDATION_ERROR
    exists to catch (see tests/test_geometry_validation.py)."""
    config = SegmentConfiguration(total_angle_deg=90.0, is_itemized=True, segment_angles_deg=[15.0, 30.0, 30.0, 10.0])
    params = _custom_params(angle_deg=90.0, radius_mm=473.0, le_mm=300.0, segment_configuration=config)
    geometry = build_segmented_elbow_geometry(params)
    assert sum(s.angle_deg for s in geometry.segments) != 90.0
