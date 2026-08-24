import pytest

from core.geometry.segmented_elbow import build_segmented_elbow_geometry
from core.library.component_family import ComponentCategory, ComponentType, get_component_family
from core.library.elbow_registration import SOURCE_GEOMETRY_AVAILABLE, SegmentDecompositionStatus, register_hdpe_segmented_elbow
from core.library.materials import MaterialFamily, get_material
from core.library.parameter_origin import ParameterOrigin
from core.library.standards import StandardDataStatus, get_standard
from data.repository import ElbowRepository


@pytest.fixture(scope="module")
def repository() -> ElbowRepository:
    return ElbowRepository.from_excel()


def test_hdpe_segmented_elbow_is_registered_as_fitting_elbow():
    family = get_component_family("HDPE_SEGMENTED_ELBOW")
    assert family.category is ComponentCategory.FITTING
    assert family.type is ComponentType.ELBOW
    assert family.implemented is True


def test_placeholder_families_are_registered_but_not_implemented():
    for key in ("GENERIC_TEE", "GENERIC_REDUCER", "GENERIC_FLANGE", "GENERIC_VALVE", "GENERIC_SUPPORT", "GENERIC_EQUIPMENT"):
        family = get_component_family(key)
        assert family.implemented is False


def test_unknown_family_key_raises():
    with pytest.raises(KeyError):
        get_component_family("NOT_A_FAMILY")


def test_din_16963_1_is_registered_as_source_data():
    standard = get_standard("DIN_16963_1")
    assert standard.organization.value == "DIN"
    assert standard.code == "16963"
    assert standard.part == "1"
    assert standard.data_status is StandardDataStatus.SOURCE_DATA


def test_asme_b16_9_is_registered_but_data_not_loaded():
    """Registering a standard is not the same as loading its tables."""
    standard = get_standard("ASME_B16_9")
    assert standard.organization.value == "ASME"
    assert standard.data_status is StandardDataStatus.DATA_NOT_LOADED


def test_custom_standard_is_registered():
    standard = get_standard("CUSTOM")
    assert standard.data_status is StandardDataStatus.CUSTOM


def test_unknown_standard_key_raises():
    with pytest.raises(KeyError):
        get_standard("NOT_A_STANDARD")


def test_pe100_material_is_registered_with_no_invented_properties():
    material = get_material("PE100")
    assert material.family is MaterialFamily.HDPE
    assert material.grade == "PE100"
    # No mechanical properties have been loaded — must not be invented.
    assert material.density_kg_m3 is None
    assert material.yield_strength_mpa is None


def test_future_steel_grades_are_registered_placeholders():
    for key in ("ASTM_A36", "ASTM_A106_GR_B", "ASTM_A312_TP304L", "ASTM_A312_TP316L"):
        material = get_material(key)
        assert material.specification is not None
        assert material.yield_strength_mpa is None  # never invented


def test_unknown_material_key_raises():
    with pytest.raises(KeyError):
        get_material("NOT_A_MATERIAL")


def test_parameter_origin_has_the_five_expected_values():
    assert {o.value for o in ParameterOrigin} == {
        "USER_INPUT", "DATABASE_VALUE", "RULE_DERIVED", "GEOMETRY_DERIVED", "SOURCE_DOCUMENT",
    }


# --- Angle configuration labeling (V0.2.2 item 4) --------------------------

@pytest.mark.parametrize("angle,expected_count", [(45, 3), (60, 3), (90, 4)])
def test_itemized_angles_are_registered_as_defined(repository, angle, expected_count):
    result = repository.lookup(dn_mm=315, pn_label="PN10", angle_deg=angle)
    geometry = build_segmented_elbow_geometry(result.elbow)
    registration = register_hdpe_segmented_elbow(result.elbow, geometry)

    assert registration.segment_decomposition_status is SegmentDecompositionStatus.DEFINED
    assert registration.source_geometry_status == SOURCE_GEOMETRY_AVAILABLE
    assert len(geometry.segments) == expected_count


def test_30_degrees_is_source_geometry_available_but_decomposition_not_defined(repository):
    """The 30-degree case must be labeled explicitly, never given an
    invented segment breakdown (no 15-15, no 10-10-10, ...)."""
    result = repository.lookup(dn_mm=110, pn_label="PN10", angle_deg=30)
    geometry = build_segmented_elbow_geometry(result.elbow)
    registration = register_hdpe_segmented_elbow(result.elbow, geometry)

    # R/Le/Z are known for 30 degrees -> source geometry IS available.
    assert registration.source_geometry_status == SOURCE_GEOMETRY_AVAILABLE
    assert result.elbow.radius_mm > 0
    assert result.elbow.z_mm is not None
    # But the segment breakdown is explicitly not defined, and nothing
    # invents one.
    assert registration.segment_decomposition_status is SegmentDecompositionStatus.NOT_DEFINED
    assert geometry.segments is None
