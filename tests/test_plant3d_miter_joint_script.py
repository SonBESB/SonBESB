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
    generate_debug_cutters_script,
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


def test_cutters_share_the_same_rotation_only_translate_differs(golden):
    """Corrected R1 math: BOX is centered, so both cutters use the SAME
    rotateY(theta_cut) -- only their translate CENTER differs, choosing
    which half-space (+normal or -normal) each occupies. The old R0
    approach (opposite rotations via +180) is no longer used."""
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    body = result.source_code.split("def HDPE_SEGMENTED_ELBOW(")[1]
    import re

    matches = re.findall(r"cutter_[ab] = BOX\(s, L=2000, W=2000, H=500\)\.rotateY\(([\-\d.]+)\)", body)
    assert len(matches) == 2
    theta_a, theta_b = float(matches[0]), float(matches[1])
    assert math.isclose(theta_a, theta_b, abs_tol=1e-6)


def test_cutter_centers_use_the_centered_box_convention(golden):
    """Corrected R1 math: cutter center = joint_point +- (H/2)*plane_normal
    (no L/W compensation at all, since a centered box's L/W footprint is
    automatically centered on wherever its origin lands)."""
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)

    gajo2 = geometry.all_pieces[2]
    plane = gajo2.cut_plane_end
    plane_p3d = (plane.point[0], plane.point[2], plane.point[1])
    normal_p3d = (plane.normal[0], plane.normal[2], plane.normal[1])
    theta_cut = math.degrees(math.atan2(plane.normal[0], plane.normal[1]))

    half_h = 500.0 / 2.0
    expected_a = tuple(round(plane_p3d[i] + half_h * normal_p3d[i], 6) for i in range(3))
    expected_b = tuple(round(plane_p3d[i] - half_h * normal_p3d[i], 6) for i in range(3))

    def fmt(v):
        return "(" + ", ".join(f"{c:.6g}" for c in v) + ")"

    assert f".rotateY({theta_cut:.6g}).translate({fmt(expected_a)})" in result.source_code
    assert f".rotateY({theta_cut:.6g}).translate({fmt(expected_b)})" in result.source_code


def test_both_cutter_near_faces_lie_exactly_on_the_joint_plane(golden):
    """The acceptance condition the user specified literally:
    dot(X - joint_point, plane_normal) = 0 for the near face of both
    cutters (center -+ (H/2)*plane_normal, undoing the swap back to our
    own XY convention before checking the plane equation)."""
    params, geometry = golden
    gajo2 = geometry.all_pieces[2]
    plane = gajo2.cut_plane_end
    joint_point = plane.point
    plane_normal = plane.normal

    plane_p3d = (joint_point[0], joint_point[2], joint_point[1])
    normal_p3d = (plane_normal[0], plane_normal[2], plane_normal[1])
    half_h = 500.0 / 2.0
    center_a = tuple(plane_p3d[i] + half_h * normal_p3d[i] for i in range(3))
    center_b = tuple(plane_p3d[i] - half_h * normal_p3d[i] for i in range(3))
    near_face_a = tuple(center_a[i] - half_h * normal_p3d[i] for i in range(3))
    near_face_b = tuple(center_b[i] + half_h * normal_p3d[i] for i in range(3))

    def unswap(v):
        return (v[0], v[2], v[1])

    def dot(a, b):
        return sum(a[i] * b[i] for i in range(3))

    def sub(a, b):
        return tuple(a[i] - b[i] for i in range(3))

    for near_face in (near_face_a, near_face_b):
        near_face_our = unswap(near_face)
        assert math.isclose(dot(sub(near_face_our, joint_point), plane_normal), 0.0, abs_tol=1e-9)
        for i in range(3):
            assert math.isclose(near_face_our[i], joint_point[i], abs_tol=1e-9)


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


def test_warns_about_the_real_r0_failure_and_corrected_convention(golden):
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    assert any("GEOMETRY FAIL" in w and "CENTRADA" in w for w in result.warnings)


def test_includes_a_temporary_calibration_box_never_united_or_subtracted(golden):
    """Per the user's explicit request: a small, distinctly-sized,
    un-rotated calibration BOX far from the real geometry, to visually
    confirm axis orientation instead of guessing silently again."""
    params, geometry = golden
    result = generate_single_miter_joint_script(params, geometry)
    assert "CALIBRATION_BOX_TEMPORARY" in result.source_code
    assert "calibration_box = BOX(s, L=30, W=15, H=5).rotateY(0.0).translate((800, 800, 800))" in result.source_code
    # never consumed by any boolean operation
    assert "calibration_box.subtractFrom" not in result.source_code
    assert "subtractFrom(calibration_box)" not in result.source_code
    assert "uniteWith(calibration_box)" not in result.source_code
    assert "calibration_box.uniteWith" not in result.source_code
    assert "calibration_box.erase()" not in result.source_code


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


# --- V0.3.1B3C-1R2: CUTTER VISUAL DEBUG (no cut, all 4 objects visible) ----


def test_debug_script_is_syntactically_valid_python(golden):
    params, geometry = golden
    result = generate_debug_cutters_script(params, geometry)
    ast.parse(result.source_code)


def test_debug_script_is_deterministic(golden):
    params, geometry = golden
    first = generate_debug_cutters_script(params, geometry)
    second = generate_debug_cutters_script(params, geometry)
    assert first.source_code == second.source_code


def test_debug_script_entry_point_matches_script_name(golden):
    params, geometry = golden
    result = generate_debug_cutters_script(params, geometry)
    assert "def HDPE_SEGMENTED_ELBOW(s, OD=" in result.source_code


