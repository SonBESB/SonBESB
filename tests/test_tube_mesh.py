import numpy as np
import pytest

from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from core.geometry.tube_mesh import build_piece_meshes
from data.repository import ElbowRepository


@pytest.fixture(scope="module")
def repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


def _perpendicular_distance_to_axis(points: np.ndarray, axis_point: np.ndarray, direction: np.ndarray) -> np.ndarray:
    to_points = points - axis_point
    projection_length = to_points @ direction
    perpendicular = to_points - np.outer(projection_length, direction)
    return np.linalg.norm(perpendicular, axis=1)


def test_mesh_piece_count_and_no_nan(repository):
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    geometry = build_segmented_elbow_geometry(result.elbow)
    meshes = build_piece_meshes(geometry, od_mm=result.elbow.od_mm, id_mm=result.elbow.inside_diameter_mm, samples=24)

    assert len(meshes) == 6  # leg1 stub + 4 gajos + leg2 stub
    for mesh in meshes:
        assert not np.isnan(mesh.vertices).any()
        assert mesh.triangles.max() < len(mesh.vertices)
        assert mesh.triangles.min() >= 0


def test_outer_and_inner_ring_radii_match_od_and_id(repository):
    """Independent check: perpendicular distance from a piece's own axis to
    its ring vertices must equal od/2 and id/2 — this is what
    core/geometry/geometry_validation.py's docstring calls out as the
    honest home for the spec's "OD generado = OD solicitado" check."""
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    e = result.elbow
    geometry = build_segmented_elbow_geometry(e)
    meshes = build_piece_meshes(geometry, od_mm=e.od_mm, id_mm=e.inside_diameter_mm, samples=24)

    stub = meshes[0]
    axis_point = np.array(geometry.leg1_stub.axis_start)
    direction = np.array(geometry.leg1_stub.direction)
    samples = 24

    outer_start = stub.vertices[:samples]
    inner_start = stub.vertices[2 * samples : 3 * samples]

    outer_dist = _perpendicular_distance_to_axis(outer_start, axis_point, direction)
    inner_dist = _perpendicular_distance_to_axis(inner_start, axis_point, direction)

    assert np.allclose(outer_dist, e.od_mm / 2, atol=1e-6)
    assert np.allclose(inner_dist, e.inside_diameter_mm / 2, atol=1e-6)


def test_mesh_works_for_non_itemized_angle_with_gap(repository):
    """30 degrees: only the two stubs get meshed, no gajo geometry."""
    result = repository.lookup(dn_mm=110, pn_label="PN10", angle_deg=30)
    geometry = build_segmented_elbow_geometry(result.elbow)
    meshes = build_piece_meshes(geometry, od_mm=result.elbow.od_mm, id_mm=result.elbow.inside_diameter_mm, samples=16)

    assert len(meshes) == 2  # only leg1_stub + leg2_stub, no gajos
    for mesh in meshes:
        assert not np.isnan(mesh.vertices).any()
