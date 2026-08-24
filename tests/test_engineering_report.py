import math

import pytest

from core.geometry.engineering_report import (
    build_fabrication_table,
    build_overall_dimensions,
    build_union_table,
)
from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from data.repository import ElbowRepository


@pytest.fixture(scope="module")
def repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


@pytest.fixture(scope="module")
def golden(repository):
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    geometry = build_segmented_elbow_geometry(result.elbow)
    return result.elbow, geometry


def test_fabrication_table_row_count_and_angles(golden):
    params, geometry = golden
    rows = build_fabrication_table(params, geometry)

    assert len(rows) == 4
    assert [r.angle_deg for r in rows] == [15.0, 30.0, 30.0, 15.0]
    assert [r.cumulative_angle_deg for r in rows] == [15.0, 45.0, 75.0, 90.0]


def test_fabrication_table_outer_inner_lengths_bracket_axis_length(golden):
    """Outer (extrados) must be longer than the axis, inner (intrados)
    shorter — and their average must equal the axis length exactly, since
    both are measured from the same symmetric bisector cut planes."""
    params, geometry = golden
    rows = build_fabrication_table(params, geometry)

    for row in rows:
        assert row.outer_length_approx_mm > row.axis_length_mm > row.inner_length_approx_mm
        average = (row.outer_length_approx_mm + row.inner_length_approx_mm) / 2
        assert math.isclose(average, row.axis_length_mm, rel_tol=1e-9)


def test_fabrication_table_is_symmetric_for_symmetric_configuration(golden):
    """15-30-30-15 is a palindrome: gajo 1 and gajo 4 (and 2/3) must match."""
    params, geometry = golden
    rows = build_fabrication_table(params, geometry)

    assert math.isclose(rows[0].axis_length_mm, rows[3].axis_length_mm, rel_tol=1e-9)
    assert math.isclose(rows[0].outer_length_approx_mm, rows[3].outer_length_approx_mm, rel_tol=1e-9)
    assert math.isclose(rows[1].axis_length_mm, rows[2].axis_length_mm, rel_tol=1e-9)


def test_cut_plane_angles_match_known_bisector_pattern(golden):
    """Matches the 3.75/11.25/15/11.25/3.75 pattern already verified in
    tests/test_segmented_elbow.py::test_every_joint_cut_plane_bisects_symmetrically."""
    params, geometry = golden
    rows = build_fabrication_table(params, geometry)

    assert math.isclose(rows[0].start_cut_plane_angle_deg, 3.75, abs_tol=1e-6)
    assert math.isclose(rows[0].end_cut_plane_angle_deg, 11.25, abs_tol=1e-6)
    assert math.isclose(rows[1].start_cut_plane_angle_deg, 11.25, abs_tol=1e-6)
    assert math.isclose(rows[1].end_cut_plane_angle_deg, 15.0, abs_tol=1e-6)


def test_union_table_labels_and_distances(golden):
    params, geometry = golden
    rows = build_fabrication_table(params, geometry)
    unions = build_union_table(geometry)

    assert len(unions) == 5  # T1, 3 interior joints, T2
    assert unions[0].label.startswith("T1")
    assert unions[-1].label.startswith("T2")
    assert unions[-1].distance_to_next_mm == 0.0

    # Distance between consecutive unions must equal the corresponding
    # gajo's own axis length (recomputed via raw coordinates here, not by
    # reusing ElbowSegment.length_mm — an independent cross-check).
    for i, row in enumerate(rows):
        assert math.isclose(unions[i].distance_to_next_mm, row.axis_length_mm, rel_tol=1e-9)


def test_overall_dimensions_match_golden_case(golden):
    params, geometry = golden
    overall = build_overall_dimensions(params, geometry)

    assert math.isclose(overall.height_mm, params.od_mm, rel_tol=1e-9)  # exact for a planar elbow
    assert math.isclose(overall.p1_p2_distance_mm, 1093.1870837144024, rel_tol=1e-6)
    assert math.isclose(overall.p1_to_vertex_mm, 773.0, abs_tol=1e-6)
    assert math.isclose(overall.p2_to_vertex_mm, 773.0, abs_tol=1e-6)
    assert overall.radius_used_mm == 473.0
    assert overall.z_resultant_mm == 773.0
    assert overall.width_mm > 0
    assert overall.length_mm > 0


def test_30_degrees_has_no_fabrication_or_union_rows_but_overall_dims_still_work(repository):
    result = repository.lookup(dn_mm=110, pn_label="PN10", angle_deg=30)
    geometry = build_segmented_elbow_geometry(result.elbow)

    assert build_fabrication_table(result.elbow, geometry) == []
    assert build_union_table(geometry) == []

    overall = build_overall_dimensions(result.elbow, geometry)
    assert overall.height_mm == pytest.approx(result.elbow.od_mm)
    assert overall.p1_to_vertex_mm == pytest.approx(result.elbow.z_mm)