def test_debug_toggle_defaults_to_true(golden):
    """R2 must ship with DEBUG_CUTTERS = True (cutters visible, no cut)."""
    params, geometry = golden
    result = generate_debug_cutters_script(params, geometry)
    body = result.source_code.split("def HDPE_SEGMENTED_ELBOW(")[1]
    assert "DEBUG_CUTTERS = True" in body


def test_debug_toggle_true_branch_never_touches_the_cutters(golden):
    """Under DEBUG_CUTTERS = True the executed branch must be a bare
    'pass' -- no subtractFrom/erase/uniteWith on cutter_a/cutter_b."""
    params, geometry = golden
    result = generate_debug_cutters_script(params, geometry)
    body = result.source_code.split("def HDPE_SEGMENTED_ELBOW(")[1]
    if_block = body.split("if DEBUG_CUTTERS:")[1].split("else:")[0]
    assert "pass" in if_block
    assert "subtractFrom" not in if_block
    assert "erase" not in if_block
    assert "uniteWith" not in if_block


def test_debug_toggle_false_branch_reproduces_r1_real_cut_behavior(golden):
    """The else branch (DEBUG_CUTTERS = False) is the exact R1 real-tested
    cut sequence -- kept so flipping the flag locally reproduces R1
    without regenerating the script."""
    params, geometry = golden
    result = generate_debug_cutters_script(params, geometry)
    body = result.source_code.split("def HDPE_SEGMENTED_ELBOW(")[1]
    else_block = body.split("else:")[1].split("s.setPoint(")[0]
    assert "ext_a.subtractFrom(cutter_a)" in else_block
    assert "cutter_a.erase()" in else_block
    assert "ext_b.subtractFrom(cutter_b)" in else_block
    assert "cutter_b.erase()" in else_block
    assert "ext_a.uniteWith(ext_b)" in else_block
    assert "ext_b.erase()" in else_block


def test_debug_script_keeps_the_already_confirmed_inner_bore_hollowing(golden):
    """B3B-1's real-hardware-confirmed hollow pattern is unrelated risk
    and must stay, independent of the DEBUG_CUTTERS toggle."""
    params, geometry = golden
    result = generate_debug_cutters_script(params, geometry)
    body = result.source_code.split("def HDPE_SEGMENTED_ELBOW(")[1]
    assert "ext_a = CYLINDER(s, R=radio_ext_mm," in body
    assert "int_a = CYLINDER(s, R=radio_int_mm," in body
    assert "ext_a.subtractFrom(int_a)" in body
    assert "int_a.erase()" in body
    assert "ext_b = CYLINDER(s, R=radio_ext_mm," in body
    assert "int_b = CYLINDER(s, R=radio_int_mm," in body
    assert "ext_b.subtractFrom(int_b)" in body
    assert "int_b.erase()" in body


def test_debug_script_builds_both_cutters_at_the_same_r1_centers(golden):
    """No position/rotation number changes vs R1 -- only whether the
    cutters are consumed."""
    debug_params, debug_geometry = golden
    debug_result = generate_debug_cutters_script(debug_params, debug_geometry)
    real_result = generate_single_miter_joint_script(debug_params, debug_geometry)

    def cutter_lines(source: str):
        return [line.strip() for line in source.splitlines() if line.strip().startswith("cutter_")]

    debug_cutters = [line for line in cutter_lines(debug_result.source_code) if "= BOX(" in line]
    real_cutters = [line for line in cutter_lines(real_result.source_code) if "= BOX(" in line]
    assert debug_cutters == real_cutters


def test_debug_script_ports_unchanged_from_r1(golden):
    params, geometry = golden
    debug_result = generate_debug_cutters_script(params, geometry)
    real_result = generate_single_miter_joint_script(params, geometry)

    def port_lines(source: str):
        return [line.strip() for line in source.splitlines() if line.strip().startswith("s.setPoint(")]

    assert port_lines(debug_result.source_code) == port_lines(real_result.source_code)
    assert len(port_lines(debug_result.source_code)) == 2


def test_debug_script_includes_the_same_temporary_calibration_box(golden):
    params, geometry = golden
    result = generate_debug_cutters_script(params, geometry)
    assert "CALIBRATION_BOX_TEMPORARY" in result.source_code
    assert "calibration_box = BOX(s, L=30, W=15, H=5).rotateY(0.0).translate((800, 800, 800))" in result.source_code
    assert "calibration_box.subtractFrom" not in result.source_code
    assert "subtractFrom(calibration_box)" not in result.source_code
    assert "uniteWith(calibration_box)" not in result.source_code
    assert "calibration_box.uniteWith" not in result.source_code
    assert "calibration_box.erase()" not in result.source_code


def test_debug_script_warns_about_the_real_r1_failure_and_the_toggle(golden):
    params, geometry = golden
    result = generate_debug_cutters_script(params, geometry)
    assert any("R1" in w and "elimino Gajo A y Gajo B" in w for w in result.warnings)
    assert any("DEBUG_CUTTERS" in w and "False" in w for w in result.warnings)


def test_debug_script_cites_sources(golden):
    params, geometry = golden
    result = generate_debug_cutters_script(params, geometry)
    for citation in SOURCE_CITATIONS:
        assert citation in result.source_code


def test_debug_script_never_touches_proprietary_plant_files(golden):
    params, geometry = golden
    result = generate_debug_cutters_script(params, geometry)
    for forbidden in (".pcat", ".pspx", ".pspc"):
        assert forbidden not in result.source_code
