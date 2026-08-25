"""V0.3.1B3C-1 tests for plant3d/generators/miter_joint_script_generator.py.

An isolated fixture: only Gajo 2 + Gajo 3 (the representative 30/30
joint), both already hollow (same subtractFrom()+erase() pattern
real-hardware-confirmed by B3B-1/B3B-2), cut against their real shared
bisector plane using BOX(...) as the cutter -- the first Plant 3D API
element in this project used without hardware confirmation since the
original best-effort CYLINDER guess in early V0.3.1A. Does NOT touch
segmented_elbow_script_generator.py's already-validated 6-piece chain.
"""

import ast
import math

from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from data.repository import ElbowRepository
from plant3d.generators.miter_joint_script_generator import (
    SOURCE_CITATIONS,
    generate_single_miter_joint_script,
)
from tests.golden_cases import GOLDEN_CASE_DN110_PN10_90

import pytest


@pytest.fixture(scope="module")
def repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


@pytest.fixture(scope="module")
def golden(repository):
    result = repository.lookup(**GOLDEN_CASE_DN110_PN10_90)
    params = result.elbow
    geometry = build_segmented_elbow_geometry(params)
    return params, geometry


def test_script_is_syntactically_valid_python(golden):
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    ast.parse(result.source_code)


def test_script_is_deterministic(golden):
    params, geometry = golden
    first = generate_single_miter_joint_script(params, geometry)
    second = generate_single_miter_joint_script(params, geometry)
    assert first.source_code == second.source_code


def test_entry_point_matches_script_name(golden):
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    assert "def HDPE_SEGMENTED_ELBOW(s, OD=" in result.source_code


def test_gajo2_and_gajo3_share_the_same_bisector_plane(golden):
    """The whole point of a miter joint: both pieces must cut against
    the SAME plane, not two independently-derived ones."""
    params, geometry = golden
    gajo2, gajo3 = geometry.all_pieces[2], geometry.all_pieces[3]
    assert gajo2.cut_plane_end.point == gajo3.cut_plane_start.point
    assert gajo2.cut_plane_end.normal == gajo3.cut_plane_start.normal
    assert gajo2.angle_deg == 30.0
    assert gajo3.angle_deg == 30.0


def test_builds_two_hollow_pieces_with_the_already_confirmed_pattern(golden):
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    body = result.source_code.split("def HDPE_SEGMENTED_ELBOW(")[1]
    assert "ext_a = CYLINDER(s, R=radio_ext_mm," in body
    assert "int_a = CYLINDER(s, R=radio_int_mm," in body
    assert "ext_a.subtractFrom(int_a)" in body
    assert "int_a.erase()" in body
    assert "ext_b = CYLINDER(s, R=radio_ext_mm," in body
    assert "int_b = CYLINDER(s, R=radio_int_mm," in body
    assert "ext_b.subtractFrom(int_b)" in body
    assert "int_b.erase()" in body


def test_uses_box_as_cutter_with_only_l_w_h_no_o(golden):
    """BOX(s, L, W, H) is confirmed to NOT accept an O parameter
    (unlike CYLINDER) -- must never be passed one."""
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    body = result.source_code.split("def HDPE_SEGMENTED_ELBOW(")[1]
    assert "cutter_a = BOX(s, L=2000, W=2000, H=500)" in body
    assert "cutter_b = BOX(s, L=2000, W=2000, H=500)" in body
    for line in body.splitlines():
        if "BOX(" in line:
            assert "O=" not in line


def test_cuts_each_piece_against_the_cutter_and_unites_afterward(golden):
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    body = result.source_code.split("def HDPE_SEGMENTED_ELBOW(")[1]
    assert "ext_a.subtractFrom(cutter_a)" in body
    assert "cutter_a.erase()" in body
    assert "ext_b.subtractFrom(cutter_b)" in body
    assert "cutter_b.erase()" in body
    # union happens AFTER both pieces are cut
    cut_a_idx = body.index("ext_a.subtractFrom(cutter_a)")
    cut_b_idx = body.index("ext_b.subtractFrom(cutter_b)")
    union_idx = body.index("ext_a.uniteWith(ext_b)")
    assert cut_a_idx < union_idx
    assert cut_b_idx < union_idx


