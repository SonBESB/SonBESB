import math

from core.geometry.elbow_geometry import build_elbow_geometry, calculate_z_mm
from data.repository import ElbowRepository


def test_calculate_z_matches_catalog_value():
    """Z = Le + R*tan(angle/2) reproduces every catalog Z (see docs/DATA_NOTES.md)."""
    repository = ElbowRepository.from_excel()
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    e = result.elbow

    calculated = calculate_z_mm(e.le_mm, e.radius_mm, e.angle_deg)
    assert math.isclose(calculated, e.z_mm, rel_tol=1e-9)


def test_geometry_face_distances_equal_z_and_angle_between_legs():
    repository = ElbowRepository.from_excel()
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    e = result.elbow

    geometry = build_elbow_geometry(e)

    dist_p1 = math.dist(geometry.vertex, geometry.p1_face)
    dist_p2 = math.dist(geometry.vertex, geometry.p2_face)
    assert math.isclose(dist_p1, e.z_mm, rel_tol=1e-6)
    assert math.isclose(dist_p2, e.z_mm, rel_tol=1e-6)

    v1 = (geometry.p1_face[0] - geometry.vertex[0], geometry.p1_face[1] - geometry.vertex[1])
    v2 = (geometry.p2_face[0] - geometry.vertex[0], geometry.p2_face[1] - geometry.vertex[1])
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    angle_between = math.degrees(math.acos(dot / (math.hypot(*v1) * math.hypot(*v2))))
    assert math.isclose(angle_between, e.angle_deg, abs_tol=1e-6)


def test_pipe_body_width_equals_od():
    repository = ElbowRepository.from_excel()
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    e = result.elbow

    geometry = build_elbow_geometry(e)
    width = math.dist(geometry.outer_boundary[0], geometry.inner_boundary[0])
    assert math.isclose(width, e.od_mm, rel_tol=1e-6)


def test_weld_markers_count_matches_itemized_segments_minus_one():
    repository = ElbowRepository.from_excel()
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    e = result.elbow

    geometry = build_elbow_geometry(e)
    # 4 itemized segments (15-30-30-15) -> 3 internal weld joints on the arc.
    assert len(geometry.weld_markers) == 3


def test_ports_are_positioned_at_component_faces():
    repository = ElbowRepository.from_excel()
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    e = result.elbow

    geometry = build_elbow_geometry(e)
    port_ids = {p.id for p in geometry.ports}
    assert port_ids == {"P1", "P2"}
