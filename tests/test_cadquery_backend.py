"""Tests for the optional CadQuery CAD backend.

Skips entirely (not fails) when cadquery is not installed, since it is a
deliberately optional dependency — see cad/backends/cadquery_backend.py.
"""

import math

import pytest

cadquery = pytest.importorskip("cadquery")

from cad.backends.cadquery_backend import CadQueryElbowBackend  # noqa: E402
from core.geometry.segmented_elbow import build_segmented_elbow_geometry  # noqa: E402
from data.repository import ElbowRepository  # noqa: E402


@pytest.fixture(scope="module")
def repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


def _expected_volume_mm3(elbow) -> float:
    """Rough independent estimate: centerline length x wall cross-section
    area. Only meant to catch gross errors (e.g. solid vs hollow, wrong
    radius), not to match exactly — the true path is slightly longer than
    straight-centerline-segment-lengths since it curves through the gajos.
    """
    geometry = build_segmented_elbow_geometry(elbow)
    centerline_length = sum(p.length_mm for p in geometry.all_pieces)
    cross_section_area = math.pi * ((elbow.od_mm / 2) ** 2 - (elbow.inside_diameter_mm / 2) ** 2)
    return centerline_length * cross_section_area


def test_golden_case_builds_valid_hollow_solid(repository, tmp_path):
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=90)
    e = result.elbow
    geometry = build_segmented_elbow_geometry(e)

    backend = CadQueryElbowBackend()
    solid = backend.build_solid(geometry, od_mm=e.od_mm, id_mm=e.inside_diameter_mm)

    assert solid.val().isValid()
    volume = solid.val().Volume()
    expected = _expected_volume_mm3(e)
    # Generous tolerance: this is a sanity check against a straight-segment
    # approximation, not an exact formula.
    assert math.isclose(volume, expected, rel_tol=0.05)

    step_path = backend.export_step(solid, tmp_path / "elbow.step")
    stl_path = backend.export_stl(solid, tmp_path / "elbow.stl")
    assert step_path.stat().st_size > 0
    assert stl_path.stat().st_size > 0


def test_non_itemized_angle_builds_only_the_two_stubs(repository, tmp_path):
    """30 degrees: no gajo geometry, so the CAD solid is just two separate
    hollow cylinders (not unioned into one continuous body)."""
    result = repository.lookup(dn_mm=110, pn_label="PN10", angle_deg=30)
    e = result.elbow
    geometry = build_segmented_elbow_geometry(e)
    assert geometry.segments is None

    backend = CadQueryElbowBackend()
    solid = backend.build_solid(geometry, od_mm=e.od_mm, id_mm=e.inside_diameter_mm)
    assert solid.val().isValid()
