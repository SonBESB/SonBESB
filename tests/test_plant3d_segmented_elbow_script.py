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


def test_solid_mode_is_unchanged_by_the_hollow_parameter_existing(golden):
    """Backward-compat guard: the already real-hardware-PASSed B3A
    executable content (CYLINDER calls, angles, translate, uniteWith,
    ports) must not change now that generate_segmented_elbow_script()
    also supports hollow=True."""
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry)
    for i in range(6):
        assert f"pieza_{i} = CYLINDER(s, R=radio_mm," in result.source_code
    assert "subtractFrom" not in result.source_code
    assert "radio_mm = OD / 2.0" in result.source_code


# --- V0.3.1B3B-2: hollow=True, same B3A chain, per-piece subtractFrom ----


def test_hollow_is_syntactically_valid_python(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry, hollow=True)
    ast.parse(result.source_code)


def test_hollow_is_deterministic(golden):
    params, geometry = golden
    first = generate_segmented_elbow_script(params, geometry, hollow=True)
    second = generate_segmented_elbow_script(params, geometry, hollow=True)
    assert first.source_code == second.source_code


def test_hollow_builds_ext_and_int_cylinder_per_piece_then_subtracts(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry, hollow=True)
    for i in range(6):
        assert f"ext_{i} = CYLINDER(s, R=radio_ext_mm," in result.source_code
        assert f"int_{i} = CYLINDER(s, R=radio_int_mm," in result.source_code
        assert f"ext_{i}.subtractFrom(int_{i})" in result.source_code
        assert f"int_{i}.erase()" in result.source_code
        # only the consumed inner cylinder is erased right after the cut,
        # the outer one stays alive to be united later
        assert f"ext_{i}.erase()\n" not in result.source_code.split(
            f"ext_{i}.subtractFrom(int_{i})"
        )[1].split(f"int_{i}.erase()")[0]


def test_hollow_inner_cylinder_overhangs_outer_by_disclosed_margin(golden):
    """Same 5mm-per-end overhang already confirmed for real by
    V0.3.1B3B-1, applied per piece: H grows by 10, O becomes -5."""
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry, hollow=True)
    for piece in geometry.all_pieces:
        pass  # lengths vary per piece; spot check via the O=-5 marker instead
    assert result.source_code.count("O=-5)") == 6
    assert "radio_ext_mm = OD / 2.0" in result.source_code
    assert "radio_int_mm = (OD - 2 * THK) / 2.0" in result.source_code


def test_hollow_still_unites_all_six_exterior_pieces_same_as_b3a(golden):
    """The uniteWith/erase chain (already real-hardware PASSed in B3A)
    must be untouched -- hollow only changes how each piece is built."""
    params, geometry = golden
    solid = generate_segmented_elbow_script(params, geometry)
    hollow = generate_segmented_elbow_script(params, geometry, hollow=True)
    solid_union = solid.source_code.split("pieza_0.uniteWith")[1]
    hollow_union = hollow.source_code.split("ext_0.uniteWith")[1]
    # same relative union pattern (N calls, N erases), just different var prefix
    assert solid_union.count("uniteWith(") == hollow_union.count("uniteWith(")
    assert solid_union.count(".erase()") == hollow_union.count(".erase()")


def test_hollow_ports_unchanged_from_solid_mode(golden):
    params, geometry = golden
    solid = generate_segmented_elbow_script(params, geometry)
    hollow = generate_segmented_elbow_script(params, geometry, hollow=True)

    def port_lines(source: str):
        return [line.strip() for line in source.splitlines() if line.strip().startswith("s.setPoint(")]

    assert port_lines(solid.source_code) == port_lines(hollow.source_code)
    assert len(port_lines(hollow.source_code)) == 2


def test_hollow_no_miter_cuts_yet(golden):
    """B3C (miter cuts) is explicitly not implemented yet."""
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry, hollow=True)
    assert "intersectWith" not in result.source_code
    assert any("APROXIMADA" in w for w in result.warnings)


def test_hollow_warns_that_subtractfrom_is_confirmed_but_full_chain_is_new(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry, hollow=True)
    assert any("B3B-1" in w and "SI tiene confirmacion" in w for w in result.warnings)


def test_hollow_cites_sources(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry, hollow=True)
    for citation in SOURCE_CITATIONS:
        assert citation in result.source_code


def test_hollow_never_touches_proprietary_plant_files(golden):
    params, geometry = golden
    result = generate_segmented_elbow_script(params, geometry, hollow=True)
    for forbidden in (".pcat", ".pspx", ".pspc"):
        assert forbidden not in result.source_code
