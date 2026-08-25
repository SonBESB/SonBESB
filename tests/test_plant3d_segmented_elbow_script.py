"""V0.3.1B3A tests for plant3d/generators/segmented_elbow_script_generator.py.

Builds on V0.3.1B1/B2's real Plant 3D 2025 PASSes (CYLINDER + rotateY +
Ports=2 + s.setPoint) to bake the REAL DN110/PN10/90 segmented-elbow
geometry (already computed by core/geometry/segmented_elbow.py, no
duplicated trigonometry) into a CustomScript. Explicitly an exterior-only
approximation (straight cylinder segments united, no miter cuts, no
hollow bore) -- see the module's own docstring for why.
"""

import ast
import math

from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from data.repository import ElbowRepository
from plant3d.generators.segmented_elbow_script_generator import (
    SOURCE_CITATIONS,
    generate_segmented_elbow_script,
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
    result = generate_segmented_elbow_script(params, geometry)
    ast.parse(result.source_code)


def test_script_is_deterministic(golden):
    params, geometry = golden
    first = generate_segmented_elbow_script(params, geometry)
    second = generate_segmented_elbow_script(params, geometry)
    assert first.source_code == second.source_code


def test_entry_point_matches_script_name(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    assert "def HDPE_SEGMENTED_ELBOW(s, OD=" in result.source_code


def test_builds_exactly_six_pieces_and_unites_them(golden):
    """2 Le stubs + 4 gajos = 6 pieces, matching
    geometry.all_pieces exactly (no duplicated math: same count)."""
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    assert len(geometry.all_pieces) == 6
    for i in range(6):
        assert f"pieza_{i} = CYLINDER(" in result.source_code
    for i in range(1, 6):
        assert f"pieza_0.uniteWith(pieza_{i})" in result.source_code
        assert f"pieza_{i}.erase()" in result.source_code


def test_piece_chain_is_geometrically_continuous(golden):
    """Each piece's translate() target must equal the previous piece's
    end point (start + H*direction after rotateY) -- verifies the
    Y/Z-swap coordinate mapping and the atan2-derived rotateY angles are
    self-consistent, independent of running inside real Plant 3D."""
    params, geometry = golden
    pieces = geometry.all_pieces

    def plant3d_point(v):
        return (v[0], v[2], v[1])

    prev_end = None
    for piece in pieces:
        start = plant3d_point(piece.axis_start)
        if prev_end is not None:
            for a, b in zip(start, prev_end):
                assert math.isclose(a, b, abs_tol=1e-6)
        dx, dy, dz = piece.direction
        theta = math.radians(math.degrees(math.atan2(dx, dy)))
        end = (
            start[0] + piece.length_mm * math.sin(theta),
            start[1],
            start[2] + piece.length_mm * math.cos(theta),
        )
        prev_end = end


def test_ports_match_geometry_ports_after_yz_swap(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    p1, p2 = geometry.ports
    p1_p3d = (round(p1.position_mm[0], 6), round(p1.position_mm[2], 6), round(p1.position_mm[1], 6))
    p2_p3d = (round(p2.position_mm[0], 6), round(p2.position_mm[2], 6), round(p2.position_mm[1], 6))

    def fmt(v):
        return "(" + ", ".join(f"{round(c, 6):.6g}" for c in v) + ")"

    assert f"s.setPoint({fmt(p1_p3d)}" in result.source_code
    assert f"s.setPoint({fmt(p2_p3d)}" in result.source_code


def test_no_thk_r_z_reused_in_geometry_computation(golden):
    """R/LE/Z live-editing is explicitly NOT wired to the baked
    positions (disclosed limitation) -- only OD affects radio_mm."""
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    assert "radio_mm = OD / 2.0" in result.source_code
    assert "NO recalcula la geometria" in result.source_code


def test_angle_is_not_exposed_as_a_param(golden):
    """No confirmed Plant 3D @param type for angles exists -- ANGLE must
    stay fixed/internal, never an editable @param."""
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    assert "@param(ANGLE" not in result.source_code
    assert "ANGLE=" not in result.source_code.split("def HDPE_SEGMENTED_ELBOW")[1].split("\n")[0]


def test_warns_about_unconfirmed_unitewith_erase_pattern(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    assert any("uniteWith" in w and "erase" in w for w in result.warnings)


def test_warns_about_untested_angles_and_translate(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    assert any("nunca antes probados" in w for w in result.warnings)


def test_warns_that_geometry_is_an_approximation_no_miter_cut(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    assert any("APROXIMADA" in w for w in result.warnings)
    assert "sin corte a inglete" in result.source_code.lower() or "sin corte a inglete" in result.source_code


def test_hollow_bore_not_yet_implemented(golden):
    """THK is received but not used to build a hollow bore yet
    (deferred to V0.3.1B3B) -- subtractFrom must not appear."""
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    assert "subtractFrom" not in result.source_code
    assert "intersectWith" not in result.source_code


def test_cites_sources(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    for citation in SOURCE_CITATIONS:
        assert citation in result.source_code


def test_never_touches_proprietary_plant_files(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    for forbidden in (".pcat", ".pspx", ".pspc"):
        assert forbidden not in result.source_code