def test_cutter_rotations_are_opposite_180_degrees_apart(golden):
    """cutter_a removes the +normal side from Gajo 2, cutter_b removes
    the -normal side from Gajo 3 -- same rotateY axis, opposite
    direction, achieved via a 180 degree offset (no new rotation axis
    invented)."""
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    body = result.source_code.split("def HDPE_SEGMENTED_ELBOW(")[1]
    import re

    matches = re.findall(r"cutter_[ab] = BOX\(s, L=2000, W=2000, H=500\)\.rotateY\(([\-\d.]+)\)", body)
    assert len(matches) == 2
    theta_a, theta_b = float(matches[0]), float(matches[1])
    assert math.isclose(abs(theta_b - theta_a), 180.0, abs_tol=1e-6)


def test_cutter_translate_centers_on_the_plane_point_under_corner_assumption(golden):
    """Verify the disclosed compensation math independently: rotating
    the box's own (-L/2, -W/2, 0) local shift by the same theta and
    adding it to the plane point must match what the generator emitted."""
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)

    gajo2 = geometry.all_pieces[2]
    plane = gajo2.cut_plane_end
    plane_p3d = (plane.point[0], plane.point[2], plane.point[1])
    theta_cut = math.degrees(math.atan2(plane.normal[0], plane.normal[1]))

    def rotate_y(v, theta_deg):
        theta = math.radians(theta_deg)
        x, y, z = v
        return (x * math.cos(theta) + z * math.sin(theta), y, -x * math.sin(theta) + z * math.cos(theta))

    shift = (-1000.0, -1000.0, 0.0)
    expected_a = tuple(round(plane_p3d[i] + rotate_y(shift, theta_cut)[i], 6) for i in range(3))
    expected_b = tuple(round(plane_p3d[i] + rotate_y(shift, theta_cut + 180.0)[i], 6) for i in range(3))

    def fmt(v):
        return "(" + ", ".join(f"{c:.6g}" for c in v) + ")"

    assert f".rotateY({theta_cut:.6g}).translate({fmt(expected_a)})" in result.source_code
    assert f".rotateY({theta_cut + 180.0:.6g}).translate({fmt(expected_b)})" in result.source_code


def test_does_not_touch_the_other_two_joints(golden):
    """B3C-1 must be isolated to the Gajo2/Gajo3 joint only -- no Gajo 1,
    Gajo 4, or the Le stubs, no six-piece chain."""
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    body = result.source_code.split("def HDPE_SEGMENTED_ELBOW(")[1]
    assert "pieza_" not in body
    assert body.count("CYLINDER(") == 4  # ext_a, int_a, ext_b, int_b only


def test_ports_at_the_free_ends_pointing_outward(golden):
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    gajo2, gajo3 = geometry.all_pieces[2], geometry.all_pieces[3]

    def fmt(v):
        return "(" + ", ".join(f"{round(c, 6):.6g}" for c in v) + ")"

    p1_pos = fmt((gajo2.axis_start[0], gajo2.axis_start[2], gajo2.axis_start[1]))
    p2_pos = fmt((gajo3.axis_end[0], gajo3.axis_end[2], gajo3.axis_end[1]))
    assert f"s.setPoint({p1_pos}," in result.source_code
    assert f"s.setPoint({p2_pos}," in result.source_code


def test_is_clearly_marked_not_the_full_elbow(golden):
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    assert "VALIDATION_MITER_JOINT_ONLY" in result.source_code
    assert "NO es el codo completo" in result.source_code


def test_warns_about_the_unconfirmed_box_origin_assumption(golden):
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    assert any("BOX" in w and "NO esta confirmada" in w for w in result.warnings)


def test_cites_sources(golden):
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    for citation in SOURCE_CITATIONS:
        assert citation in result.source_code


def test_never_touches_proprietary_plant_files(golden):
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    for forbidden in (".pcat", ".pspx", ".pspc"):
        assert forbidden not in result.source_code
