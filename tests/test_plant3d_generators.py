"""V0.3 tests for plant3d/generators/ — P1/P2 port mapping and the
CustomScript generator, using GOLDEN_CASE_DN110_PN10_90.

These tests check three things the V0.3 spec called out explicitly:
  1. The port mapping is a straight read of geometry.ports — no new
     coordinates are computed here.
  2. plant_end_type defaults to REQUIRES_PLANT_CONFIGURATION and is never
     invented, since no real Plant 3D EndType code was confirmed.
  3. The generated .py text is syntactically valid Python and
     deterministic (same inputs -> byte-identical output).
"""

import ast

import pytest

from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from core.library.elbow_registration import register_hdpe_segmented_elbow
from data.repository import ElbowRepository
from plant3d.generators.custom_script_generator import (
    SOURCE_CITATIONS,
    generate_custom_script,
)
from plant3d.generators.port_mapping import (
    PLANT_END_TYPE_REQUIRES_CONFIGURATION,
    map_ports,
)
from tests.golden_cases import GOLDEN_CASE_DN110_PN10_90


@pytest.fixture(scope="module")
def repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


@pytest.fixture(scope="module")
def golden(repository):
    result = repository.lookup(**GOLDEN_CASE_DN110_PN10_90)
    params = result.elbow
    geometry = build_segmented_elbow_geometry(params)
    params.ports = geometry.ports
    registration = register_hdpe_segmented_elbow(params, geometry)
    return params, geometry, registration


def test_map_ports_reads_existing_geometry_ports_unchanged(golden):
    params, geometry, _registration = golden
    mappings = map_ports(geometry)

    assert len(mappings) == len(geometry.ports)
    for mapping, port in zip(mappings, geometry.ports):
        assert mapping.source_port_id == port.id
        assert mapping.position_mm == port.position_mm
        assert mapping.direction == port.direction
        assert mapping.nominal_diameter_mm == port.nominal_diameter_mm
        assert mapping.outside_diameter_mm == port.outside_diameter_mm
        assert mapping.source_end_type == port.end_type.value


def test_map_ports_indexes_from_one_in_port_order(golden):
    _params, geometry, _registration = golden
    mappings = map_ports(geometry)
    assert [m.plant_port_index for m in mappings] == list(range(1, len(mappings) + 1))
    assert mappings[0].source_port_id == "P1"
    assert mappings[1].source_port_id == "P2"


def test_map_ports_end_type_defaults_to_requires_configuration_never_invented(golden):
    """No confirmed Plant 3D EndType code exists for HDPE thermofusion —
    the mapping must never invent one."""
    _params, geometry, _registration = golden
    mappings = map_ports(geometry)
    for mapping in mappings:
        assert mapping.plant_end_type == PLANT_END_TYPE_REQUIRES_CONFIGURATION
        assert mapping.plant_end_type_confirmed is False


def test_map_ports_end_type_override_is_honored(golden):
    _params, geometry, _registration = golden
    mappings = map_ports(geometry, plant_end_type_override="THERMOFUSION_CONFIRMED_EXAMPLE")
    for mapping in mappings:
        assert mapping.plant_end_type == "THERMOFUSION_CONFIRMED_EXAMPLE"
        assert mapping.plant_end_type_confirmed is True


def test_generated_script_is_syntactically_valid_python(golden):
    params, geometry, registration = golden
    result = generate_custom_script(params, geometry, registration)
    ast.parse(result.source_code)  # must not raise SyntaxError


def test_generated_script_is_deterministic(golden):
    params, geometry, registration = golden
    first = generate_custom_script(params, geometry, registration)
    second = generate_custom_script(params, geometry, registration)
    assert first.source_code == second.source_code


def test_generated_script_carries_golden_case_values(golden):
    params, geometry, registration = golden
    result = generate_custom_script(params, geometry, registration)
    assert "110" in result.source_code  # od_mm
    assert "165" in result.source_code  # radius_mm
    assert "315" in result.source_code  # z_mm
    assert "UNCONFIRMED_PLANT3D_ENTRY_POINT" in result.source_code
    assert "NOT_VERIFIED_AGAINST_REAL_PLANT3D_API" in result.source_code
    for citation in SOURCE_CITATIONS:
        assert citation in result.source_code


def test_generated_script_warns_about_unconfirmed_end_type(golden):
    params, geometry, registration = golden
    result = generate_custom_script(params, geometry, registration)
    assert any("REQUIRES_PLANT_CONFIGURATION" in w for w in result.warnings)


def test_generated_script_never_touches_proprietary_plant_files(golden):
    """No .pcat/.pspx/.pspc content or file-write calls may appear in a
    generated CustomScript — those are edited only via Autodesk's own
    Catalog Builder / Spec Editor workflows."""
    params, geometry, registration = golden
    result = generate_custom_script(params, geometry, registration)
    for forbidden in (".pcat", ".pspx", ".pspc"):
        assert forbidden not in result.source_code
